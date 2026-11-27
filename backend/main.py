"""API Avalia & Trata - backend/main.py (versao 2.5.0)."""

import os
import logging
from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Analise, Enfermeiro, Imagem, RelatorioIA
from models import Paciente
from routers.auth import router as auth_router, obter_enfermeiro_atual
from routers.pacientes import router as pacientes_router, obter_anamnese_ativa
from routers.consentimento import router as consentimento_router
from routers.analises import router as analises_router
from routers.relatorios_persistentes import router as relatorios_persistentes_router
from routers.comparacoes import router as comparacoes_router, salvar_comparacao, ComparacaoMultimodal, garantir_tabela
from routers.marcacoes import router as marcacoes_router
from services.contexto_anamnese import montar_contexto_anamnese
from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
    ResultadoProvedor,
    ResultadoAnaliseMultimodal,
    RespostaEstruturadaModelo,
)
from services.image_processing import ImageProcessingService
from services.medidas_geometricas import calcular_estimativas
from services.storage import PREFIXO_STORAGE, baixar_original
from services.multimodal.orchestrator import MultimodalOrchestrator
from services.multimodal.comparador import comparar_resultados
from services.multimodal.relatorio import gerar_relatorios

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="API Avalia & Trata",
    description=(
        "Sistema de apoio a documentacao e analise descritiva de feridas. "
        "Resultados automatizados exigem validacao profissional."
    ),
    version="2.5.0",
)

# Cada router e registrado uma unica vez.
app.include_router(auth_router)
app.include_router(pacientes_router)
app.include_router(consentimento_router)
app.include_router(analises_router)
app.include_router(relatorios_persistentes_router)
app.include_router(comparacoes_router)
app.include_router(marcacoes_router)

# Origens permitidas para o frontend.
origens_locais = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:19006",
]

origens_producao = [
    origem.strip().rstrip("/")
    for origem in os.getenv("FRONTEND_URL", "").split(",")
    if origem.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_locais + origens_producao,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nao publicar uploads/processed como arquivos estaticos sem controle de acesso.
orquestrador_multimodal = MultimodalOrchestrator()


def texto_opcional(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    return valor.strip() or None


def converter_odor(valor: Optional[str]) -> Optional[bool]:
    valor = (valor or "").strip().lower()
    if valor in ("sim", "true", "1", "yes"):
        return True
    if valor in ("nao", "não", "false", "0", "no"):
        return False
    if valor in ("", "null", "none", "nao informado", "não informado"):
        return None
    raise HTTPException(
        status_code=400,
        detail="Valor invalido para odor. Use sim, nao ou vazio.",
    )


def montar_dados_clinicos(
    localizacao: str,
    comprimento: str,
    largura: str,
    tipoExsudato: str,
    odor: str,
    nivelDor: str,
    queixaPrincipal: str,
    observacoes: str,
) -> DadosClinicosInput:
    localizacao = localizacao.strip()
    if not localizacao:
        raise HTTPException(
            status_code=400,
            detail="A localizacao anatomica e obrigatoria.",
        )
    return DadosClinicosInput(
        localizacao=localizacao,
        comprimento=texto_opcional(comprimento),
        largura=texto_opcional(largura),
        tipoExsudato=texto_opcional(tipoExsudato),
        odor=converter_odor(odor),
        nivelDor=texto_opcional(nivelDor),
        queixaPrincipal=texto_opcional(queixaPrincipal),
        observacoes=texto_opcional(observacoes),
    )


def obter_analise_autorizada(
    analise_id: int,
    enfermeiro: Enfermeiro,
    db: Session,
) -> Analise:
    analise = db.scalar(
        select(Analise).where(
            Analise.id_analise == analise_id,
            Analise.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
            Analise.deleted_at.is_(None),
            Analise.id_paciente_fk.in_(select(Paciente.id_paciente)
                .where(
                    Paciente.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
                    Paciente.deleted_at.is_(None),
                )
            ),
        )
    )
    if analise is None:
        raise HTTPException(
            status_code=404,
            detail="Analise nao encontrada ou acesso nao autorizado.",
        )
    return analise


def resolver_caminho_imagem(caminho: str, pasta_temporaria: Path) -> str:
    """Busca imagem privada no Supabase ou valida arquivo local antigo."""
    if caminho.startswith(PREFIXO_STORAGE):
        chave = caminho[len(PREFIXO_STORAGE):]
        extensao = Path(chave).suffix.lower()
        if extensao not in (".jpg", ".jpeg", ".png", ".webp"):
            raise HTTPException(status_code=400, detail="Formato de imagem invalido.")
        destino = pasta_temporaria / f"{uuid4().hex}{extensao}"
        try:
            baixar_original(chave, destino)
        except Exception as erro:
            logger.exception("Falha ao recuperar imagem privada do Supabase.")
            raise HTTPException(
                status_code=502,
                detail="Nao foi possivel recuperar a imagem armazenada.",
            ) from erro
        return str(destino)

    valor = Path(caminho)
    if valor.is_absolute():
        candidato = valor.resolve()
    else:
        candidato = (BASE_DIR / valor).resolve()
        if not candidato.is_file():
            candidato = (BASE_DIR.parent / valor).resolve()
    if not candidato.is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(
            status_code=400,
            detail="O caminho da imagem nao pertence a pasta autorizada.",
        )
    if not candidato.is_file():
        raise HTTPException(
            status_code=404,
            detail="Arquivo da imagem original nao encontrado.",
        )
    return str(candidato)


def obter_pasta_temporaria():
    """Limpa imagens baixadas e processadas ao terminar a requisicao."""
    with TemporaryDirectory(prefix="avalia_trata_") as pasta:
        yield Path(pasta)


def obter_imagem_analise(analise_id: int, db: Session) -> Imagem:
    imagem = db.scalar(
        select(Imagem).where(
            Imagem.id_analise_fk == analise_id,
            Imagem.deleted_at.is_(None),
        )
    )
    if imagem is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Esta analise ainda nao possui imagem. "
                "Envie uma imagem pela rota de analises primeiro."
            ),
        )
    return imagem


