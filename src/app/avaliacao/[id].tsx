import { useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator, Alert, ScrollView, StyleSheet, Text,
  TextInput, TouchableOpacity, View,
} from 'react-native';
import { apiJson } from '../../config/cliente';

type Relatorio = {
  id_relatorio: string;
  provedor: string;
  status: string;
  conteudo_editavel: {
    conteudo_descricao?: string;
    avaliacao_times?: { componente: string; nome: string; status: string; observacoes_visuais?: string[] }[];
    medidas?: { comprimento_informado_cm?: string | null; largura_informada_cm?: string | null; area_calculada_cm2?: number | null };
  };
  revisao_profissional_necessaria: boolean;
  data_aprovacao: string | null;
};
type Comparacao = {
  id_comparacao: string;
  criado_em: string | null;
  comparacao_multimodal: {
    componentes?: Record<string, {
      nome?: string; situacao_descritiva?: string;
      divergencia_status?: boolean; observacao_descritiva?: string;
    }>;
    observacao_metodologica?: string;
  };
};

export default function DetalheAvaliacaoScreen() {
  const { id, pacienteId } = useLocalSearchParams<{ id: string; pacienteId?: string }>();
  const [relatorios, setRelatorios] = useState<Relatorio[]>([]);
  const [comparacoes, setComparacoes] = useState<Comparacao[]>([]);
  const [selecionado, setSelecionado] = useState('');
  const [descricao, setDescricao] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async () => {
    if (!id || !/^\d+$/.test(id)) { setErro('Avaliação inválida.'); setCarregando(false); return; }
    setCarregando(true); setErro('');
    try {
      const [r, c] = await Promise.all([
        apiJson<{ relatorios: Relatorio[] }>(`/analises/${id}/relatorios`),
        apiJson<{ comparacoes: { id_comparacao: string }[] }>(`/analises/${id}/comparacoes`),
      ]);
      setRelatorios(r.relatorios || []);
      if (c.comparacoes?.length) {
        const detalhes = await apiJson<Comparacao>(`/analises/${id}/comparacoes/${c.comparacoes[0].id_comparacao}`);
        setComparacoes([detalhes]);
      } else setComparacoes([]);
    } catch (e) { setErro(e instanceof Error ? e.message : 'Falha ao carregar relatórios.'); }
    finally { setCarregando(false); }
  }, [id]);
  useFocusEffect(useCallback(() => { void carregar(); }, [carregar]));

  const selecionar = (r: Relatorio) => {
    setSelecionado(r.provedor);
    setDescricao(r.conteudo_editavel?.conteudo_descricao || '');
  };
  const relatorioAtual = relatorios.find((r) => r.provedor === selecionado);

  const salvar = async () => {
    if (!relatorioAtual || !descricao.trim() || relatorioAtual.status === 'aprovado') return;
    setSalvando(true);
    try {
      await apiJson(`/analises/${id}/relatorios/${selecionado}`, {
        method: 'PATCH', body: JSON.stringify({ campo: 'conteudo_descricao', novo_valor: descricao.trim() }),
      });
      await carregar();
      Alert.alert('Salvo', 'Revisão salva com sucesso.');
    } catch (e) { Alert.alert('Erro', e instanceof Error ? e.message : 'Falha ao salvar.'); }
    finally { setSalvando(false); }
  };

  const aprovar = () => {
    if (!relatorioAtual || relatorioAtual.status === 'aprovado') return;
    Alert.alert('Confirmar aprovação', 'Você revisou o relatório e deseja aprová-lo como profissional responsável?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Aprovar', onPress: async () => {
        setSalvando(true);
        try {
          await apiJson(`/analises/${id}/relatorios/${selecionado}/aprovar`, { method: 'POST' });
          await carregar();
          Alert.alert('Aprovado', 'Relatório aprovado com sucesso.');
        } catch (e) { Alert.alert('Erro', e instanceof Error ? e.message : 'Falha ao aprovar.'); }
        finally { setSalvando(false); }
      } },
    ]);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.titulo}>Avaliação #{id}</Text>
      {pacienteId ? <Text style={styles.menor}>Prontuário nº {pacienteId}</Text> : null}
      {carregando ? <ActivityIndicator color="#0056b3" size="large" /> : null}
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      <Text style={styles.secao}>Relatórios das IAs</Text>
      {!carregando && !relatorios.length ? <Text style={styles.menor}>Nenhum relatório salvo nesta avaliação.</Text> : null}
      {relatorios.map((r) => (
        <TouchableOpacity key={r.provedor} style={[styles.card, selecionado === r.provedor && styles.ativo]} onPress={() => selecionar(r)}>
          <Text style={styles.subtitulo}>{r.provedor.toUpperCase()}</Text>
          <Text style={styles.menor}>{r.status === 'aprovado' ? 'Aprovado' : r.status === 'revisado' ? 'Revisado' : 'Aguardando revisão profissional'}</Text>
          <Text style={styles.menor}>Toque para visualizar e revisar</Text>
        </TouchableOpacity>
      ))}
      {relatorioAtual ? (
        <View style={styles.card}>
          <Text style={styles.subtitulo}>Descrição — {relatorioAtual.provedor.toUpperCase()}</Text>
          <TextInput
            style={styles.input}
            multiline
            textAlignVertical="top"
            value={descricao}
            onChangeText={setDescricao}
            editable={relatorioAtual.status !== 'aprovado' && !salvando}
          />
          <Text style={styles.subtitulo}>Avaliação T.I.M.E.S.</Text>
          {(relatorioAtual.conteudo_editavel?.avaliacao_times || []).map((t, i) => (
            <View key={`${t.componente}-${i}`} style={styles.item}>
              <Text style={styles.subtitulo}>{t.componente} — {t.nome}</Text>
              <Text style={styles.menor}>Estado: {t.status}</Text>
              {(t.observacoes_visuais || []).map((obs, j) => (
                <Text key={j} style={styles.menor}>• {obs}</Text>
              ))}
            </View>
          ))}
          {relatorioAtual.conteudo_editavel?.medidas ? (
            <View style={styles.item}>
              <Text style={styles.subtitulo}>Medidas informadas</Text>
              <Text style={styles.menor}>Comprimento: {relatorioAtual.conteudo_editavel.medidas.comprimento_informado_cm || '—'} cm</Text>
              <Text style={styles.menor}>Largura: {relatorioAtual.conteudo_editavel.medidas.largura_informada_cm || '—'} cm</Text>
              <Text style={styles.menor}>Área calculada: {relatorioAtual.conteudo_editavel.medidas.area_calculada_cm2 ?? 'Não calculada'} cm²</Text>
            </View>
          ) : null}
          {relatorioAtual.status === 'aprovado' ? (
            <Text style={styles.aprovado}>Relatório aprovado. Edição bloqueada.</Text>
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
          <Text style={styles.menor}>Aprovação é decisão do profissional; o texto da IA pode conter erros.</Text>
        </View>
      ) : null}
      <Text style={styles.secao}>Comparação T.I.M.E.S.</Text>
      {!carregando && !comparacoes.length ? <Text style={styles.menor}>Nenhuma comparação disponível nesta avaliação.</Text> : null}
      {comparacoes.map((c) => (
        <View key={c.id_comparacao} style={styles.card}>
          {Object.entries(c.comparacao_multimodal?.componentes || {}).map(([letra, item]) => (
            <View key={letra} style={styles.item}>
              <Text style={styles.subtitulo}>{letra} — {item.nome || ''}</Text>
              <Text style={styles.menor}>Situação descritiva: {item.situacao_descritiva || 'Inconclusiva'}</Text>
              <Text style={styles.menor}>Possibilidade de avaliação: {item.divergencia_status ? 'As análises apresentam diferenças' : 'Sem diferenças identificadas'}</Text>
              <Text style={styles.menor}>{item.observacao_descritiva || ''}</Text>
            </View>
          ))}
          <Text style={styles.menor}>{c.comparacao_multimodal?.observacao_metodologica || ''}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 18, paddingBottom: 60, backgroundColor: '#f8fafc', flexGrow: 1 },
  titulo: { fontSize: 20, fontWeight: 'bold', color: '#0056b3', marginBottom: 8 },
  secao: { fontSize: 17, fontWeight: 'bold', color: '#0056b3', marginTop: 18, marginBottom: 10 },
  subtitulo: { fontSize: 15, fontWeight: 'bold', color: '#0056b3', marginBottom: 5 },
  menor: { fontSize: 13, color: '#475569', lineHeight: 19, marginBottom: 5 },
  card: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 10, padding: 14, marginBottom: 12 },
  ativo: { borderColor: '#0056b3', backgroundColor: '#eff6ff' },
  item: { borderBottomWidth: 1, borderBottomColor: '#e2e8f0', paddingBottom: 8, marginBottom: 8 },
  input: { borderWidth: 1, borderColor: '#cbd5e1', backgroundColor: '#fff', borderRadius: 8, minHeight: 150, padding: 12, marginBottom: 10 },
  botao: { backgroundColor: '#0056b3', padding: 14, borderRadius: 8, alignItems: 'center', marginBottom: 10 },
  botaoTexto: { color: '#fff', fontWeight: 'bold' },
  erro: { color: '#b91c1c', marginBottom: 10 },
  aprovado: { color: '#15803d', fontWeight: 'bold', marginBottom: 10 },
});
