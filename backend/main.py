import os
import uuid

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    HTTPException
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from schemas.multimodal import AnaliseMultimodalInput
from services.image_processing import ImageProcessingService
from services.multimodal.orchestrator import MultimodalOrchestrator


# ============================================================
# CONFIGURAÇÃO DA API
# ============================================================

app = FastAPI(
    title="API Avalia & Trata",
    description=(
        "Backend para processamento de imagens "
        "e análise multimodal"
    ),
    version="1.0.0"
)


# ============================================================
# DIRETÓRIOS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

PROCESSED_DIR = os.path.join(
    BASE_DIR,
    "processed"
)


os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

os.makedirs(
    PROCESSED_DIR,
    exist_ok=True
)


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads"
)

app.mount(
    "/processed",
    StaticFiles(directory=PROCESSED_DIR),
    name="processed"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ORQUESTRADOR MULTIMODAL
# ============================================================

multimodal_orchestrator = MultimodalOrchestrator()


# ============================================================
# TESTE DA API
# ============================================================

@app.get("/")
def read_root():

    return {
        "status": "online",
        "message": (
            "API Avalia & Trata funcionando "
            "com FastAPI + OpenCV + análise multimodal"
        )
    }


# ============================================================
# FUNÇÃO AUXILIAR
# ============================================================

async def salvar_e_processar_imagem(
    file: UploadFile,
):
    """
    Recebe a imagem, valida o arquivo, salva a imagem original
    e executa o processamento inicial com OpenCV.

    Essa função é reutilizada pelos endpoints que trabalham
    com a imagem.
    """

    # ========================================================
    # 1. VALIDAR ARQUIVO
    # ========================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Nenhuma imagem foi enviada."
        )

    content_type = (
        file.content_type or ""
    ).lower()

    if not content_type.startswith("image/"):

        raise HTTPException(
            status_code=400,
            detail=(
                "O arquivo enviado não "
                "é uma imagem válida."
            )
        )

    # ========================================================
    # 2. VALIDAR EXTENSÃO
    # ========================================================

    extensao = os.path.splitext(
        file.filename
    )[1].lower()

    extensoes_permitidas = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    if extensao not in extensoes_permitidas:

        raise HTTPException(
            status_code=400,
            detail=(
                "Formato de imagem não suportado. "
                "Utilize JPG, JPEG, PNG ou WEBP."
            )
        )

    # ========================================================
    # 3. GERAR NOME ÚNICO
    # ========================================================

    nome_unico = (
        f"{uuid.uuid4().hex}"
        f"{extensao}"
    )

    caminho_imagem_original = os.path.join(
        UPLOAD_DIR,
        nome_unico
    )

    # ========================================================
    # 4. RECEBER IMAGEM
    # ========================================================

    conteudo = await file.read()

    if not conteudo:

        raise HTTPException(
            status_code=400,
            detail="A imagem recebida está vazia."
        )

    # ========================================================
    # 5. SALVAR IMAGEM ORIGINAL
    # ========================================================

    with open(
        caminho_imagem_original,
        "wb"
    ) as arquivo:

        arquivo.write(conteudo)

    # ========================================================
    # 6. PROCESSAR COM OPENCV
    # ========================================================

    resultado_opencv = (
        ImageProcessingService
        .processar_imagem_lesao(
            caminho_imagem_original=(
                caminho_imagem_original
            ),
            pasta_destino_processadas=(
                PROCESSED_DIR
            )
        )
    )

    # ========================================================
    # 7. MONTAR CAMINHO DA IMAGEM PROCESSADA
    # ========================================================

    nome_arquivo_processado = (
        resultado_opencv[
            "nome_arquivo_processado"
        ]
    )

    caminho_imagem_processada = os.path.join(
        PROCESSED_DIR,
        nome_arquivo_processado
    )

    # ========================================================
    # 8. URLS
    # ========================================================

    imagem_original_url = (
        f"/uploads/{nome_unico}"
    )

    imagem_processada_url = (
        f"/processed/"
        f"{nome_arquivo_processado}"
    )

    return {
        "nome_arquivo_original": nome_unico,

        "caminho_imagem_original":
            caminho_imagem_original,

        "caminho_imagem_processada":
            caminho_imagem_processada,

        "imagem_original_url":
            imagem_original_url,

        "imagem_processada_url":
            imagem_processada_url,

        "resultado_opencv":
            resultado_opencv
    }


