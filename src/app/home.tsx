import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function HomeScreen() {
  const router = useRouter();

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.welcomeTitle}>Bem-vindo ao Avalia & Trata</Text>
      <Text style={styles.subtitle}>Selecione uma das opções abaixo para navegar no aplicativo:</Text>

      <TouchableOpacity
        style={styles.card}
        activeOpacity={0.7}
        onPress={() => router.push('/pacientes')}
      >
        <Text style={styles.cardIcon}>👥</Text>
        <View style={styles.cardTextContainer}>
          <Text style={styles.cardTitle}>Lista de Pacientes</Text>
          <Text style={styles.cardDescription}>Visualizar, buscar e gerenciar o prontuário dos pacientes.</Text>
        </View>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.card}
        activeOpacity={0.7}
        onPress={() => router.push('/paciente/novo')}
      >
        <Text style={styles.cardIcon}>➕</Text>
        <View style={styles.cardTextContainer}>
          <Text style={styles.cardTitle}>Cadastrar Novo Paciente</Text>
          <Text style={styles.cardDescription}>Registrar novos dados cadastrais e histórico no sistema.</Text>
        </View>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.card}
        activeOpacity={0.7}
        onPress={() => router.push('/avaliacao/nova?pacienteId=1')}
      >
        <Text style={styles.cardIcon}>📋</Text>
        <View style={styles.cardTextContainer}>
          <Text style={styles.cardTitle}>Nova Avaliação Clínica</Text>
          <Text style={styles.cardDescription}>Capturar fotos de lesões e enviar dados para análise do backend.</Text>
        </View>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.card, { backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }]}
        activeOpacity={0.7}
        onPress={() => router.push('/explore')}
      >
        <Text style={styles.cardIcon}>⚙️</Text>
        <View style={styles.cardTextContainer}>
          <Text style={styles.cardTitle}>Explorar Recurso & Testes</Text>
          <Text style={styles.cardDescription}>Verificar testes adicionais e configurações do sistema.</Text>
        </View>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#f8fafc', flexGrow: 1 },
  welcomeTitle: { fontSize: 22, fontWeight: 'bold', color: '#0056b3', marginBottom: 6 },
  subtitle: { fontSize: 14, color: '#64748b', marginBottom: 20 },
  card: { flexDirection: 'row', backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 10, padding: 16, marginBottom: 14, alignItems: 'center', elevation: 2 },
  cardIcon: { fontSize: 32, marginRight: 16 },
  cardTextContainer: { flex: 1 },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#1e293b', marginBottom: 4 },
  cardDescription: { fontSize: 13, color: '#64748b' },
});