def gerar_comparacao_segura(resultado) -> dict:
    try:
        return comparar_resultados(resultado).model_dump(mode="json")
    except Exception:
        logger.exception("Falha na comparacao multimodal.")
        return {
            "erro": "A comparacao automatica nao foi concluida.",
            "provedores_comparados": [],
            "componentes": {},
            "validacao_profissional_necessaria": True,
        }


def salvar_relatorios_no_banco(
    analise_id: int,
    conjunto,
    db: Session,
    provedores_com_sucesso: set[str],
) -> dict:
    """Persiste o conteudo interno dos relatorios sem sobrescrever revisoes."""
    salvos = []
    existentes = []
    nao_salvos = []

    for provedor, relatorio in conjunto.relatorios.items():
        if provedor not in ("openai", "gemini", "kimi"):
            continue
        if provedor not in provedores_com_sucesso:
            nao_salvos.append(provedor)
            continue

        existente = db.scalar(
            select(RelatorioIA).where(
                RelatorioIA.id_analise_fk == analise_id,
                RelatorioIA.provedor == provedor,
            )
        )
        if existente is not None:
            existentes.append(provedor)
            continue

        dados_relatorio = relatorio.model_dump(mode="json")
        conteudo_original = dados_relatorio.get("conteudo_original")
        conteudo_editavel = dados_relatorio.get("conteudo_editavel")
        alertas = dados_relatorio.get("alertas_validacao") or []

        if (
            not isinstance(conteudo_original, dict)
            or not isinstance(conteudo_editavel, dict)
            or not isinstance(alertas, (list, dict))
        ):
            logger.warning("Relatorio %s com estrutura inesperada.", provedor)
            nao_salvos.append(provedor)
            continue

        registro = RelatorioIA(
            id_relatorio=str(uuid4()),
            id_analise_fk=analise_id,
            provedor=provedor,
            conteudo_original=deepcopy(conteudo_original),
            conteudo_editavel=deepcopy(conteudo_editavel),
            status="gerado",
            alertas_validacao=deepcopy(alertas),
            revisao_profissional_necessaria=True,
        )
        db.add(registro)
        salvos.append(provedor)

    try:
        db.commit()
    except IntegrityError as erro:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflito ao salvar relatorios. Consulte os ja existentes.",
        ) from erro
    except Exception as erro:
        db.rollback()
        logger.exception("Erro ao salvar relatorios no MySQL.")
        raise HTTPException(
            status_code=500,
            detail="Falha ao salvar relatorios no banco de dados.",
        ) from erro

    return {
        "salvos": salvos,
        "ja_existentes": existentes,
        "nao_salvos": nao_salvos,
    }


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "API Avalia & Trata operacional.",
        "versao": "2.5.0",
        "modulos": {
            "autenticacao": True,
            "pacientes": True,
            "anamnese": True,
            "analises": True,
            "opencv": True,
            "marcacoes_ia": True,
            "estimativas_geometricas": True,
            "multimodal": True,
            "comparador": True,
            "relatorios_mysql": True,
            "comparacoes_mysql": True,
            "edicao_relatorios": True,
            "historico_edicoes": True,
            "aprovacao_profissional": True,
        },
    }


