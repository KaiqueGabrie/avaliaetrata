import { useRouter } from 'expo-router';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function WelcomeScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Avalia & Trata</Text>

        <Text style={styles.subtitle}>
          Sistema inteligente de triagem, registro clínico e análise de lesões corporais.
        </Text>

        <TouchableOpacity
          style={styles.button}
          activeOpacity={0.8}
          onPress={() => router.replace('/home')}
        >
          <Text style={styles.buttonText}>Acessar o Sistema</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0056b3', justifyContent: 'center', padding: 24 },
  content: { alignItems: 'center', backgroundColor: '#ffffff', padding: 28, borderRadius: 12, elevation: 4 },
  title: { fontSize: 28, fontWeight: 'bold', color: '#0056b3', marginBottom: 12 },
  subtitle: { fontSize: 15, color: '#555', textAlign: 'center', marginBottom: 24, lineHeight: 22 },
  button: { backgroundColor: '#0056b3', paddingVertical: 14, paddingHorizontal: 32, borderRadius: 8, width: '100%', alignItems: 'center' },
  buttonText: { color: '#ffffff', fontSize: 16, fontWeight: 'bold' },
});