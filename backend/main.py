import logging
import os
import uuid

from threading import RLock
from typing import Dict, Literal, Optional
from routers.pacientes import router as pacientes_router
from routers.auth import router as auth_router
from routers.analises import router as analises_router

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field, ValidationError

from services.image_processing import ImageProcessingService

from services.multimodal.orchestrator import (
    MultimodalOrchestrator,
)

from services.multimodal.comparador import (
    comparar_resultados,
)

from services.multimodal.relatorio import (
    gerar_relatorios,
    selecionar_relatorio,
    editar_campo,
    aprovar_relatorio,
)

from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
    ResultadoAnaliseMultimodal,
)

from schemas.relatorio import (
    ConjuntoRelatorios,
    RelatorioIndividual,
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Avalia & Trata",
    description=(
        "Sistema de apoio à documentação e análise "
        "descritiva de feridas. Os resultados automatizados "
        "exigem validação profissional."
    ),
    version="2.3.0",
)

app.include_router(auth_router)
app.include_router(auth_router)
app.include_router(pacientes_router)
app.include_router(auth_router)
app.include_router(pacientes_router)
app.include_router(analises_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

EXTENSOES_PERMITIDAS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

TAMANHO_MAXIMO_IMAGEM = 15 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

# ATENÇÃO:
# Estas rotas são adequadas somente ao protótipo local.
# Não exponha imagens clínicas reais sem autenticação,
# autorização e armazenamento protegido.

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


# ============================================================
# CORS
# ============================================================

# Configuração exclusiva para desenvolvimento local.
# Restringir origens antes de publicar a aplicação.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# SERVIÇOS
# ============================================================

orquestrador_multimodal = MultimodalOrchestrator()


# ============================================================
# ARMAZENAMENTO TEMPORÁRIO DOS RELATÓRIOS
# ============================================================

# PROTÓTIPO:
# Os relatórios ficam somente na memória do processo.
# Não existe persistência após reiniciar o servidor.
# Utilizar apenas um processo/worker nesta etapa.
#
# Futuramente, substituir por banco de dados,
# autenticação e controle de acesso profissional.

RELATORIOS_TEMPORARIOS: Dict[
    str,
    ConjuntoRelatorios,
] = {}

LOCK_RELATORIOS = RLock()


# ============================================================
# SCHEMAS PARA EDIÇÃO E APROVAÇÃO
# ============================================================

class EditarCampoRequest(BaseModel):
    campo: str = Field(..., min_length=1)
    novo_valor: str
    profissional_id: str = Field(..., min_length=1)


class AprovarRelatorioRequest(BaseModel):
    profissional_id: str = Field(..., min_length=1)


# ============================================================
# FUNÇÕES AUXILIARES — IMAGEM
# ============================================================

def obter_extensao_arquivo(
    filename: Optional[str],
) -> str:

    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "O arquivo enviado não possui nome válido."
            ),
        )

    extensao = os.path.splitext(filename)[1].lower()

    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Formato não permitido. "
                "Utilize JPG, JPEG, PNG ou WEBP."
            ),
        )

    return extensao


def converter_odor(
    valor: Optional[str],
) -> Optional[bool]:

    normalizado = (valor or "").strip().lower()

    if normalizado in {
        "true",
        "1",
        "sim",
        "yes",
    }:
        return True

    if normalizado in {
        "false",
        "0",
        "nao",
        "não",
        "no",
    }:
        return False

    if normalizado in {
        "",
        "null",
        "none",
        "não informado",
        "nao informado",
    }:
        return None

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Valor inválido para odor. "
            "Utilize sim, não ou deixe vazio."
        ),
    )


def texto_opcional(
    valor: Optional[str],
) -> Optional[str]:

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
            detail=(
                "A localização anatômica é obrigatória."
            ),
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


