"""Revisão manual das marcações; distinta das respostas originais das IAs."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Classe = Literal[
    'contorno_lesao', 'granulacao', 'esfacelo', 'necrose',
    'pele_perilesional', 'nao_classificado',
]
Provedor = Literal['openai', 'gemini', 'kimi', 'manual']

class PontoManual(BaseModel):
    model_config = ConfigDict(extra='forbid')
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)

class RegiaoManual(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    classe: Classe
    pontos: list[PontoManual] = Field(min_length=3, max_length=60)
    origem: Literal['ia', 'profissional'] = 'profissional'
    descricao: str = Field(default='', max_length=240)
    # Proveniência da sugestão original, preservada após correção profissional.
    classe_proposta_ia: Classe | None = None
    justificativa_classificacao_ia: str = Field(default='', max_length=320)
    confianca_classificacao_ia: Literal['baixa', 'moderada', 'alta'] | None = None

class SalvarRevisao(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provedor_base: Provedor
    revisao_esperada: int = Field(ge=0)
    regioes: list[RegiaoManual] = Field(min_length=1, max_length=24)

class AprovarRevisao(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revisao_esperada: int = Field(ge=1)
