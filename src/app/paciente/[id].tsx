import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { apiJson } from '../../config/cliente';
import type { AnaliseResumo, Paciente } from '../../types/paciente';
import { formatarData } from '../../types/paciente';

const POR_PAGINA = 12;

type ResumoRevisao = {
  status: 'aprovado';
  versao: number | null;
  provedor_base: string | null;
  percentuais: {
    granulacao: number;
    esfacelo: number;
    necrose: number;
    nao_classificado: number;
  };
};

type Previa = {
  revisao_resumo?: ResumoRevisao | null;
  imagem_url: string | null;
  tecido_predominante: {
    classe: 'granulacao' | 'esfacelo' | 'necrose';
    percentual: number;
  } | null;
};

const nomesTecidos = {
  granulacao: 'Granulação',
  esfacelo: 'Esfacelo',
  necrose: 'Necrose',
};

function FotoPrevia({ url }: { url: string }) {
  const [falhou, setFalhou] = useState(false);
  if (falhou) return null;

  return (
    <Image
      accessibilityLabel="Fotografia da avaliação"
      source={{ uri: url }}
      style={styles.miniatura}
      resizeMode="contain"
      onError={() => setFalhou(true)}
    />
  );
}

function situacaoAvaliacao(status: string) {
  const estado = status.trim().toLowerCase();

  if (estado === 'pendente') {
    return { texto: 'Aguardando análise', concluida: false };
  }

  if (estado === 'concluida' || estado === 'concluída' || estado === 'concluído') {
    return { texto: 'Concluída', concluida: true };
  }

  return { texto: status || 'Situação não informada', concluida: false };
}

function normalizarBusca(texto: string) {
  return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/#(?=\d)/g, '').trim();
}

function filtrarAvaliacoes(analises: AnaliseResumo[], busca: string) {
  const numero = /^#\s*(\d+)$/.exec(busca.trim());
  if (numero) return analises.filter(analise => String(analise.id_analise) === numero[1]);

  const termos = normalizarBusca(busca).split(/\s+/).filter(Boolean);
  if (!termos.length) return analises;

  return analises.filter(analise => {
    const conteudo = normalizarBusca([
      'avaliação',
      analise.id_analise,
      formatarData(analise.data_analise),
      analise.data_analise?.slice(0, 10),
      analise.queixa_principal,
      situacaoAvaliacao(analise.status).texto,
    ].join(' '));
    return termos.every(termo => conteudo.includes(termo));
  });
}

