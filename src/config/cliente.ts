import * as SecureStore from 'expo-secure-store';
import { API_URL } from './api';

export async function obterToken(): Promise<string> {
  const token = await SecureStore.getItemAsync('access_token');
  if (!token) throw new Error('Sessão não encontrada. Volte ao início e faça login.');
  return token;
}

export async function mensagemErro(resposta: Response): Promise<string> {
  // Mensagens claras para o profissional, sem expor respostas técnicas do serviço.
  switch (resposta.status) {
    case 400:
    case 422:
      return 'Confira os dados informados e tente novamente.';
    case 401:
    case 403:
      return 'Sua sessão expirou ou você não tem permissão. Faça login novamente.';
    case 404:
      return 'O registro solicitado não foi encontrado.';
    case 409:
      return 'Já existe um registro com essas informações ou esta ação já foi realizada.';
    case 413:
      return 'A fotografia é muito grande. Selecione uma imagem menor.';
    case 429:
      return 'Muitas solicitações no momento. Aguarde um pouco e tente novamente.';
    case 502:
    case 503:
    case 504:
      return 'A análise está temporariamente indisponível. Tente novamente mais tarde.';
    default:
      return 'Não foi possível concluir a operação. Tente novamente.';
  }
}

export async function apiJson<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const token = await obterToken();
  const resposta = await fetch(`${API_URL}${caminho}`, {
    ...opcoes,
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
      ...(opcoes.body ? { 'Content-Type': 'application/json' } : {}),
      ...opcoes.headers,
    },
  });
  if (!resposta.ok) throw new Error(await mensagemErro(resposta));
  return resposta.json() as Promise<T>;
}
