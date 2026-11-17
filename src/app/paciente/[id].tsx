import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { apiJson } from '../../config/cliente';
import type { AnaliseResumo, Paciente } from '../../types/paciente';
import { formatarData } from '../../types/paciente';

export default function ProntuarioPacienteScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [paciente, setPaciente] = useState<Paciente | null>(null);
  const [analises, setAnalises] = useState<AnaliseResumo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async () => {
    if (!id || !/^\d+$/.test(id)) {
      setErro('Paciente inválido.');
      setCarregando(false);
      return;
    }

    setCarregando(true);
    setErro('');

    try {
      const [dadosPaciente, dadosAnalises] = await Promise.all([
        apiJson<Paciente>(`/pacientes/${id}`),
        apiJson<AnaliseResumo[]>(`/pacientes/${id}/analises`),
      ]);

      setPaciente(dadosPaciente);
      setAnalises(dadosAnalises);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível carregar o prontuário.');
    } finally {
      setCarregando(false);
    }
  }, [id]);

  useFocusEffect(useCallback(() => {
    void carregar();
  }, [carregar]));

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {carregando ? <ActivityIndicator size="large" color="#0056b3" /> : null}
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}

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

          <Text style={styles.sectionTitle}>Histórico de Avaliações</Text>
          {!carregando && !erro && !analises.length ? (
            <Text style={styles.vazio}>Nenhuma avaliação registrada para este paciente.</Text>
          ) : null}

          {analises.map((analise) => (
            <TouchableOpacity
              key={analise.id_analise}
              accessibilityRole="button"
              style={styles.cardAvaliacao}
              onPress={() => router.push(`/avaliacao/${analise.id_analise}?pacienteId=${id}`)}
            >
              <Text style={styles.dataAvaliacao}>
                Avaliação #{analise.id_analise} — {formatarData(analise.data_analise)}
              </Text>
              <Text style={styles.textoAvaliacao}>
                Queixa: {analise.queixa_principal || 'Não informada'}
              </Text>
              <Text style={styles.statusAvaliacao}>
                Situação: {analise.status === 'pendente'
                  ? 'Aguardando análise'
                  : analise.status === 'concluida' || analise.status === 'concluído'
                    ? 'Concluída'
                    : analise.status}
              </Text>
              <Text style={styles.textoAvaliacao}>Toque para consultar os relatórios</Text>
            </TouchableOpacity>
          ))}
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
  statusAvaliacao: { fontSize: 13, fontWeight: '600', color: '#16a34a', marginTop: 6 },
  erro: { color: '#b91c1c', marginBottom: 12 },
  vazio: { color: '#64748b', marginBottom: 16 },
});