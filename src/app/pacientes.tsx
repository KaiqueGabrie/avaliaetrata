
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import IconeInterface from '../components/icone-interface';
import { apiJson } from '../config/cliente';
import type { Paciente } from '../types/paciente';
import { formatarData } from '../types/paciente';
import { Aviso } from '../utils/avisos';

type Aba = 'ativos' | 'arquivados';

function normalizar(valor: string) {
  return valor
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function evolucao(status: string | null) {
  switch (normalizar(status || '')) {
    case 'melhora':
      return {
        texto: 'Melhora',
        cor: '#15803d',
        fundo: '#dcfce7',
      };
    case 'estavel':
      return {
        texto: 'Estável',
        cor: '#854d0e',
        fundo: '#fef3c7',
      };
    case 'piora':
      return {
        texto: 'Piora',
        cor: '#b91c1c',
        fundo: '#fee2e2',
      };
    default:
      return {
        texto: 'Não avaliada',
        cor: '#64748b',
        fundo: '#f1f5f9',
      };
  }
}

function ocultarCpf(cpf: string | null) {
  if (!cpf) return 'Não informado';

  const digitos = cpf.replace(/\D/g, '');

  return digitos.length === 11
    ? `***.***.***-${digitos.slice(-2)}`
    : 'CPF cadastrado';
}

export default function PacientesScreen() {
  const router = useRouter();

  const bloqueado = useRef(false);
  const versaoCarga = useRef(0);

  const [aba, setAba] = useState<Aba>('ativos');
  const [busca, setBusca] = useState('');

  const [ativos, setAtivos] = useState<Paciente[]>([]);
  const [arquivados, setArquivados] = useState<Paciente[]>([]);

  const [carregando, setCarregando] = useState(true);
  const [operando, setOperando] = useState<number | null>(null);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async (signal?: AbortSignal) => {
    const versao = ++versaoCarga.current;

    setCarregando(true);
    setErro('');

    try {
      const [listaAtivos, listaArquivados] =
        await Promise.all([
          apiJson<Paciente[]>(
            '/pacientes',
            { signal, cache: 'no-store' },
          ),
          apiJson<Paciente[]>(
            '/pacientes?arquivados=true',
            { signal, cache: 'no-store' },
          ),
        ]);

      if (
        !signal?.aborted &&
        versao === versaoCarga.current
      ) {
        setAtivos(listaAtivos);
        setArquivados(listaArquivados);
      }
    } catch (e) {
      if (
        !signal?.aborted &&
        versao === versaoCarga.current
      ) {
        setAtivos([]);
        setArquivados([]);

        setErro(
          e instanceof Error
            ? e.message
            : 'Falha ao carregar pacientes.',
        );
      }
    } finally {
      if (
        !signal?.aborted &&
        versao === versaoCarga.current
      ) {
        setCarregando(false);
      }
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      const requisicao = new AbortController();

      setAtivos([]);
      setArquivados([]);

      void carregar(requisicao.signal);

      return () => {
        requisicao.abort();
        versaoCarga.current++;
      };
    }, [carregar]),
  );

  async function alterarArquivamento(
    paciente: Paciente,
    arquivar: boolean,
  ) {
    if (bloqueado.current) return;

    bloqueado.current = true;
    setOperando(paciente.id_paciente);
    setErro('');

    try {
      await apiJson<{
        id_paciente: number;
        arquivado: boolean;
      }>(
        `/pacientes/${paciente.id_paciente}/${
          arquivar ? 'arquivar' : 'restaurar'
        }`,
        { method: 'POST' },
      );

      // Atualiza a lista imediatamente.
      if (arquivar) {
        setAtivos(lista =>
          lista.filter(
            p => p.id_paciente !== paciente.id_paciente,
          ),
        );

        setArquivados(lista => [
          ...lista.filter(
            p => p.id_paciente !== paciente.id_paciente,
          ),
          paciente,
        ]);
      } else {
        setArquivados(lista =>
          lista.filter(
            p => p.id_paciente !== paciente.id_paciente,
          ),
        );

        setAtivos(lista => [
          ...lista.filter(
            p => p.id_paciente !== paciente.id_paciente,
          ),
          paciente,
        ]);
      }

      await carregar();

      Aviso.alert(
        arquivar
          ? 'Paciente arquivado'
          : 'Paciente restaurado',
        arquivar
          ? 'O prontuário e todos os seus registros foram preservados.'
          : 'O paciente voltou à lista de pacientes ativos.',
      );
    } catch (e) {
      Aviso.alert(
        'Não foi possível concluir',
        e instanceof Error
          ? e.message
          : 'Tente novamente.',
      );
    } finally {
      bloqueado.current = false;
      setOperando(null);
    }
  }

  function confirmar(
    paciente: Paciente,
    arquivar: boolean,
  ) {
    if (bloqueado.current) return;

    Aviso.alert(
      arquivar ? 'Arquivar paciente' : 'Restaurar paciente',
      arquivar
        ? `Deseja arquivar ${paciente.nome_completo}? As avaliações, fotografias e demais documentos serão preservados.`
        : `Deseja restaurar ${paciente.nome_completo}? O prontuário voltará a ficar disponível.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: arquivar ? 'Arquivar' : 'Restaurar',
          onPress: () =>
            void alterarArquivamento(paciente, arquivar),
        },
      ],
    );
  }

  const pacientes =
    aba === 'ativos' ? ativos : arquivados;

  const termo = normalizar(busca);
  const buscaNumerica = /^[\d.\-#\s]+$/.test(termo);
  const digitos = termo.replace(/\D/g, '');

  const filtrados = pacientes.filter(paciente => {
    if (!termo) return true;

    if (normalizar(paciente.nome_completo).includes(termo)) {
      return true;
    }

    if (buscaNumerica && digitos) {
      const cpf = (paciente.cpf || '').replace(/\D/g, '');

      return (
        cpf.includes(digitos) ||
        String(paciente.id_paciente) === digitos
      );
    }

    return false;
  });

  return (
    <View style={styles.tela}>
      <View style={styles.container}>
        <View style={styles.cabecalho}>
          <View style={styles.textos}>
            <Text style={styles.titulo}>Pacientes</Text>
            <Text style={styles.subtitulo}>
              Consulte e gerencie os prontuários cadastrados.
            </Text>
          </View>

          <TouchableOpacity
            accessibilityRole="button"
            style={styles.botaoNovo}
            onPress={() => router.push('/paciente/novo')}
          >
            <IconeInterface
              nome="novo-paciente"
              tamanho={22}
              cor="#ffffff"
            />
            <Text style={styles.textoBotaoNovo}>
              Novo paciente
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.abas}>
          {([
            { valor: 'ativos', titulo: 'Ativos', total: ativos.length },
            { valor: 'arquivados', titulo: 'Arquivados', total: arquivados.length },
          ] as const).map(item => (
            <TouchableOpacity
              key={item.valor}
              accessibilityRole="button"
              accessibilityState={{
                selected: aba === item.valor,
              }}
              disabled={operando !== null}
              style={[
                styles.aba,
                aba === item.valor && styles.abaAtiva,
              ]}
              onPress={() => setAba(item.valor)}
            >
              <Text style={[
                styles.textoAba,
                aba === item.valor && styles.textoAbaAtiva,
              ]}>
                {item.titulo} ({item.total})
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {aba === 'arquivados' ? (
          <View style={styles.aviso}>
            <IconeInterface nome="arquivo" tamanho={22} />

            <Text style={[styles.subtitulo, { flex: 1 }]}>
              Os pacientes arquivados mantêm seus registros.
              Restaure o paciente para acessar seu prontuário.
            </Text>
          </View>
        ) : null}

        <View style={styles.campoBusca}>
          <IconeInterface nome="pesquisa" tamanho={22} />

          <TextInput
            style={styles.inputBusca}
            accessibilityLabel="Pesquisar pacientes"
            placeholder="Buscar por nome, CPF ou prontuário"
            placeholderTextColor="#64748b"
            autoCorrect={false}
            value={busca}
            onChangeText={setBusca}
          />

          {busca ? (
            <TouchableOpacity onPress={() => setBusca('')}>
              <Text style={styles.link}>Limpar</Text>
            </TouchableOpacity>
          ) : null}
        </View>

        {!carregando && !erro ? (
          <Text style={styles.contagem}>
            {filtrados.length} de {pacientes.length} paciente(s)
          </Text>
        ) : null}

        {erro ? (
          <View style={styles.caixaErro}>
            <Text style={styles.erro}>{erro}</Text>

            <TouchableOpacity
              onPress={() => void carregar()}
            >
              <Text style={styles.link}>
                Tentar novamente
              </Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {carregando && pacientes.length === 0 ? (
          <ActivityIndicator
            size="large"
            color="#005088"
            style={{ marginVertical: 24 }}
          />
        ) : null}

        <FlatList
          style={{ flex: 1 }}
          contentContainerStyle={{ paddingBottom: 20 }}
          keyboardShouldPersistTaps="handled"
          data={filtrados}
          keyExtractor={item => String(item.id_paciente)}
          refreshControl={
            <RefreshControl
              refreshing={carregando}
              onRefresh={() => void carregar()}
            />
          }
          renderItem={({ item }) => {
            const estado = evolucao(item.status_evolucao);

            const arquivado = aba === 'arquivados';

            return (
              <View style={styles.card}>
                <TouchableOpacity
                  accessibilityRole="button"
                  accessibilityState={{
                    disabled: arquivado,
                  }}
                  disabled={arquivado || operando !== null}
                  activeOpacity={0.75}
                  style={styles.cardConteudo}
                  onPress={() =>
                    router.push(`/paciente/${item.id_paciente}`)
                  }
                >
                  <View style={styles.avatar}>
                    <IconeInterface nome="perfil" tamanho={32} />
                  </View>

                  <View style={styles.textos}>
                    <Text style={styles.nome}>
                      {item.nome_completo}
                    </Text>

                    <Text style={styles.detalhe}>
                      Prontuário nº {item.id_paciente}
                    </Text>

                    <Text style={styles.detalhe}>
                      CPF: {ocultarCpf(item.cpf)}
                    </Text>

                    <Text style={styles.detalhe}>
                      Nascimento: {formatarData(item.data_nascimento)}
                    </Text>

                    <View style={styles.linhaEstado}>
                      <View style={[
                        styles.indicador,
                        {
                          backgroundColor: arquivado
                            ? '#f1f5f9'
                            : estado.fundo,
                        },
                      ]}>
                        <Text style={[
                          styles.textoIndicador,
                          {
                            color: arquivado
                              ? '#64748b'
                              : estado.cor,
                          },
                        ]}>
                          {arquivado
                            ? 'Arquivado'
                            : estado.texto}
                        </Text>
                      </View>
                    </View>
                  </View>

                  {!arquivado ? (
                    <IconeInterface
                      nome="seta"
                      tamanho={20}
                      cor="#809bae"
                    />
                  ) : null}
                </TouchableOpacity>

                <View style={styles.acoes}>
                  <TouchableOpacity
                    accessibilityRole="button"
                    disabled={
                      operando !== null || carregando
                    }
                    style={[
                      styles.botaoAcao,
                      operando !== null && { opacity: 0.5 },
                    ]}
                    onPress={() =>
                      confirmar(item, !arquivado)
                    }
                  >
                    {operando === item.id_paciente ? (
                      <ActivityIndicator
                        size="small"
                        color="#005088"
                      />
                    ) : (
                      <IconeInterface
                        nome={arquivado ? 'confirmar' : 'arquivo'}
                        tamanho={19}
                      />
                    )}

                    <Text style={styles.link}>
                      {arquivado
                        ? 'Restaurar paciente'
                        : 'Arquivar paciente'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            );
          }}
          ListEmptyComponent={
            !carregando && !erro ? (
              <View style={styles.vazio}>
                <IconeInterface
                  nome={aba === 'arquivados' ? 'arquivo' : 'pacientes'}
                  tamanho={42}
                  cor="#809bae"
                />

                <Text style={styles.tituloVazio}>
                  Nenhum paciente encontrado
                </Text>

                <Text style={styles.subtitulo}>
                  {busca
                    ? 'Tente pesquisar por outros dados.'
                    : aba === 'arquivados'
                      ? 'Não existem pacientes arquivados.'
                      : 'Cadastre um paciente para começar.'}
                </Text>
              </View>
            ) : undefined
          }
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  tela: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  container: {
    flex: 1,
    width: '100%',
    maxWidth: 1120,
    alignSelf: 'center',
    padding: 20,
  },
  cabecalho: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 14,
    marginBottom: 22,
  },
  textos: {
    flex: 1,
    minWidth: 0,
  },
  titulo: {
    color: '#005088',
    fontSize: 26,
    fontWeight: '700',
    marginBottom: 6,
  },
  subtitulo: {
    fontSize: 13,
    color: '#64748b',
    lineHeight: 20,
  },
  botaoNovo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#005088',
    borderRadius: 10,
    minHeight: 46,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  textoBotaoNovo: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  abas: {
    flexDirection: 'row',
    backgroundColor: '#e5eff6',
    borderRadius: 10,
    padding: 4,
    gap: 4,
    marginBottom: 16,
  },
  aba: {
    flex: 1,
    minHeight: 44,
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
    fontWeight: '700',
  },
  aviso: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    backgroundColor: '#eaf2f8',
    borderRadius: 10,
    marginBottom: 15,
  },
  campoBusca: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 10,
    paddingHorizontal: 14,
    marginBottom: 14,
  },
  inputBusca: {
    flex: 1,
    minWidth: 0,
    minHeight: 50,
    color: '#1e293b',
    fontSize: 14,
  },
  link: {
    color: '#005088',
    fontSize: 13,
    fontWeight: '700',
  },
  contagem: {
    color: '#64748b',
    fontSize: 13,
    marginBottom: 14,
  },
  card: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 12,
    marginBottom: 12,
  },
  cardConteudo: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    gap: 14,
  },
  avatar: {
    width: 60,
    height: 60,
    backgroundColor: '#e5eff6',
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  nome: {
    fontSize: 16,
    color: '#005088',
    fontWeight: '700',
    marginBottom: 5,
  },
  detalhe: {
    fontSize: 13,
    color: '#475569',
    marginBottom: 3,
  },
  linhaEstado: {
    flexDirection: 'row',
    marginTop: 7,
  },
  indicador: {
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  textoIndicador: {
    fontSize: 12,
    fontWeight: '600',
  },
  acoes: {
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    paddingHorizontal: 16,
    paddingVertical: 6,
    alignItems: 'flex-end',
  },
  botaoAcao: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 6,
    minHeight: 40,
  },
  caixaErro: {
    backgroundColor: '#fef2f2',
    padding: 14,
    borderRadius: 10,
    marginBottom: 14,
    gap: 10,
  },
  erro: {
    color: '#b91c1c',
    fontSize: 13,
  },
  vazio: {
    alignItems: 'center',
    padding: 28,
    gap: 10,
  },
  tituloVazio: {
    color: '#334155',
    fontSize: 17,
    fontWeight: '700',
    textAlign: 'center',
  },
});
