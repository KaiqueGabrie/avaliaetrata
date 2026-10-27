
export type StatusAvaliacao =
  | 'avaliavel'
  | 'parcialmente_avaliavel'
  | 'nao_avaliavel';

export type Confianca = 'baixa' | 'moderada' | 'alta';

export interface PontoImagem {
  x: number;
  y: number;
}

export interface RegiaoIdentificada {
  identificador: string;
  rotulo: string;
  descricao: string;
  pontos: PontoImagem[];
  confianca_autodeclarada: Confianca | null;
  revisao_profissional_necessaria: boolean;
}

export interface RespostaEstruturadaIA {
  status_resposta: string;
  conteudo_descricao: string;
  limitacoes_declaradas: string[];

  qualidade_imagem: {
    status: StatusAvaliacao;
    observacoes: string[];
    limitacoes: string[];
  };

  caracteristicas_visuais: {
    caracteristica: string;
    descricao: string;
    status: StatusAvaliacao;
    confianca_autodeclarada: Confianca | null;
    justificativa: string | null;
  }[];

  avaliacao_times: {
    componente: 'T' | 'I' | 'M' | 'E' | 'S';
    nome: string;
    status: StatusAvaliacao;
    observacoes_visuais: string[];
    dados_clinicos_relacionados: string[];
    informacoes_pendentes: string[];
    limitacoes: string[];
  }[];

  medidas: {
    comprimento_informado_cm: string | null;
    largura_informada_cm: string | null;
    area_calculada_cm2: number | null;
    metodo_medicao: string | null;
    observacoes: string[];
  };

  dados_clinicos_organizados: {
    localizacao: string | null;
    comprimento: string | null;
    largura: string | null;
    tipo_exsudato: string | null;
    odor: boolean | null;
    nivel_dor: string | null;
    queixa_principal: string | null;
    observacoes: string | null;
    dados_nao_informados: string[];
  };

  pontos_para_revisao_profissional: string[];
  validacao_profissional_necessaria: boolean;

  avaliacao_tecidos: {
    status: StatusAvaliacao;
    tecidos: {
      tipo: string;
      descricao_visual: string;
      percentual_estimado: number | null;
      confianca_autodeclarada: Confianca | null;
      justificativa: string | null;
      revisao_profissional_necessaria: boolean;
    }[];
    metodo_estimativa: string | null;
    limitacoes: string[];
  };

  marcacoes_imagem: {
    sistema_coordenadas: 'normalizado_0_1';
    imagem_referencia: 'processada';
    regioes: RegiaoIdentificada[];
    limitacoes: string[];
  };

  plano_cuidados_proposto: {
    status: 'rascunho_para_revisao';
    sugestoes: {
      titulo: string;
      justificativa: string;
      dados_a_confirmar: string[];
      depende_validacao_profissional: boolean;
    }[];
    observacoes: string[];
  };
}

export interface ResultadoProvedorIA {
  provedor: string;
  modo: string;
  sucesso: boolean;
  tempo_execucao_segundos: number;
  resposta: RespostaEstruturadaIA | null;
  mensagem_erro: string | null;
}

export interface ResultadoAnaliseIA {
  sucesso_geral: boolean;
  data_processamento: string;
  resultados: Record<string, ResultadoProvedorIA>;
}