@app.post(
    "/analises/{analise_id}/executar-multimodal",
    tags=["Analise Multimodal"],
)
def executar_analise_multimodal(
    analise_id: int,
    localizacao: str = Form(...),
    comprimento: str = Form(""),
    largura: str = Form(""),
    tipoExsudato: str = Form(""),
    odor: str = Form(""),
    nivelDor: str = Form(""),
    queixaPrincipal: str = Form(""),
    observacoes: str = Form(""),
    provedor: Literal["gemini", "openai", "kimi", "todos"] = Form("gemini"),
    incluir_anamnese: bool = Form(False),
    confirmar_envio_ia: bool = Form(False),
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
    pasta_temporaria: Path = Depends(obter_pasta_temporaria),
):
    analise = obter_analise_autorizada(analise_id, enfermeiro, db)

    if incluir_anamnese is True and confirmar_envio_ia is not True:
        raise HTTPException(
            status_code=403,
            detail="Confirme o envio do contexto clinico aos provedores.",
        )

    imagem = obter_imagem_analise(analise_id, db)
    caminho_original = resolver_caminho_imagem(
        imagem.caminho_imagem_original, pasta_temporaria
    )

    try:
        dados_clinicos = montar_dados_clinicos(
            localizacao=localizacao,
            comprimento=comprimento,
            largura=largura,
            tipoExsudato=tipoExsudato,
            odor=odor,
            nivelDor=nivelDor,
            queixaPrincipal=queixaPrincipal,
            observacoes=observacoes,
        )
    except ValidationError as erro:
        raise HTTPException(
            status_code=400,
            detail=erro.errors(include_url=False, include_context=False),
        ) from erro

    contexto_anamnese = None

    if incluir_anamnese is True:
        anamnese = obter_anamnese_ativa(
            db,
            analise.id_paciente_fk,
        )

        contexto_anamnese = montar_contexto_anamnese(
            anamnese
        )

        if contexto_anamnese is None:
            raise HTTPException(
                status_code=409,
                detail="Anamnese indisponivel ou sem dados estruturados.",
            )

        dados_clinicos.anamnese_contexto = contexto_anamnese

    mapa_provedores = {
        "gemini": ["gemini"],
        "openai": ["openai"],
        "kimi": ["kimi"],
        "todos": ["gemini", "openai", "kimi"],
    }
    provedores_desejados = mapa_provedores[provedor]

    try:
        resultado_opencv = ImageProcessingService.processar_imagem_lesao(
            caminho_imagem_original=caminho_original,
            pasta_destino_processadas=str(pasta_temporaria),
        )
        caminho_processado = str(
            pasta_temporaria / resultado_opencv["nome_arquivo_processado"]
        )
    except Exception as erro:
        logger.exception("Falha no processamento OpenCV.")
        raise HTTPException(
            status_code=500,
            detail="Falha no processamento tecnico da imagem.",
        ) from erro

    avaliacao_id = uuid4().hex
    try:
        entrada = AnaliseMultimodalInput(
            avaliacao_id=avaliacao_id,
            caminho_imagem_original=caminho_original,
            caminho_imagem_processada=caminho_processado,
            dimensoes_originais=resultado_opencv["dimensoes_originais"],
            dimensoes_processadas=resultado_opencv["dimensoes_processadas"],
            analise_tecnica=AnaliseTecnicaOpenCVInput(
                brilho_medio=resultado_opencv["analise_tecnica"]["brilho_medio"],
                contraste_global=resultado_opencv["analise_tecnica"]["contraste_global"],
            ),
            dados_clinicos=dados_clinicos,
        )
    except (ValidationError, ValueError) as erro:
        logger.exception("Falha na montagem dos dados multimodais.")
        raise HTTPException(
            status_code=400,
            detail="Dados de entrada multimodal invalidos.",
        ) from erro

    # Preserva o contexto efetivamente utilizado nesta tentativa.
    if contexto_anamnese is not None:
        contexto_atual = dict(
            analise.contexto_clinico_json or {}
        )

        registros = dict(
            contexto_atual.get("contextos_anamnese_ia") or {}
        )

        registros[avaliacao_id] = {
            "dados": contexto_anamnese.model_dump(mode="json"),
            "provedores": provedores_desejados,
        }

        contexto_atual["contextos_anamnese_ia"] = registros
        analise.contexto_clinico_json = contexto_atual

        db.commit()

    contexto_atual = dict(
        analise.contexto_clinico_json or {}
    )

    entradas = dict(
        contexto_atual.get("entradas_multimodais") or {}
    )

    entradas[avaliacao_id] = {
        "dados": dados_clinicos.model_dump(mode="json"),
        "provedores": provedores_desejados,
        "imagem_original": imagem.caminho_imagem_original,
    }

    contexto_atual["entradas_multimodais"] = entradas
    analise.contexto_clinico_json = contexto_atual
    db.commit()

    try:
        resultado = orquestrador_multimodal.executar_analise_comparativa(
            input_data=entrada,
            provedores_desejados=provedores_desejados,
        )
    except Exception as erro:
        logger.exception("Falha na execucao multimodal.")
        raise HTTPException(
            status_code=502,
            detail="Falha ao executar os provedores de IA. Consulte o terminal.",
        ) from erro

    comparacao = gerar_comparacao_segura(resultado)

    # So persistir respostas realmente concluidas, nunca resultados de erro.
    provedores_com_sucesso = {
        nome
        for nome, resposta in resultado.resultados.items()
        if resposta.sucesso and resposta.resposta is not None
    }

    if not provedores_com_sucesso:
        return {
            "sucesso": False,
            "analise_id": analise_id,
            "avaliacao_id": avaliacao_id,
            "provedores_solicitados": provedores_desejados,
            "analise_multimodal": resultado.model_dump(mode="json"),
            "comparacao_multimodal": comparacao,
            "persistencia_mysql": {
                "salvos": [],
                "ja_existentes": [],
                "nao_salvos": provedores_desejados,
            },
            "relatorios_disponiveis": [],
            "mensagem": "Nenhum provedor concluiu a analise.",
        }

    try:
        conjunto = gerar_relatorios(
            resultado=resultado,
            avaliacao_id=avaliacao_id,
        )
    except Exception as erro:
        logger.exception("Falha na geracao dos relatorios.")
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar relatorios individuais.",
        ) from erro

    persistencia = salvar_relatorios_no_banco(
        analise_id=analise_id,
        conjunto=conjunto,
        db=db,
        provedores_com_sucesso=provedores_com_sucesso,
    )

    persistencia_comparacao = salvar_comparacao(
        db=db,
        analise_id=analise_id,
        avaliacao_id=avaliacao_id,
        comparacao=comparacao,
        provedores_com_sucesso=provedores_com_sucesso,
    )

    return {
        "sucesso": resultado.sucesso_geral,
        "analise_id": analise_id,
        "avaliacao_id": avaliacao_id,
        "provedor_selecionado": provedor,
        "provedores_solicitados": provedores_desejados,
        "analise_multimodal": resultado.model_dump(mode="json"),
        "comparacao_multimodal": comparacao,
        "medidas_geometricas": calcular_estimativas(dados_clinicos.comprimento, dados_clinicos.largura),
        "persistencia_mysql": persistencia,
        "persistencia_comparacao": persistencia_comparacao,
        "relatorios_disponiveis": list(conjunto.relatorios.keys()),
        "mensagem": (
            "Processamento concluido. Consulte os relatorios persistentes "
            "para verificar os resultados."
        ),
        "aviso": (
            "Resultados auxiliares, sujeitos a erro e a revisao profissional. "
            "A imagem nao confirma isoladamente diagnostico ou medidas fisicas."
        ),
    }