# ============================================================
# ENDPOINT ATUAL — OPENCV
# ============================================================

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

    observacoes: str = Form("")
):

    try:

        resultado = (
            await salvar_e_processar_imagem(
                file
            )
        )

        resultado_opencv = (
            resultado[
                "resultado_opencv"
            ]
        )

        return {

            "sucesso":
                True,

            "mensagem":
                "Imagem recebida e processada com sucesso.",

            "imagem_original_url":
                resultado[
                    "imagem_original_url"
                ],

            "imagem_processada_url":
                resultado[
                    "imagem_processada_url"
                ],

            "dimensoes_originais":
                resultado_opencv[
                    "dimensoes_originais"
                ],

            "dimensoes_processadas":
                resultado_opencv[
                    "dimensoes_processadas"
                ],

            "analise_tecnica":
                resultado_opencv[
                    "analise_tecnica"
                ],

            "processamento_aplicado":
                resultado_opencv[
                    "processamento_aplicado"
                ],

            "dados_clinicos": {

                "localizacao":
                    localizacao,

                "comprimento":
                    comprimento,

                "largura":
                    largura,

                "tipoExsudato":
                    tipoExsudato,

                "odor":
                    odor,

                "nivelDor":
                    nivelDor,

                "queixaPrincipal":
                    queixaPrincipal,

                "observacoes":
                    observacoes
            }
        }

    except HTTPException:
        raise

    except ValueError as erro:

        print(
            f"Erro de validação da imagem: {erro}"
        )

        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )

    except Exception as erro:

        print(
            f"Erro no processamento da imagem: {erro}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro interno ao processar a imagem: "
                f"{str(erro)}"
            )
        )


# ============================================================
# ENDPOINT — ANÁLISE MULTIMODAL
# ============================================================

@app.post("/preparar-analise-multimodal")
async def preparar_analise_multimodal(

    file: UploadFile = File(...),

    avaliacao_id: str = Form(""),

    localizacao: str = Form(...),

    comprimento: str = Form(""),

    largura: str = Form(""),

    tipoExsudato: str = Form(""),

    odor: str = Form("false"),

    nivelDor: str = Form(""),

    queixaPrincipal: str = Form(""),

    observacoes: str = Form("")
):

    """
    Recebe a imagem e os dados clínicos, executa o
    processamento inicial com OpenCV e envia a entrada
    estruturada para os provedores multimodais.

    Nesta etapa o Gemini é o primeiro provedor real
    conectado ao sistema.
    """

    try:

        # ====================================================
        # 1. PROCESSAR IMAGEM
        # ====================================================

        resultado = (
            await salvar_e_processar_imagem(
                file
            )
        )

        resultado_opencv = (
            resultado[
                "resultado_opencv"
            ]
        )

        # ====================================================
        # 2. NORMALIZAR ODOR
        # ====================================================

        odor_normalizado = (
            str(odor).strip().lower()
            in {
                "true",
                "1",
                "sim",
                "yes"
            }
        )

        # ====================================================
        # 3. CRIAR DADOS CLÍNICOS
        # ====================================================

        dados_clinicos = {

            "localizacao":
                localizacao,

            "comprimento":
                comprimento or None,

            "largura":
                largura or None,

            "tipoExsudato":
                tipoExsudato or None,

            "odor":
                odor_normalizado,

            "nivelDor":
                nivelDor or None,

            "queixaPrincipal":
                queixaPrincipal or None,

            "observacoes":
                observacoes or None
        }

        # ====================================================
        # 4. CRIAR ENTRADA MULTIMODAL
        # ====================================================

        entrada_multimodal = AnaliseMultimodalInput(
            avaliacao_id=avaliacao_id or None,

            caminho_imagem_original=(
                resultado[
                    "caminho_imagem_original"
                ]
            ),

            caminho_imagem_processada=(
                resultado[
                    "caminho_imagem_processada"
                ]
            ),

            dimensoes_originais=(
                resultado_opencv[
                    "dimensoes_originais"
                ]
            ),

            dimensoes_processadas=(
                resultado_opencv[
                    "dimensoes_processadas"
                ]
            ),

            analise_tecnica=(
                resultado_opencv[
                    "analise_tecnica"
                ]
            ),

            dados_clinicos=dados_clinicos
        )

        # ====================================================
        # 5. EXECUTAR ANÁLISE MULTIMODAL
        # ====================================================

        resultado_multimodal = (
            multimodal_orchestrator
            .executar_analise_comparativa(
                input_data=entrada_multimodal,
                provedores_desejados=[
                    "gemini"
                ]
            )
        )

        # ====================================================
        # 6. RETORNO
        # ====================================================

        return {

            "sucesso":
                True,

            "mensagem":
                (
                    "Imagem processada e enviada "
                    "para análise multimodal."
                ),

            "imagem_original_url":
                resultado[
                    "imagem_original_url"
                ],

            "imagem_processada_url":
                resultado[
                    "imagem_processada_url"
                ],

            "entrada_multimodal":
                entrada_multimodal.model_dump(),

            "resultado_multimodal":
                resultado_multimodal.model_dump()
        }

    except HTTPException:
        raise

    except ValueError as erro:

        print(
            f"Erro de validação da análise multimodal: {erro}"
        )

        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )

    except Exception as erro:

        print(
            f"Erro na análise multimodal: {erro}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erro interno na análise multimodal: "
                f"{str(erro)}"
            )
        )