
import { Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Platform,
    ScrollView,
    StyleSheet,
    Text,
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

type Termo = {
  id_termo: number;
  id_paciente: number;
  tamanho_bytes: number;
  declarado_assinado: boolean;
  data_registro: string;
};

const LIMITE_PDF = 5 * 1024 * 1024;

function formatarRegistro(valor: string) {
  const data = new Date(valor);

  return Number.isNaN(data.getTime())
    ? valor
    : data.toLocaleString('pt-BR');
}

function formatarTamanho(bytes: number) {
  if (bytes >= 1024 * 1024) {
    return (
      (bytes / (1024 * 1024))
        .toLocaleString('pt-BR', {
          maximumFractionDigits: 2,
        }) + ' MB'
    );
  }

  return (
    Math.max(1, Math.round(bytes / 1024)) + ' KB'
  );
}

export default function ConsentimentoScreen() {
  const { pacienteId } = useLocalSearchParams<{
    pacienteId?: string;
  }>();

  const id =
    typeof pacienteId === 'string' &&
    /^\d+$/.test(pacienteId)
      ? pacienteId
      : '';

  const bloqueado = useRef(false);

  const [paciente, setPaciente] =
    useState<Paciente | null>(null);

  const [termos, setTermos] = useState<Termo[]>([]);
  const [arquivo, setArquivo] = useState<File | null>(null);

  const [confirmado, setConfirmado] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [ocupado, setOcupado] = useState(false);

  const [erroCarga, setErroCarga] = useState('');
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    const requisicao = new AbortController();
    const { signal } = requisicao;

    setCarregando(true);
    setErroCarga('');
    setErro('');
    setSucesso('');
    setPaciente(null);
    setTermos([]);
    setArquivo(null);
    setConfirmado(false);

    async function carregar() {
      try {
        if (!id) {
          throw new Error('Prontuário inválido.');
        }

        const [dadosPaciente, documentos] =
          await Promise.all([
            apiJson<Paciente>(
              `/pacientes/${id}`,
              { signal, cache: 'no-store' },
            ),

            apiJson<Termo[]>(
              `/pacientes/${id}/consentimento`,
              { signal, cache: 'no-store' },
            ),
          ]);

        if (signal.aborted) return;

        setPaciente(dadosPaciente);
        setTermos(documentos);

      } catch (e) {
        if (!signal.aborted) {
          setErroCarga(
            e instanceof Error
              ? e.message
              : 'Não foi possível consultar os documentos.',
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

  function selecionarArquivo() {
    if (
      Platform.OS !== 'web' ||
      ocupado ||
      bloqueado.current
    ) return;

    setErro('');
    setSucesso('');

    const input = document.createElement('input');

    input.type = 'file';
    input.accept = 'application/pdf,.pdf';

    input.onchange = () => {
      const selecionado = input.files?.[0];

      if (!selecionado) return;

      if (!selecionado.name.toLowerCase().endsWith('.pdf')) {
        setErro('Selecione um documento PDF.');
        return;
      }

      if (
        selecionado.size === 0 ||
        selecionado.size > LIMITE_PDF
      ) {
        setErro('Selecione um PDF de até 5 MB.');
        return;
      }

      setArquivo(selecionado);
      setConfirmado(false);
    };

    input.click();
  }

  async function baixarPdf(
    caminho: string,
    nome: string,
  ) {
    if (
      Platform.OS !== 'web' ||
      bloqueado.current
    ) return;

    bloqueado.current = true;
    setOcupado(true);
    setErro('');
    setSucesso('');

    try {
      const token = await obterToken();

      const resposta = await fetch(
        `${API_URL}${caminho}`,
        {
          method: 'GET',
          cache: 'no-store',

          headers: {
            Accept: 'application/pdf',
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!resposta.ok) {
        throw new Error(
          await mensagemErro(resposta)
        );
      }

      const blob = await resposta.blob();

      const endereco = URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = endereco;
      link.download = nome;

      document.body.appendChild(link);
      link.click();
      link.remove();

      setTimeout(() => {
        URL.revokeObjectURL(endereco);
      }, 60000);

      setSucesso('Download solicitado.');

    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Não foi possível baixar o documento.',
      );
    } finally {
      bloqueado.current = false;
      setOcupado(false);
    }
  }

  async function salvarTermo() {
    if (
      bloqueado.current ||
      !arquivo ||
      !confirmado ||
      !id
    ) return;

    bloqueado.current = true;
    setOcupado(true);
    setErro('');
    setSucesso('');

    try {
      const token = await obterToken();

      const formulario = new FormData();

      formulario.append(
        'arquivo',
        arquivo,
        arquivo.name,
      );

      formulario.append(
        'declarado_assinado',
        'true',
      );

      const resposta = await fetch(
        `${API_URL}/pacientes/${id}/consentimento`,
        {
          method: 'POST',

          headers: {
            Accept: 'application/json',
            Authorization: `Bearer ${token}`,
          },

          body: formulario,
        },
      );

      if (!resposta.ok) {
        const mensagens: Record<number, string> = {
          409: 'Este documento já foi registrado.',
          413: 'O documento excede o limite de 5 MB.',
          422: 'Confira se o PDF é válido e não possui senha.',
          502: 'Não foi possível armazenar o documento.',
          503: 'O armazenamento de termos não está configurado.',
        };

        throw new Error(
          mensagens[resposta.status] ||
          await mensagemErro(resposta),
        );
      }

      const termo =
        await resposta.json() as Termo;

      setTermos(anteriores => [
        termo,
        ...anteriores,
      ]);

      setArquivo(null);
      setConfirmado(false);

      setSucesso(
        'Documento registrado com sucesso.',
      );

    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Não foi possível registrar o documento.',
      );
    } finally {
      bloqueado.current = false;
      setOcupado(false);
    }
  }

  const navegador = Platform.OS === 'web';

  return (
    <>
      <Stack.Screen
        options={{ title: 'Termo de Consentimento' }}
      />

      <ScrollView
        style={styles.tela}
        contentContainerStyle={styles.scroll}
      >
        <View style={styles.container}>

          <View style={styles.cabecalho}>
            <View style={styles.icone}>
              <IconeInterface
                nome="arquivo"
                tamanho={30}
              />
            </View>

            <View style={styles.textos}>
              <Text style={styles.titulo}>
                Termo de consentimento
              </Text>

              <Text style={styles.subtitulo}>
                Prontuário nº {id || '—'}
              </Text>

              {paciente ? (
                <Text style={styles.nome}>
                  {paciente.nome_completo}
                </Text>
              ) : null}
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
              <Text style={styles.erro}>
                {erroCarga}
              </Text>

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
                  nome="escudo"
                  tamanho={24}
                />

                <View style={styles.textos}>
                  <Text style={styles.tituloAviso}>
                    Privacidade das informações
                  </Text>

                  <Text style={styles.subtitulo}>
                    Os documentos são armazenados de forma
                    privada e vinculados ao prontuário.
                    Utilize apenas documentos autorizados.
                  </Text>
                </View>
              </View>

              {!navegador ? (
                <View style={styles.card}>
                  <Text style={styles.subtitulo}>
                    Nesta versão, a geração e anexação
                    de documentos estão disponíveis
                    pelo navegador web.
                  </Text>
                </View>
              ) : null}

              <View style={styles.card}>
                <Text style={styles.tituloCard}>
                  1. Gerar modelo do termo
                </Text>

                <Text style={styles.descricao}>
                  Gere o documento preenchido com a
                  identificação do paciente e do profissional.
                  O modelo acadêmico exige aprovação
                  institucional antes do uso real.
                </Text>

                <TouchableOpacity
                  accessibilityRole="button"
                  disabled={ocupado || !navegador}
                  style={[
                    styles.botao,
                    (ocupado || !navegador) &&
                      styles.desabilitado,
                  ]}
                  onPress={() => void baixarPdf(
                    `/pacientes/${id}/consentimento/modelo`,
                    `termo-modelo-${id}.pdf`,
                  )}
                >
                  <IconeInterface
                    nome="arquivo"
                    tamanho={21}
                    cor="#ffffff"
                  />

                  <Text style={styles.textoBotao}>
                    Gerar termo em PDF
                  </Text>
                </TouchableOpacity>
              </View>

              <View style={styles.card}>
                <Text style={styles.tituloCard}>
                  2. Anexar termo assinado
                </Text>

                <Text style={styles.descricao}>
                  Selecione o PDF correspondente ao
                  documento recebido do paciente
                  ou de seu responsável.
                </Text>

                <TouchableOpacity
                  accessibilityRole="button"
                  disabled={ocupado || !navegador}
                  style={[
                    styles.areaArquivo,
                    (ocupado || !navegador) &&
                      styles.desabilitado,
                  ]}
                  onPress={selecionarArquivo}
                >
                  <IconeInterface
                    nome="arquivo"
                    tamanho={34}
                  />

                  <Text
                    style={styles.nomeArquivo}
                    numberOfLines={2}
                  >
                    {arquivo
                      ? arquivo.name
                      : 'Selecionar documento PDF'}
                  </Text>

                  <Text style={styles.subtitulo}>
                    {arquivo
                      ? formatarTamanho(arquivo.size)
                      : 'Tamanho máximo: 5 MB'}
                  </Text>
                </TouchableOpacity>

                {arquivo ? (
                  <TouchableOpacity
                    disabled={ocupado}
                    style={styles.remover}
                    onPress={() => {
                      setArquivo(null);
                      setConfirmado(false);
                    }}
                  >
                    <Text style={styles.textoRemover}>
                      Remover arquivo selecionado
                    </Text>
                  </TouchableOpacity>
                ) : null}

                <TouchableOpacity
                  accessibilityRole="checkbox"
                  accessibilityState={{
                    checked: confirmado,
                    disabled: ocupado || !arquivo,
                  }}
                  disabled={ocupado || !arquivo}
                  style={styles.confirmacao}
                  onPress={() => setConfirmado(v => !v)}
                >
                  <View style={[
                    styles.checkbox,
                    confirmado && styles.checkboxAtivo,
                  ]}>
                    {confirmado ? (
                      <IconeInterface
                        nome="confirmar"
                        tamanho={18}
                        cor="#ffffff"
                      />
                    ) : null}
                  </View>

                  <Text style={styles.textoConfirmacao}>
                    Confirmo que recebi o documento
                    assinado pelo paciente ou responsável
                    e que ele corresponde a este prontuário.
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  accessibilityRole="button"
                  disabled={
                    ocupado ||
                    !arquivo ||
                    !confirmado ||
                    !navegador
                  }
                  style={[
                    styles.botao,
                    (
                      ocupado ||
                      !arquivo ||
                      !confirmado ||
                      !navegador
                    ) && styles.desabilitado,
                  ]}
                  onPress={() => void salvarTermo()}
                >
                  {ocupado ? (
                    <ActivityIndicator color="#ffffff" />
                  ) : (
                    <Text style={styles.textoBotao}>
                      Salvar documento
                    </Text>
                  )}
                </TouchableOpacity>
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
                    accessibilityLiveRegion="polite"
                    style={styles.textoSucesso}
                  >
                    {sucesso}
                  </Text>
                </View>
              ) : null}

              <Text style={styles.tituloHistorico}>
                Documentos registrados
              </Text>

              {termos.length === 0 ? (
                <View style={styles.card}>
                  <Text style={styles.subtitulo}>
                    Nenhum termo foi registrado
                    para este paciente.
                  </Text>
                </View>
              ) : (
                termos.map(termo => (
                  <View
                    key={termo.id_termo}
                    style={styles.documento}
                  >
                    <View style={styles.iconeDocumento}>
                      <IconeInterface
                        nome="arquivo"
                        tamanho={25}
                      />
                    </View>

                    <View style={styles.textos}>
                      <Text style={styles.tituloDocumento}>
                        Termo nº {termo.id_termo}
                      </Text>

                      <Text style={styles.subtitulo}>
                        Registrado em{' '}
                        {formatarRegistro(termo.data_registro)}
                      </Text>

                      <Text style={styles.subtitulo}>
                        {formatarTamanho(termo.tamanho_bytes)}
                      </Text>

                      <Text style={styles.estado}>
                        Assinatura declarada pelo profissional
                      </Text>

                      <TouchableOpacity
                        accessibilityRole="button"
                        disabled={ocupado || !navegador}
                        style={styles.baixar}
                        onPress={() => void baixarPdf(
                          `/pacientes/${id}/consentimento/${termo.id_termo}/arquivo`,
                          `termo-${termo.id_termo}.pdf`,
                        )}
                      >
                        <Text style={styles.textoBaixar}>
                          Baixar documento
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ))
              )}

              <Text style={styles.observacaoFinal}>
                O registro do documento não verifica
                automaticamente a autenticidade da assinatura
                nem determina se todas as condições de
                consentimento foram atendidas.
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
    marginBottom: 22,
  },

  icone: {
    width: 60,
    height: 60,
    backgroundColor: '#e5eff6',
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },

  textos: {
    flex: 1,
    minWidth: 0,
  },

  titulo: {
    fontSize: 23,
    color: '#005088',
    fontWeight: '700',
    marginBottom: 6,
  },

  subtitulo: {
    fontSize: 13,
    color: '#64748b',
    lineHeight: 20,
  },

  nome: {
    fontSize: 14,
    fontWeight: '600',
    color: '#334155',
    marginTop: 5,
  },

  aviso: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    backgroundColor: '#eaf2f8',
    borderWidth: 1,
    borderColor: '#ccdfec',
    padding: 16,
    borderRadius: 12,
    marginBottom: 18,
  },

  tituloAviso: {
    color: '#005088',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 6,
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
    color: '#005088',
    fontSize: 17,
    fontWeight: '700',
    marginBottom: 12,
  },

  descricao: {
    color: '#475569',
    fontSize: 14,
    lineHeight: 21,
    marginBottom: 18,
  },

  botao: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 9,
    backgroundColor: '#005088',
    minHeight: 52,
    padding: 13,
    borderRadius: 10,
  },

  textoBotao: {
    fontSize: 14,
    color: '#ffffff',
    fontWeight: '700',
  },

  desabilitado: {
    opacity: 0.55,
  },

  areaArquivo: {
    backgroundColor: '#f5f9fc',
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: '#9bb5c8',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    gap: 10,
  },

  nomeArquivo: {
    color: '#005088',
    fontWeight: '700',
    fontSize: 14,
    textAlign: 'center',
  },

  remover: {
    alignSelf: 'center',
    padding: 12,
  },

  textoRemover: {
    fontSize: 12,
    color: '#b91c1c',
    fontWeight: '600',
  },

  confirmacao: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    paddingVertical: 20,
  },

  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 1,
    borderColor: '#809bae',
    borderRadius: 5,
    justifyContent: 'center',
    alignItems: 'center',
  },

  checkboxAtivo: {
    backgroundColor: '#005088',
    borderColor: '#005088',
  },

  textoConfirmacao: {
    flex: 1,
    fontSize: 13,
    color: '#334155',
    lineHeight: 20,
  },

  tituloHistorico: {
    color: '#172c3c',
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 14,
  },

  documento: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },

  iconeDocumento: {
    backgroundColor: '#e5eff6',
    width: 46,
    height: 46,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },

  tituloDocumento: {
    fontSize: 15,
    color: '#005088',
    fontWeight: '700',
    marginBottom: 6,
  },

  estado: {
    fontSize: 12,
    fontWeight: '600',
    color: '#15803d',
    marginTop: 8,
  },

  baixar: {
    marginTop: 10,
    paddingVertical: 10,
    alignSelf: 'flex-start',
  },

  textoBaixar: {
    color: '#005088',
    fontWeight: '700',
    fontSize: 13,
  },

  caixaErro: {
    backgroundColor: '#fef2f2',
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
  },

  erro: {
    color: '#b91c1c',
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 8,
  },

  caixaSucesso: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 14,
    backgroundColor: '#dcfce7',
    borderRadius: 10,
    marginBottom: 16,
  },

  textoSucesso: {
    flex: 1,
    color: '#15803d',
    fontWeight: '600',
    fontSize: 13,
  },

  observacaoFinal: {
    color: '#64748b',
    fontSize: 12,
    lineHeight: 18,
    marginTop: 8,
  },
});

