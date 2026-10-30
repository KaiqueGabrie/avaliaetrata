import { ScrollView, StyleSheet, Text } from 'react-native';

export default function ExploreScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Orientações de uso</Text>
      <Text style={styles.text}>
        Cadastre o paciente, abra seu prontuário e inicie uma nova avaliação. Registre as observações clínicas e uma fotografia adequada. Confira os resultados apresentados, corrija o que for necessário e aprove o relatório somente após sua revisão profissional. As análises automatizadas são auxiliares e não substituem o julgamento clínico.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#fff', flexGrow: 1 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#0056b3', marginBottom: 12 },
  text: { fontSize: 14, color: '#555', lineHeight: 20 },
});