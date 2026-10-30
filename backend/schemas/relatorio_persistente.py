
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ProvedorIA = Literal["openai", "gemini", "kimi"]


class RelatorioSalvar(BaseModel):
    provedor: ProvedorIA
    conteudo: dict[str, Any]
    alertas_validacao: list | dict | None = None


class RelatorioEditar(BaseModel):
    campo: str = Field(min_length=1)
    novo_valor: Any


class RelatorioResposta(BaseModel):
    id_relatorio: str
    id_analise_fk: int
    provedor: str
    conteudo_original: dict
    conteudo_editavel: dict
    status: str
    alertas_validacao: list | dict | None
    revisao_profissional_necessaria: bool
    profissional_responsavel_fk: int | None
    data_aprovacao: datetime | None
