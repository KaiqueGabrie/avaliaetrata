
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Enfermeiro, Paciente, Anamnese, LogAuditoria
from routers.auth import obter_enfermeiro_atual

from schemas.paciente import (
    PacienteCriar,
    PacienteAtualizar,
    PacienteResposta,
    AnamneseDados,
    AnamneseResposta,
)


router = APIRouter(
    prefix="/pacientes",
    tags=["Pacientes e Anamnese"],
)


def registrar_log(
    db: Session,
    enfermeiro_id: int,
    acao: str,
    entidade: str,
    registro_id: int,
):
    db.add(
        LogAuditoria(
            id_enfermeiro_fk=enfermeiro_id,
            acao=acao,
            entidade=entidade,
            registro_id=str(registro_id),
            detalhes={"origem": "api"},
        )
    )


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


def obter_anamnese_ativa(
    db: Session,
    paciente_id: int,
) -> Anamnese | None:
    return db.scalar(
        select(Anamnese).where(
            Anamnese.id_paciente_fk == paciente_id,
            Anamnese.deleted_at.is_(None),
        )
    )


def salvar_alteracoes(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflito com um registro existente.",
        )


# ==========================================
# CADASTRAR PACIENTE
# ==========================================

@router.post(
    "",
    response_model=PacienteResposta,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_paciente(
    dados: PacienteCriar,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    paciente = Paciente(
        **dados.model_dump(),
        id_enfermeiro_fk=enfermeiro.id_enfermeiro,
    )

    db.add(paciente)
    db.flush()

    registrar_log(
        db,
        enfermeiro.id_enfermeiro,
        "CADASTRO_PACIENTE",
        "paciente",
        paciente.id_paciente,
    )

    salvar_alteracoes(db)
    db.refresh(paciente)

    return paciente


# ==========================================
# LISTAR PACIENTES
# ==========================================

@router.get(
    "",
    response_model=list[PacienteResposta],
)
def listar_pacientes(
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    return db.scalars(
        select(Paciente).where(
            Paciente.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
            Paciente.deleted_at.is_(None),
        ).order_by(Paciente.nome_completo)
    ).all()


# ==========================================
# CONSULTAR PACIENTE
# ==========================================

@router.get(
    "/{paciente_id}",
    response_model=PacienteResposta,
)
def consultar_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    return obter_paciente_autorizado(
        paciente_id, enfermeiro, db
    )


# ==========================================
# ATUALIZAR PACIENTE
# ==========================================

@router.patch(
    "/{paciente_id}",
    response_model=PacienteResposta,
)
def atualizar_paciente(
    paciente_id: int,
    dados: PacienteAtualizar,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    paciente = obter_paciente_autorizado(
        paciente_id, enfermeiro, db
    )

    alteracoes = dados.model_dump(exclude_unset=True)

    for campo, valor in alteracoes.items():
        if campo == "nome_completo" and valor is None:
            raise HTTPException(
                status_code=422,
                detail="Nome completo nao pode ser nulo.",
            )
        setattr(paciente, campo, valor)

    registrar_log(
        db,
        enfermeiro.id_enfermeiro,
        "ATUALIZACAO_PACIENTE",
        "paciente",
        paciente.id_paciente,
    )

    salvar_alteracoes(db)
    db.refresh(paciente)

    return paciente


# ==========================================
# CADASTRAR ANAMNESE
# ==========================================

@router.post(
    "/{paciente_id}/anamnese",
    response_model=AnamneseResposta,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_anamnese(
    paciente_id: int,
    dados: AnamneseDados,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    obter_paciente_autorizado(
        paciente_id, enfermeiro, db
    )

    existente = db.scalar(
        select(Anamnese).where(
            Anamnese.id_paciente_fk == paciente_id
        )
    )

    if existente is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Paciente ja possui anamnese. "
                "Utilize PATCH para atualizar."
            ),
        )

    anamnese = Anamnese(
        id_paciente_fk=paciente_id,
        **dados.model_dump(),
    )

    db.add(anamnese)
    db.flush()

    registrar_log(
        db,
        enfermeiro.id_enfermeiro,
        "CADASTRO_ANAMNESE",
        "anamnese",
        anamnese.id_anamnese,
    )

    salvar_alteracoes(db)
    db.refresh(anamnese)

    return anamnese


# ==========================================
# CONSULTAR ANAMNESE
# ==========================================

@router.get(
    "/{paciente_id}/anamnese",
    response_model=AnamneseResposta,
)
def consultar_anamnese(
    paciente_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    obter_paciente_autorizado(
        paciente_id, enfermeiro, db
    )

    anamnese = obter_anamnese_ativa(
        db, paciente_id
    )

    if anamnese is None:
        raise HTTPException(
            status_code=404,
            detail="Anamnese nao encontrada.",
        )

    return anamnese


# ==========================================
# ATUALIZAR ANAMNESE
# ==========================================

@router.patch(
    "/{paciente_id}/anamnese",
    response_model=AnamneseResposta,
)
def atualizar_anamnese(
    paciente_id: int,
    dados: AnamneseDados,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    obter_paciente_autorizado(
        paciente_id, enfermeiro, db
    )

    anamnese = obter_anamnese_ativa(
        db, paciente_id
    )

    if anamnese is None:
        raise HTTPException(
            status_code=404,
            detail="Anamnese nao encontrada.",
        )

    alteracoes = dados.model_dump(exclude_unset=True)

    for campo, valor in alteracoes.items():
        setattr(anamnese, campo, valor)

    registrar_log(
        db,
        enfermeiro.id_enfermeiro,
        "ATUALIZACAO_ANAMNESE",
        "anamnese",
        anamnese.id_anamnese,
    )

    salvar_alteracoes(db)
    db.refresh(anamnese)

    return anamnese
