// Campos reais retornados pelo FastAPI em GET /pacientes.
export interface Paciente {
  id_paciente: number;
  id_enfermeiro_fk: number;
  id_instituicao_fk: number | null;
  nome_completo: string;
  cpf: string | null;
  data_nascimento: string | null;
  telefone: string | null;
  email: string | null;
  diagnostico: string | null;
  local_lesao: string | null;
  status_evolucao: string | null;
  data_cadastro: string;
}

export interface AnaliseResumo {
  id_analise: number;
  id_paciente_fk: number;
  data_analise: string;
  queixa_principal: string | null;
  status: string;
  area_estimada: string | number | null;
  created_at: string;
}

export function formatarData(valor: string | null | undefined): string {
  if (!valor) return 'Não informada';
  const parte = valor.slice(0, 10);
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(parte);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : valor;
}