async def salvar_imagem_enviada(
    file: UploadFile,
) -> str:

    extensao = obter_extensao_arquivo(
        file.filename
    )

    conteudo = await file.read(
        TAMANHO_MAXIMO_IMAGEM + 1
    )

    if not conteudo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )

    if len(conteudo) > TAMANHO_MAXIMO_IMAGEM:
        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
            detail=(
                "A imagem ultrapassa o limite de 15 MB."
            ),
        )

    caminho = os.path.join(
        UPLOAD_DIR,
        f"{uuid.uuid4().hex}{extensao}",
    )

    with open(caminho, "wb") as arquivo:
        arquivo.write(conteudo)

    return caminho


def processar_imagem(
    caminho_imagem_original: str,
) -> dict:

    return ImageProcessingService.processar_imagem_lesao(
        caminho_imagem_original=caminho_imagem_original,
        pasta_destino_processadas=PROCESSED_DIR,
    )


def montar_url_imagem(
    nome_arquivo: str,
    pasta_url: str,
) -> str:

    return f"{pasta_url}/{nome_arquivo}"


def metadados_imagem(
    caminho_original: str,
    resultado_opencv: dict,
) -> dict:

    return {
        "imagem_original_url": montar_url_imagem(
            os.path.basename(caminho_original),
            "/uploads",
        ),
        "imagem_processada_url": montar_url_imagem(
            resultado_opencv["nome_arquivo_processado"],
            "/processed",
        ),
        "dimensoes_originais": (
            resultado_opencv["dimensoes_originais"]
        ),
        "dimensoes_processadas": (
            resultado_opencv["dimensoes_processadas"]
        ),
        "analise_tecnica": (
            resultado_opencv["analise_tecnica"]
        ),
        "processamento_aplicado": (
            resultado_opencv["processamento_aplicado"]
        ),
    }


def tratar_erro_processamento(
    erro: Exception,
    etapa: str,
) -> HTTPException:

    logger.exception(
        "Falha interna durante %s.",
        etapa,
    )

    return HTTPException(
        status_code=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        detail=(
            f"Falha interna durante {etapa}. "
            "Consulte os logs do servidor."
        ),
    )


# ============================================================
# COMPARAÇÃO MULTIMODAL
# ============================================================

def gerar_comparacao_segura(
    resultado: ResultadoAnaliseMultimodal,
) -> dict:

    try:
        comparacao = comparar_resultados(
            resultado
        )

        print(
            "\n[COMPARADOR EXECUTADO] "
            f"Provedores: "
            f"{comparacao.provedores_comparados} | "
            f"Concordantes: "
            f"{comparacao.componentes_com_status_concordante} | "
            f"Divergentes: "
            f"{comparacao.componentes_com_status_divergente}",
            flush=True,
        )

        return comparacao.model_dump(
            mode="json"
        )

    except Exception:
        logger.exception(
            "Falha durante a comparação multimodal."
        )

        return {
            "versao": "1.2",
            "erro": (
                "A comparação automática não pôde "
                "ser concluída. As análises individuais "
                "continuam disponíveis."
            ),
            "provedores_comparados": [],
            "componentes": {},
            "validacao_profissional_necessaria": True,
        }


# ============================================================
# FUNÇÕES AUXILIARES — RELATÓRIOS
# ============================================================

def gerar_relatorios_seguro(
    resultado: ResultadoAnaliseMultimodal,
    avaliacao_id: str,
) -> Optional[ConjuntoRelatorios]:

    try:
        conjunto = gerar_relatorios(
            resultado=resultado,
            avaliacao_id=avaliacao_id,
        )

        print(
            "\n[RELATÓRIOS GERADOS] "
            f"Avaliação: {avaliacao_id} | "
            f"Provedores: {list(conjunto.relatorios.keys())}",
            flush=True,
        )

        return conjunto

    except Exception:
        logger.exception(
            "Falha durante a geração dos relatórios."
        )

        return None


