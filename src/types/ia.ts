export interface ResultadoAnaliseIA {
  sucesso: boolean;
  mensagem: string;
  tipoLesaoEstimado?: string;
  confianca?: number;
  recomendacaoTratamento?: string;
  detalhesSegmentacao?: string;
}