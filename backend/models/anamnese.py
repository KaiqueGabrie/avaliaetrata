
from datetime import date, datetime

from sqlalchemy import (
    Integer,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Anamnese(Base):
    __tablename__ = "anamnese"

    id_anamnese: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Uma anamnese por paciente
    id_paciente_fk: Mapped[int] = mapped_column(
        ForeignKey("paciente.id_paciente"),
        unique=True,
        nullable=False,
    )

    historia_pregressa: Mapped[str | None] = mapped_column(Text)

    tabagismo: Mapped[int | None] = mapped_column(TINYINT)
    mobilidade_reduzida: Mapped[int | None] = mapped_column(TINYINT)
    possui_varizes: Mapped[int | None] = mapped_column(TINYINT)
    historico_amputacao: Mapped[int | None] = mapped_column(TINYINT)

    pulsos_perifericos: Mapped[str | None] = mapped_column(
        String(20)
    )

    data_surgimento_ferida: Mapped[date | None] = mapped_column(
        Date
    )

    causa_provavel: Mapped[str | None] = mapped_column(
        String(50)
    )

    outras_patologias: Mapped[str | None] = mapped_column(Text)

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
