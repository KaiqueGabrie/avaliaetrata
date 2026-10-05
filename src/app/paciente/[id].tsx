import { useLocalSearchParams, useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function ProntuarioPacienteScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.cardHeader}>
        <Text style={styles.nome}>Maria Silva Santos</Text>
        <Text style={styles.subtext}>ID do Registro: {id}</Text>
        <Text style={styles.subtext}>CPF: 123.456.789-00</Text>
        <Text style={styles.subtext}>Data Nasc.: 15/04/1965</Text>
      </View>

      <Text style={styles.sectionTitle}>Histórico de Avaliações</Text>

      <View style={styles.cardAvaliacao}>
        <Text style={styles.dataAvaliacao}>Data: 28/09/2026</Text>
        <Text style={styles.textoAvaliacao}>Localização: Calcanhar esquerdo</Text>
        <Text style={styles.textoAvaliacao}>Dimensões: 4.5 cm x 3.0 cm</Text>
        <Text style={styles.statusAvaliacao}>Status: Em acompanhamento</Text>
      </View>

      <TouchableOpacity
        style={styles.btnNovaAvaliacao}
        activeOpacity={0.8}
        onPress={() => router.push(`/avaliacao/nova?pacienteId=${id}`)}
      >
        <Text style={styles.btnNovaAvaliacaoTexto}>+ Realizar Nova Avaliação</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#f8fafc', flexGrow: 1 },
  cardHeader: { backgroundColor: '#0056b3', padding: 16, borderRadius: 8, marginBottom: 20 },
  nome: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  subtext: { fontSize: 13, color: '#e2e8f0', marginTop: 2 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#1e293b', marginBottom: 12 },
  cardAvaliacao: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 8, padding: 14, marginBottom: 16 },
  dataAvaliacao: { fontSize: 14, fontWeight: 'bold', color: '#0056b3', marginBottom: 4 },
  textoAvaliacao: { fontSize: 13, color: '#475569' },
  statusAvaliacao: { fontSize: 13, fontWeight: '600', color: '#16a34a', marginTop: 6 },
  btnNovaAvaliacao: { backgroundColor: '#0056b3', paddingVertical: 14, borderRadius: 8, alignItems: 'center' },
  btnNovaAvaliacaoTexto: { color: '#fff', fontWeight: 'bold', fontSize: 15 },
});