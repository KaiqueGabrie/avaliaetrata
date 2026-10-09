
import os
import uuid
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.image_processing import ImageProcessingService
from services.multimodal.orchestrator import MultimodalOrchestrator
from schemas.multimodal import (
    AnaliseMultimodalInput,
    DadosClinicosInput,
    AnaliseTecnicaOpenCVInput,
    ResultadoAnaliseMultimodal,
)

app = FastAPI(
    title="API Avalia & Trata - Análise Técnica e Arquitetura Multimodal",
    description=(
        "Sistema de apoio à análise descritiva e ao acompanhamento "
        "de feridas, com processamento de imagem e análise multimodal."
    ),
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

EXTENSOES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

app.mount(
    "/processed",
    StaticFiles(directory=PROCESSED_DIR),
    name="processed",
)
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orquestrador_multimodal = MultimodalOrchestrator()


def obter_extensao_arquivo(filename: Optional[str]) -> str:
    """Valida a extensão do arquivo enviado."""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado não possui um nome válido.",
        )

    extensao = os.path.splitext(filename)[1].lower()

    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagem não permitido. Use JPG, JPEG, PNG ou WEBP.",
        )

    return extensao


def converter_odor(valor: Optional[str]) -> bool:
    """Converte valores comuns de formulário para booleano."""
    valor_normalizado = (valor or "").strip().lower()

    if valor_normalizado in {"true", "1", "sim", "yes"}:
        return True

    if valor_normalizado in {"false", "0", "nao", "não", "no", ""}:
        return False

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Valor inválido para odor. Informe true ou false.",
    )


async def salvar_imagem_enviada(file: UploadFile) -> str:
    """Salva a imagem original e retorna seu caminho no servidor."""
    extensao = obter_extensao_arquivo(file.filename)
    nome_unico = f"{uuid.uuid4().hex}{extensao}"
    caminho_imagem_original = os.path.join(UPLOAD_DIR, nome_unico)

    conteudo = await file.read()

    if not conteudo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )

    with open(caminho_imagem_original, "wb") as arquivo:
        arquivo.write(conteudo)

    return caminho_imagem_original


def processar_imagem(caminho_imagem_original: str):
    """Executa o processamento técnico da imagem com OpenCV."""
    return ImageProcessingService.processar_imagem_lesao(
        caminho_imagem_original=caminho_imagem_original,
        pasta_destino_processadas=PROCESSED_DIR,
    )


def montar_url_imagem(nome_arquivo: str, pasta_url: str) -> str:
    """Monta a URL relativa de uma imagem disponibilizada pela API."""
    return f"{pasta_url}/{nome_arquivo}"


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "API Avalia & Trata operacional.",
    }


@app.post("/analisar-imagem")
async def analisar_imagem(
    file: UploadFile = File(...),
    localizacao: str = Form(...),
    comprimento: str = Form(""),
    largura: str = Form(""),
    tipoExsudato: str = Form(""),
    odor: str = Form("false"),
    nivelDor: str = Form(""),
    queixaPrincipal: str = Form(""),
    observacoes: str = Form(""),
):
    """
    Recebe uma imagem, executa o processamento técnico com OpenCV
    e retorna os dados da imagem e as informações clínicas fornecidas.
    """
    caminho_imagem_original = None

    try:
        caminho_imagem_original = await salvar_imagem_enviada(file)
        resultado_opencv = processar_imagem(caminho_imagem_original)

        nome_original = os.path.basename(caminho_imagem_original)
        nome_processado = resultado_opencv["nome_arquivo_processado"]

        return {
            "sucesso": True,
            "mensagem": "Imagem recebida, validada e pré-processada com sucesso.",
            "imagem_original_url": montar_url_imagem(
                nome_original, "/uploads"
            ),
            "imagem_processada_url": montar_url_imagem(
                nome_processado, "/processed"
            ),
            "dimensoes_originais": resultado_opencv["dimensoes_originais"],
            "dimensoes_processadas": resultado_opencv["dimensoes_processadas"],
            "analise_tecnica": resultado_opencv["analise_tecnica"],
            "processamento_aplicado": resultado_opencv["processamento_aplicado"],
            "dados_clinicos": {
                "localizacao": localizacao,
                "comprimento": comprimento,
                "largura": largura,
                "tipoExsudato": tipoExsudato,
                "odor": odor,
                "nivelDor": nivelDor,
                "queixaPrincipal": queixaPrincipal,
                "observacoes": observacoes,
            },
        }

    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro),
        )
    except Exception as erro:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no pré-processamento da imagem: {str(erro)}",
        )
    finally:
        await file.close()


