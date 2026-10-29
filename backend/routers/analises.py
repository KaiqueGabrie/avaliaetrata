
import logging
import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db

from models import (
    Enfermeiro,
    Paciente,
    Analise,
    Imagem,
    LogAuditoria,
)

from routers.auth import obter_enfermeiro_atual

from schemas.analise import (
    AnaliseCriar,
    AnaliseAtualizar,
    AnaliseResposta,
    AnaliseResumo,
)

from services.image_processing import ImageProcessingService


# ============================================================
# CONFIGURAÇÕES
# ============================================================

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pacientes/{paciente_id}/analises",
    tags=["Analises"],
)

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

EXTENSOES_PERMITIDAS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

TAMANHO_MAXIMO_IMAGEM = 15 * 1024 * 1024


# ============================================================
# FUNÇÕES AUXILIARES — AUTORIZAÇÃO
# ============================================================

def obter_paciente_autorizado(
    paciente_id: int,
    enfermeiro: Enfermeiro,
    db: Session,
) -> Paciente:

    paciente = db.scalar(
        select(Paciente).where(
            Paciente.id_paciente == paciente_id,
            Paciente.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
            Paciente.deleted_at.is_(None),
        )
    )

    if paciente is None:
        raise HTTPException(
            status_code=404,
            detail="Paciente nao encontrado.",
        )

    return paciente


def obter_analise_autorizada(
    paciente_id: int,
    analise_id: int,
    enfermeiro: Enfermeiro,
    db: Session,
) -> Analise:

    obter_paciente_autorizado(
        paciente_id,
        enfermeiro,
        db,
    )

    analise = db.scalar(
        select(Analise).where(
            Analise.id_analise == analise_id,
            Analise.id_paciente_fk == paciente_id,
            Analise.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
            Analise.deleted_at.is_(None),
        )
    )

    if analise is None:
        raise HTTPException(
            status_code=404,
            detail="Analise nao encontrada.",
        )

    return analise


# ============================================================
# FUNÇÕES AUXILIARES — BANCO DE DADOS
# ============================================================

def registrar_log(
    db: Session,
    enfermeiro_id: int,
    acao: str,
    registro_id: int,
):

    db.add(
        LogAuditoria(
            id_enfermeiro_fk=enfermeiro_id,
            acao=acao,
            entidade="analise",
            registro_id=str(registro_id),
            detalhes={
                "origem": "api",
            },
        )
    )


def salvar_alteracoes(db: Session):

    try:
        db.commit()

    except IntegrityError as erro:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Conflito ao salvar os dados.",
        ) from erro

    except Exception:
        db.rollback()
        raise


# ============================================================
# FUNÇÕES AUXILIARES — ARQUIVOS
# ============================================================

def remover_arquivo(caminho: Path | None):

    if caminho is None:
        return

    try:
        caminho.unlink(missing_ok=True)

    except OSError:
        logger.warning(
            "Nao foi possivel remover arquivo temporario.",
            exc_info=True,
        )


def validar_extensao(filename: str | None) -> str:

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Arquivo sem nome valido.",
        )

    extensao = Path(filename).suffix.lower()

    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Formato nao permitido. "
                "Utilize JPG, JPEG, PNG ou WEBP."
            ),
        )

    return extensao


async def salvar_upload(
    arquivo: UploadFile,
) -> Path:

    extensao = validar_extensao(
        arquivo.filename
    )

    caminho = UPLOAD_DIR / (
        f"{uuid.uuid4().hex}{extensao}"
    )

    total = 0

    try:
        with caminho.open("wb") as destino:

            while True:
                bloco = await arquivo.read(
                    1024 * 1024
                )

                if not bloco:
                    break

                total += len(bloco)

                if total > TAMANHO_MAXIMO_IMAGEM:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Imagem ultrapassa "
                            "o limite de 15 MB."
                        ),
                    )

                destino.write(bloco)

        if total == 0:
            raise HTTPException(
                status_code=400,
                detail="Arquivo enviado esta vazio.",
            )

        # Confere o formato real do arquivo.
        # A extensao sozinha nao e suficiente.
        import cv2

        imagem_teste = cv2.imread(
            str(caminho)
        )

        if imagem_teste is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Arquivo invalido ou "
                    "imagem nao reconhecida."
                ),
            )

        return caminho

    except Exception:
        remover_arquivo(caminho)
        raise


