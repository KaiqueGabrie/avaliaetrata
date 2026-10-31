"""API Avalia & Trata - backend/main.py (versao 2.4.1)."""

import os
import logging
from copy import deepcopy
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Analise, Enfermeiro, Imagem, RelatorioIA
from routers.auth import router as auth_router, obter_enfermeiro_atual
from routers.pacientes import router as pacientes_router
from routers.analises import router as analises_router
from routers.relatorios_persistentes import router as relatorios_persistentes_router
from routers.comparacoes import router as comparacoes_router, salvar_comparacao
from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
)
from services.image_processing import ImageProcessingService
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
    version="2.4.1",
)

# Cada router e registrado uma unica vez.
app.include_router(auth_router)
app.include_router(pacientes_router)
app.include_router(analises_router)
app.include_router(relatorios_persistentes_router)
app.include_router(comparacoes_router)

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
        )
    )
    if analise is None:
        raise HTTPException(
            status_code=404,
            detail="Analise nao encontrada ou acesso nao autorizado.",
        )
    return analise


def resolver_caminho_imagem(caminho: str) -> str:
    """Aceita somente imagens na pasta privada de uploads."""
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
        "versao": "2.4.1",
        "modulos": {
            "autenticacao": True,
            "pacientes": True,
            "anamnese": True,
            "analises": True,
            "opencv": True,
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
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    obter_analise_autorizada(analise_id, enfermeiro, db)
    imagem = obter_imagem_analise(analise_id, db)
    caminho_original = resolver_caminho_imagem(imagem.caminho_imagem_original)

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
            pasta_destino_processadas=str(PROCESSED_DIR),
        )
        caminho_processado = str(
            PROCESSED_DIR / resultado_opencv["nome_arquivo_processado"]
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