def salvar_relatorios_temporarios(
    avaliacao_id: str,
    conjunto: ConjuntoRelatorios,
) -> None:

    with LOCK_RELATORIOS:
        RELATORIOS_TEMPORARIOS[avaliacao_id] = (
            conjunto.model_copy(deep=True)
        )


def obter_conjunto_relatorios(
    avaliacao_id: str,
) -> ConjuntoRelatorios:

    with LOCK_RELATORIOS:
        conjunto = RELATORIOS_TEMPORARIOS.get(
            avaliacao_id
        )

        if conjunto is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Nenhum conjunto de relatórios foi "
                    "encontrado para esta avaliação."
                ),
            )

        return conjunto.model_copy(deep=True)


def obter_relatorio_individual(
    avaliacao_id: str,
    provedor: str,
) -> RelatorioIndividual:

    conjunto = obter_conjunto_relatorios(
        avaliacao_id
    )

    try:
        return selecionar_relatorio(
            conjunto,
            provedor,
        ).model_copy(deep=True)

    except ValueError as erro:
        raise HTTPException(
            status_code=404,
            detail=str(erro),
        ) from erro


# ============================================================
# ROTA INICIAL
# ============================================================

@app.get("/")
def read_root():

    return {
        "status": "online",
        "message": (
            "API Avalia & Trata operacional."
        ),
        "versao": "2.3.0",
        "modulos": {
            "opencv": True,
            "multimodal": True,
            "comparador": True,
            "validador": True,
            "relatorios_individuais": True,
            "edicao_relatorios": True,
            "aprovacao_relatorios": True,
        },
    }


# ============================================================
# ANÁLISE TÉCNICA DA IMAGEM
# ============================================================

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
            localizacao,
            comprimento,
            largura,
            tipoExsudato,
            odor,
            nivelDor,
            queixaPrincipal,
            observacoes,
        )

        caminho_original = (
            await salvar_imagem_enviada(file)
        )

        resultado_opencv = processar_imagem(
            caminho_original
        )

        return {
            "sucesso": True,
            "mensagem": (
                "Imagem recebida e processada "
                "tecnicamente. Nenhum diagnóstico "
                "clínico foi realizado."
            ),
            **metadados_imagem(
                caminho_original,
                resultado_opencv,
            ),
            "dados_clinicos": (
                dados_clinicos.model_dump()
            ),
        }

    except HTTPException:
        raise

    except (
        ValueError,
        ValidationError,
    ) as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro),
        ) from erro

    except Exception as erro:
        raise tratar_erro_processamento(
            erro,
            "o processamento da imagem",
        ) from erro

    finally:
        await file.close()


