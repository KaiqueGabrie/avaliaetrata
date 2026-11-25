
import hashlib
import logging
import os

from io import BytesIO
from uuid import uuid4
from xml.sax.saxutils import escape

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
)

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Enfermeiro
from models.consentimento import TermoConsentimento

from routers.auth import obter_enfermeiro_atual
from routers.pacientes import (
    obter_paciente_autorizado,
    registrar_log,
)

from services.storage import obter_cliente


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pacientes",
    tags=["Consentimento"],
)

LIMITE_PDF = 5 * 1024 * 1024

HEADERS_PRIVADOS = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
}


def bucket_termos():
    nome = os.getenv(
        "SUPABASE_CONSENT_BUCKET",
        "",
    ).strip()

    if not nome:
        raise HTTPException(
            status_code=503,
            detail="Armazenamento de termos nao configurado.",
        )

    return obter_cliente().storage.from_(nome)


def serializar_termo(termo: TermoConsentimento) -> dict:
    return {
        "id_termo": termo.id_termo,
        "id_paciente": termo.id_paciente_fk,
        "tamanho_bytes": termo.tamanho_bytes,
        "declarado_assinado": termo.declarado_assinado,
        "data_registro": termo.created_at.isoformat(),
    }


def validar_pdf(conteudo: bytes):
    if not conteudo:
        raise HTTPException(
            status_code=422,
            detail="Arquivo vazio.",
        )

    if len(conteudo) > LIMITE_PDF:
        raise HTTPException(
            status_code=413,
            detail="O PDF deve possuir ate 5 MB.",
        )

    if not conteudo.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=422,
            detail="O arquivo deve ser um PDF valido.",
        )

    try:
        leitor = PdfReader(
            BytesIO(conteudo),
            strict=False,
        )

        if leitor.is_encrypted:
            raise ValueError("PDF protegido.")

        if len(leitor.pages) < 1:
            raise ValueError("PDF sem paginas.")

    except Exception as erro:
        raise HTTPException(
            status_code=422,
            detail=(
                "PDF invalido, danificado ou protegido "
                "por senha."
            ),
        ) from erro


