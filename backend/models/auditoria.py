
from datetime import datetime

from sqlalchemy import (
    BigInteger, Integer, String, DateTime,
    JSON, ForeignKey, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    id_log: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    id_enfermeiro_fk: Mapped[int | None] = mapped_column(
        ForeignKey("enfermeiro.id_enfermeiro")
    )

    acao: Mapped[str] = mapped_column(String(100))
    entidade: Mapped[str] = mapped_column(String(100))
    registro_id: Mapped[str | None] = mapped_column(String(50))

    id_analise_fk: Mapped[int | None] = mapped_column(
        ForeignKey("analise.id_analise")
    )

    detalhes: Mapped[dict | None] = mapped_column(JSON)

    data_evento: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_log_data", "data_evento"),
        Index("idx_log_entidade", "entidade", "registro_id"),
    )
