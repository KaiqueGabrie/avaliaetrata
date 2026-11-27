
import { Stack, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import type { TextInputProps } from 'react-native';
import {
    ActivityIndicator,
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

type CampoProps = TextInputProps & {
  rotulo: string;
  alternarSenha?: () => void;
};

function Campo({
  rotulo,
  alternarSenha,
  ...props
}: CampoProps) {
  return (
    <View style={styles.grupoCampo}>
      <Text style={styles.label}>{rotulo}</Text>

      <View style={styles.campo}>
        <TextInput
          placeholderTextColor="#64748b"
          {...props}
          accessibilityLabel={rotulo}
          style={styles.input}
        />

        {alternarSenha ? (
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel={
              props.secureTextEntry
                ? 'Mostrar conteúdo'
                : 'Ocultar conteúdo'
            }
            style={styles.botaoOlho}
            onPress={alternarSenha}
          >
            <IconeInterface
              nome={
                props.secureTextEntry
                  ? 'olho'
                  : 'olho-fechado'
              }
              tamanho={21}
            />
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

function mascaraCpf(texto: string) {
  const cpf = texto.replace(/\D/g, '').slice(0, 11);

  return cpf
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3}\.\d{3})(\d)/, '$1.$2')
    .replace(/(\.\d{3})(\d{1,2})$/, '$1-$2');
}

function validarCpf(texto: string) {
  const cpf = texto.replace(/\D/g, '');

  if (
    cpf.length !== 11 ||
    /^(\d)\1{10}$/.test(cpf)
  ) {
    return false;
  }

  for (const tamanho of [9, 10]) {
    let soma = 0;

    for (let i = 0; i < tamanho; i++) {
      soma +=
        Number(cpf[i]) * (tamanho + 1 - i);
    }

    let digito = (soma * 10) % 11;

    if (digito === 10) digito = 0;

    if (digito !== Number(cpf[tamanho])) {
      return false;
    }
  }

  return true;
}

function mascaraData(texto: string) {
  const digitos = texto
    .replace(/\D/g, '')
    .slice(0, 8);

  if (digitos.length <= 2) {
    return digitos;
  }

  if (digitos.length <= 4) {
    return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
  }

  return (
    `${digitos.slice(0, 2)}/` +
    `${digitos.slice(2, 4)}/` +
    digitos.slice(4)
  );
}

function converterData(texto: string): string | null {
  if (!texto.trim()) return null;

  const partes =
    /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto);

  if (!partes) {
    throw new Error(
      'Informe a data no formato DD/MM/AAAA.'
    );
  }

  const [, dia, mes, ano] = partes;

  const data = new Date(
    Number(ano),
    Number(mes) - 1,
    Number(dia),
  );

  if (
    data.getDate() !== Number(dia) ||
    data.getMonth() !== Number(mes) - 1 ||
    data.getFullYear() !== Number(ano) ||
    Number(ano) < 1900 ||
    data > new Date()
  ) {
    throw new Error(
      'Informe uma data de nascimento válida.'
    );
  }

  return `${ano}-${mes}-${dia}`;
}

export default function CadastroEnfermeiroScreen() {
  const router = useRouter();
  const enviando = useRef(false);

  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [nascimento, setNascimento] = useState('');
  const [telefone, setTelefone] = useState('');
  const [coren, setCoren] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [convite, setConvite] = useState('');

  const [mostrarSenha, setMostrarSenha] =
    useState(false);

  const [mostrarConfirmacao, setMostrarConfirmacao] =
    useState(false);

  const [mostrarConvite, setMostrarConvite] =
    useState(false);

  const [carregando, setCarregando] =
    useState(false);

  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState(false);

  async function cadastrar() {
    if (enviando.current || sucesso) return;

    setErro('');

    if (nome.trim().length < 3) {
      setErro('Informe seu nome completo.');
      return;
    }

    if (!validarCpf(cpf)) {
      setErro('Informe um CPF válido.');
      return;
    }

    if (coren.trim().length < 3) {
      setErro('Informe o registro profissional.');
      return;
    }

    if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
        email.trim()
      )
    ) {
      setErro('Informe um endereço de e-mail válido.');
      return;
    }

    if (senha.length < 12) {
      setErro(
        'A senha deve possuir pelo menos 12 caracteres.'
      );
      return;
    }

    if (senha !== confirmacao) {
      setErro('As senhas informadas não coincidem.');
      return;
    }

    if (!convite.trim()) {
      setErro('Informe o código de convite.');
      return;
    }

    let dataNascimento: string | null;

    try {
      dataNascimento = converterData(nascimento);
    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Data inválida.'
      );
      return;
    }

    enviando.current = true;
    setCarregando(true);

    try {
      const resposta = await fetch(
        `${API_URL.replace(/\/+$/, '')}/auth/cadastro`,
        {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            'X-Registration-Invite': convite.trim(),
          },

          body: JSON.stringify({
            nome: nome.trim(),
            cpf: cpf.replace(/\D/g, ''),
            data_nascimento: dataNascimento,
            telefone: telefone.trim() || null,
            registro_coren: coren.trim(),
            email: email.trim().toLowerCase(),
            senha,
          }),
        },
      );

      if (!resposta.ok) {
        const mensagens: Record<number, string> = {
          400: 'Confira os dados informados.',
          403: 'Convite inválido ou cadastro indisponível.',
          409: 'Já existe uma conta com esse CPF ou e-mail.',
          422: 'Confira os campos e tente novamente.',
          429: 'Muitas solicitações. Tente novamente mais tarde.',
          503: 'O serviço está temporariamente indisponível.',
        };

        throw new Error(
          mensagens[resposta.status] ||
          'Não foi possível realizar o cadastro.'
        );
      }

      setSenha('');
      setConfirmacao('');
      setConvite('');
      setSucesso(true);

    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Não foi possível criar a conta.'
      );
    } finally {
      enviando.current = false;
      setCarregando(false);
    }
  }

  return (
    <>
      <Stack.Screen
        options={{
          headerShown: false,
          title: 'Cadastro de Enfermeiro',
        }}
      />

      <SafeAreaView style={styles.tela}>
        <KeyboardAvoidingView
          style={styles.tela}
          behavior={
            Platform.OS === 'ios'
              ? 'padding'
              : undefined
          }
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
                <View style={styles.abas}>
                  <TouchableOpacity
                    accessibilityRole="button"
                    disabled={carregando}
                    style={styles.aba}
                    onPress={() => router.replace('/')}
                  >
                    <Text style={styles.textoAba}>
                      Login
                    </Text>
                  </TouchableOpacity>

                  <View style={[
                    styles.aba,
                    styles.abaAtiva,
                  ]}>
                    <Text style={styles.textoAbaAtiva}>
                      Cadastrar-se
                    </Text>
                  </View>
                </View>

                {sucesso ? (
                  <View style={styles.sucesso}>
                    <View style={styles.iconeSucesso}>
                      <IconeInterface
                        nome="confirmar"
                        tamanho={38}
                        cor="#15803d"
                      />
                    </View>

                    <Text style={styles.tituloFormulario}>
                      Conta criada com sucesso!
                    </Text>

                    <Text style={styles.descricao}>
                      Utilize seu e-mail e sua senha
                      para acessar o sistema.
                    </Text>

                    <TouchableOpacity
                      accessibilityRole="button"
                      style={styles.botao}
                      onPress={() => router.replace('/')}
                    >
                      <Text style={styles.textoBotao}>
                        Ir para o login
                      </Text>
                    </TouchableOpacity>
                  </View>
                ) : (
                  <>
                    <Text style={styles.tituloFormulario}>
                      Crie sua conta profissional
                    </Text>

                    <Text style={styles.descricao}>
                      Preencha seus dados para acessar
                      o Avalia & Trata.
                    </Text>

                    <Campo
                      rotulo="Nome completo *"
                      placeholder="Informe seu nome"
                      value={nome}
                      onChangeText={setNome}
                      autoCapitalize="words"
                      maxLength={150}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="CPF *"
                      placeholder="000.000.000-00"
                      value={cpf}
                      onChangeText={texto =>
                        setCpf(mascaraCpf(texto))
                      }
                      keyboardType="numeric"
                      maxLength={14}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="Data de nascimento"
                      placeholder="DD/MM/AAAA"
                      value={nascimento}
                      onChangeText={texto =>
                        setNascimento(mascaraData(texto))
                      }
                      keyboardType="numeric"
                      maxLength={10}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="Telefone"
                      placeholder="(00) 00000-0000"
                      value={telefone}
                      onChangeText={setTelefone}
                      keyboardType="phone-pad"
                      maxLength={20}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="Registro profissional (COREN) *"
                      placeholder="Informe seu registro"
                      value={coren}
                      onChangeText={setCoren}
                      autoCapitalize="characters"
                      maxLength={30}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="E-mail *"
                      placeholder="Digite seu e-mail"
                      value={email}
                      onChangeText={setEmail}
                      keyboardType="email-address"
                      autoCapitalize="none"
                      autoCorrect={false}
                      autoComplete="email"
                      maxLength={150}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="Senha *"
                      placeholder="Mínimo de 12 caracteres"
                      value={senha}
                      onChangeText={setSenha}
                      secureTextEntry={!mostrarSenha}
                      alternarSenha={() =>
                        setMostrarSenha(v => !v)
                      }
                      autoCapitalize="none"
                      autoCorrect={false}
                      autoComplete="new-password"
                      maxLength={128}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="Confirmar senha *"
                      placeholder="Repita sua senha"
                      value={confirmacao}
                      onChangeText={setConfirmacao}
                      secureTextEntry={!mostrarConfirmacao}
                      alternarSenha={() =>
                        setMostrarConfirmacao(v => !v)
                      }
                      autoCapitalize="none"
                      autoCorrect={false}
                      maxLength={128}
                      editable={!carregando}
                    />

                    <Campo
                      rotulo="Código de convite *"
                      placeholder="Informe o código recebido"
                      value={convite}
                      onChangeText={setConvite}
                      secureTextEntry={!mostrarConvite}
                      alternarSenha={() =>
                        setMostrarConvite(v => !v)
                      }
                      autoCapitalize="none"
                      autoCorrect={false}
                      maxLength={256}
                      editable={!carregando}
                    />

                    <Text style={styles.orientacao}>
                      Utilize uma senha exclusiva, com
                      pelo menos 12 caracteres.
                    </Text>

                    {erro ? (
                      <View style={styles.caixaErro}>
                        <Text
                          accessibilityLiveRegion="polite"
                          style={styles.textoErro}
                        >
                          {erro}
                        </Text>
                      </View>
                    ) : null}

                    <TouchableOpacity
                      accessibilityRole="button"
                      disabled={carregando}
                      style={[
                        styles.botao,
                        carregando && styles.desabilitado,
                      ]}
                      onPress={() => void cadastrar()}
                    >
                      {carregando ? (
                        <View style={styles.carregamento}>
                          <ActivityIndicator color="#ffffff" />

                          <Text style={styles.textoBotao}>
                            Criando conta...
                          </Text>
                        </View>
                      ) : (
                        <Text style={styles.textoBotao}>
                          Criar conta
                        </Text>
                      )}
                    </TouchableOpacity>

                    <Text style={styles.camposObrigatorios}>
                      * Campos obrigatórios
                    </Text>
                  </>
                )}

                <View style={styles.rodape}>
                  <IconeInterface
                    nome="escudo"
                    tamanho={22}
                    cor="#64748b"
                  />

                  <Text style={styles.textoRodape}>
                    Cadastro restrito a profissionais
                    convidados. O registro informado
                    não constitui verificação automática
                    da habilitação profissional.
                  </Text>
                </View>
              </View>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </>
  );
}

