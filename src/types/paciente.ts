export interface Paciente {
  id: string;
  nome: string;
  cpf: string;
  dataNascimento: string;
  telefone: string;
  endereco?: string;
  historicoClinico?: string;
}