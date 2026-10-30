"""Persistencia e consulta autenticada de comparacoes multimodais (MySQL)."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import JSON, Column, DateTime, Integer, String, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import Base, get_db
from models import Analise, Enfermeiro
from routers.auth import obter_enfermeiro_atual

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Comparacoes Multimodais"])


class ComparacaoMultimodal(Base):
    __tablename__ = "comparacoes_multimodais"

    id_comparacao = Column(String(36), primary_key=True)
    id_analise_fk = Column(Integer, nullable=False, index=True)
    avaliacao_id = Column(String(64), nullable=False, unique=True, index=True)
    provedores_comparados = Column(JSON, nullable=False)
    conteudo = Column(JSON, nullable=False)
    criado_em = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


def garantir_tabela(db: Session) -> None:
    """Cria somente a tabela nova, sem alterar as tabelas existentes."""
    try:
        ComparacaoMultimodal.__table__.create(bind=db.get_bind(), checkfirst=True)
    except SQLAlchemyError as erro:
        logger.exception("Falha ao verificar/criar tabela comparacoes_multimodais")
        raise HTTPException(status_code=500, detail="Falha ao preparar tabela de comparacoes no MySQL.") from erro


def verificar_acesso(analise_id: int, db: Session, enfermeiro: Enfermeiro) -> None:
    analise = db.scalar(select(Analise).where(
        Analise.id_analise == analise_id,
        Analise.id_enfermeiro_fk == enfermeiro.id_enfermeiro,
        Analise.deleted_at.is_(None),
    ))
    if analise is None:
        raise HTTPException(status_code=404, detail="Analise nao encontrada ou acesso nao autorizado.")


def salvar_comparacao(
    db: Session,
    analise_id: int,
    avaliacao_id: str,
    comparacao: dict,
    provedores_com_sucesso: set[str],
) -> dict:
    """Salva uma comparacao por execucao; nunca substitui historicos anteriores."""
    if "erro" in comparacao or len(provedores_com_sucesso) < 2:
        return {"salva": False, "motivo": "Comparacao indisponivel ou menos de dois provedores concluidos."}

    garantir_tabela(db)
    registro = ComparacaoMultimodal(
        id_comparacao=str(uuid4()),
        id_analise_fk=analise_id,
        avaliacao_id=avaliacao_id,
        provedores_comparados=sorted(provedores_com_sucesso),
        conteudo=comparacao,
    )
    db.add(registro)
    try:
        db.commit()
        db.refresh(registro)
    except SQLAlchemyError as erro:
        db.rollback()
        logger.exception("Falha ao salvar comparacao multimodal")
        raise HTTPException(status_code=500, detail="Relatorios salvos, mas houve falha ao salvar a comparacao.") from erro
    return {"salva": True, "id_comparacao": registro.id_comparacao, "avaliacao_id": avaliacao_id}


def serializar_resumo(registro: ComparacaoMultimodal) -> dict:
    return {
        "id_comparacao": registro.id_comparacao,
        "analise_id": registro.id_analise_fk,
        "avaliacao_id": registro.avaliacao_id,
        "provedores_comparados": registro.provedores_comparados,
        "criado_em": registro.criado_em.isoformat() if registro.criado_em else None,
    }


@router.get("/analises/{analise_id}/comparacoes")
def listar_comparacoes(
    analise_id: int,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    verificar_acesso(analise_id, db, enfermeiro)
    garantir_tabela(db)
    registros = db.scalars(
        select(ComparacaoMultimodal)
        .where(ComparacaoMultimodal.id_analise_fk == analise_id)
        .order_by(ComparacaoMultimodal.criado_em.desc())
    ).all()
    return {"analise_id": analise_id, "total": len(registros), "comparacoes": [serializar_resumo(r) for r in registros]}


@router.get("/analises/{analise_id}/comparacoes/{id_comparacao}")
def obter_comparacao(
    analise_id: int,
    id_comparacao: str,
    db: Session = Depends(get_db),
    enfermeiro: Enfermeiro = Depends(obter_enfermeiro_atual),
):
    verificar_acesso(analise_id, db, enfermeiro)
    garantir_tabela(db)
    registro = db.scalar(select(ComparacaoMultimodal).where(
        ComparacaoMultimodal.id_analise_fk == analise_id,
        ComparacaoMultimodal.id_comparacao == id_comparacao,
    ))
    if registro is None:
        raise HTTPException(status_code=404, detail="Comparacao nao encontrada.")
    return {**serializar_resumo(registro), "comparacao_multimodal": registro.conteudo}