# ============================================================
# ANÁLISE MULTIMODAL + COMPARAÇÃO + RELATÓRIOS
# ============================================================

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
    provedor: Literal[
        "gemini",
        "openai",
        "kimi",
        "todos",
    ] = Form("gemini"),
):

    try:
        provedores_disponiveis = {
            "gemini": ["gemini"],
            "openai": ["openai"],
            "kimi": ["kimi"],
            "todos": [
                "gemini",
                "openai",
                "kimi",
            ],
        }

        provedores_desejados = (
            provedores_disponiveis[provedor]
        )

        dados_clinicos = montar_dados_clinicos(
            localizacao,
            comprimento,
            largura,
            tipoExsudato,
            odor,
            nivelDor,
            queixaPrincipal,
            observacoes,
        )

        caminho_original = (
            await salvar_imagem_enviada(file)
        )

        resultado_opencv = processar_imagem(
            caminho_original
        )

        caminho_processado = os.path.join(
            PROCESSED_DIR,
            resultado_opencv[
                "nome_arquivo_processado"
            ],
        )

        avaliacao_id = uuid.uuid4().hex

        input_multimodal = AnaliseMultimodalInput(
            avaliacao_id=avaliacao_id,
            caminho_imagem_original=caminho_original,
            caminho_imagem_processada=caminho_processado,
            dimensoes_originais=(
                resultado_opencv["dimensoes_originais"]
            ),
            dimensoes_processadas=(
                resultado_opencv["dimensoes_processadas"]
            ),
            analise_tecnica=AnaliseTecnicaOpenCVInput(
                brilho_medio=(
                    resultado_opencv[
                        "analise_tecnica"
                    ]["brilho_medio"]
                ),
                contraste_global=(
                    resultado_opencv[
                        "analise_tecnica"
                    ]["contraste_global"]
                ),
            ),
            dados_clinicos=dados_clinicos,
        )

        # ----------------------------------------------------
        # 1. EXECUÇÃO DAS IAS
        # ----------------------------------------------------

        resultado: ResultadoAnaliseMultimodal = (
            orquestrador_multimodal.executar_analise_comparativa(
                input_data=input_multimodal,
                provedores_desejados=(
                    provedores_desejados
                ),
            )
        )

        # ----------------------------------------------------
        # 2. COMPARAÇÃO MULTIMODAL
        # ----------------------------------------------------

        comparacao = gerar_comparacao_segura(
            resultado
        )

        # ----------------------------------------------------
        # 3. GERAÇÃO DOS RELATÓRIOS INDIVIDUAIS
        # ----------------------------------------------------

        conjunto_relatorios = gerar_relatorios_seguro(
            resultado=resultado,
            avaliacao_id=avaliacao_id,
        )

        relatorios_json = None

        if conjunto_relatorios is not None:

            # Mantém a comparação já calculada
            # pela rota principal como referência.
            # Evita apresentar duas comparações
            # diferentes no retorno.
            conjunto_relatorios.comparacao = comparacao

            salvar_relatorios_temporarios(
                avaliacao_id,
                conjunto_relatorios,
            )

            relatorios_json = (
                conjunto_relatorios.model_dump(
                    mode="json"
                )
            )

        # ----------------------------------------------------
        # 4. RETORNO DA API
        # ----------------------------------------------------

        return {
            "sucesso": resultado.sucesso_geral,
            "avaliacao_id": avaliacao_id,
            "mensagem": (
                "Pelo menos um provedor concluiu "
                "a análise; os resultados exigem "
                "revisão profissional."
                if resultado.sucesso_geral
                else (
                    "Nenhum provedor concluiu "
                    "a análise. Consulte os "
                    "erros individuais."
                )
            ),
            "provedor_selecionado": provedor,
            "provedores_solicitados": (
                provedores_desejados
            ),
            **metadados_imagem(
                caminho_original,
                resultado_opencv,
            ),
            "dados_clinicos": (
                dados_clinicos.model_dump()
            ),
            "analise_multimodal": (
                resultado.model_dump(
                    mode="json"
                )
            ),
            "comparacao_multimodal": comparacao,
            "relatorios_individuais": relatorios_json,
            "relatorios_disponiveis": (
                list(conjunto_relatorios.relatorios.keys())
                if conjunto_relatorios is not None
                else []
            ),
            "aviso": (
                "Análise automatizada auxiliar, "
                "sujeita a erro. Não confirma "
                "diagnóstico, infecção, profundidade, "
                "fase de cicatrização, tipos de tecido "
                "ou medidas físicas. Marcações e "
                "percentuais sugeridos exigem "
                "conferência do enfermeiro."
            ),
        }

    except HTTPException:
        raise

    except (
        ValueError,
        ValidationError,
    ) as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro),
        ) from erro

    except Exception as erro:
        raise tratar_erro_processamento(
            erro,
            "a análise multimodal",
        ) from erro

    finally:
        await file.close()


# ============================================================
# CONSULTAR TODOS OS RELATÓRIOS DE UMA AVALIAÇÃO
# ============================================================