export default function ProntuarioPacienteScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [paciente, setPaciente] = useState<Paciente | null>(null);
  const [busca, setBusca] = useState('');
  const [pagina, setPagina] = useState(0);
  const [previas, setPrevias] = useState<Record<string, Previa>>({});
  const [analises, setAnalises] = useState<AnaliseResumo[]>([]);
  const [carregandoPaciente, setCarregandoPaciente] = useState(true);
  const [carregandoHistorico, setCarregandoHistorico] = useState(true);
  const [erroPaciente, setErroPaciente] = useState('');
  const [erroHistorico, setErroHistorico] = useState('');

  useFocusEffect(useCallback(() => {
    if (!id || !/^\d+$/.test(id)) {
      setErroPaciente('Paciente inválido.');
      setCarregandoPaciente(false);
      setCarregandoHistorico(false);
      return;
    }

    const requisicao = new AbortController();
    const { signal } = requisicao;
    setCarregandoPaciente(true);
    setCarregandoHistorico(true);
    setErroPaciente('');
    setErroHistorico('');

    void apiJson<Paciente>(`/pacientes/${id}`, { signal })
      .then(dados => {
        if (!signal.aborted) setPaciente(dados);
      })
      .catch(e => {
        if (!signal.aborted) {
          setErroPaciente(e instanceof Error ? e.message : 'Não foi possível carregar o prontuário.');
        }
      })
      .finally(() => {
        if (!signal.aborted) setCarregandoPaciente(false);
      });

    void apiJson<AnaliseResumo[]>(`/pacientes/${id}/analises`, { signal })
      .then(dados => {
        if (!signal.aborted) setAnalises(dados);
      })
      .catch(e => {
        if (!signal.aborted) {
          setErroHistorico(e instanceof Error ? e.message : 'Não foi possível carregar o histórico.');
        }
      })
      .finally(() => {
        if (!signal.aborted) setCarregandoHistorico(false);
      });

    return () => requisicao.abort();
  }, [id]));

  const historicoPaciente = analises.filter(analise => String(analise.id_paciente_fk) === id);
  const avaliacoesFiltradas = filtrarAvaliacoes(historicoPaciente, busca);

  const totalPaginas = Math.max(1, Math.ceil(avaliacoesFiltradas.length / POR_PAGINA));
  const paginaAtual = Math.min(pagina, totalPaginas - 1);
  const avaliacoesDaPagina = avaliacoesFiltradas.slice(
    paginaAtual * POR_PAGINA,
    (paginaAtual + 1) * POR_PAGINA,
  );
  const consultaPrevias = avaliacoesDaPagina.map(item => 'ids=' + item.id_analise).join('&');

  useEffect(() => {
    if (!id || carregandoHistorico || !consultaPrevias) return;

    const requisicao = new AbortController();
    const { signal } = requisicao;

    void apiJson<{ previas: Record<string, Previa> }>(
      '/pacientes/' + id + '/analises/previas?' + consultaPrevias,
      { signal },
    ).then(dados => {
      if (!signal.aborted) setPrevias(dados.previas);
    }).catch(() => {
      if (!signal.aborted) setPrevias({});
    });

    return () => requisicao.abort();
  }, [id, carregandoHistorico, consultaPrevias]);

  const alterarBusca = (texto: string) => {
    setBusca(texto);
    setPagina(0);
  };

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      {carregandoPaciente && String(paciente?.id_paciente) !== id ? (
        <ActivityIndicator size="large" color="#0056b3" />
      ) : null}
      {erroPaciente ? <Text style={styles.erro}>{erroPaciente}</Text> : null}

      {paciente && String(paciente.id_paciente) === id ? (
        <>
          <View style={styles.cardHeader}>
            <Text style={styles.nome}>{paciente.nome_completo}</Text>
            <Text style={styles.subtext}>Prontuário nº {paciente.id_paciente}</Text>
            <Text style={styles.subtext}>CPF: {paciente.cpf || 'Não informado'}</Text>
            <Text style={styles.subtext}>Data Nasc.: {formatarData(paciente.data_nascimento)}</Text>
            <Text style={styles.subtext}>Telefone: {paciente.telefone || 'Não informado'}</Text>
            <Text style={styles.subtext}>Diagnóstico: {paciente.diagnostico || 'Não informado'}</Text>
            <Text style={styles.subtext}>Local da lesão: {paciente.local_lesao || 'Não informado'}</Text>
            <Text style={styles.subtext}>Evolução: {paciente.status_evolucao || 'Ainda não avaliada'}</Text>
          </View>

          <TouchableOpacity
            accessibilityRole="button"
            style={styles.btnNovaAvaliacao}
            activeOpacity={0.8}
            onPress={() => router.push(`/avaliacao/nova?pacienteId=${id}`)}
          >
            <Text style={styles.btnNovaAvaliacaoTexto}>+ Realizar Nova Avaliação</Text>
          </TouchableOpacity>

          <TouchableOpacity
            accessibilityRole="button"
            style={styles.cardTutorial}
            activeOpacity={0.8}
            onPress={() => router.push('/explore')}
          >
            <Text style={styles.tituloTutorial}>Como realizar uma avaliação</Text>
            <Text style={styles.textoAvaliacao}>
              Orientações sobre o preenchimento, a fotografia e a revisão dos resultados.
            </Text>
          </TouchableOpacity>

          <Text accessibilityRole="header" style={styles.sectionTitle}>
            Histórico de Avaliações
          </Text>

          {carregandoHistorico ? (
            <Text accessibilityLiveRegion="polite" style={styles.vazio}>Carregando avaliações…</Text>
          ) : null}
          {erroHistorico ? <Text style={styles.erro}>{erroHistorico}</Text> : null}

          {historicoPaciente.length > 0 ? (
            <View style={styles.campoBusca}>
              <TextInput
                accessibilityLabel="Pesquisar avaliações"
                style={styles.busca}
                placeholder="Buscar por nº, data, queixa ou situação"
                placeholderTextColor="#64748b"
                autoCorrect={false}
                value={busca}
                onChangeText={alterarBusca}
              />
              {busca ? (
                <TouchableOpacity
                  accessibilityRole="button"
                  accessibilityLabel="Limpar pesquisa"
                  style={styles.limparBusca}
                  onPress={() => alterarBusca('')}
                >
                  <Text style={styles.acao}>Limpar</Text>
                </TouchableOpacity>
              ) : null}
            </View>
          ) : null}

          {!carregandoHistorico && !erroHistorico && avaliacoesFiltradas.length === 0 ? (
            <Text style={styles.vazio}>
              {historicoPaciente.length
                ? 'Nenhuma avaliação encontrada para essa pesquisa.'
                : 'Nenhuma avaliação registrada para este paciente.'}
            </Text>
          ) : null}

          {avaliacoesDaPagina.map(analise => {
            const situacao = situacaoAvaliacao(analise.status);
            const previa = previas[analise.id_analise];
            const tecido = previa?.tecido_predominante;
            const resumo = previa?.revisao_resumo;

            return (
              <TouchableOpacity
                key={analise.id_analise}
                accessibilityRole="button"
                style={styles.cardAvaliacao}
                activeOpacity={0.8}
                onPress={() => router.push({
                  pathname: '/avaliacao/[id]',
                  params: { id: String(analise.id_analise), pacienteId: id },
                })}
              >
                <View style={styles.previaAvaliacao}>
                  {previa?.imagem_url ? (
                    <FotoPrevia key={previa.imagem_url} url={previa.imagem_url} />
                  ) : null}
                  <View style={styles.dadosAvaliacao}>
                <View style={styles.linhaAvaliacao}>
                  <View style={styles.identificacaoAvaliacao}>
                    <Text style={styles.dataAvaliacao}>Avaliação #{analise.id_analise}</Text>
                    <Text style={styles.textoAvaliacao}>{formatarData(analise.data_analise)}</Text>
                  </View>
                  <Text style={[styles.statusAvaliacao, situacao.concluida && styles.statusConcluida]}>
                    {situacao.texto}
                  </Text>
                </View>
                <Text style={styles.queixa} numberOfLines={2}>
                  Queixa: {analise.queixa_principal || 'Não informada'}
                </Text>
                {resumo ? (
                  <View style={styles.resumoTecidos}>
                    <Text style={styles.resumoTitulo}>
                      Revisão profissional aprovada
                      {resumo.provedor_base
                        ? ' — ' + resumo.provedor_base.toUpperCase()
                        : ''}
                    </Text>
                    <Text style={styles.tecido}>
                      Granulação: {resumo.percentuais.granulacao.toLocaleString('pt-BR')}%
                      {' · '}Esfacelo: {resumo.percentuais.esfacelo.toLocaleString('pt-BR')}%
                    </Text>
                    <Text style={styles.tecido}>
                      Necrose: {resumo.percentuais.necrose.toLocaleString('pt-BR')}%
                      {' · '}Não classificado: {resumo.percentuais.nao_classificado.toLocaleString('pt-BR')}%
                    </Text>
                    {tecido ? (
                      <Text style={styles.resumoTitulo}>
                        Tecido predominante: {nomesTecidos[tecido.classe]}
                      </Text>
                    ) : (
                      <Text style={styles.resumoObservacao}>
                        Nenhum tecido classificado predomina sobre a área não classificada.
                      </Text>
                    )}
                  </View>
                ) : null}
                <Text style={styles.acao}>Abrir relatórios</Text>
                  </View>
                </View>
              </TouchableOpacity>
            );
          })}

          {totalPaginas > 1 ? (
            <View style={styles.paginacao}>
              <TouchableOpacity
                accessibilityRole="button"
                disabled={paginaAtual === 0}
                style={[styles.botaoPagina, paginaAtual === 0 && styles.botaoInativo]}
                onPress={() => setPagina(paginaAtual - 1)}
              >
                <Text style={styles.acao}>Anterior</Text>
              </TouchableOpacity>
              <Text style={styles.textoAvaliacao}>{paginaAtual + 1} de {totalPaginas}</Text>
              <TouchableOpacity
                accessibilityRole="button"
                disabled={paginaAtual + 1 >= totalPaginas}
                style={[styles.botaoPagina, paginaAtual + 1 >= totalPaginas && styles.botaoInativo]}
                onPress={() => setPagina(paginaAtual + 1)}
              >
                <Text style={styles.acao}>Próxima</Text>
              </TouchableOpacity>
            </View>
          ) : null}
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#f8fafc', flexGrow: 1 },
  cardHeader: { backgroundColor: '#0056b3', padding: 16, borderRadius: 8, marginBottom: 16 },
  nome: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  subtext: { fontSize: 13, color: '#e2e8f0', marginTop: 2 },
  btnNovaAvaliacao: {
    backgroundColor: '#0056b3',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  btnNovaAvaliacaoTexto: { color: '#fff', fontWeight: 'bold', fontSize: 15 },
  cardTutorial: {
    backgroundColor: '#eff6ff',
    borderWidth: 1,
    borderColor: '#bfdbfe',
    borderRadius: 8,
    padding: 14,
    marginBottom: 24,
  },
  tituloTutorial: { fontSize: 14, fontWeight: 'bold', color: '#0056b3', marginBottom: 4 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#1e293b', marginBottom: 12 },
  cardAvaliacao: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 8,
    padding: 14,
    marginBottom: 16,
  },
  dataAvaliacao: { fontSize: 14, fontWeight: 'bold', color: '#0056b3', marginBottom: 4 },
  textoAvaliacao: { fontSize: 13, color: '#475569' },
  previaAvaliacao: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  dadosAvaliacao: { flex: 1, minWidth: 0 },
  miniatura: { width: 68, height: 68, borderRadius: 8, backgroundColor: '#eef2f6' },
  resumoTecidos: {
    backgroundColor: '#f1f5f9',
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  resumoTitulo: {
    color: '#0056b3',
    fontWeight: '700',
    fontSize: 13,
    marginBottom: 5,
  },
  resumoObservacao: {
    color: '#64748b',
    fontSize: 12,
    marginTop: 3,
  },
  tecido: { color: '#334155', fontSize: 13, marginBottom: 8 },
  paginacao: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  botaoPagina: { minHeight: 44, paddingHorizontal: 10, justifyContent: 'center' },
  botaoInativo: { opacity: 0.45 },
  campoBusca: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    backgroundColor: '#fff',
    borderRadius: 8,
    marginBottom: 16,
  },
  busca: { flex: 1, minHeight: 46, paddingHorizontal: 12, color: '#1e293b', fontSize: 14 },
  limparBusca: { minHeight: 46, paddingHorizontal: 12, justifyContent: 'center' },
  linhaAvaliacao: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 10 },
  identificacaoAvaliacao: { flexGrow: 1 },
  statusAvaliacao: {
    color: '#475569',
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    fontSize: 12,
    fontWeight: '600',
  },
  statusConcluida: { color: '#166534', backgroundColor: '#dcfce7' },
  queixa: { color: '#475569', fontSize: 13, marginTop: 10, marginBottom: 12, lineHeight: 18 },
  acao: { color: '#005088', fontSize: 13, fontWeight: '700' },
  erro: { color: '#b91c1c', marginBottom: 12 },
  vazio: { color: '#64748b', marginBottom: 16 },
});

