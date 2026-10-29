
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, String, Text, DateTime,
    DECIMAL, JSON, ForeignKey, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Analise(Base):
    __tablename__ = "analise"

    id_analise: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    id_paciente_fk: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente")
    )
    id_enfermeiro_fk: Mapped[int] = mapped_column(
        ForeignKey("enfermeiro.id_enfermeiro")
    )

    data_analise: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    queixa_principal: Mapped[str | None] = mapped_column(Text)
    observacoes_clinicas: Mapped[str | None] = mapped_column(Text)
    relatorio_texto: Mapped[str | None] = mapped_column(Text)

    area_estimada: Mapped[Decimal | None] = mapped_column(
        DECIMAL(6, 2)
    )
    tecido_granulacao: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2)
    )
    tecido_esfacelo: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2)
    )
    tecido_necrose: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2)
    )

    status: Mapped[str] = mapped_column(
        String(20), server_default="pendente"
    )

    contexto_clinico_json: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_analise_paciente", "id_paciente_fk"),
        Index("idx_analise_enfermeiro", "id_enfermeiro_fk"),
        Index("idx_analise_data", "data_analise"),
    )