const styles = StyleSheet.create({
  tela: {
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
    color: '#dce9f2',
    fontSize: 14,
    lineHeight: 21,
  },

  formulario: {
    padding: 26,
  },

  abas: {
    flexDirection: 'row',
    backgroundColor: '#f1f5f9',
    padding: 4,
    gap: 4,
    borderRadius: 10,
    marginBottom: 24,
  },

  aba: {
    flex: 1,
    minHeight: 42,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },

  abaAtiva: {
    backgroundColor: '#005088',
  },

  textoAba: {
    color: '#005088',
    fontSize: 14,
    fontWeight: '600',
  },

  textoAbaAtiva: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
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

  grupoCampo: {
    marginBottom: 17,
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
    borderWidth: 1,
    borderColor: '#b7c9d5',
    borderRadius: 10,
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 12,
  },

  input: {
    flex: 1,
    minWidth: 0,
    minHeight: 50,
    paddingVertical: 12,
    color: '#1e293b',
    fontSize: 14,
  },

  botaoOlho: {
    width: 42,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },

  orientacao: {
    color: '#64748b',
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 18,
  },

  botao: {
    backgroundColor: '#005088',
    minHeight: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 12,
  },

  textoBotao: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },

  desabilitado: {
    opacity: 0.6,
  },

  carregamento: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },

  caixaErro: {
    backgroundColor: '#fef2f2',
    borderWidth: 1,
    borderColor: '#fecaca',
    borderRadius: 9,
    padding: 13,
    marginBottom: 14,
  },

  textoErro: {
    color: '#b91c1c',
    fontSize: 13,
    lineHeight: 20,
  },

  camposObrigatorios: {
    color: '#64748b',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 14,
  },

  sucesso: {
    gap: 10,
  },

  iconeSucesso: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: '#dcfce7',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
    marginBottom: 12,
  },

  rodape: {
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    marginTop: 24,
    paddingTop: 18,
  },

  textoRodape: {
    flex: 1,
    color: '#64748b',
    fontSize: 12,
    lineHeight: 18,
  },
});