@app.post("/preparar-analise-multimodal")
async def preparar_analise_multimodal(
    file: UploadFile = File(...),
    localizacao: str = Form(...),
    comprimento: str = Form(""),
    largura: str = Form(""),
    tipoExsudato: str = Form(""),
    odor: str = Form("false"),
    nivelDor: str = Form(""),
    queixaPrincipal: str = Form(""),
    observacoes: str = Form(""),
    provedor: Optional[str] = Form("gemini"),
):
    """
    Recebe uma imagem e os dados clínicos, executa o OpenCV e solicita
    a análise multimodal ao provedor selecionado.

    Valores aceitos para provedor:
    - gemini: executa somente o Gemini.
    - openai: executa somente a OpenAI.
    - todos: solicita a execução dos dois provedores.
    """
    try:
        provedor_normalizado = (provedor or "gemini").strip().lower()

        provedores_disponiveis = {
            "gemini": ["gemini"],
            "openai": ["openai"],
            "todos": ["gemini", "openai"],
        }

        if provedor_normalizado not in provedores_disponiveis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Provedor inválido. Os valores permitidos são: "
                    "'gemini', 'openai' ou 'todos'."
                ),
            )

        provedores_desejados = provedores_disponiveis[provedor_normalizado]

        # 1. Recebe e salva a imagem original.
        caminho_imagem_original = await salvar_imagem_enviada(file)

        # 2. Executa o processamento técnico com OpenCV.
        resultado_opencv = processar_imagem(caminho_imagem_original)

        caminho_imagem_processada = os.path.join(
            PROCESSED_DIR,
            resultado_opencv["nome_arquivo_processado"],
        )

        # 3. Monta os dados padronizados enviados aos provedores.
        input_multimodal = AnaliseMultimodalInput(
            avaliacao_id=uuid.uuid4().hex,
            caminho_imagem_original=caminho_imagem_original,
            caminho_imagem_processada=caminho_imagem_processada,
            dimensoes_originais=resultado_opencv["dimensoes_originais"],
            dimensoes_processadas=resultado_opencv["dimensoes_processadas"],
            analise_tecnica=AnaliseTecnicaOpenCVInput(
                brilho_medio=resultado_opencv["analise_tecnica"]["brilho_medio"],
                contraste_global=resultado_opencv["analise_tecnica"]["contraste_global"],
            ),
            dados_clinicos=DadosClinicosInput(
                localizacao=localizacao,
                comprimento=comprimento,
                largura=largura,
                tipoExsudato=tipoExsudato,
                odor=converter_odor(odor),
                nivelDor=nivelDor,
                queixaPrincipal=queixaPrincipal,
                observacoes=observacoes,
            ),
        )

        # 4. Executa a análise pelos provedores solicitados.
        resultado_comparativo: ResultadoAnaliseMultimodal = (
            orquestrador_multimodal.executar_analise_comparativa(
                input_data=input_multimodal,
                provedores_desejados=provedores_desejados,
            )
        )

        # 5. A mensagem acompanha o resultado geral informado pelo orquestrador.
        if resultado_comparativo.sucesso_geral:
            mensagem = (
                "A análise foi concluída com sucesso para pelo menos "
                "um dos provedores solicitados."
            )
        else:
            mensagem = (
                "Nenhum dos provedores solicitados concluiu a análise com sucesso. "
                "Consulte os resultados e as mensagens de erro retornadas."
            )

        nome_original = os.path.basename(caminho_imagem_original)
        nome_processado = resultado_opencv["nome_arquivo_processado"]

        return {
            "sucesso": resultado_comparativo.sucesso_geral,
            "mensagem": mensagem,
            "provedor_selecionado": provedor_normalizado,
            "provedores_solicitados": provedores_desejados,
            "imagem_original_url": montar_url_imagem(
                nome_original, "/uploads"
            ),
            "imagem_processada_url": montar_url_imagem(
                nome_processado, "/processed"
            ),
            "dimensoes_originais": resultado_opencv["dimensoes_originais"],
            "dimensoes_processadas": resultado_opencv["dimensoes_processadas"],
            "analise_tecnica": resultado_opencv["analise_tecnica"],
            "dados_clinicos": input_multimodal.dados_clinicos.model_dump(),
            "analise_multimodal": resultado_comparativo.model_dump(),
        }

    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro),
        )
    except Exception as erro:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na pipeline multimodal: {str(erro)}",
        )
    finally:
        await file.close()

