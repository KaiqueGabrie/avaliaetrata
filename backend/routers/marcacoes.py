"""Imagens privadas com contornos propostos por cada IA (nunca aprovados automaticamente)."""
from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

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
