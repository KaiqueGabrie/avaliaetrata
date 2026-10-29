from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


StatusAnalise = Literal[
    "pendente",
    "em_processamento",
    "concluida",
    "erro",
]


class AnaliseCriar(BaseModel):
    queixa_principal: str | None = None
    observacoes_clinicas: str | None = None

    contexto_clinico_json: dict[str, Any] | None = None


class AnaliseAtualizar(BaseModel):
    queixa_principal: str | None = None
    observacoes_clinicas: str | None = None

    contexto_clinico_json: dict[str, Any] | None = None


class AnaliseResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_analise: int

    id_paciente_fk: int
    id_enfermeiro_fk: int

    data_analise: datetime

    queixa_principal: str | None
    observacoes_clinicas: str | None
    relatorio_texto: str | None

    area_estimada: Decimal | None

    tecido_granulacao: Decimal | None
    tecido_esfacelo: Decimal | None
    tecido_necrose: Decimal | None

    status: str

    contexto_clinico_json: dict[str, Any] | None

    created_at: datetime
    updated_at: datetime


class AnaliseResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_analise: int
    id_paciente_fk: int

    data_analise: datetime

    queixa_principal: str | None
    status: str

    area_estimada: Decimal | None

    created_at: datetime