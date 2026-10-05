from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class DadosClinicosInput(BaseModel):
    """
    Representa os dados clínicos inseridos no aplicativo pelo enfermeiro.
    """
    localizacao: str = Field(..., description="Localização anatômica da lesão")
    comprimento: Optional[str] = Field(None, description="Comprimento em cm")
    largura: Optional[str] = Field(None, description="Largura em cm")
    tipoExsudato: Optional[str] = Field(None, description="Tipo de exsudato")
    odor: bool = Field(False, description="Presença de odor")
    nivelDor: Optional[str] = Field(None, description="Nível de dor informado")
    queixaPrincipal: Optional[str] = Field(None, description="Queixa do paciente")
    observacoes: Optional[str] = Field(None, description="Observações complementares")

class AnaliseTecnicaOpenCVInput(BaseModel):
    """
    Dados técnicos exatamente como já produzidos pelo OpenCV existente.
    """
    brilho_medio: float
    contraste_global: float

class AnaliseMultimodalInput(BaseModel):
    """
    Estrutura única de entrada enviada a cada provedor multimodal.
    """
    avaliacao_id: Optional[str] = Field(None, description="Identificador único da avaliação")
    caminho_imagem_original: str = Field(..., description="Caminho do arquivo da imagem original")
    caminho_imagem_processada: str = Field(..., description="Caminho da imagem pré-processada pelo OpenCV")
    dimensoes_originais: Dict[str, Any]
    dimensoes_processadas: Dict[str, Any]
    analise_tecnica: AnaliseTecnicaOpenCVInput
    dados_clinicos: DadosClinicosInput

class RespostaEstruturadaModelo(BaseModel):
    """
    Contrato de saída estruturado e neutro do modelo.
    """
    status_resposta: str = Field("simulacao_estrutura", description="Status da resposta do provedor")
    conteudo_descricao: str = Field("", description="Descrição das características visuais neutras")
    limitacoes_declaradas: List[str] = Field(default_factory=list, description="Avisos sobre a análise técnica")

class ResultadoProvedor(BaseModel):
    """
    Resultado individual de cada provedor (Gemini, OpenAI, Kimi).
    """
    provedor: str = Field(..., description="Nome do provedor ('gemini', 'openai', 'kimi')")
    modo: str = Field("simulacao", description="Modo de execução ('simulacao' ou 'api_real')")
    sucesso: bool = Field(..., description="Status da execução")
    tempo_execucao_segundos: float = Field(..., description="Tempo de processamento")
    resposta: Optional[RespostaEstruturadaModelo] = Field(None, description="Resposta estruturada")
    mensagem_erro: Optional[str] = Field(None, description="Mensagem em caso de erro")

class ResultadoAnaliseMultimodal(BaseModel):
    """
    Resultado consolidado do orquestrador com a resposta dos três modelos.
    """
    sucesso_geral: bool
    data_processamento: str
    resultados: Dict[str, ResultadoProvedor]