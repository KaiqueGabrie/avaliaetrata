
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import IconeInterface from '../components/icone-interface';
import { API_URL } from '../config/api';
import { salvarToken } from '../utils/tokenStorage';

export default function WelcomeScreen() {
  const router = useRouter();
  const enviando = useRef(false);

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [mensagemErro, setMensagemErro] = useState('');
  const [loginDemorado, setLoginDemorado] = useState(false);

  // Mantém o aquecimento da API do Render.
  useEffect(() => {
    const requisicao = new AbortController();
    const endereco = API_URL.replace(/\/+$/, '');

    void fetch(`${endereco}/`, {
      signal: requisicao.signal,
      cache: 'no-store',
    }).catch(() => {});

    return () => requisicao.abort();
  }, []);

  useEffect(() => {
    if (!carregando) return;

    const aviso = setTimeout(() => {
      setLoginDemorado(true);
    }, 5000);

    return () => clearTimeout(aviso);
  }, [carregando]);

  const mostrarErro = (titulo: string, mensagem: string) => {
    if (Platform.OS === 'web') {
      setMensagemErro(mensagem);
    } else {
      Alert.alert(titulo, mensagem);
    }
  };

  const handleLogin = async () => {
    if (enviando.current) return;

    setMensagemErro('');

    if (!email.trim() || !senha) {
      mostrarErro(
        'Campos obrigatórios',
        'Informe seu e-mail e sua senha.',
      );
      return;
    }

    enviando.current = true;
    setLoginDemorado(false);
    setCarregando(true);

    try {
      const resposta = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          senha,
        }),
      });

      if (!resposta.ok) {
        if (resposta.status === 401 || resposta.status === 403) {
          mostrarErro(
            'Erro no login',
            'E-mail ou senha inválidos.',
          );
        } else {
          mostrarErro(
            'Erro no login',
            'Não foi possível entrar no momento. Tente novamente.',
          );
        }

        return;
      }

      const dados = await resposta.json();

      if (
        typeof dados.access_token !== 'string' ||
        !dados.access_token
      ) {
        mostrarErro(
          'Erro',
          'Não foi possível concluir o acesso.',
        );
        return;
      }

      await salvarToken('access_token', dados.access_token);

      setSenha('');
      router.replace('/home');
    } catch (erro) {
      console.error('Erro ao realizar login:', erro);

      mostrarErro(
        'Erro de conexão',
        'Não foi possível acessar o sistema. Verifique sua conexão e tente novamente.',
      );
    } finally {
      enviando.current = false;
      setCarregando(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.card}>
            <View style={styles.cabecalho}>
              <View style={styles.marca}>
                <View style={styles.logo}>
                  <IconeInterface
                    nome="avaliacao"
                    tamanho={30}
                    cor="#ffffff"
                  />
                </View>

                <Text style={styles.nomeSistema}>
                  Avalia & Trata
                </Text>
              </View>

              <Text style={styles.titulo}>
                Comece agora
              </Text>

              <Text style={styles.subtitulo}>
                Sistema de apoio à avaliação e ao
                acompanhamento de lesões cutâneas.
              </Text>
            </View>

            <View style={styles.formulario}>
              <Text style={styles.tituloFormulario}>
                Acesse sua conta
              </Text>

              <Text style={styles.descricao}>
                Informe suas credenciais profissionais.
              </Text>

              <Text style={styles.label}>E-mail</Text>

              <View style={styles.campo}>
                <IconeInterface nome="email" tamanho={21} />

                <TextInput
                  style={styles.input}
                  accessibilityLabel="E-mail"
                  placeholder="Digite seu e-mail"
                  placeholderTextColor="#64748b"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="email"
                  value={email}
                  onChangeText={setEmail}
                  editable={!carregando}
                />
              </View>

              <Text style={styles.label}>Senha</Text>

              <View style={styles.campo}>
                <IconeInterface nome="cadeado" tamanho={21} />

                <TextInput
                  style={styles.input}
                  accessibilityLabel="Senha"
                  placeholder="Digite sua senha"
                  placeholderTextColor="#64748b"
                  secureTextEntry={!mostrarSenha}
                  autoCapitalize="none"
                  autoCorrect={false}
                  autoComplete="current-password"
                  value={senha}
                  onChangeText={setSenha}
                  editable={!carregando}
                  onSubmitEditing={() => void handleLogin()}
                />

                <TouchableOpacity
                  accessibilityRole="button"
                  accessibilityLabel={
                    mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'
                  }
                  style={styles.botaoOlho}
                  onPress={() => setMostrarSenha(v => !v)}
                >
                  <IconeInterface
                    nome={mostrarSenha ? 'olho-fechado' : 'olho'}
                    tamanho={21}
                  />
                </TouchableOpacity>
              </View>

              {mensagemErro ? (
                <View style={styles.caixaErro}>
                  <Text
                    accessibilityLiveRegion="polite"
                    style={styles.textoErro}
                  >
                    {mensagemErro}
                  </Text>
                </View>
              ) : null}

              <TouchableOpacity
                accessibilityRole="button"
                accessibilityState={{ disabled: carregando }}
                style={[
                  styles.botao,
                  carregando && styles.desabilitado,
                ]}
                activeOpacity={0.8}
                onPress={() => void handleLogin()}
                disabled={carregando}
              >
                {carregando ? (
                  <View style={styles.linhaCarregamento}>
                    <ActivityIndicator color="#ffffff" />
                    <Text style={styles.textoBotao}>
                      Entrando...
                    </Text>
                  </View>
                ) : (
                  <Text style={styles.textoBotao}>
                    Entrar
                  </Text>
                )}
              </TouchableOpacity>

              {carregando && loginDemorado ? (
                <Text
                  accessibilityLiveRegion="polite"
                  style={styles.avisoAcesso}
                >
                  O servidor pode estar iniciando.
                  Aguarde a conclusão do acesso.
                </Text>
              ) : null}

              <View style={styles.rodape}>
                <IconeInterface
                  nome="escudo"
                  tamanho={21}
                  cor="#64748b"
                />

                <Text style={styles.textoRodape}>
                  Acesso destinado aos profissionais cadastrados.
                </Text>
              </View>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#e4edf3',
  },

  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },

  card: {
    width: '100%',
    maxWidth: 440,
    backgroundColor: '#ffffff',
    borderRadius: 20,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    elevation: 4,
  },

  cabecalho: {
    backgroundColor: '#005088',
    paddingHorizontal: 26,
    paddingTop: 30,
    paddingBottom: 32,
  },

  marca: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 25,
  },

  logo: {
    width: 48,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#78a5c2',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ffffff15',
  },

  nomeSistema: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 21,
  },

  titulo: {
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: 30,
    marginBottom: 10,
  },

  subtitulo: {
    fontSize: 14,
    color: '#dce9f2',
    lineHeight: 21,
  },

  formulario: {
    padding: 26,
  },

  tituloFormulario: {
    color: '#172c3c',
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 6,
  },

  descricao: {
    color: '#64748b',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 24,
  },

  label: {
    color: '#1e293b',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },

  campo: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f1f5f9',
    borderWidth: 1,
    borderColor: '#b7c9d5',
    borderRadius: 10,
    paddingLeft: 14,
    paddingRight: 4,
    marginBottom: 18,
    gap: 10,
  },

  input: {
    flex: 1,
    minWidth: 0,
    minHeight: 50,
    paddingVertical: 12,
    paddingRight: 8,
    color: '#1e293b',
    fontSize: 15,
  },

  botaoOlho: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },

  botao: {
    backgroundColor: '#005088',
    minHeight: 52,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
    padding: 12,
  },

  textoBotao: {
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
  },

  desabilitado: {
    opacity: 0.65,
  },

  linhaCarregamento: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },

  caixaErro: {
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },

  textoErro: {
    fontSize: 13,
    color: '#b91c1c',
    lineHeight: 20,
  },

  avisoAcesso: {
    color: '#475569',
    fontSize: 13,
    lineHeight: 20,
    textAlign: 'center',
    marginTop: 12,
  },

  rodape: {
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingTop: 18,
    marginTop: 24,
  },

  textoRodape: {
    flex: 1,
    fontSize: 12,
    color: '#64748b',
    lineHeight: 18,
  },
});