# ============================================================
# ETAPA 05A - RECUPERACAO INDIVIDUAL DE RELATORIOS
# ============================================================

PROVEDORES_RECUPERACAO = (
    "openai",
    "gemini",
    "kimi",
)


def consultar_comparacao_recuperacao(analise_id, db):
    garantir_tabela(db)

    return db.scalar(
        select(ComparacaoMultimodal)
        .where(
            ComparacaoMultimodal.id_analise_fk == analise_id
        )
        .order_by(
            ComparacaoMultimodal.criado_em.desc(),
            ComparacaoMultimodal.id_comparacao.desc(),
        )
        .limit(1)
    )


def consultar_relatorios_recuperacao(analise_id, db):
    registros = db.scalars(
        select(RelatorioIA).where(
            RelatorioIA.id_analise_fk == analise_id
        )
    ).all()

    return {
        registro.provedor: registro
        for registro in registros
    }


def estado_falha_provedor(resumo):
    mensagem = str(
        resumo.get("mensagem_erro") or ""
    ).casefold()

    indicadores_timeout = (
        "timeout",
        "tempo limite",
        "timed out",
        "excedeu o limite",
        "tempo de espera",
    )

    if any(
        indicador in mensagem
        for indicador in indicadores_timeout
    ):
        return "timeout"

    return "falha"


