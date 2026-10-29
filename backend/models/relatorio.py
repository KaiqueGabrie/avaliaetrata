
from datetime import datetime

from sqlalchemy import (
    BigInteger, Integer, String, DateTime,
    Boolean, JSON, ForeignKey, Index,
    UniqueConstraint, CheckConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class RelatorioIA(Base):
    __tablename__ = "relatorio_ia"

    id_relatorio: Mapped[str] = mapped_column(
        String(36), primary_key=True
    )

    id_analise_fk: Mapped[int] = mapped_column(
        ForeignKey("analise.id_analise")
    )

    provedor: Mapped[str] = mapped_column(String(20))
    conteudo_original: Mapped[dict] = mapped_column(JSON)
    conteudo_editavel: Mapped[dict] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(
        String(20), server_default="gerado"
    )
    alertas_validacao: Mapped[list | dict | None] = mapped_column(JSON)

    revisao_profissional_necessaria: Mapped[bool] = mapped_column(
        Boolean, server_default="1"
    )

    data_processamento: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    profissional_responsavel_fk: Mapped[int | None] = mapped_column(
        ForeignKey("enfermeiro.id_enfermeiro")
    )

    data_aprovacao: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "id_analise_fk",
            "provedor",
            name="uq_relatorio_analise_provedor"
        ),
        CheckConstraint(
            "provedor IN ('openai', 'gemini', 'kimi')",
            name="chk_relatorio_provedor"
        ),
        CheckConstraint(
            "status IN ('gerado', 'em_edicao', 'aprovado')",
            name="chk_relatorio_status"
        ),
        Index("idx_relatorio_analise", "id_analise_fk"),
    )


class HistoricoEdicao(Base):
    __tablename__ = "historico_edicao"

    id_edicao: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    id_relatorio_fk: Mapped[str] = mapped_column(
        ForeignKey("relatorio_ia.id_relatorio")
    )

    id_enfermeiro_fk: Mapped[int] = mapped_column(
        ForeignKey("enfermeiro.id_enfermeiro")
    )

    campo: Mapped[str] = mapped_column(String(150))
    valor_anterior: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    valor_novo: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)

    data_edicao: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_edicao_relatorio", "id_relatorio_fk"),
    )
