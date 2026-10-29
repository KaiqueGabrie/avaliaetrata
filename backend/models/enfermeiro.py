
from datetime import date, datetime

from sqlalchemy import (
    Integer,
    String,
    Date,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Enfermeiro(Base):
    __tablename__ = "enfermeiro"

    id_enfermeiro: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
    )

    # Armazenar somente hash seguro da senha
    senha: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    cpf: Mapped[str] = mapped_column(
        String(14),
        unique=True,
        nullable=False,
    )

    data_nascimento: Mapped[date | None] = mapped_column(Date)
    telefone: Mapped[str | None] = mapped_column(String(20))
    registro_coren: Mapped[str | None] = mapped_column(String(30))

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