@app.get("/relatorios/{avaliacao_id}")
def consultar_relatorios(
    avaliacao_id: str,
):

    conjunto = obter_conjunto_relatorios(
        avaliacao_id
    )

    return {
        "sucesso": True,
        "avaliacao_id": avaliacao_id,
        "dados": conjunto.model_dump(
            mode="json"
        ),
    }


# ============================================================
# CONSULTAR RELATÓRIO DE UMA IA
# ============================================================

@app.get("/relatorios/{avaliacao_id}/{provedor}")
def consultar_relatorio_individual(
    avaliacao_id: str,
    provedor: str,
):

    relatorio = obter_relatorio_individual(
        avaliacao_id,
        provedor,
    )

    return {
        "sucesso": True,
        "avaliacao_id": avaliacao_id,
        "provedor": provedor,
        "relatorio": relatorio.model_dump(
            mode="json"
        ),
    }


# ============================================================
# EDITAR RELATÓRIO SELECIONADO
# ============================================================

@app.patch("/relatorios/{avaliacao_id}/{provedor}")
def editar_relatorio_endpoint(
    avaliacao_id: str,
    provedor: str,
    dados: EditarCampoRequest,
):

    with LOCK_RELATORIOS:

        conjunto = RELATORIOS_TEMPORARIOS.get(
            avaliacao_id
        )

        if conjunto is None:
            raise HTTPException(
                status_code=404,
                detail="Avaliação não encontrada.",
            )

        if provedor not in conjunto.relatorios:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Relatório do provedor "
                    f"'{provedor}' não encontrado."
                ),
            )

        relatorio_atual = (
            conjunto.relatorios[provedor]
        )

        try:
            relatorio_editado = editar_campo(
                relatorio=relatorio_atual,
                campo=dados.campo,
                novo_valor=dados.novo_valor,
                profissional_id=dados.profissional_id,
            )

        except ValueError as erro:
            raise HTTPException(
                status_code=400,
                detail=str(erro),
            ) from erro

        # Substitui apenas a cópia editável
        # daquele provedor.
        # A resposta original permanece preservada.

        conjunto.relatorios[provedor] = (
            relatorio_editado
        )

        retorno = relatorio_editado.model_dump(
            mode="json"
        )

    return {
        "sucesso": True,
        "mensagem": (
            "Campo atualizado com sucesso. "
            "A análise original foi preservada."
        ),
        "avaliacao_id": avaliacao_id,
        "provedor": provedor,
        "relatorio": retorno,
    }


# ============================================================
# APROVAR RELATÓRIO SELECIONADO
# ============================================================

@app.post(
    "/relatorios/{avaliacao_id}/{provedor}/aprovar"
)
def aprovar_relatorio_endpoint(
    avaliacao_id: str,
    provedor: str,
    dados: AprovarRelatorioRequest,
):

    with LOCK_RELATORIOS:

        conjunto = RELATORIOS_TEMPORARIOS.get(
            avaliacao_id
        )

        if conjunto is None:
            raise HTTPException(
                status_code=404,
                detail="Avaliação não encontrada.",
            )

        if provedor not in conjunto.relatorios:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Relatório do provedor "
                    f"'{provedor}' não encontrado."
                ),
            )

        relatorio_atual = (
            conjunto.relatorios[provedor]
        )

        try:
            relatorio_aprovado = aprovar_relatorio(
                relatorio=relatorio_atual,
                profissional_id=dados.profissional_id,
            )

        except ValueError as erro:
            raise HTTPException(
                status_code=400,
                detail=str(erro),
            ) from erro

        conjunto.relatorios[provedor] = (
            relatorio_aprovado
        )

        retorno = relatorio_aprovado.model_dump(
            mode="json"
        )

    return {
        "sucesso": True,
        "mensagem": (
            "Relatório aprovado pelo profissional. "
            "A versão aprovada está bloqueada "
            "para novas edições."
        ),
        "avaliacao_id": avaliacao_id,
        "provedor": provedor,
        "relatorio": retorno,
    }
