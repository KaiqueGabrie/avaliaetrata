export interface Avaliacao {
  id: string;
  pacienteId: string;
  dataHora: string;
  localizacao: string;
  comprimento?: string;
  largura?: string;
  tipoExsudato?: string;
  odor: boolean;
  nivelDor?: string;
  queixaPrincipal?: string;
  observacoes?: string;
  imagemUrl?: string;
}