def recuperar_entrada_original(
    analise,
    imagem,
    comparacao,
):
    if comparacao is None:
        return None

    contexto = analise.contexto_clinico_json or {}

    conteudo = comparacao.conteudo or {}

    origem = (
        conteudo.get("origem_reprocessamento")
        or comparacao.avaliacao_id
    )

    entradas = contexto.get("entradas_multimodais") or {}

    registro = entradas.get(origem)

    if registro is not None:
        if (
            registro.get("imagem_original")
            != imagem.caminho_imagem_original
        ):
            return None

        try:
            dados = DadosClinicosInput.model_validate(
                registro["dados"]
            )
        except (ValidationError, KeyError, TypeError):
            return None

        return {
            "dados": dados,
            "provedores": registro.get("provedores") or [],
            "origem": origem,
            "reconstruido": False,
        }

    # Compatibilidade com a avaliacao 29 e outras
    # avaliacoes anteriores a esta atualizacao.
    #
    # Somente permite recuperar quando existe um
    # contexto de anamnese inequivocamente associado
    # a execucao original.

    contextos = contexto.get(
        "contextos_anamnese_ia"
    ) or {}

    registro_anamnese = contextos.get(origem)

    if (
        len(contextos) != 1
        or not isinstance(registro_anamnese, dict)
    ):
        return None

    try:
        dados = montar_dados_clinicos(
            localizacao=str(
                contexto.get("localizacao") or ""
            ),
            comprimento=str(
                contexto.get("comprimento") or ""
            ),
            largura=str(
                contexto.get("largura") or ""
            ),
            tipoExsudato=str(
                contexto.get("tipoExsudato") or ""
            ),
            odor=str(
                contexto.get("odor")
                if contexto.get("odor") is not None
                else ""
            ),
            nivelDor=str(
                contexto.get("nivelDor")
                if contexto.get("nivelDor") is not None
                else ""
            ),
            queixaPrincipal=analise.queixa_principal or "",
            observacoes=analise.observacoes_clinicas or "",
        )

        dados = DadosClinicosInput.model_validate({
            **dados.model_dump(mode="json"),
            "anamnese_contexto": registro_anamnese["dados"],
        })

    except (
        ValidationError,
        HTTPException,
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    return {
        "dados": dados,
        "provedores": registro_anamnese.get(
            "provedores"
        ) or [],
        "origem": origem,
        "reconstruido": True,
    }


@app.get(
    "/analises/{analise_id}/disponibilidade-ias",
    tags=["Analise Multimodal"],
)
def consultar_disponibilidade_ias(
    analise_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):
    analise = obter_analise_autorizada(
        analise_id,
        enfermeiro,
        db,
    )

    relatorios = consultar_relatorios_recuperacao(
        analise_id,
        db,
    )

    comparacao = consultar_comparacao_recuperacao(
        analise_id,
        db,
    )

    conteudo = (
        comparacao.conteudo or {}
        if comparacao is not None
        else {}
    )

    resumos = conteudo.get(
        "resumos_provedores"
    ) or {}

    entrada = None

    if comparacao is not None:
        try:
            imagem = obter_imagem_analise(
                analise_id,
                db,
            )

            entrada = recuperar_entrada_original(
                analise,
                imagem,
                comparacao,
            )
        except HTTPException:
            entrada = None

    itens = []

    for nome in PROVEDORES_RECUPERACAO:
        resumo = resumos.get(nome) or {}

        if nome in relatorios:
            estado = "disponivel"

        elif resumo.get("sucesso") is True:
            estado = "sem_relatorio"

        elif nome in resumos:
            estado = estado_falha_provedor(resumo)

        else:
            estado = "indisponivel"

        pode_recuperar = bool(
            nome not in relatorios
            and entrada is not None
            and nome in entrada["provedores"]
            and nome in resumos
        )

        itens.append({
            "provedor": nome,
            "estado": estado,
            "pode_recuperar": pode_recuperar,
            "contexto_reconstruido": bool(
                entrada
                and entrada["reconstruido"]
            ),
        })

    return {
        "analise_id": analise_id,
        "provedores": itens,
    }


@app.post(
    "/analises/{analise_id}/reprocessar/{provedor}",
    tags=["Analise Multimodal"],
)
def reprocessar_provedor_indisponivel(
    analise_id: int,
    provedor: Literal["openai", "gemini", "kimi"],
    confirmar_envio: bool = False,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
    pasta_temporaria: Path = Depends(
        obter_pasta_temporaria
    ),
):
    obter_analise_autorizada(
        analise_id,
        enfermeiro,
        db,
    )

    if confirmar_envio is not True:
        raise HTTPException(
            status_code=400,
            detail="Confirme o novo envio ao provedor.",
        )

    # Serializa as recuperacoes desta avaliacao
    # enquanto a transacao estiver aberta.

    analise = db.scalar(
        select(Analise)
        .where(
            Analise.id_analise == analise_id,
            Analise.id_enfermeiro_fk
            == enfermeiro.id_enfermeiro,
            Analise.deleted_at.is_(None),
            Analise.id_paciente_fk.in_(
                select(Paciente.id_paciente).where(
                    Paciente.id_enfermeiro_fk
                    == enfermeiro.id_enfermeiro,
                    Paciente.deleted_at.is_(None),
                )
            ),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if analise is None:
        raise HTTPException(
            status_code=404,
            detail="Analise nao encontrada.",
        )

    relatorios = consultar_relatorios_recuperacao(
        analise_id,
        db,
    )

    if provedor in relatorios:
        raise HTTPException(
            status_code=409,
            detail="O relatorio deste provedor ja existe.",
        )

    comparacao_anterior = (
        consultar_comparacao_recuperacao(
            analise_id,
            db,
        )
    )

    imagem = obter_imagem_analise(
        analise_id,
        db,
    )

    contexto = recuperar_entrada_original(
        analise,
        imagem,
        comparacao_anterior,
    )

    if (
        contexto is None
        or provedor not in contexto["provedores"]
    ):
        raise HTTPException(
            status_code=409,
            detail="Contexto original indisponivel para recuperacao segura.",
        )

    resumos = (
        comparacao_anterior.conteudo or {}
    ).get("resumos_provedores") or {}

    if provedor not in resumos:
        raise HTTPException(
            status_code=409,
            detail="Provedor nao identificado na execucao anterior.",
        )

    resultados_anteriores = {}

    # Utiliza os relatorios originais, nunca as
    # versoes editadas ou aprovadas pelo enfermeiro.

    for nome, registro in relatorios.items():
        if (
            nome not in contexto["provedores"]
            or nome not in resumos
            or not resumos[nome].get("sucesso")
        ):
            raise HTTPException(
                status_code=409,
                detail="Nao foi possivel vincular os relatorios a mesma execucao.",
            )

        try:
            resposta = RespostaEstruturadaModelo.model_validate(
                registro.conteudo_original
            )
        except ValidationError as erro:
            raise HTTPException(
                status_code=409,
                detail="Relatorio original incompativel.",
            ) from erro

        resultados_anteriores[nome] = ResultadoProvedor(
            provedor=nome,
            modo="relatorio_persistido",
            sucesso=True,
            tempo_execucao_segundos=float(
                resumos[nome].get(
                    "tempo_execucao_segundos"
                ) or 0
            ),
            resposta=resposta,
        )

    caminho_original = resolver_caminho_imagem(
        imagem.caminho_imagem_original,
        pasta_temporaria,
    )

    try:
        opencv = (
            ImageProcessingService.processar_imagem_lesao(
                caminho_imagem_original=caminho_original,
                pasta_destino_processadas=str(
                    pasta_temporaria
                ),
            )
        )

        caminho_processado = str(
            pasta_temporaria
            / opencv["nome_arquivo_processado"]
        )

        nova_execucao = uuid4().hex

        entrada = AnaliseMultimodalInput(
            avaliacao_id=nova_execucao,
            caminho_imagem_original=caminho_original,
            caminho_imagem_processada=caminho_processado,
            dimensoes_originais=opencv[
                "dimensoes_originais"
            ],
            dimensoes_processadas=opencv[
                "dimensoes_processadas"
            ],
            analise_tecnica=AnaliseTecnicaOpenCVInput(
                brilho_medio=opencv[
                    "analise_tecnica"
                ]["brilho_medio"],
                contraste_global=opencv[
                    "analise_tecnica"
                ]["contraste_global"],
            ),
            dados_clinicos=contexto["dados"],
        )

        resultado = (
            orquestrador_multimodal.executar_analise_comparativa(
                input_data=entrada,
                provedores_desejados=[provedor],
            )
        )

    except Exception as erro:
        logger.exception(
            "Falha ao recuperar provedor %s.",
            provedor,
        )

        raise HTTPException(
            status_code=502,
            detail="Falha ao recuperar o provedor.",
        ) from erro

    resposta_nova = resultado.resultados.get(
        provedor
    )

    if resposta_nova is None:
        return {
            "sucesso": False,
            "provedor": provedor,
            "estado": "falha",
        }

    sucesso = bool(
        resposta_nova.sucesso
        and resposta_nova.resposta is not None
    )

    if sucesso:
        conjunto = gerar_relatorios(
            resultado=resultado,
            avaliacao_id=nova_execucao,
        )

        persistencia = salvar_relatorios_no_banco(
            analise_id=analise_id,
            conjunto=conjunto,
            db=db,
            provedores_com_sucesso={provedor},
        )

        if provedor not in persistencia["salvos"]:
            raise HTTPException(
                status_code=409,
                detail="Nao foi possivel registrar o novo relatorio.",
            )

    resultados_anteriores[provedor] = resposta_nova

    # Preserva outros provedores indisponiveis,
    # sem executar novamente suas APIs.

    for nome in contexto["provedores"]:
        if nome in resultados_anteriores:
            continue

        resumo = resumos.get(nome) or {}

        resultados_anteriores[nome] = ResultadoProvedor(
            provedor=nome,
            modo="resultado_anterior",
            sucesso=False,
            tempo_execucao_segundos=float(
                resumo.get(
                    "tempo_execucao_segundos"
                ) or 0
            ),
            mensagem_erro=resumo.get(
                "mensagem_erro"
            ) or "Relatorio indisponivel.",
        )

    resultado_combinado = ResultadoAnaliseMultimodal(
        sucesso_geral=any(
            item.sucesso
            for item in resultados_anteriores.values()
        ),
        data_processamento=datetime.now(
            timezone.utc
        ).isoformat(),
        resultados=resultados_anteriores,
    )

    comparacao_nova = gerar_comparacao_segura(
        resultado_combinado
    )

    comparacao_nova["origem_reprocessamento"] = (
        contexto["origem"]
    )

    comparacao_nova["execucoes_distintas"] = True

    comparacao_nova["contexto_reconstruido"] = (
        contexto["reconstruido"]
    )

    comparacao_nova["observacao_metodologica"] = (
        comparacao_nova.get(
            "observacao_metodologica",
            "",
        )
        + " Comparacao atualizada com relatorios originais "
        "de tentativas distintas da mesma avaliacao. "
        + (
            "Os dados clinicos foram reconstruidos "
            "a partir do registro persistido."
            if contexto["reconstruido"]
            else "A entrada clinica original foi reutilizada."
        )
    ).strip()

    provedores_com_sucesso = {
        nome
        for nome, resposta in resultados_anteriores.items()
        if resposta.sucesso
        and resposta.resposta is not None
    }

    persistencia_comparacao = salvar_comparacao(
        db=db,
        analise_id=analise_id,
        avaliacao_id=nova_execucao,
        comparacao=comparacao_nova,
        provedores_com_sucesso=provedores_com_sucesso,
    )

    return {
        "sucesso": sucesso,
        "provedor": provedor,
        "estado": (
            "disponivel"
            if sucesso
            else estado_falha_provedor({
                "mensagem_erro": resposta_nova.mensagem_erro,
            })
        ),
        "comparacao_atualizada": bool(
            persistencia_comparacao.get("salva")
        ),
    }
