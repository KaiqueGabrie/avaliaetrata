
from datetime import datetime

from sqlalchemy import (
    Integer, String, DateTime, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Imagem(Base):
    __tablename__ = "imagem"

    id_imagem: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    id_analise_fk: Mapped[int] = mapped_column(
        ForeignKey("analise.id_analise"),
        unique=True
    )

    caminho_imagem_original: Mapped[str | None] = mapped_column(
        String(255)
    )
    caminho_imagem_marcada: Mapped[str | None] = mapped_column(
        String(255)
    )
    data_captura: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
