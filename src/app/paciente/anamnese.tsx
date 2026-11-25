
import { Stack, useLocalSearchParams } from 'expo-router';
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

import IconeInterface from '../../components/icone-interface';
import { API_URL } from '../../config/api';
import {
    apiJson,
    mensagemErro,
    obterToken,
} from '../../config/cliente';
import type { Paciente } from '../../types/paciente';
import { formatarData } from '../../types/paciente';

type Anamnese = {
  historia_pregressa: string | null;
  tabagismo: boolean | null;
  mobilidade_reduzida: boolean | null;
  possui_varizes: boolean | null;
  historico_amputacao: boolean | null;
  pulsos_perifericos: string | null;
  data_surgimento_ferida: string | null;
  causa_provavel: string | null;
  outras_patologias: string | null;
};

const inicial: Anamnese = {
  historia_pregressa: null,
  tabagismo: null,
  mobilidade_reduzida: null,
  possui_varizes: null,
  historico_amputacao: null,
  pulsos_perifericos: null,
  data_surgimento_ferida: null,
  causa_provavel: null,
  outras_patologias: null,
};

const perguntas = [
  { campo: 'tabagismo', titulo: 'Tabagismo' },
  {
    campo: 'mobilidade_reduzida',
    titulo: 'Mobilidade reduzida',
  },
  { campo: 'possui_varizes', titulo: 'Possui varizes' },
  {
    campo: 'historico_amputacao',
    titulo: 'Histórico de amputação',
  },
] as const;

const respostas = [
  { valor: null, texto: 'Não informado' },
  { valor: true, texto: 'Sim' },
  { valor: false, texto: 'Não' },
] as const;

function mascaraData(texto: string) {
  const digitos = texto.replace(/\D/g, '').slice(0, 8);

  if (digitos.length <= 2) return digitos;

  if (digitos.length <= 4) {
    return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
  }

  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
}

function converterData(texto: string): string | null {
  if (!texto.trim()) return null;

  const partes = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto);

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
    throw new Error(
      'Informe uma data de surgimento válida.',
    );
  }

  return `${ano}-${mes}-${dia}`;
}

