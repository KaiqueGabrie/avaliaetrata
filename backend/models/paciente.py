
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


class Paciente(Base):
    __tablename__ = "paciente"

    id_paciente: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    id_enfermeiro_fk: Mapped[int] = mapped_column(
        ForeignKey("enfermeiro.id_enfermeiro"),
        nullable=False,
    )

    id_instituicao_fk: Mapped[int | None] = mapped_column(
        ForeignKey("instituicao_saude.id_instituicao")
    )

    nome_completo: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    cpf: Mapped[str | None] = mapped_column(
        String(14),
        unique=True,
    )

    data_nascimento: Mapped[date | None] = mapped_column(Date)
    telefone: Mapped[str | None] = mapped_column(String(20))

    email: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
    )

    diagnostico: Mapped[str | None] = mapped_column(String(200))
    local_lesao: Mapped[str | None] = mapped_column(String(100))
    status_evolucao: Mapped[str | None] = mapped_column(String(10))

    data_cadastro: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

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

    __table_args__ = (
        Index(
            "idx_paciente_enfermeiro",
            "id_enfermeiro_fk",
        ),
        Index(
            "idx_paciente_instituicao",
            "id_instituicao_fk",
        ),
    )