# ============================================================
# CADASTRAR ANÁLISE
# ============================================================

@router.post(
    "",
    response_model=AnaliseResposta,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_analise(
    paciente_id: int,
    dados: AnaliseCriar,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    obter_paciente_autorizado(
        paciente_id,
        enfermeiro,
        db,
    )

    analise = Analise(
        id_paciente_fk=paciente_id,
        id_enfermeiro_fk=enfermeiro.id_enfermeiro,
        queixa_principal=dados.queixa_principal,
        observacoes_clinicas=dados.observacoes_clinicas,
        contexto_clinico_json=dados.contexto_clinico_json,
        status="pendente",
    )

    db.add(analise)
    db.flush()

    registrar_log(
        db,
        enfermeiro.id_enfermeiro,
        "CADASTRO_ANALISE",
        analise.id_analise,
    )

    salvar_alteracoes(db)
    db.refresh(analise)

    return analise


# ============================================================
# LISTAR ANÁLISES DO PACIENTE
# ============================================================

@router.get(
    "",
    response_model=list[AnaliseResumo],
)
def listar_analises(
    paciente_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    obter_paciente_autorizado(
        paciente_id,
        enfermeiro,
        db,
    )

    return db.scalars(
        select(Analise)
        .where(
            Analise.id_paciente_fk == paciente_id,
            Analise.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
            Analise.deleted_at.is_(None),
        )
        .order_by(
            Analise.data_analise.desc(),
            Analise.id_analise.desc(),
        )
    ).all()


# ============================================================
# CONSULTAR ANÁLISE ESPECÍFICA
# ============================================================

@router.get(
    "/{analise_id}",
    response_model=AnaliseResposta,
)
def consultar_analise(
    paciente_id: int,
    analise_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    return obter_analise_autorizada(
        paciente_id,
        analise_id,
        enfermeiro,
        db,
    )


# ============================================================
# ATUALIZAR DADOS CLÍNICOS DA ANÁLISE
# ============================================================

@router.patch(
    "/{analise_id}",
    response_model=AnaliseResposta,
)
def atualizar_analise(
    paciente_id: int,
    analise_id: int,
    dados: AnaliseAtualizar,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    analise = obter_analise_autorizada(
        paciente_id,
        analise_id,
        enfermeiro,
        db,
    )

    if analise.status != "pendente":
        raise HTTPException(
            status_code=409,
            detail=(
                "Somente analises pendentes "
                "podem ser alteradas."
            ),
        )

    alteracoes = dados.model_dump(
        exclude_unset=True
    )

    for campo, valor in alteracoes.items():
        setattr(
            analise,
            campo,
            valor,
        )

    if alteracoes:
        registrar_log(
            db,
            enfermeiro.id_enfermeiro,
            "ATUALIZACAO_ANALISE",
            analise.id_analise,
        )

        salvar_alteracoes(db)
        db.refresh(analise)

    return analise


# ============================================================
# ENVIAR E PROCESSAR IMAGEM DA ANÁLISE
# ============================================================

@router.post(
    "/{analise_id}/imagem",
    status_code=status.HTTP_201_CREATED,
)
async def enviar_imagem_analise(
    paciente_id: int,
    analise_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):

    caminho_original = None
    caminho_processado = None

    try:
        analise = obter_analise_autorizada(
            paciente_id,
            analise_id,
            enfermeiro,
            db,
        )

        if analise.status != "pendente":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Esta analise nao esta pendente "
                    "e nao pode receber imagem."
                ),
            )

        imagem_existente = db.scalar(
            select(Imagem).where(
                Imagem.id_analise_fk == analise_id
            )
        )

        if imagem_existente is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Esta analise ja possui imagem. "
                    "Crie outra analise para "
                    "registrar uma nova avaliacao."
                ),
            )

        # ----------------------------------------------------
        # 1. SALVAR IMAGEM ORIGINAL
        # ----------------------------------------------------

        caminho_original = await salvar_upload(
            file
        )

        # ----------------------------------------------------
        # 2. EXECUTAR OPENCV EXISTENTE
        # ----------------------------------------------------

        resultado_opencv = (
            ImageProcessingService
            .processar_imagem_lesao(
                caminho_imagem_original=str(
                    caminho_original
                ),
                pasta_destino_processadas=str(
                    PROCESSED_DIR
                ),
            )
        )

        nome_processado = resultado_opencv[
            "nome_arquivo_processado"
        ]

        # O servico deve devolver apenas o nome
        # do arquivo gerado dentro de processed.
        if (
            not isinstance(nome_processado, str)
            or not nome_processado
            or Path(nome_processado).name != nome_processado
        ):
            raise ValueError(
                "Nome de arquivo processado invalido."
            )

        caminho_processado = (
            PROCESSED_DIR / nome_processado
        )

        if not caminho_processado.is_file():
            raise ValueError(
                "Imagem processada nao foi encontrada."
            )

        # ----------------------------------------------------
        # 3. SALVAR REGISTRO NA TABELA IMAGEM
        # ----------------------------------------------------

        imagem = Imagem(
            id_analise_fk=analise_id,
            caminho_imagem_original=(
                f"uploads/{caminho_original.name}"
            ),
            caminho_imagem_marcada=(
                f"processed/{caminho_processado.name}"
            ),
        )

        db.add(imagem)

        # ----------------------------------------------------
        # 4. REGISTRAR METADADOS TECNICOS
        # ----------------------------------------------------

        contexto_atual = dict(
            analise.contexto_clinico_json or {}
        )

        contexto_atual["processamento_opencv"] = {
            "dimensoes_originais": (
                resultado_opencv.get(
                    "dimensoes_originais"
                )
            ),
            "dimensoes_processadas": (
                resultado_opencv.get(
                    "dimensoes_processadas"
                )
            ),
            "analise_tecnica": (
                resultado_opencv.get(
                    "analise_tecnica"
                )
            ),
            "processamento_aplicado": (
                resultado_opencv.get(
                    "processamento_aplicado"
                )
            ),
        }

        analise.contexto_clinico_json = (
            contexto_atual
        )

        # O OpenCV atual nao fornece uma area
        # fisica validada nem percentuais de
        # tecidos clinicamente confirmados.
        #
        # Por isso, nao preenchemos:
        # area_estimada
        # tecido_granulacao
        # tecido_esfacelo
        # tecido_necrose

        analise.status = "concluida"

        db.flush()

        registrar_log(
            db,
            enfermeiro.id_enfermeiro,
            "PROCESSAMENTO_IMAGEM",
            analise.id_analise,
        )

        salvar_alteracoes(db)

        db.refresh(analise)
        db.refresh(imagem)

        # ----------------------------------------------------
        # 5. RETORNO
        # ----------------------------------------------------

        return {
            "sucesso": True,
            "mensagem": (
                "Imagem processada e vinculada "
                "a analise com sucesso. "
                "Nenhum diagnostico clinico "
                "foi realizado."
            ),
            "id_paciente": paciente_id,
            "id_analise": analise.id_analise,
            "id_imagem": imagem.id_imagem,
            "status_analise": analise.status,
            "imagem_original_url": (
                f"/uploads/{caminho_original.name}"
            ),
            "imagem_processada_url": (
                f"/processed/{caminho_processado.name}"
            ),
            "analise_tecnica": (
                resultado_opencv.get(
                    "analise_tecnica"
                )
            ),
            "processamento_aplicado": (
                resultado_opencv.get(
                    "processamento_aplicado"
                )
            ),
            "aviso": (
                "Resultados automatizados "
                "exigem revisao profissional."
            ),
        }

    except HTTPException:
        db.rollback()

        remover_arquivo(caminho_original)
        remover_arquivo(caminho_processado)

        raise

    except Exception as erro:
        db.rollback()

        remover_arquivo(caminho_original)
        remover_arquivo(caminho_processado)

        logger.exception(
            "Falha ao processar imagem da analise %s.",
            analise_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Falha interna durante o "
                "processamento da imagem."
            ),
        ) from erro

    finally:
        await file.close()
