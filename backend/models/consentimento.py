
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TermoConsentimento(Base):
    __tablename__ = "termo_consentimento"

    id_termo: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    id_paciente_fk: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"),
        nullable=False,
        index=True,
    )

    id_enfermeiro_fk: Mapped[int] = mapped_column(
        ForeignKey("enfermeiro.id_enfermeiro"),
        nullable=False,
    )

    chave_storage: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    tamanho_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    declarado_assinado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
