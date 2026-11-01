import { Alert, Platform } from 'react-native';
import type { AlertButton } from 'react-native';

/** Alert.alert não abre diálogos no React Native Web. */
export const Aviso = {
  alert(titulo: string, mensagem?: string, botoes?: AlertButton[]): void {
    if (Platform.OS !== 'web') {
      Alert.alert(titulo, mensagem, botoes);
      return;
    }

    const texto = [titulo, mensagem].filter(Boolean).join('\n\n');
    const opcoes = botoes ?? [];
    const cancelar = opcoes.find((botao) => botao.style === 'cancel');
    const acao = opcoes.find((botao) => botao.style !== 'cancel');

    if (cancelar && acao) {
      if (window.confirm(texto)) {
        acao.onPress?.();
      }
      return;
    }

    window.alert(texto);
    if (opcoes.length === 1) {
      opcoes[0].onPress?.();
    }
  },
};
