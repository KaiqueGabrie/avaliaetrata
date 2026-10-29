
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PacienteCriar(BaseModel):
    nome_completo: str = Field(min_length=3, max_length=150)
    cpf: str | None = Field(default=None, max_length=14)
    data_nascimento: date | None = None
    telefone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    diagnostico: str | None = Field(default=None, max_length=200)
    local_lesao: str | None = Field(default=None, max_length=100)
    status_evolucao: Literal[
        "melhora", "estavel", "piora"
    ] | None = None


class PacienteAtualizar(BaseModel):
    nome_completo: str | None = Field(
        default=None, min_length=3, max_length=150
    )
    cpf: str | None = Field(default=None, max_length=14)
    data_nascimento: date | None = None
    telefone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    diagnostico: str | None = Field(default=None, max_length=200)
    local_lesao: str | None = Field(default=None, max_length=100)
    status_evolucao: Literal[
        "melhora", "estavel", "piora"
    ] | None = None


class PacienteResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_paciente: int
    id_enfermeiro_fk: int
    id_instituicao_fk: int | None
    nome_completo: str
    cpf: str | None
    data_nascimento: date | None
    telefone: str | None
    email: str | None
    diagnostico: str | None
    local_lesao: str | None
    status_evolucao: str | None
    data_cadastro: datetime


class AnamneseDados(BaseModel):
    historia_pregressa: str | None = None
    tabagismo: bool | None = None
    mobilidade_reduzida: bool | None = None
    possui_varizes: bool | None = None
    historico_amputacao: bool | None = None
    pulsos_perifericos: str | None = Field(
        default=None, max_length=20
    )
    data_surgimento_ferida: date | None = None
    causa_provavel: str | None = Field(
        default=None, max_length=50
    )
    outras_patologias: str | None = None


class AnamneseResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_anamnese: int
    id_paciente_fk: int
    historia_pregressa: str | None
    tabagismo: bool | None
    mobilidade_reduzida: bool | None
    possui_varizes: bool | None
    historico_amputacao: bool | None
    pulsos_perifericos: str | None
    data_surgimento_ferida: date | None
    causa_provavel: str | None
    outras_patologias: str | None
    created_at: datetime
    updated_at: datetime
