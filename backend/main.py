import os
import uuid
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from services.image_processing import ImageProcessingService
from services.multimodal.orchestrator import MultimodalOrchestrator
from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
    ResultadoAnaliseMultimodal,
)


app = FastAPI(
    title="API Avalia & Trata",
    description=(
        "Sistema de apoio à documentação e análise descritiva de feridas. "
        "Os resultados automatizados exigem validação profissional."
    ),
    version="2.1.0",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
EXTENSOES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}
TAMANHO_MAXIMO_IMAGEM = 15 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

app.mount("/processed", StaticFiles(directory=PROCESSED_DIR), name="processed")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Para o protótipo local; restringir origens antes de publicar em produção.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

orquestrador_multimodal = MultimodalOrchestrator()


def obter_extensao_arquivo(filename: Optional[str]) -> str:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado não possui nome válido.",
        )
    extensao = os.path.splitext(filename)[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato não permitido. Utilize JPG, JPEG, PNG ou WEBP.",
        )
    return extensao


def converter_odor(valor: Optional[str]) -> Optional[bool]:
    normalizado = (valor or "").strip().lower()
    if normalizado in {"true", "1", "sim", "yes"}:
        return True
    if normalizado in {"false", "0", "nao", "não", "no"}:
        return False
    if normalizado in {"", "null", "none", "não informado", "nao informado"}:
        return None
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Valor inválido para odor. Utilize sim, não ou deixe vazio.",
    )


def texto_opcional(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A localização anatômica é obrigatória.",
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


async def salvar_imagem_enviada(file: UploadFile) -> str:
    extensao = obter_extensao_arquivo(file.filename)
    conteudo = await file.read(TAMANHO_MAXIMO_IMAGEM + 1)
    if not conteudo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )
    if len(conteudo) > TAMANHO_MAXIMO_IMAGEM:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="A imagem ultrapassa o limite de 15 MB.",
        )
    caminho = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{extensao}")
    with open(caminho, "wb") as arquivo:
        arquivo.write(conteudo)
    return caminho


def processar_imagem(caminho_imagem_original: str) -> dict:
    return ImageProcessingService.processar_imagem_lesao(
        caminho_imagem_original=caminho_imagem_original,
        pasta_destino_processadas=PROCESSED_DIR,
    )


def montar_url_imagem(nome_arquivo: str, pasta_url: str) -> str:
    return f"{pasta_url}/{nome_arquivo}"


def metadados_imagem(caminho_original: str, resultado_opencv: dict) -> dict:
    """Mantém as mesmas chaves usadas atualmente pelo aplicativo."""
    return {
        "imagem_original_url": montar_url_imagem(
            os.path.basename(caminho_original), "/uploads"
        ),
        "imagem_processada_url": montar_url_imagem(
            resultado_opencv["nome_arquivo_processado"], "/processed"
        ),
        "dimensoes_originais": resultado_opencv["dimensoes_originais"],
        "dimensoes_processadas": resultado_opencv["dimensoes_processadas"],
        "analise_tecnica": resultado_opencv["analise_tecnica"],
        "processamento_aplicado": resultado_opencv["processamento_aplicado"],
    }


def tratar_erro_processamento(erro: Exception, etapa: str) -> HTTPException:
    # Evita retornar detalhes internos, caminhos locais ou dados sensíveis.
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Falha interna durante {etapa}. Consulte os logs do servidor.",
    )


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "API Avalia & Trata operacional.",
        "versao": "2.1.0",
    }


@app.post("/analisar-imagem")
async def analisar_imagem(
    file: UploadFile = File(...),
    localizacao: str = Form(...),
    comprimento: str = Form(""),
    largura: str = Form(""),
    tipoExsudato: str = Form(""),
    odor: str = Form(""),
    nivelDor: str = Form(""),
    queixaPrincipal: str = Form(""),
    observacoes: str = Form(""),
):
    try:
        dados_clinicos = montar_dados_clinicos(
            localizacao, comprimento, largura, tipoExsudato,
            odor, nivelDor, queixaPrincipal, observacoes,
        )
        caminho_original = await salvar_imagem_enviada(file)
        resultado_opencv = processar_imagem(caminho_original)
        return {
            "sucesso": True,
            "mensagem": (
                "Imagem recebida e processada tecnicamente. "
                "Nenhum diagnóstico clínico foi realizado."
            ),
            **metadados_imagem(caminho_original, resultado_opencv),
            "dados_clinicos": dados_clinicos.model_dump(),
        }
    except HTTPException:
        raise
    except (ValueError, ValidationError) as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except Exception as erro:
        raise tratar_erro_processamento(erro, "o processamento da imagem") from erro
    finally:
        await file.close()


@app.post("/preparar-analise-multimodal")
async def preparar_analise_multimodal(
    file: UploadFile = File(...),
    localizacao: str = Form(...),
    comprimento: str = Form(""),
    largura: str = Form(""),
    tipoExsudato: str = Form(""),
    odor: str = Form(""),
    nivelDor: str = Form(""),
    queixaPrincipal: str = Form(""),
    observacoes: str = Form(""),
    provedor: Literal["gemini", "openai", "kimi", "todos"] = Form("gemini"),
):
    try:
        provedores_disponiveis = {
            "gemini": ["gemini"],
            "openai": ["openai"],
            "kimi": ["kimi"],
            "todos": ["gemini", "openai", "kimi"],
        }
        provedores_desejados = provedores_disponiveis[provedor]
        dados_clinicos = montar_dados_clinicos(
            localizacao, comprimento, largura, tipoExsudato,
            odor, nivelDor, queixaPrincipal, observacoes,
        )
        caminho_original = await salvar_imagem_enviada(file)
        resultado_opencv = processar_imagem(caminho_original)
        caminho_processado = os.path.join(
            PROCESSED_DIR, resultado_opencv["nome_arquivo_processado"]
        )
        input_multimodal = AnaliseMultimodalInput(
            avaliacao_id=uuid.uuid4().hex,
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
        resultado: ResultadoAnaliseMultimodal = (
            orquestrador_multimodal.executar_analise_comparativa(
                input_data=input_multimodal,
                provedores_desejados=provedores_desejados,
            )
        )
        return {
            "sucesso": resultado.sucesso_geral,
            "mensagem": (
                "Pelo menos um provedor concluiu a análise; "
                "os resultados exigem revisão profissional."
                if resultado.sucesso_geral
                else "Nenhum provedor concluiu a análise. Consulte os erros individuais."
            ),
            "provedor_selecionado": provedor,
            "provedores_solicitados": provedores_desejados,
            **metadados_imagem(caminho_original, resultado_opencv),
            "dados_clinicos": dados_clinicos.model_dump(),
            "analise_multimodal": resultado.model_dump(),
            "aviso": (
                "Análise automatizada auxiliar, sujeita a erro. "
                "Não confirma diagnóstico, infecção, profundidade, "
                "fase de cicatrização, tipos de tecido ou medidas físicas. "
                "Marcações e percentuais sugeridos exigem conferência do enfermeiro."
            ),
        }
    except HTTPException:
        raise
    except (ValueError, ValidationError) as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except Exception as erro:
        raise tratar_erro_processamento(erro, "a análise multimodal") from erro
    finally:
        await file.close()