export default function AnamneseScreen() {
  const { pacienteId } = useLocalSearchParams<{
    pacienteId?: string;
  }>();

  const id =
    typeof pacienteId === 'string' &&
    /^\d+$/.test(pacienteId)
      ? pacienteId
      : '';

  const enviando = useRef(false);

  const [paciente, setPaciente] =
    useState<Paciente | null>(null);

  const [dados, setDados] = useState<Anamnese>({
    ...inicial,
  });

  const [dataFerida, setDataFerida] = useState('');
  const [existente, setExistente] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erroCarga, setErroCarga] = useState('');
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [tentativa, setTentativa] = useState(0);

  function alterar<K extends keyof Anamnese>(
    campo: K,
    valor: Anamnese[K],
  ) {
    setDados(anterior => ({
      ...anterior,
      [campo]: valor,
    }));

    setSucesso('');
    setErro('');
  }

  useEffect(() => {
    const requisicao = new AbortController();
    const { signal } = requisicao;

    setCarregando(true);
    setErroCarga('');
    setErro('');
    setSucesso('');
    setPaciente(null);
    setExistente(false);
    setDados({ ...inicial });
    setDataFerida('');

    async function carregar() {
      try {
        if (!id) {
          throw new Error('Prontuário inválido.');
        }

        // Confirma primeiro o acesso ao paciente.
        const pacienteAtual = await apiJson<Paciente>(
          `/pacientes/${id}`,
          { signal },
        );

        if (signal.aborted) return;

        setPaciente(pacienteAtual);

        const token = await obterToken();

        const resposta = await fetch(
          `${API_URL}/pacientes/${id}/anamnese`,
          {
            signal,
            headers: {
              Accept: 'application/json',
              Authorization: `Bearer ${token}`,
            },
          },
        );

        if (signal.aborted) return;

        // A ausência de anamnese permite um novo cadastro.
        if (resposta.status === 404) {
          setExistente(false);
          return;
        }

        if (!resposta.ok) {
          throw new Error(await mensagemErro(resposta));
        }

        const registro = await resposta.json() as Anamnese;

        if (signal.aborted) return;

        setDados({
          historia_pregressa:
            registro.historia_pregressa ?? null,
          tabagismo: registro.tabagismo ?? null,
          mobilidade_reduzida:
            registro.mobilidade_reduzida ?? null,
          possui_varizes: registro.possui_varizes ?? null,
          historico_amputacao:
            registro.historico_amputacao ?? null,
          pulsos_perifericos:
            registro.pulsos_perifericos ?? null,
          data_surgimento_ferida:
            registro.data_surgimento_ferida ?? null,
          causa_provavel:
            registro.causa_provavel ?? null,
          outras_patologias:
            registro.outras_patologias ?? null,
        });

        setDataFerida(
          registro.data_surgimento_ferida
            ? formatarData(registro.data_surgimento_ferida)
            : '',
        );

        setExistente(true);
      } catch (e) {
        if (!signal.aborted) {
          setErroCarga(
            e instanceof Error
              ? e.message
              : 'Não foi possível carregar a anamnese.',
          );
        }
      } finally {
        if (!signal.aborted) {
          setCarregando(false);
        }
      }
    }

    void carregar();

    return () => requisicao.abort();
  }, [id, tentativa]);

  async function salvar() {
    if (
      enviando.current ||
      carregando ||
      erroCarga ||
      !paciente ||
      !id
    ) return;

    setErro('');
    setSucesso('');

    let dataFormatada: string | null;

    try {
      dataFormatada = converterData(dataFerida);
    } catch (e) {
      setErro(
        e instanceof Error ? e.message : 'Data inválida.',
      );
      return;
    }

    enviando.current = true;
    setSalvando(true);

    try {
      const corpo: Anamnese = {
        ...dados,
        historia_pregressa:
          dados.historia_pregressa?.trim() || null,
        outras_patologias:
          dados.outras_patologias?.trim() || null,
        causa_provavel:
          dados.causa_provavel?.trim() || null,
        data_surgimento_ferida: dataFormatada,
      };

      await apiJson<Anamnese>(
        `/pacientes/${id}/anamnese`,
        {
          method: existente ? 'PATCH' : 'POST',
          body: JSON.stringify(corpo),
        },
      );

      setDados(corpo);
      setExistente(true);
      setSucesso('Anamnese salva com sucesso.');
    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Não foi possível salvar a anamnese.',
      );
    } finally {
      enviando.current = false;
      setSalvando(false);
    }
  }

  return (
    <>
      <Stack.Screen
        options={{ title: 'Anamnese de Admissão' }}
      />

      <ScrollView
        style={styles.tela}
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.container}>
          <View style={styles.cabecalho}>
            <View style={styles.icone}>
              <IconeInterface nome="avaliacao" tamanho={30} />
            </View>

            <View style={styles.textos}>
              <Text style={styles.titulo}>
                Anamnese de admissão
              </Text>

              <Text style={styles.subtitulo}>
                Prontuário nº {id || '—'}
              </Text>

              {paciente ? (
                <Text style={styles.nomePaciente}>
                  {paciente.nome_completo}
                </Text>
              ) : null}
            </View>
          </View>

          {carregando ? (
            <ActivityIndicator
              size="large"
              color="#005088"
              style={{ marginVertical: 30 }}
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
              <View style={styles.aviso}>
                <IconeInterface
                  nome="arquivo"
                  tamanho={24}
                />

                <View style={styles.textos}>
                  <Text style={styles.tituloAviso}>
                    {existente
                      ? 'Anamnese cadastrada'
                      : 'Nova anamnese'}
                  </Text>

                  <Text style={styles.subtitulo}>
                    Registre apenas informações conhecidas
                    ou avaliadas pelo profissional.
                    Os campos desconhecidos podem permanecer
                    como não informados.
                  </Text>
                </View>
              </View>

              <View style={styles.card}>
                <Text style={styles.tituloCard}>
                  Histórico clínico
                </Text>

                <Text style={styles.label}>
                  História pregressa
                </Text>

                <TextInput
                  style={[styles.input, styles.multilinha]}
                  accessibilityLabel="História pregressa"
                  placeholder="Informe o histórico clínico do paciente"
                  placeholderTextColor="#64748b"
                  value={dados.historia_pregressa || ''}
                  onChangeText={texto =>
                    alterar('historia_pregressa', texto)
                  }
                  multiline
                  editable={!salvando}
                />

                {perguntas.map(pergunta => (
                  <View
                    key={pergunta.campo}
                    style={styles.grupo}
                  >
                    <Text style={styles.label}>
                      {pergunta.titulo}
                    </Text>

                    <View style={styles.opcoes}>
                      {respostas.map(opcao => {
                        const ativo =
                          dados[pergunta.campo] === opcao.valor;

                        return (
                          <TouchableOpacity
                            key={opcao.texto}
                            accessibilityRole="button"
                            accessibilityState={{
                              selected: ativo,
                            }}
                            disabled={salvando}
                            style={[
                              styles.opcao,
                              ativo && styles.opcaoAtiva,
                            ]}
                            onPress={() =>
                              alterar(
                                pergunta.campo,
                                opcao.valor,
                              )
                            }
                          >
                            <Text
                              style={[
                                styles.textoOpcao,
                                ativo && styles.textoAtivo,
                              ]}
                            >
                              {opcao.texto}
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  </View>
                ))}
              </View>

              <View style={styles.card}>
                <Text style={styles.tituloCard}>
                  Informações complementares
                </Text>

                <Text style={styles.label}>
                  Pulsos periféricos
                </Text>

                <View style={styles.opcoesPulsos}>
                  {[
                    { valor: null, texto: 'Não informado' },
                    { valor: 'presentes', texto: 'Presentes' },
                    {
                      valor: 'diminuidos',
                      texto: 'Diminuídos',
                    },
                    { valor: 'ausentes', texto: 'Ausentes' },
                  ].map(opcao => {
                    const ativo =
                      dados.pulsos_perifericos === opcao.valor;

                    return (
                      <TouchableOpacity
                        key={opcao.texto}
                        accessibilityRole="button"
                        accessibilityState={{ selected: ativo }}
                        disabled={salvando}
                        style={[
                          styles.opcaoPulso,
                          ativo && styles.opcaoAtiva,
                        ]}
                        onPress={() =>
                          alterar(
                            'pulsos_perifericos',
                            opcao.valor,
                          )
                        }
                      >
                        <Text
                          style={[
                            styles.textoOpcao,
                            ativo && styles.textoAtivo,
                          ]}
                        >
                          {opcao.texto}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                <Text style={styles.label}>
                  Data de surgimento da ferida
                </Text>

                <TextInput
                  style={styles.input}
                  accessibilityLabel="Data de surgimento da ferida"
                  placeholder="DD/MM/AAAA"
                  placeholderTextColor="#64748b"
                  keyboardType="numeric"
                  maxLength={10}
                  value={dataFerida}
                  editable={!salvando}
                  onChangeText={texto => {
                    setDataFerida(mascaraData(texto));
                    setSucesso('');
                    setErro('');
                  }}
                />

                <Text style={styles.label}>
                  Causa provável (etiologia)
                </Text>

                <TextInput
                  style={styles.input}
                  accessibilityLabel="Causa provável"
                  placeholder="Informe, se conhecida"
                  placeholderTextColor="#64748b"
                  maxLength={50}
                  editable={!salvando}
                  value={dados.causa_provavel || ''}
                  onChangeText={texto =>
                    alterar('causa_provavel', texto)
                  }
                />

                <Text style={styles.label}>
                  Outras patologias e histórico familiar
                </Text>

                <TextInput
                  style={[styles.input, styles.multilinha]}
                  accessibilityLabel="Outras patologias e histórico familiar"
                  placeholder="Informe condições relevantes"
                  placeholderTextColor="#64748b"
                  multiline
                  editable={!salvando}
                  value={dados.outras_patologias || ''}
                  onChangeText={texto =>
                    alterar('outras_patologias', texto)
                  }
                />
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

              {sucesso ? (
                <View style={styles.caixaSucesso}>
                  <IconeInterface
                    nome="confirmar"
                    tamanho={22}
                    cor="#15803d"
                  />

                  <Text
                    style={styles.sucesso}
                    accessibilityLiveRegion="polite"
                  >
                    {sucesso}
                  </Text>
                </View>
              ) : null}

              <TouchableOpacity
                accessibilityRole="button"
                disabled={salvando}
                style={[
                  styles.botao,
                  salvando && { opacity: 0.6 },
                ]}
                onPress={() => void salvar()}
              >
                {salvando ? (
                  <ActivityIndicator color="#ffffff" />
                ) : (
                  <Text style={styles.textoBotao}>
                    {existente
                      ? 'Salvar alterações'
                      : 'Salvar anamnese'}
                  </Text>
                )}
              </TouchableOpacity>
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
    marginBottom: 22,
  },

  icone: {
    width: 60,
    height: 60,
    borderRadius: 14,
    backgroundColor: '#e5eff6',
    justifyContent: 'center',
    alignItems: 'center',
  },

  textos: {
    flex: 1,
    minWidth: 0,
  },

  titulo: {
    fontSize: 23,
    color: '#005088',
    fontWeight: '700',
    marginBottom: 5,
  },

  subtitulo: {
    fontSize: 13,
    color: '#64748b',
    lineHeight: 20,
  },

  nomePaciente: {
    fontSize: 14,
    color: '#334155',
    fontWeight: '600',
    marginTop: 4,
  },

  aviso: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    padding: 15,
    backgroundColor: '#eaf2f8',
    borderWidth: 1,
    borderColor: '#ccdfec',
    borderRadius: 12,
    marginBottom: 18,
  },

  tituloAviso: {
    color: '#005088',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 5,
  },

  card: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 14,
    padding: 18,
    marginBottom: 18,
  },

  tituloCard: {
    fontSize: 17,
    fontWeight: '700',
    color: '#005088',
    marginBottom: 20,
  },

  label: {
    fontSize: 14,
    color: '#1e293b',
    fontWeight: '600',
    marginBottom: 8,
  },

  input: {
    minHeight: 48,
    padding: 13,
    borderWidth: 1,
    borderColor: '#b7c9d5',
    borderRadius: 9,
    backgroundColor: '#f1f5f9',
    fontSize: 14,
    color: '#1e293b',
    marginBottom: 18,
  },

  multilinha: {
    minHeight: 100,
    textAlignVertical: 'top',
  },

  grupo: {
    marginBottom: 17,
  },

  opcoes: {
    flexDirection: 'row',
    gap: 6,
  },

  opcao: {
    flex: 1,
    minWidth: 0,
    minHeight: 46,
    padding: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
  },

  opcaoAtiva: {
    backgroundColor: '#e5eff6',
    borderColor: '#005088',
  },

  textoOpcao: {
    fontSize: 13,
    color: '#475569',
    textAlign: 'center',
  },

  textoAtivo: {
    fontWeight: '700',
    color: '#005088',
  },

  opcoesPulsos: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 18,
  },

  opcaoPulso: {
    flexGrow: 1,
    flexBasis: '45%',
    minHeight: 46,
    padding: 10,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
  },

  botao: {
    minHeight: 52,
    backgroundColor: '#005088',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },

  textoBotao: {
    fontSize: 15,
    fontWeight: '700',
    color: '#ffffff',
  },

  caixaErro: {
    backgroundColor: '#fef2f2',
    padding: 14,
    borderRadius: 9,
    marginBottom: 14,
  },

  erro: {
    fontSize: 13,
    color: '#b91c1c',
    lineHeight: 20,
  },

  caixaSucesso: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 14,
    borderRadius: 9,
    backgroundColor: '#dcfce7',
    marginBottom: 14,
  },

  sucesso: {
    flex: 1,
    fontWeight: '600',
    fontSize: 14,
    color: '#15803d',
  },
});
