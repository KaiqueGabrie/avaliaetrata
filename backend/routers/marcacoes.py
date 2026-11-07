"""Imagens privadas com contornos propostos por cada IA (nunca aprovados automaticamente)."""
from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database import get_db
from models import Enfermeiro, Imagem, RelatorioIA
from routers.auth import obter_enfermeiro_atual
from routers.analises import obter_analise_autorizada
from services.storage import (
    PREFIXO_STORAGE, bucket, criar_chave, enviar_arquivo, remover_remotos,
    storage_ativo, url_assinada,
)
from services.visualizacao_marcacoes import (
    VisualizacaoMarcacoesService, assinatura_regioes, validar_regioes_persistidas,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/pacientes/{paciente_id}/analises', tags=['Marcações de IA'])
PROVEDORES = ('openai', 'gemini', 'kimi')


def _relatorios(analise_id: int, db: Session) -> dict[str, RelatorioIA]:
    return {
        relatorio.provedor: relatorio
        for relatorio in db.scalars(select(RelatorioIA).where(RelatorioIA.id_analise_fk == analise_id)).all()
        if relatorio.provedor in PROVEDORES
    }


def _imagem_processada(analise_id: int, db: Session) -> str:
    imagem = db.scalar(select(Imagem).where(
        Imagem.id_analise_fk == analise_id,
        Imagem.deleted_at.is_(None),
    ))
    if imagem is None or not imagem.caminho_imagem_marcada:
        raise HTTPException(status_code=404, detail='Fotografia processada não encontrada.')
    return imagem.caminho_imagem_marcada


def _resumo(analise, relatorios: dict[str, RelatorioIA], caminho_processada: str) -> dict:
    cache = (analise.contexto_clinico_json or {}).get('imagens_marcadas_ia') or {}
    if not isinstance(cache, dict):
        cache = {}
    resultado = {}
    for provedor in PROVEDORES:
        relatorio = relatorios.get(provedor)
        if not relatorio:
            resultado[provedor] = {
                'status': 'indisponivel', 'url': None, 'total_regioes': 0,
                'mensagem': 'Relatório desta IA não disponível nesta avaliação.',
            }
            continue
        regioes = validar_regioes_persistidas(relatorio.conteudo_editavel)
        if not regioes:
            resultado[provedor] = {
                'status': 'sem_regioes', 'url': None, 'total_regioes': 0,
                'mensagem': 'A IA não forneceu polígonos com geometria válida para desenhar.',
            }
            continue
        assinatura = assinatura_regioes(regioes, caminho_processada)
        registro = cache.get(provedor)
        caminho = registro.get('caminho') if isinstance(registro, dict) else None
        valido = (
            isinstance(registro, dict)
            and registro.get('assinatura') == assinatura
            and isinstance(caminho, str)
            and caminho.startswith(PREFIXO_STORAGE + 'marcacoes/')
        )
        url = url_assinada(caminho[len(PREFIXO_STORAGE):]) if valido else None
        resultado[provedor] = {
            'status': 'pronta' if url else 'pendente',
            'url': url,
            'total_regioes': len(regioes),
            'mensagem': (
                'Proposta visual não validada pelo enfermeiro.' if url
                else 'Há polígonos propostos; gere a imagem marcada para visualizar.'
            ),
        }
    return resultado


@router.get('/{analise_id}/marcacoes')
def consultar_marcacoes(
    paciente_id: int, analise_id: int, response: Response,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    analise = obter_analise_autorizada(paciente_id, analise_id, enfermeiro, db)
    caminho = _imagem_processada(analise_id, db)
    response.headers['Cache-Control'] = 'private, no-store'
    return {
        'analise_id': analise_id,
        'marcacoes_por_ia': _resumo(analise, _relatorios(analise_id, db), caminho),
        'aviso': 'Marcações propostas por IA; não constituem segmentação ou validação clínica.',
    }


@router.post('/{analise_id}/marcacoes/gerar')
def gerar_marcacoes(
    paciente_id: int, analise_id: int, response: Response,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    analise = obter_analise_autorizada(paciente_id, analise_id, enfermeiro, db)
    caminho = _imagem_processada(analise_id, db)
    relatorios = _relatorios(analise_id, db)
    if not storage_ativo():
        raise HTTPException(status_code=503, detail='Armazenamento privado indisponível para gerar marcações.')
    if not caminho.startswith(PREFIXO_STORAGE + 'processadas/'):
        raise HTTPException(status_code=409, detail='Fotografia processada não está no armazenamento privado.')

    contexto = dict(analise.contexto_clinico_json or {})
    cache = dict(contexto.get('imagens_marcadas_ia') or {})
    novas_chaves: list[str] = []
    houve_alteracao = False
    try:
        with TemporaryDirectory(prefix='avalia_marcacoes_') as pasta:
            origem = Path(pasta) / 'fotografia_processada.png'
            # A mesma imagem processada (sem recorte) serve como referência a todas as IAs.
            imagem_baixada = False
            for provedor in PROVEDORES:
                relatorio = relatorios.get(provedor)
                if not relatorio:
                    continue
                regioes = validar_regioes_persistidas(relatorio.conteudo_editavel)
                if not regioes:
                    continue
                assinatura = assinatura_regioes(regioes, caminho)
                existente = cache.get(provedor)
                if (isinstance(existente, dict)
                        and existente.get('assinatura') == assinatura
                        and isinstance(existente.get('caminho'), str)
                        and existente['caminho'].startswith(PREFIXO_STORAGE + 'marcacoes/')):
                    continue
                if not imagem_baixada:
                    origem.write_bytes(bucket().download(caminho[len(PREFIXO_STORAGE):]))
                    imagem_baixada = True
                saida = Path(pasta) / f'marcacao_{provedor}.png'
                VisualizacaoMarcacoesService.gerar(str(origem), regioes, str(saida), provedor)
                chave = criar_chave('marcacoes', enfermeiro.id_enfermeiro, paciente_id, analise_id, '.png')
                caminho_salvo = enviar_arquivo(saida, chave)
                novas_chaves.append(chave)
                cache[provedor] = {'caminho': caminho_salvo, 'assinatura': assinatura}
                houve_alteracao = True
        if houve_alteracao:
            contexto['imagens_marcadas_ia'] = cache
            analise.contexto_clinico_json = contexto
            db.commit()
            db.refresh(analise)
    except Exception as erro:
        db.rollback()
        remover_remotos(novas_chaves)
        logger.exception('Falha ao gerar marcações propostas da avaliação %s.', analise_id)
        raise HTTPException(status_code=500, detail='Não foi possível gerar as imagens marcadas. Consulte os logs do backend.') from erro
    response.headers['Cache-Control'] = 'private, no-store'
    return {
        'analise_id': analise_id,
        'marcacoes_por_ia': _resumo(analise, relatorios, caminho),
        'aviso': 'Contornos automáticos propostos, não revisados nem aprovados pelo profissional.',
    }

# ============================================================
# Etapa 2F — edição manual e validação das regiões pelo enfermeiro
# Não modifica a resposta original das IAs ou o relatório T.I.M.E.S.
# ============================================================
from datetime import datetime, timezone
# Endpoints adicionais de revisao profissional
from models import LogAuditoria
from schemas.revisao_marcacoes import AprovarRevisao, SalvarRevisao
from services.segmentacao_profissional import (
    validar_geometrias, gerar_visualizacao,
)


def _registro_revisao(analise) -> dict | None:
    valor = (analise.contexto_clinico_json or {}).get('revisao_marcacoes_profissional')
    return valor if isinstance(valor, dict) else None


def _resposta_revisao(registro: dict | None) -> dict | None:
    if registro is None:
        return None
    caminho = registro.get('caminho_imagem')
    url = None
    if isinstance(caminho, str) and caminho.startswith(PREFIXO_STORAGE + 'revisadas/'):
        url = url_assinada(caminho[len(PREFIXO_STORAGE):])
    return {
        'versao': registro.get('versao', 0),
        'status': registro.get('status', 'rascunho'),
        'provedor_base': registro.get('provedor_base', 'manual'),
        'regioes': registro.get('regioes', []),
        'estatisticas': registro.get('estatisticas'),
        'imagem_url': url,
        'atualizado_em': registro.get('atualizado_em'),
        'aprovado_em': registro.get('aprovado_em'),
        'observacao': 'Regiões revistas por profissional. Percentuais representam pixels, não área física.',
    }


def _regioes_propostas(relatorios: dict[str, RelatorioIA]) -> dict:
    resultado = {}
    for provedor in PROVEDORES:
        relatorio = relatorios.get(provedor)
        itens = validar_regioes_persistidas(relatorio.conteudo_editavel) if relatorio else []
        resultado[provedor] = [
            {
                'id': f'{provedor}_{i}',
                'classe': 'contorno_lesao' if r.identificador.startswith('contorno_visual_lesao-') else 'nao_classificado',
                'origem': 'ia',
                'descricao': f'{r.rotulo}: {r.descricao}'[:240],
                'pontos': [p.model_dump() for p in r.pontos],
            }
            for i, r in enumerate(itens, start=1)
        ]
    return resultado


def _auditar_revisao(db: Session, enfermeiro_id: int, analise_id: int, acao: str, versao: int) -> None:
    db.add(LogAuditoria(
        id_enfermeiro_fk=enfermeiro_id,
        acao=acao,
        entidade='analise',
        registro_id=str(analise_id),
        detalhes={'versao_revisao_marcacoes': versao, 'origem': 'editor_marcacoes'},
    ))


def _persistir_revisao(
    *, analise, paciente_id: int, analise_id: int, enfermeiro: Enfermeiro,
    db: Session, regioes, provedor: str, versao: int, aprovado: bool,
    aprovado_em: str | None = None,
) -> dict:
    if not storage_ativo():
        raise HTTPException(status_code=503, detail='Armazenamento privado indisponível.')
    caminho = _imagem_processada(analise_id, db)
    if not caminho.startswith(PREFIXO_STORAGE + 'processadas/'):
        raise HTTPException(status_code=409, detail='A fotografia processada não está no armazenamento privado.')
    nova_chave = None
    try:
        with TemporaryDirectory(prefix='avalia_revisao_') as pasta:
            origem = Path(pasta) / 'processada.png'
            origem.write_bytes(bucket().download(caminho[len(PREFIXO_STORAGE):]))
            destino = Path(pasta) / 'revisada.png'
            _, estatisticas = gerar_visualizacao(
                str(origem), regioes, str(destino), aprovado=aprovado, provedor=provedor,
            )
            nova_chave = criar_chave('revisadas', enfermeiro.id_enfermeiro, paciente_id, analise_id, '.png')
            caminho_salvo = enviar_arquivo(destino, nova_chave)
        contexto = dict(analise.contexto_clinico_json or {})
        anterior = _registro_revisao(analise)
        historico = list(contexto.get('historico_revisoes_marcacoes') or [])
        if anterior:
            # Preserva o histórico de versões e os caminhos das imagens antigas.
            historico.append(anterior)
        instante = datetime.now(timezone.utc).isoformat()
        registro = {
            'versao': versao,
            'status': 'aprovado' if aprovado else 'rascunho',
            'provedor_base': provedor,
            'regioes': [r.model_dump(mode='json') for r in regioes],
            'estatisticas': estatisticas,
            'caminho_imagem': caminho_salvo,
            'imagem_referencia': caminho,
            'atualizado_em': instante,
            'aprovado_em': aprovado_em or (instante if aprovado else None),
            'enfermeiro_id': enfermeiro.id_enfermeiro,
        }
        contexto['revisao_marcacoes_profissional'] = registro
        contexto['historico_revisoes_marcacoes'] = historico
        analise.contexto_clinico_json = contexto
        flag_modified(analise, "contexto_clinico_json")
        _auditar_revisao(db, enfermeiro.id_enfermeiro, analise_id,
                         'aprovar_marcacoes' if aprovado else 'editar_marcacoes', versao)
        db.commit()
        # Confere a persistência real após o commit, não apenas a resposta em memória.
        db.refresh(analise)
        confirmado = _registro_revisao(analise)
        if not confirmado or int(confirmado.get('versao', -1)) != versao:
            logger.error('Revisão %s não confirmada no banco após commit da análise %s.', versao, analise_id)
            raise HTTPException(status_code=500, detail='A revisão não pôde ser confirmada no banco. Atualize e consulte o histórico.')
        return confirmado
    except ValueError as erro:
        db.rollback()
        if nova_chave:
            remover_remotos([nova_chave])
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    except Exception as erro:
        db.rollback()
        if nova_chave:
            remover_remotos([nova_chave])
        logger.exception('Falha ao salvar revisão manual da avaliação %s', analise_id)
        raise HTTPException(status_code=500, detail='Falha ao salvar revisão. Consulte os logs do backend.') from erro


@router.get('/{analise_id}/marcacoes/editor')
def consultar_editor_marcacoes(
    paciente_id: int, analise_id: int, response: Response,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    analise = obter_analise_autorizada(paciente_id, analise_id, enfermeiro, db)
    caminho = _imagem_processada(analise_id, db)
    url = url_assinada(caminho[len(PREFIXO_STORAGE):]) if caminho.startswith(PREFIXO_STORAGE) else None
    if not url:
        raise HTTPException(status_code=503, detail='Fotografia processada indisponível. Atualize a página.')
    registro = _registro_revisao(analise)
    if registro and registro.get('imagem_referencia') != caminho:
        raise HTTPException(status_code=409, detail='A fotografia mudou; a revisão anterior não pode ser aplicada a esta imagem.')
    response.headers['Cache-Control'] = 'private, no-store'
    return {
        'analise_id': analise_id,
        'imagem_processada_url': url,
        'regioes_propostas_ia': _regioes_propostas(_relatorios(analise_id, db)),
        'revisao': _resposta_revisao(registro),
        'aviso': 'As classificações dos tecidos são decisões do profissional, não diagnósticos automáticos.',
    }


@router.put('/{analise_id}/marcacoes/editor')
def salvar_editor_marcacoes(
    paciente_id: int, analise_id: int, dados: SalvarRevisao, response: Response,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    analise = obter_analise_autorizada(paciente_id, analise_id, enfermeiro, db)
    atual = _registro_revisao(analise)
    if atual and atual.get('imagem_referencia') != _imagem_processada(analise_id, db):
        raise HTTPException(status_code=409, detail='A fotografia foi substituída; recarregue antes de editar.')
    if atual and atual.get('status') == 'aprovado':
        raise HTTPException(status_code=409, detail='Imagem já aprovada. Uma nova revisão exige fluxo de retificação auditável.')
    versao = int(atual.get('versao', 0)) if atual else 0
    if versao != dados.revisao_esperada:
        raise HTTPException(status_code=409, detail='A revisão foi modificada. Recarregue antes de salvar.')
    if dados.provedor_base != 'manual' and dados.provedor_base not in _relatorios(analise_id, db):
        raise HTTPException(status_code=422, detail='O relatório de IA escolhido não existe nesta avaliação.')
    try:
        validar_geometrias(dados.regioes)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    registro = _persistir_revisao(
        analise=analise, paciente_id=paciente_id, analise_id=analise_id,
        enfermeiro=enfermeiro, db=db, regioes=dados.regioes,
        provedor=dados.provedor_base, versao=versao + 1, aprovado=False,
    )
    response.headers['Cache-Control'] = 'private, no-store'
    return {'revisao': _resposta_revisao(registro)}


@router.post('/{analise_id}/marcacoes/editor/aprovar')
def aprovar_editor_marcacoes(
    paciente_id: int, analise_id: int, dados: AprovarRevisao, response: Response,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    analise = obter_analise_autorizada(paciente_id, analise_id, enfermeiro, db)
    atual = _registro_revisao(analise)
    if atual and atual.get('imagem_referencia') != _imagem_processada(analise_id, db):
        raise HTTPException(status_code=409, detail='A fotografia foi substituída; recarregue antes de aprovar.')
    if not atual or atual.get('status') == 'aprovado':
        raise HTTPException(status_code=409, detail='Não existe rascunho pendente para aprovação.')
    if int(atual.get('versao', 0)) != dados.revisao_esperada:
        raise HTTPException(status_code=409, detail='Rascunho alterado. Recarregue antes de aprovar.')
    if not any(r.get('classe') == 'contorno_lesao' for r in atual.get('regioes', [])):
        raise HTTPException(status_code=422, detail='Delimite o contorno da lesão antes de aprovar.')
    from schemas.revisao_marcacoes import RegiaoManual
    regioes = [RegiaoManual.model_validate(r) for r in atual['regioes']]
    registro = _persistir_revisao(
        analise=analise, paciente_id=paciente_id, analise_id=analise_id,
        enfermeiro=enfermeiro, db=db, regioes=regioes,
        provedor=atual['provedor_base'], versao=int(atual['versao']) + 1,
        aprovado=True,
    )
    response.headers['Cache-Control'] = 'private, no-store'
    return {'revisao': _resposta_revisao(registro)}


@router.post('/{analise_id}/marcacoes/editor/retificar')
def retificar_editor_marcacoes(
    paciente_id: int, analise_id: int, dados: AprovarRevisao, response: Response,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    """Abre nova versão sem sobrescrever a versão anteriormente aprovada."""
    analise = obter_analise_autorizada(paciente_id, analise_id, enfermeiro, db)
    atual = _registro_revisao(analise)
    if atual and atual.get('imagem_referencia') != _imagem_processada(analise_id, db):
        raise HTTPException(status_code=409, detail='A fotografia foi substituída; recarregue antes de retificar.')
    if not atual or atual.get('status') != 'aprovado':
        raise HTTPException(status_code=409, detail='Não existe imagem aprovada para retificar.')
    if int(atual.get('versao', 0)) != dados.revisao_esperada:
        raise HTTPException(status_code=409, detail='A revisão foi alterada. Recarregue antes de retificar.')
    contexto = dict(analise.contexto_clinico_json or {})
    historico = list(contexto.get('historico_revisoes_marcacoes') or [])
    historico.append(atual)
    novo = {
        **atual,
        'versao': int(atual['versao']) + 1,
        'status': 'rascunho',
        'aprovado_em': None,
        'caminho_imagem': None,
        'atualizado_em': datetime.now(timezone.utc).isoformat(),
        'retificacao_da_versao': atual['versao'],
    }
    contexto['historico_revisoes_marcacoes'] = historico
    contexto['revisao_marcacoes_profissional'] = novo
    analise.contexto_clinico_json = contexto
    flag_modified(analise, 'contexto_clinico_json')
    _auditar_revisao(db, enfermeiro.id_enfermeiro, analise_id, 'retificar_marcacoes', novo['versao'])
    try:
        db.commit()
    except Exception as erro:
        db.rollback()
        logger.exception('Falha ao abrir retificação da avaliação %s', analise_id)
        raise HTTPException(status_code=500, detail='Não foi possível abrir uma retificação.') from erro
    response.headers['Cache-Control'] = 'private, no-store'
    return {'revisao': _resposta_revisao(novo)}
