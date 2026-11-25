
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
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

  const [busca, setBusca] = useState('');
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async (signal?: AbortSignal) => {
    setCarregando(true);
    setErro('');

    try {
      const dados = await apiJson<Paciente[]>(
        '/pacientes',
        { signal },
      );

      if (!signal?.aborted) {
        setPacientes(dados);
      }
    } catch (e) {
      if (!signal?.aborted) {
        setErro(
          e instanceof Error
            ? e.message
            : 'Falha ao carregar pacientes.',
        );
      }
    } finally {
      if (!signal?.aborted) {
        setCarregando(false);
      }
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      const requisicao = new AbortController();

      void carregar(requisicao.signal);

      return () => requisicao.abort();
    }, [carregar]),
  );

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
          <View style={styles.textosCabecalho}>
            <Text style={styles.titulo}>Pacientes</Text>

            <Text style={styles.subtitulo}>
              Consulte e gerencie os prontuários cadastrados.
            </Text>
          </View>

          <TouchableOpacity
            style={styles.botaoNovo}
            accessibilityRole="button"
            activeOpacity={0.8}
            onPress={() => router.push('/paciente/novo')}
          >
            <IconeInterface
              nome="novo-paciente"
              tamanho={22}
              cor="#ffffff"
            />

            <Text style={styles.botaoNovoTexto}>
              Novo paciente
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.campoBusca}>
          <IconeInterface nome="pesquisa" tamanho={22} />

          <TextInput
            style={styles.inputBusca}
            accessibilityLabel="Pesquisar pacientes"
            placeholder="Buscar por nome, CPF ou prontuário"
            placeholderTextColor="#64748b"
            value={busca}
            autoCorrect={false}
            onChangeText={setBusca}
          />

          {busca ? (
            <TouchableOpacity
              accessibilityRole="button"
              onPress={() => setBusca('')}
              style={styles.botaoLimpar}
            >
              <Text style={styles.limpar}>Limpar</Text>
            </TouchableOpacity>
          ) : null}
        </View>

        {!carregando && !erro ? (
          <Text style={styles.contagem}>
            {filtrados.length} de {pacientes.length}
            {' '}paciente(s)
          </Text>
        ) : null}

        {erro ? (
          <View style={styles.caixaErro}>
            <Text style={styles.erro}>{erro}</Text>

            <TouchableOpacity
              accessibilityRole="button"
              onPress={() => void carregar()}
            >
              <Text style={styles.limpar}>
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
          style={styles.lista}
          contentContainerStyle={styles.conteudoLista}
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

            return (
              <TouchableOpacity
                style={styles.card}
                accessibilityRole="button"
                activeOpacity={0.75}
                onPress={() =>
                  router.push(`/paciente/${item.id_paciente}`)
                }
              >
                <View style={styles.avatar}>
                  <IconeInterface nome="perfil" tamanho={32} />
                </View>

                <View style={styles.dados}>
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

                  <View style={styles.linhaEvolucao}>
                    <Text style={styles.rotuloEvolucao}>
                      Evolução registrada:
                    </Text>

                    <View
                      style={[
                        styles.indicador,
                        { backgroundColor: estado.fundo },
                      ]}
                    >
                      <View
                        style={[
                          styles.ponto,
                          { backgroundColor: estado.cor },
                        ]}
                      />

                      <Text
                        style={[
                          styles.textoIndicador,
                          { color: estado.cor },
                        ]}
                      >
                        {estado.texto}
                      </Text>
                    </View>
                  </View>
                </View>

                <IconeInterface
                  nome="seta"
                  tamanho={20}
                  cor="#809bae"
                />
              </TouchableOpacity>
            );
          }}
          ListEmptyComponent={
            !carregando && !erro ? (
              <View style={styles.vazio}>
                <IconeInterface
                  nome="pacientes"
                  tamanho={42}
                  cor="#809bae"
                />

                <Text style={styles.tituloVazio}>
                  Nenhum paciente encontrado
                </Text>

                <Text style={styles.subtitulo}>
                  {busca
                    ? 'Tente pesquisar por outros dados.'
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
  textosCabecalho: {
    flex: 1,
    minWidth: 180,
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
  botaoNovoTexto: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
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
    fontSize: 14,
    color: '#1e293b',
  },
  botaoLimpar: {
    minHeight: 44,
    justifyContent: 'center',
  },
  limpar: {
    color: '#005088',
    fontSize: 13,
    fontWeight: '700',
  },
  contagem: {
    fontSize: 13,
    color: '#64748b',
    marginBottom: 14,
  },
  lista: {
    flex: 1,
  },
  conteudoLista: {
    paddingBottom: 20,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    gap: 14,
  },
  avatar: {
    backgroundColor: '#e5eff6',
    width: 60,
    height: 60,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dados: {
    flex: 1,
    minWidth: 0,
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
  linhaEvolucao: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 6,
    marginTop: 7,
  },
  rotuloEvolucao: {
    color: '#64748b',
    fontSize: 12,
  },
  indicador: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 20,
    paddingHorizontal: 9,
    paddingVertical: 5,
    gap: 5,
  },
  ponto: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  textoIndicador: {
    fontSize: 12,
    fontWeight: '600',
  },
  caixaErro: {
    backgroundColor: '#fef2f2',
    padding: 12,
    borderRadius: 8,
    gap: 10,
    marginBottom: 12,
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
