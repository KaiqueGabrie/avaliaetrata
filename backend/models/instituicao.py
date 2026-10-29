
from datetime import date, datetime

from sqlalchemy import (
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class InstituicaoSaude(Base):
    __tablename__ = "instituicao_saude"

    id_instituicao: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    cnpj: Mapped[str | None] = mapped_column(
        String(14),
        unique=True,
    )

    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(150))
    endereco: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime
    )


class EnfermeiroInstituicao(Base):
    __tablename__ = "enfermeiro_instituicao"

    id_vinculo: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    id_enfermeiro_fk: Mapped[int] = mapped_column(
        ForeignKey("enfermeiro.id_enfermeiro"),
        nullable=False,
    )

    id_instituicao_fk: Mapped[int] = mapped_column(
        ForeignKey("instituicao_saude.id_instituicao"),
        nullable=False,
    )

    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "idx_vinculo_enfermeiro",
            "id_enfermeiro_fk",
        ),
        Index(
            "idx_vinculo_instituicao",
            "id_instituicao_fk",
        ),
    )
