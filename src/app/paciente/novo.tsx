
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import type { TextInputProps } from 'react-native';

import IconeInterface from '../../components/icone-interface';
import { apiJson } from '../../config/cliente';
import type { Paciente } from '../../types/paciente';
import { formatarData } from '../../types/paciente';
import { Aviso } from '../../utils/avisos';

type Evolucao = 'melhora' | 'estavel' | 'piora' | '';

const opcoesEvolucao: {
  valor: Evolucao;
  texto: string;
}[] = [
  { valor: '', texto: 'Não avaliada' },
  { valor: 'melhora', texto: 'Melhora' },
  { valor: 'estavel', texto: 'Estável' },
  { valor: 'piora', texto: 'Piora' },
];

function Campo({
  rotulo,
  ...props
}: TextInputProps & { rotulo: string }) {
  return (
    <View style={styles.grupoCampo}>
      <Text style={styles.label}>{rotulo}</Text>

      <TextInput
        placeholderTextColor="#64748b"
        {...props}
        accessibilityLabel={rotulo}
        style={[
          styles.input,
          props.multiline && styles.inputMultilinha,
          props.style,
        ]}
      />
    </View>
  );
}

function mascaraData(texto: string) {
  const valor = texto.replace(/\D/g, '').slice(0, 8);

  if (valor.length <= 2) return valor;

  if (valor.length <= 4) {
    return `${valor.slice(0, 2)}/${valor.slice(2)}`;
  }

  return `${valor.slice(0, 2)}/${valor.slice(2, 4)}/${valor.slice(4)}`;
}

function converterData(valor: string): string | null {
  if (!valor.trim()) return null;

  const partes = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(valor);

  if (!partes) {
    throw new Error('Informe a data no formato DD/MM/AAAA.');
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
    throw new Error('Informe uma data de nascimento válida.');
  }

  return `${ano}-${mes}-${dia}`;
}

function mascaraCpf(texto: string) {
  const valor = texto.replace(/\D/g, '').slice(0, 11);

  return valor
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3}\.\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
}

