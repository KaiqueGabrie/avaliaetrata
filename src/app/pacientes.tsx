import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator, FlatList, RefreshControl, StyleSheet,
  Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { apiJson } from '../config/cliente';
import type { Paciente } from '../types/paciente';
import { formatarData } from '../types/paciente';

export default function PacientesScreen() {
  const router = useRouter();
  const [busca, setBusca] = useState('');
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      setPacientes(await apiJson<Paciente[]>('/pacientes'));
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha ao carregar pacientes.');
    } finally {
      setCarregando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void carregar(); }, [carregar]));

  const filtrados = pacientes.filter((p) =>
    p.nome_completo.toLowerCase().includes(busca.trim().toLowerCase()) ||
    (p.cpf || '').includes(busca.trim())
  );

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.inputBusca}
        placeholder="🔍 Buscar paciente por nome ou CPF..."
        value={busca}
        onChangeText={setBusca}
      />
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {carregando && pacientes.length === 0 ? <ActivityIndicator size="large" color="#0056b3" /> : null}
      <FlatList
        data={filtrados}
        keyExtractor={(item) => String(item.id_paciente)}
        refreshControl={<RefreshControl refreshing={carregando} onRefresh={carregar} />}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.cardPaciente}
            activeOpacity={0.7}
            onPress={() => router.push(`/paciente/${item.id_paciente}`)}
          >
            <View style={{ flex: 1 }}>
              <Text style={styles.nome}>{item.nome_completo}</Text>
              <Text style={styles.detalhe}>CPF: {item.cpf || 'Não informado'}</Text>
              <Text style={styles.detalhe}>Data de Nasc.: {formatarData(item.data_nascimento)}</Text>
            </View>
            <Text style={styles.seta}>➔</Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={!carregando && !erro ? (
          <Text style={styles.emptyText}>Nenhum paciente encontrado.</Text>
        ) : null}
      />
      <TouchableOpacity
        style={styles.btnNovoPaciente}
        activeOpacity={0.8}
        onPress={() => router.push('/paciente/novo')}
      >
        <Text style={styles.btnNovoPacienteTexto}>+ Cadastrar Paciente</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  inputBusca: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8, padding: 12, backgroundColor: '#fff', fontSize: 14, marginBottom: 16 },
  cardPaciente: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 8, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 10 },
  nome: { fontSize: 16, fontWeight: 'bold', color: '#0056b3', marginBottom: 4 },
  detalhe: { fontSize: 13, color: '#64748b' },
  seta: { fontSize: 18, color: '#0056b3', fontWeight: 'bold' },
  emptyText: { textAlign: 'center', color: '#94a3b8', marginTop: 24, fontSize: 14 },
  erro: { color: '#b91c1c', marginBottom: 12 },
  btnNovoPaciente: { backgroundColor: '#0056b3', paddingVertical: 14, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  btnNovoPacienteTexto: { color: '#fff', fontWeight: 'bold', fontSize: 15 },
});
