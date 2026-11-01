import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

export async function salvarToken(
  chave: string,
  valor: string
): Promise<void> {
  if (Platform.OS === 'web') {
    sessionStorage.setItem(chave, valor);
    return;
  }

  await SecureStore.setItemAsync(chave, valor);
}

export async function obterToken(
  chave: string
): Promise<string | null> {
  if (Platform.OS === 'web') {
    return sessionStorage.getItem(chave);
  }

  return SecureStore.getItemAsync(chave);
}

export async function removerToken(
  chave: string
): Promise<void> {
  if (Platform.OS === 'web') {
    sessionStorage.removeItem(chave);
    return;
  }

  await SecureStore.deleteItemAsync(chave);
}