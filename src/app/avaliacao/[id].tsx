import { useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import BotaoRelatorioPdf from '../../components/botao-relatorio-pdf';
import ComparacaoConfiancaIA from '../../components/comparacao-confianca-ia';
import EditorMarcacoes from '../../components/editor-marcacoes';
import type { ImagensAvaliacao } from '../../components/fotografias-avaliacao';
import FotografiasAvaliacao from '../../components/fotografias-avaliacao';
import RelatorioCompleto from '../../components/relatorio-completo';
import { apiJson } from '../../config/cliente';
import type { RespostaEstruturadaIA } from '../../types/ia';
import { Aviso } from '../../utils/avisos';

type Relatorio = {
  id_relatorio: string;
  provedor: string;
  status: string;
  conteudo_editavel: RespostaEstruturadaIA;
  conteudo_original?: RespostaEstruturadaIA;
  alertas_validacao?: {
    codigo?: string;
    mensagem?: string;
    severidade?: string;
  }[];
  revisao_profissional_necessaria: boolean;
  data_aprovacao: string | null;
};

type Comparacao = {
  id_comparacao: string;
  criado_em: string | null;
  comparacao_multimodal: {
    componentes?: Record<
      string,
      {
        nome?: string;
        situacao_descritiva?: string;
        divergencia_status?: boolean;
        observacao_descritiva?: string;
      }
    >;
    observacao_metodologica?: string;
  };
};

type RespostaMarcacoes = {
  marcacoes_por_ia: ImagensAvaliacao['marcacoes_por_ia'];
};

export default function DetalheAvaliacaoScreen() {
  const { id, pacienteId, provedor } = useLocalSearchParams<{
    id: string;
    pacienteId?: string;
    provedor?: string;
  }>();

  const selecaoInicialAplicada = useRef('');
  const [relatorios, setRelatorios] = useState<Relatorio[]>([]);
  const [imagens, setImagens] = useState<ImagensAvaliacao | null>(null);
  const [comparacoes, setComparacoes] = useState<Comparacao[]>([]);
  const [selecionado, setSelecionado] = useState('');
  const [descricao, setDescricao] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [gerandoMarcacoes, setGerandoMarcacoes] = useState(false);
  const [reprocessandoOpenAI, setReprocessandoOpenAI] = useState(false);
  const [verOriginal, setVerOriginal] = useState(false);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async () => {
    if (!id || !/^\d+$/.test(id)) {
      setErro('Avaliação inválida.');
      setCarregando(false);
      return;
    }

    setCarregando(true);
    setErro('');

    try {
      const [respostaRelatorios, respostaComparacoes, fotos, marcacoes] =
        await Promise.all([
          apiJson<{ relatorios: Relatorio[] }>(`/analises/${id}/relatorios`),
          apiJson<{ comparacoes: { id_comparacao: string }[] }>(
            `/analises/${id}/comparacoes`,
          ),
          pacienteId
            ? apiJson<ImagensAvaliacao>(
                `/pacientes/${pacienteId}/analises/${id}/imagens`,
              ).catch(() => null)
            : Promise.resolve(null),
          pacienteId
            ? apiJson<RespostaMarcacoes>(
                `/pacientes/${pacienteId}/analises/${id}/marcacoes`,
              ).catch(() => null)
            : Promise.resolve(null),
        ]);

      setImagens(fotos ? { ...fotos, ...(marcacoes || {}) } : null);

      const relatoriosRecebidos = respostaRelatorios.relatorios || [];
      setRelatorios(relatoriosRecebidos);

      const chaveSelecao = `${id}:${provedor || ''}`;

      if (provedor && selecaoInicialAplicada.current !== chaveSelecao) {
        const inicial = relatoriosRecebidos.find(item => item.provedor === provedor);

        if (inicial) {
          selecaoInicialAplicada.current = chaveSelecao;
          setSelecionado(inicial.provedor);
          setVerOriginal(false);
          setDescricao(inicial.conteudo_editavel?.conteudo_descricao || '');
        }
      }

      const primeiraComparacao = respostaComparacoes.comparacoes?.[0];

      if (primeiraComparacao) {
        const detalhes = await apiJson<Comparacao>(
          `/analises/${id}/comparacoes/${primeiraComparacao.id_comparacao}`,
        );
        setComparacoes([detalhes]);
      } else {
        setComparacoes([]);
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha ao carregar relatórios.');
    } finally {
      setCarregando(false);
    }
  }, [id, pacienteId, provedor]);

  useFocusEffect(
    useCallback(() => {
      void carregar();
    }, [carregar]),
  );

  const atualizarFotografias = async () => {
    if (!pacienteId || !id) return;

    try {
      const [fotos, marcacoes] = await Promise.all([
        apiJson<ImagensAvaliacao>(
          `/pacientes/${pacienteId}/analises/${id}/imagens`,
        ),
        apiJson<RespostaMarcacoes>(
          `/pacientes/${pacienteId}/analises/${id}/marcacoes`,
        ).catch(() => null),
      ]);

      setImagens({ ...fotos, ...(marcacoes || {}) });
    } catch (e) {
      Aviso.alert(
        'Fotografias',
        e instanceof Error ? e.message : 'Não foi possível atualizar as imagens.',
      );
    }
  };

  const gerarMarcacoes = async () => {
    if (!pacienteId || !id) return;

    setGerandoMarcacoes(true);

    try {
      const dados = await apiJson<RespostaMarcacoes>(
        `/pacientes/${pacienteId}/analises/${id}/marcacoes/gerar`,
        { method: 'POST' },
      );

      setImagens(anterior => anterior ? { ...anterior, ...dados } : anterior);
    } catch (e) {
      Aviso.alert(
        'Marcações',
        e instanceof Error ? e.message : 'Não foi possível gerar as imagens.',
      );
    } finally {
      setGerandoMarcacoes(false);
    }
  };

  const reprocessarOpenAI = async () => {
    if (!pacienteId || !id) return;

    setReprocessandoOpenAI(true);

    try {
      const resposta = await apiJson<{
        total_regioes: number;
        mensagem: string;
      }>(
        `/pacientes/${pacienteId}/analises/${id}/marcacoes/openai/reprocessar`,
        { method: 'POST' },
      );

      if (resposta.total_regioes > 0) {
        const imagensMarcadas = await apiJson<RespostaMarcacoes>(
          `/pacientes/${pacienteId}/analises/${id}/marcacoes/gerar`,
          { method: 'POST' },
        );

        setImagens(anterior =>
          anterior ? { ...anterior, ...imagensMarcadas } : anterior,
        );

        await atualizarFotografias();

        Aviso.alert(
          'OpenAI — proposta complementar',
          `${resposta.total_regioes} região(ões) proposta(s). Confira os contornos e reabra o relatório para importá-los no editor. O T.I.M.E.S. original foi preservado.`,
        );
      } else {
        await atualizarFotografias();
        Aviso.alert('Sem coordenadas', resposta.mensagem);
      }
    } catch (e) {
      Aviso.alert(
        'OpenAI',
        e instanceof Error ? e.message : 'Falha ao tentar obter contornos.',
      );
    } finally {
      setReprocessandoOpenAI(false);
    }
  };

  const selecionar = (relatorio: Relatorio) => {
    setSelecionado(relatorio.provedor);
    setVerOriginal(false);
    setDescricao(relatorio.conteudo_editavel?.conteudo_descricao || '');
  };

  const relatorioAtual = relatorios.find(relatorio => relatorio.provedor === selecionado);

  const salvar = async () => {
    if (!relatorioAtual || !descricao.trim() || relatorioAtual.status === 'aprovado') {
      return;
    }

    setSalvando(true);

    try {
      await apiJson(`/analises/${id}/relatorios/${selecionado}`, {
        method: 'PATCH',
        body: JSON.stringify({
          campo: 'conteudo_descricao',
          novo_valor: descricao.trim(),
        }),
      });

      await carregar();
      Aviso.alert('Salvo', 'Revisão salva com sucesso.');
    } catch (e) {
      Aviso.alert('Erro', e instanceof Error ? e.message : 'Falha ao salvar.');
    } finally {
      setSalvando(false);
    }
  };

  const aprovar = () => {
    if (!relatorioAtual || relatorioAtual.status === 'aprovado') return;

    Aviso.alert(
      'Confirmar aprovação',
      'Você revisou o relatório e deseja aprová-lo como profissional responsável?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Aprovar',
          onPress: async () => {
            setSalvando(true);

            try {
              await apiJson(`/analises/${id}/relatorios/${selecionado}/aprovar`, {
                method: 'POST',
              });

              await carregar();
              Aviso.alert('Aprovado', 'Relatório aprovado com sucesso.');
            } catch (e) {
              Aviso.alert('Erro', e instanceof Error ? e.message : 'Falha ao aprovar.');
            } finally {
              setSalvando(false);
            }
          },
        },
      ],
    );
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.titulo}>Avaliação #{id}</Text>

      {pacienteId ? (
        <Text style={styles.menor}>Prontuário nº {pacienteId}</Text>
      ) : null}

      {carregando ? <ActivityIndicator color="#0056b3" size="large" /> : null}
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}

      {!carregando && relatorios.length > 0 ? (
        <ComparacaoConfiancaIA relatorios={relatorios} />
      ) : null}

      {imagens ? (
        <FotografiasAvaliacao
          alertasContornos={Object.fromEntries(
            relatorios.map(relatorio => [
              relatorio.provedor.toLowerCase(),
              (
                (relatorio.conteudo_original ?? relatorio.conteudo_editavel)
                  ?.marcacoes_imagem?.limitacoes ?? []
              ).filter(aviso => aviso.startsWith('[AUDITORIA_CONTORNO]')),
            ]),
          )}
          imagens={imagens}
          onAtualizar={atualizarFotografias}
          onGerar={gerarMarcacoes}
          gerando={gerandoMarcacoes}
          onReprocessarOpenAI={reprocessarOpenAI}
          reprocessandoOpenAI={reprocessandoOpenAI}
        />
      ) : null}

      {pacienteId && id ? (
        <EditorMarcacoes pacienteId={pacienteId} analiseId={id} />
      ) : null}

      <Text style={styles.secao}>Relatórios das IAs</Text>

      {!carregando && !relatorios.length ? (
        <Text style={styles.menor}>Nenhum relatório salvo nesta avaliação.</Text>
      ) : null}

      {relatorios.map(relatorio => (
        <TouchableOpacity
          key={relatorio.provedor}
          style={[styles.card, selecionado === relatorio.provedor && styles.ativo]}
          onPress={() => selecionar(relatorio)}
        >
          <Text style={styles.subtitulo}>{relatorio.provedor.toUpperCase()}</Text>
          <Text style={styles.menor}>
            {relatorio.status === 'aprovado'
              ? 'Aprovado'
              : relatorio.status === 'em_edicao'
                ? 'Em edição'
                : 'Aguardando revisão profissional'}
          </Text>
          <Text style={styles.menor}>Toque para visualizar e revisar</Text>
        </TouchableOpacity>
      ))}

      {relatorioAtual ? (
        <View style={styles.card}>
          <Text style={styles.subtitulo}>
            Descrição — {relatorioAtual.provedor.toUpperCase()}
          </Text>

          <TextInput
            style={styles.input}
            multiline
            textAlignVertical="top"
            value={descricao}
            onChangeText={setDescricao}
            editable={relatorioAtual.status !== 'aprovado' && !salvando}
          />

          <RelatorioCompleto
            resposta={relatorioAtual.conteudo_editavel}
            mostrarDescricao={false}
          />

          {relatorioAtual.alertas_validacao?.length ? (
            <View style={styles.item}>
              <Text style={styles.subtitulo}>Alertas de validação técnica</Text>

              {relatorioAtual.alertas_validacao.map((alerta, indice) => (
                <Text key={indice} style={styles.menor}>
                  • {alerta.codigo || 'Alerta'} ({alerta.severidade || 'revisão'}):{' '}
                  {alerta.mensagem || 'Sem descrição'}
                </Text>
              ))}
            </View>
          ) : null}

          {relatorioAtual.conteudo_original ? (
            <>
              <TouchableOpacity
                style={styles.item}
                onPress={() => setVerOriginal(anterior => !anterior)}
                accessibilityRole="button"
              >
                <Text style={styles.subtitulo}>
                  {verOriginal ? '▾ Ocultar' : '▸ Consultar'} relatório original da IA
                </Text>
              </TouchableOpacity>

              {verOriginal ? (
                <RelatorioCompleto resposta={relatorioAtual.conteudo_original} />
              ) : null}
            </>
          ) : null}

          {relatorioAtual.status === 'aprovado' ? (
            <>
              <Text style={styles.aprovado}>Relatório aprovado. Edição bloqueada.</Text>

              {id && pacienteId ? (
                <BotaoRelatorioPdf
                  analiseId={id}
                  pacienteId={pacienteId}
                  provedor={relatorioAtual.provedor}
                  aprovadoEm={relatorioAtual.data_aprovacao}
                  relatorio={relatorioAtual.conteudo_editavel}
                />
              ) : null}
            </>
          ) : (
            <>
              <TouchableOpacity style={styles.botao} onPress={salvar} disabled={salvando}>
                <Text style={styles.botaoTexto}>Salvar revisão</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.botao} onPress={aprovar} disabled={salvando}>
                <Text style={styles.botaoTexto}>Aprovar relatório</Text>
              </TouchableOpacity>
            </>
          )}

          <Text style={styles.menor}>
            O profissional é responsável pela aprovação. O texto da IA pode conter erros.
          </Text>
        </View>
      ) : null}

      <Text style={styles.secao}>Comparação T.I.M.E.S.</Text>

      {!carregando && !comparacoes.length ? (
        <Text style={styles.menor}>Nenhuma comparação disponível nesta avaliação.</Text>
      ) : null}

      {comparacoes.map(comparacao => (
        <View key={comparacao.id_comparacao} style={styles.card}>
          {Object.entries(comparacao.comparacao_multimodal?.componentes || {}).map(
            ([letra, item]) => (
              <View key={letra} style={styles.item}>
                <Text style={styles.subtitulo}>{letra} — {item.nome || ''}</Text>
                <Text style={styles.menor}>
                  Situação descritiva: {item.situacao_descritiva || 'Inconclusiva'}
                </Text>
                <Text style={styles.menor}>
                  Diferença no estado de avaliação: {item.divergencia_status ? 'Sim' : 'Não'}
                </Text>
                <Text style={styles.menor}>{item.observacao_descritiva || ''}</Text>
              </View>
            ),
          )}

          <Text style={styles.menor}>
            {comparacao.comparacao_multimodal?.observacao_metodologica || ''}
          </Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 18,
    paddingBottom: 60,
    backgroundColor: '#f8fafc',
    flexGrow: 1,
  },
  titulo: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 8,
  },
  secao: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#0056b3',
    marginTop: 18,
    marginBottom: 10,
  },
  subtitulo: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 5,
  },
  menor: {
    fontSize: 13,
    color: '#475569',
    lineHeight: 19,
    marginBottom: 5,
  },
  card: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
  },
  ativo: {
    borderColor: '#0056b3',
    backgroundColor: '#eff6ff',
  },
  item: {
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    paddingBottom: 8,
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    backgroundColor: '#fff',
    borderRadius: 8,
    minHeight: 150,
    padding: 12,
    marginBottom: 10,
  },
  botao: {
    backgroundColor: '#0056b3',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 10,
  },
  botaoTexto: {
    color: '#fff',
    fontWeight: 'bold',
  },
  erro: {
    color: '#b91c1c',
    marginBottom: 10,
  },
  aprovado: {
    color: '#15803d',
    fontWeight: 'bold',
    marginBottom: 10,
  },
});