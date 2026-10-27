from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


StatusAvaliacao = Literal[
    "avaliavel",
    "parcialmente_avaliavel",
    "nao_avaliavel",
]


class SchemaBase(BaseModel):
    """Configuração comum para os modelos de dados."""

    model_config = ConfigDict(extra="forbid")


class DadosClinicosInput(SchemaBase):
    """Informações fornecidas pelo profissional, não inferidas da foto."""

    localizacao: str = Field(..., min_length=1)
    comprimento: Optional[str] = None
    largura: Optional[str] = None
    tipoExsudato: Optional[str] = None
    odor: Optional[bool] = None
    nivelDor: Optional[str] = None
    queixaPrincipal: Optional[str] = None
    observacoes: Optional[str] = None


class AnaliseTecnicaOpenCVInput(SchemaBase):
    """Métricas de imagem; não representam achados clínicos."""

    brilho_medio: float
    contraste_global: float


class AnaliseMultimodalInput(SchemaBase):
    avaliacao_id: Optional[str] = None
    caminho_imagem_original: str
    caminho_imagem_processada: str
    dimensoes_originais: Dict[str, Any]
    dimensoes_processadas: Dict[str, Any]
    analise_tecnica: AnaliseTecnicaOpenCVInput
    dados_clinicos: DadosClinicosInput


class QualidadeImagem(SchemaBase):
    status: StatusAvaliacao = "nao_avaliavel"
    observacoes: List[str] = Field(default_factory=list)
    limitacoes: List[str] = Field(default_factory=list)


class ObservacaoVisual(SchemaBase):
    caracteristica: str
    descricao: str
    status: StatusAvaliacao = "nao_avaliavel"
    confianca_autodeclarada: Optional[Literal["baixa", "moderada", "alta"]] = None
    justificativa: Optional[str] = None


class AvaliacaoComponenteTimestamps(SchemaBase):
    """T.I.M.E.S.: observações auxiliares, sem diagnóstico automático."""

    componente: Literal["T", "I", "M", "E", "S"]
    nome: str
    status: StatusAvaliacao = "nao_avaliavel"
    observacoes_visuais: List[str] = Field(default_factory=list)
    dados_clinicos_relacionados: List[str] = Field(default_factory=list)
    informacoes_pendentes: List[str] = Field(default_factory=list)
    limitacoes: List[str] = Field(default_factory=list)


class MedidasLesao(SchemaBase):
    comprimento_informado_cm: Optional[str] = None
    largura_informada_cm: Optional[str] = None
    area_calculada_cm2: Optional[float] = Field(default=None, ge=0)
    metodo_medicao: Optional[str] = None
    observacoes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def verificar_area(self):
        if self.area_calculada_cm2 is not None and not self.metodo_medicao:
            raise ValueError(
                "Uma área calculada exige a identificação do método de medição."
            )
        return self


class DadosClinicosOrganizados(SchemaBase):
    localizacao: Optional[str] = None
    comprimento: Optional[str] = None
    largura: Optional[str] = None
    tipo_exsudato: Optional[str] = None
    odor: Optional[bool] = None
    nivel_dor: Optional[str] = None
    queixa_principal: Optional[str] = None
    observacoes: Optional[str] = None
    dados_nao_informados: List[str] = Field(default_factory=list)


class PontoImagem(SchemaBase):
    """Coordenada normalizada entre 0 e 1, relativa à imagem analisada."""

    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)


class RegiaoIdentificada(SchemaBase):
    """Polígono sugerido por IA, ainda não validado pelo profissional."""

    identificador: str
    rotulo: str
    descricao: str = ""
    pontos: List[PontoImagem] = Field(default_factory=list)
    confianca_autodeclarada: Optional[Literal["baixa", "moderada", "alta"]] = None
    revisao_profissional_necessaria: bool = True


class CaracterizacaoTecido(SchemaBase):
    """Hipótese visual sobre tecido, sem confirmação histológica/clínica."""

    tipo: str
    descricao_visual: str = ""
    percentual_estimado: Optional[float] = Field(default=None, ge=0, le=100)
    confianca_autodeclarada: Optional[Literal["baixa", "moderada", "alta"]] = None
    justificativa: Optional[str] = None
    revisao_profissional_necessaria: bool = True


class AvaliacaoTecidos(SchemaBase):
    status: StatusAvaliacao = "nao_avaliavel"
    tecidos: List[CaracterizacaoTecido] = Field(default_factory=list)
    metodo_estimativa: Optional[str] = None
    limitacoes: List[str] = Field(default_factory=list)


class MarcacoesImagem(SchemaBase):
    """Coordenadas referentes à imagem processada, normalizadas de 0 a 1."""

    sistema_coordenadas: Literal["normalizado_0_1"] = "normalizado_0_1"
    imagem_referencia: Literal["processada"] = "processada"
    regioes: List[RegiaoIdentificada] = Field(default_factory=list)
    limitacoes: List[str] = Field(default_factory=list)


class SugestaoRevisaoCuidado(SchemaBase):
    """Tópicos para análise do enfermeiro, não prescrições automáticas."""

    titulo: str
    justificativa: str = ""
    dados_a_confirmar: List[str] = Field(default_factory=list)
    depende_validacao_profissional: bool = True


class PlanoCuidadosProposto(SchemaBase):
    status: Literal["rascunho_para_revisao"] = "rascunho_para_revisao"
    sugestoes: List[SugestaoRevisaoCuidado] = Field(default_factory=list)
    observacoes: List[str] = Field(default_factory=list)


class RespostaEstruturadaModelo(SchemaBase):
    """Contrato único para Gemini, OpenAI e Kimi."""

    status_resposta: str = "sucesso"
    conteudo_descricao: str = ""
    limitacoes_declaradas: List[str] = Field(default_factory=list)
    qualidade_imagem: QualidadeImagem = Field(default_factory=QualidadeImagem)
    caracteristicas_visuais: List[ObservacaoVisual] = Field(default_factory=list)
    avaliacao_times: List[AvaliacaoComponenteTimestamps] = Field(default_factory=list)
    medidas: MedidasLesao = Field(default_factory=MedidasLesao)
    dados_clinicos_organizados: DadosClinicosOrganizados = Field(
        default_factory=DadosClinicosOrganizados
    )
    pontos_para_revisao_profissional: List[str] = Field(default_factory=list)
    validacao_profissional_necessaria: bool = True

    # Extensões exigidas pelo fluxo de resultados e relatório do TCC.
    avaliacao_tecidos: AvaliacaoTecidos = Field(default_factory=AvaliacaoTecidos)
    marcacoes_imagem: MarcacoesImagem = Field(default_factory=MarcacoesImagem)
    plano_cuidados_proposto: PlanoCuidadosProposto = Field(
        default_factory=PlanoCuidadosProposto
    )

    @model_validator(mode="after")
    def garantir_validacao(self):
        self.validacao_profissional_necessaria = True
        return self


class ResultadoProvedor(SchemaBase):
    provedor: str
    modo: str = "api_real"
    sucesso: bool
    tempo_execucao_segundos: float
    resposta: Optional[RespostaEstruturadaModelo] = None
    mensagem_erro: Optional[str] = None


class ResultadoAnaliseMultimodal(SchemaBase):
    sucesso_geral: bool
    data_processamento: str
    resultados: Dict[str, ResultadoProvedor]