export default function NovoPacienteScreen() {
  const router = useRouter();

  const { editarId } = useLocalSearchParams<{
    editarId?: string;
  }>();

  const editando = Boolean(editarId);
  const enviando = useRef(false);

  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [cpfOriginal, setCpfOriginal] = useState('');
  const [dataNascimento, setDataNascimento] = useState('');
  const [telefone, setTelefone] = useState('');
  const [email, setEmail] = useState('');
  const [diagnostico, setDiagnostico] = useState('');
  const [localLesao, setLocalLesao] = useState('');
  const [statusEvolucao, setStatusEvolucao] =
    useState<Evolucao>('');

  const [carregando, setCarregando] = useState(editando);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [erroCarga, setErroCarga] = useState('');
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    setErro('');
    setErroCarga('');

    if (!editarId) {
      setCarregando(false);
      setNome('');
      setCpf('');
      setCpfOriginal('');
      setDataNascimento('');
      setTelefone('');
      setEmail('');
      setDiagnostico('');
      setLocalLesao('');
      setStatusEvolucao('');
      return;
    }

    if (!/^\d+$/.test(editarId)) {
      setErroCarga('Prontuário inválido.');
      setCarregando(false);
      return;
    }

    const requisicao = new AbortController();
    const { signal } = requisicao;

    setCarregando(true);

    void apiJson<Paciente>(
      `/pacientes/${editarId}`,
      { signal },
    )
      .then(paciente => {
        if (signal.aborted) return;

        setNome(paciente.nome_completo);
        setCpf(paciente.cpf || '');
        setCpfOriginal(paciente.cpf || '');

        setDataNascimento(
          paciente.data_nascimento
            ? formatarData(paciente.data_nascimento)
            : '',
        );

        setTelefone(paciente.telefone || '');
        setEmail(paciente.email || '');
        setDiagnostico(paciente.diagnostico || '');
        setLocalLesao(paciente.local_lesao || '');

        const status = paciente.status_evolucao;

        setStatusEvolucao(
          status === 'melhora' ||
          status === 'estavel' ||
          status === 'piora'
            ? status
            : '',
        );
      })
      .catch(e => {
        if (!signal.aborted) {
          setErroCarga(
            e instanceof Error
              ? e.message
              : 'Não foi possível consultar o paciente.',
          );
        }
      })
      .finally(() => {
        if (!signal.aborted) setCarregando(false);
      });

    return () => requisicao.abort();
  }, [editarId, tentativa]);

  const handleSalvar = async () => {
    if (enviando.current || carregando || erroCarga) return;

    setErro('');

    if (nome.trim().length < 3) {
      setErro('Informe o nome completo do paciente.');
      return;
    }

    const cpfDigitos = cpf.replace(/\D/g, '');

    const cpfFoiAlterado =
      !editando ||
      cpfDigitos !== cpfOriginal.replace(/\D/g, '');

    if (cpfFoiAlterado && cpfDigitos.length !== 11) {
      setErro('Informe um CPF com 11 dígitos.');
      return;
    }

    if (!editando && !cpfDigitos) {
      setErro('Informe o CPF do paciente.');
      return;
    }

    if (
      email.trim() &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
    ) {
      setErro('Informe um endereço de e-mail válido.');
      return;
    }

    let dataFormatada: string | null;

    try {
      dataFormatada = converterData(dataNascimento);
    } catch (e) {
      setErro(
        e instanceof Error ? e.message : 'Data inválida.',
      );
      return;
    }

    enviando.current = true;
    setSalvando(true);

    try {
      const dados = {
        nome_completo: nome.trim(),
        cpf: cpfFoiAlterado
          ? cpfDigitos
          : cpfOriginal || null,
        data_nascimento: dataFormatada,
        telefone: telefone.trim() || null,
        email: email.trim() || null,
        diagnostico: diagnostico.trim() || null,
        local_lesao: localLesao.trim() || null,
        status_evolucao: statusEvolucao || null,
      };

      const paciente = await apiJson<Paciente>(
        editando
          ? `/pacientes/${editarId}`
          : '/pacientes',
        {
          method: editando ? 'PATCH' : 'POST',
          body: JSON.stringify(dados),
        },
      );

      Aviso.alert(
        'Sucesso',
        editando
          ? 'Dados do paciente atualizados.'
          : 'Paciente cadastrado com sucesso!',
        [
          {
            text: 'OK',
            onPress: () => {
              if (editando && router.canGoBack()) {
                router.back();
              } else {
                router.replace({
                  pathname: '/paciente/[id]',
                  params: {
                    id: String(paciente.id_paciente),
                  },
                });
              }
            },
          },
        ],
      );
    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Não foi possível salvar os dados.',
      );
    } finally {
      enviando.current = false;
      setSalvando(false);
    }
  };

  const habilitado = !salvando && !carregando;

  return (
    <>
      <Stack.Screen
        options={{
          title: editando
            ? 'Editar Paciente'
            : 'Cadastrar Paciente',
        }}
      />

      <ScrollView
        style={styles.tela}
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.container}>
          <View style={styles.cabecalho}>
            <View style={styles.avatar}>
              <IconeInterface
                nome={editando ? 'editar' : 'novo-paciente'}
                tamanho={30}
              />
            </View>

            <View style={styles.textosCabecalho}>
              <Text style={styles.titulo}>
                {editando
                  ? 'Editar paciente'
                  : 'Cadastrar paciente'}
              </Text>

              <Text style={styles.subtitulo}>
                {editando
                  ? `Prontuário nº ${editarId}`
                  : 'Registre os dados iniciais do paciente.'}
              </Text>
            </View>
          </View>

          {carregando ? (
            <ActivityIndicator
              size="large"
              color="#005088"
              style={{ marginVertical: 32 }}
            />
          ) : erroCarga ? (
            <View style={styles.card}>
              <Text style={styles.erro}>{erroCarga}</Text>

              <TouchableOpacity
                style={styles.botao}
                onPress={() => setTentativa(v => v + 1)}
              >
                <Text style={styles.textoBotao}>
                  Tentar novamente
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <View style={styles.card}>
                <View style={styles.tituloCardLinha}>
                  <IconeInterface nome="perfil" tamanho={22} />

                  <Text style={styles.tituloCard}>
                    Dados pessoais
                  </Text>
                </View>

                <Campo
                  rotulo="Nome completo *"
                  placeholder="Informe o nome completo"
                  value={nome}
                  onChangeText={setNome}
                  editable={habilitado}
                  maxLength={150}
                  autoCapitalize="words"
                />

                <Campo
                  rotulo="CPF *"
                  placeholder="000.000.000-00"
                  keyboardType="numeric"
                  value={cpf}
                  onChangeText={texto => setCpf(mascaraCpf(texto))}
                  editable={habilitado}
                  maxLength={14}
                />

                <Campo
                  rotulo="Data de nascimento"
                  placeholder="DD/MM/AAAA"
                  keyboardType="numeric"
                  value={dataNascimento}
                  onChangeText={texto =>
                    setDataNascimento(mascaraData(texto))
                  }
                  editable={habilitado}
                  maxLength={10}
                />

                <Campo
                  rotulo="Telefone de contato"
                  placeholder="(00) 00000-0000"
                  keyboardType="phone-pad"
                  value={telefone}
                  onChangeText={setTelefone}
                  editable={habilitado}
                  maxLength={20}
                />

                <Campo
                  rotulo="E-mail"
                  placeholder="paciente@exemplo.com"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoCorrect={false}
                  value={email}
                  onChangeText={setEmail}
                  editable={habilitado}
                  maxLength={150}
                />
              </View>

              <View style={styles.card}>
                <View style={styles.tituloCardLinha}>
                  <IconeInterface nome="avaliacao" tamanho={22} />

                  <Text style={styles.tituloCard}>
                    Informações clínicas iniciais
                  </Text>
                </View>

                <Campo
                  rotulo="Diagnóstico de base"
                  placeholder="Informe o diagnóstico, se conhecido"
                  value={diagnostico}
                  onChangeText={setDiagnostico}
                  editable={habilitado}
                  maxLength={200}
                  multiline
                />

                <Campo
                  rotulo="Local da lesão"
                  placeholder="Ex.: calcanhar esquerdo"
                  value={localLesao}
                  onChangeText={setLocalLesao}
                  editable={habilitado}
                  maxLength={100}
                />

                <Text style={styles.label}>
                  Evolução registrada pelo profissional
                </Text>

                <View style={styles.opcoes}>
                  {opcoesEvolucao.map(opcao => {
                    const ativo = statusEvolucao === opcao.valor;

                    return (
                      <TouchableOpacity
                        key={opcao.valor || 'nao-avaliada'}
                        accessibilityRole="button"
                        accessibilityState={{ selected: ativo }}
                        disabled={salvando}
                        style={[
                          styles.opcao,
                          ativo && styles.opcaoAtiva,
                        ]}
                        onPress={() =>
                          setStatusEvolucao(opcao.valor)
                        }
                      >
                        <Text
                          style={[
                            styles.textoOpcao,
                            ativo && styles.textoOpcaoAtiva,
                          ]}
                        >
                          {opcao.texto}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                <Text style={styles.observacao}>
                  A evolução deve ser registrada pelo profissional.
                  Ela não é determinada automaticamente pela IA.
                </Text>
              </View>

              {erro ? (
                <View style={styles.caixaErro}>
                  <Text
                    style={styles.erro}
                    accessibilityLiveRegion="polite"
                  >
                    {erro}
                  </Text>
                </View>
              ) : null}

              <TouchableOpacity
                accessibilityRole="button"
                style={[
                  styles.botao,
                  salvando && styles.desabilitado,
                ]}
                disabled={salvando}
                onPress={() => void handleSalvar()}
              >
                {salvando ? (
                  <ActivityIndicator color="#ffffff" />
                ) : (
                  <Text style={styles.textoBotao}>
                    {editando
                      ? 'Salvar alterações'
                      : 'Salvar cadastro'}
                  </Text>
                )}
              </TouchableOpacity>

              <Text style={styles.observacaoFinal}>
                * Campos obrigatórios para novos cadastros.
              </Text>
            </>
          )}
        </View>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  tela: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  scroll: {
    flexGrow: 1,
    alignItems: 'center',
  },
  container: {
    width: '100%',
    maxWidth: 760,
    padding: 20,
    paddingBottom: 36,
  },
  cabecalho: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 24,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#e5eff6',
  },
  textosCabecalho: {
    flex: 1,
  },
  titulo: {
    color: '#005088',
    fontSize: 23,
    fontWeight: '700',
    marginBottom: 5,
  },
  subtitulo: {
    fontSize: 13,
    color: '#64748b',
    lineHeight: 20,
  },
  card: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 14,
    padding: 18,
    marginBottom: 18,
  },
  tituloCardLinha: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 20,
  },
  tituloCard: {
    flex: 1,
    color: '#005088',
    fontSize: 17,
    fontWeight: '700',
  },
  grupoCampo: {
    marginBottom: 16,
  },
  label: {
    color: '#1e293b',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: '#b7c9d5',
    backgroundColor: '#f1f5f9',
    color: '#1e293b',
    borderRadius: 9,
    paddingHorizontal: 13,
    paddingVertical: 12,
    fontSize: 14,
  },
  inputMultilinha: {
    minHeight: 76,
    textAlignVertical: 'top',
  },
  opcoes: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 8,
  },
  opcao: {
    width: '48%',
    minHeight: 44,
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
  },
  opcaoAtiva: {
    backgroundColor: '#e5eff6',
    borderColor: '#005088',
  },
  textoOpcao: {
    color: '#475569',
    fontSize: 13,
  },
  textoOpcaoAtiva: {
    color: '#005088',
    fontWeight: '700',
  },
  observacao: {
    color: '#64748b',
    fontSize: 12,
    lineHeight: 18,
    marginTop: 14,
  },
  observacaoFinal: {
    color: '#64748b',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 16,
  },
  botao: {
    backgroundColor: '#005088',
    minHeight: 52,
    padding: 14,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  textoBotao: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
  },
  desabilitado: {
    opacity: 0.6,
  },
  caixaErro: {
    backgroundColor: '#fef2f2',
    borderRadius: 8,
    padding: 12,
    marginBottom: 14,
  },
  erro: {
    color: '#b91c1c',
    fontSize: 13,
    marginBottom: 8,
  },
});
