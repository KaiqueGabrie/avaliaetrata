import { ScrollView, StyleSheet, Text } from 'react-native';

export default function ExploreScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Explorar Recursos do Sistema</Text>
      <Text style={styles.text}>
        Esta tela é destinada para configurações adicionais, testes de módulo de inteligência artificial e visualização de parâmetros técnicos do aplicativo.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#fff', flexGrow: 1 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#0056b3', marginBottom: 12 },
  text: { fontSize: 14, color: '#555', lineHeight: 20 },
});