def gerar_pdf_modelo(paciente, enfermeiro) -> bytes:
    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=35,
        bottomMargin=35,
        title="Modelo de Termo de Consentimento",
        author="Avalia & Trata",
    )

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloTermo",
        parent=estilos["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#005088"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    subtitulo = ParagraphStyle(
        "SubtituloTermo",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#005088"),
        spaceBefore=10,
        spaceAfter=6,
    )

    texto = ParagraphStyle(
        "TextoTermo",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=7,
    )

    aviso = ParagraphStyle(
        "AvisoTermo",
        parent=texto,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#92400e"),
        spaceAfter=14,
    )

    elementos = [
        Paragraph(
            "Avalia &amp; Trata",
            titulo,
        ),

        Paragraph(
            "MODELO DE TERMO DE CONSENTIMENTO",
            titulo,
        ),

        Paragraph(
            "Modelo acadêmico — sujeito à revisão e "
            "aprovação institucional antes do uso real.",
            aviso,
        ),
    ]

    def adicionar_titulo(valor):
        elementos.append(
            Paragraph(escape(valor), subtitulo)
        )

    def adicionar_texto(valor):
        elementos.append(
            Paragraph(escape(valor), texto)
        )

    adicionar_titulo("1. Identificação")

    adicionar_texto(
        f"Paciente: {paciente.nome_completo}"
    )

    adicionar_texto(
        f"Prontuário: {paciente.id_paciente}"
    )

    adicionar_texto(
        f"Profissional responsável: {enfermeiro.nome}"
    )

    adicionar_texto(
        "Instituição responsável: __________________________"
    )

    adicionar_titulo("2. Finalidade")

    adicionar_texto(
        "Este documento destina-se ao registro da autorização "
        "para aquisição e utilização de fotografias relacionadas "
        "à avaliação e ao acompanhamento de lesões cutâneas "
        "por meio do sistema Avalia & Trata."
    )

    adicionar_titulo("3. Processamento das informações")

    adicionar_texto(
        "O sistema utiliza informações clínicas e fotografias "
        "para organizar registros e produzir análises "
        "automatizadas de apoio ao profissional."
    )

    adicionar_texto(
        "As análises podem envolver serviços externos de "
        "inteligência artificial, incluindo Gemini, OpenAI e Kimi. "
        "A instituição deverá informar previamente os serviços "
        "utilizados, as condições de processamento e os riscos "
        "associados ao tratamento dessas informações."
    )

    adicionar_titulo("4. Limitações")

    adicionar_texto(
        "Os resultados automatizados podem apresentar erros "
        "e não substituem a avaliação clínica presencial, "
        "a decisão ou a responsabilidade do profissional."
    )

    adicionar_titulo("5. Privacidade e esclarecimentos")

    adicionar_texto(
        "Antes da assinatura, deverão ser esclarecidos os "
        "procedimentos de armazenamento, compartilhamento, "
        "prazo de retenção, acesso aos registros e os canais "
        "para exercício dos direitos do titular."
    )

    adicionar_texto(
        "Contato institucional: ______________________________"
    )

    adicionar_texto(
        "Prazo de retenção: __________________________________"
    )

    adicionar_titulo("6. Manifestação de vontade")

    adicionar_texto(
        "Declaro que recebi os esclarecimentos necessários "
        "sobre a utilização das informações e que tive "
        "oportunidade de apresentar dúvidas antes de manifestar "
        "minha decisão."
    )

    adicionar_texto(
        "Decisão: (  ) Autorizo    (  ) Não autorizo"
    )

    elementos.append(Spacer(1, 18))

    adicionar_texto(
        "Assinatura do paciente ou responsável:"
    )

    adicionar_texto(
        "__________________________________________________"
    )

    adicionar_texto(
        "Assinatura do profissional:"
    )

    adicionar_texto(
        "__________________________________________________"
    )

    adicionar_texto(
        "Data: ______ / ______ / __________"
    )

    documento.build(elementos)

    return buffer.getvalue()


# ==========================================
# GERAR MODELO DE TERMO
# ==========================================

@router.get("/{paciente_id}/consentimento/modelo")
def gerar_modelo_consentimento(
    paciente_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(
        obter_enfermeiro_atual
    ),
):
    paciente = obter_paciente_autorizado(
        paciente_id,
        enfermeiro,
        db,
    )

    conteudo = gerar_pdf_modelo(
        paciente,
        enfermeiro,
    )

    registrar_log(
        db,
        enfermeiro.id_enfermeiro,
        "GERACAO_MODELO_CONSENTIMENTO",
        "paciente",
        paciente_id,
    )

    db.commit()

    return Response(
        content=conteudo,
        media_type="application/pdf",
        headers={
            **HEADERS_PRIVADOS,
            "Content-Disposition": (
                f'attachment; filename="termo-modelo-{paciente_id}.pdf"'
            ),
        },
    )


# ==========================================
# LISTAR TERMOS REGISTRADOS
# ==========================================

@router.get("/{paciente_id}/consentimento")
def listar_termos(
    paciente_id: int,
    response: Response,
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

    response.headers["Cache-Control"] = (
        "private, no-store"
    )

    termos = db.scalars(
        select(TermoConsentimento)
        .where(
            TermoConsentimento.id_paciente_fk == paciente_id
        )
        .order_by(
            TermoConsentimento.id_termo.desc()
        )
    ).all()

    return [
        serializar_termo(termo)
        for termo in termos
    ]


# ==========================================
# REGISTRAR TERMO ASSINADO
# ==========================================

@router.post(
    "/{paciente_id}/consentimento",
    status_code=201,
)
def registrar_termo(
    paciente_id: int,
    arquivo: UploadFile = File(...),
    declarado_assinado: bool = Form(...),
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

    if not declarado_assinado:
        raise HTTPException(
            status_code=422,
            detail="Confirme o recebimento do termo assinado.",
        )

    try:
        conteudo = arquivo.file.read(
            LIMITE_PDF + 1
        )
    finally:
        arquivo.file.close()

    validar_pdf(conteudo)

    hash_documento = hashlib.sha256(
        conteudo
    ).hexdigest()

    existente = db.scalar(
        select(TermoConsentimento).where(
            TermoConsentimento.id_paciente_fk == paciente_id,
            TermoConsentimento.sha256 == hash_documento,
        )
    )

    if existente is not None:
        raise HTTPException(
            status_code=409,
            detail="Este documento ja foi registrado.",
        )

    chave = (
        f"{enfermeiro.id_enfermeiro}/"
        f"{paciente_id}/"
        f"{uuid4().hex}.pdf"
    )

    bucket = bucket_termos()

    try:
        bucket.upload(
            path=chave,
            file=conteudo,
            file_options={
                "content-type": "application/pdf",
                "upsert": "false",
            },
        )

    except Exception as erro:
        logger.exception(
            "Falha ao armazenar termo de consentimento."
        )

        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel armazenar o documento.",
        ) from erro

    try:
        termo = TermoConsentimento(
            id_paciente_fk=paciente_id,
            id_enfermeiro_fk=enfermeiro.id_enfermeiro,
            chave_storage=chave,
            tamanho_bytes=len(conteudo),
            sha256=hash_documento,
            declarado_assinado=True,
        )

        db.add(termo)
        db.flush()

        registrar_log(
            db,
            enfermeiro.id_enfermeiro,
            "REGISTRO_TERMO_CONSENTIMENTO",
            "termo_consentimento",
            termo.id_termo,
        )

        db.commit()
        db.refresh(termo)

        return serializar_termo(termo)

    except Exception as erro:
        db.rollback()

        logger.exception(
            "Falha ao registrar os metadados do termo."
        )

        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel confirmar o registro.",
        ) from erro


# ==========================================
# BAIXAR DOCUMENTO REGISTRADO
# ==========================================

@router.get(
    "/{paciente_id}/consentimento/{termo_id}/arquivo"
)
def baixar_termo(
    paciente_id: int,
    termo_id: int,
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

    termo = db.scalar(
        select(TermoConsentimento).where(
            TermoConsentimento.id_termo == termo_id,
            TermoConsentimento.id_paciente_fk == paciente_id,
        )
    )

    if termo is None:
        raise HTTPException(
            status_code=404,
            detail="Documento nao encontrado.",
        )

    prefixo = (
        f"{termo.id_enfermeiro_fk}/"
        f"{paciente_id}/"
    )

    if (
        not termo.chave_storage.startswith(prefixo)
        or ".." in termo.chave_storage.split("/")
    ):
        raise HTTPException(
            status_code=500,
            detail="Referencia de documento invalida.",
        )

    try:
        conteudo = bucket_termos().download(
            termo.chave_storage
        )

    except Exception as erro:
        logger.exception(
            "Falha ao recuperar termo de consentimento."
        )

        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel recuperar o documento.",
        ) from erro

    if (
        hashlib.sha256(conteudo).hexdigest()
        != termo.sha256
    ):
        raise HTTPException(
            status_code=500,
            detail="Falha na verificacao do documento.",
        )

    registrar_log(
        db,
        enfermeiro.id_enfermeiro,
        "DOWNLOAD_TERMO_CONSENTIMENTO",
        "termo_consentimento",
        termo.id_termo,
    )

    db.commit()

    return Response(
        content=conteudo,
        media_type="application/pdf",
        headers={
            **HEADERS_PRIVADOS,
            "Content-Disposition": (
                f'attachment; filename="termo-{termo_id}.pdf"'
            ),
        },
    )
