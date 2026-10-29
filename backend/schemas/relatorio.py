
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SchemaRelatorio(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EdicaoRelatorio(SchemaRelatorio):
    campo: str
    valor_anterior: Any
    valor_novo: Any
    profissional_id: str
    data_edicao: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RelatorioIndividual(SchemaRelatorio):
    relatorio_id: str = Field(
        default_factory=lambda: str(uuid4())
    )
    avaliacao_id: Optional[str] = None
    provedor: str
    data_processamento: str

    # Resposta original imutável no fluxo de edição.
    conteudo_original: Dict[str, Any]

    # Cópia de trabalho editável.
    conteudo_editavel: Dict[str, Any]

    status: Literal[
        "gerado",
        "em_edicao",
        "aprovado",
    ] = "gerado"

    historico_edicoes: List[EdicaoRelatorio] = Field(
        default_factory=list
    )

    profissional_responsavel: Optional[str] = None
    data_aprovacao: Optional[datetime] = None

    alertas_validacao: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    revisao_profissional_necessaria: bool = True


class ConjuntoRelatorios(SchemaRelatorio):
    avaliacao_id: Optional[str] = None
    data_processamento: str
    relatorios: Dict[str, RelatorioIndividual] = Field(
        default_factory=dict
    )
    provedores_indisponiveis: List[str] = Field(
        default_factory=list
    )
    comparacao: Optional[Dict[str, Any]] = None
