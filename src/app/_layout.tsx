import { Stack } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import RodapeNavegacao from '../components/rodape-navegacao';

export default function Layout() {
  return (
    <SafeAreaProvider style={styles.tela}>
      <View style={styles.tela}>
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: '#0056b3' },
            headerTintColor: '#fff',
            headerTitleStyle: { fontWeight: 'bold' },
          }}
        >
          <Stack.Screen name="index" options={{ title: 'Início', headerShown: false }} />
          <Stack.Screen name="home" options={{ title: 'Painel Principal' }} />
          <Stack.Screen name="pacientes" options={{ title: 'Pacientes Cadastrados' }} />
          <Stack.Screen name="paciente/novo" options={{ title: 'Novo Paciente' }} />
          <Stack.Screen name="paciente/[id]" options={{ title: 'Prontuário do Paciente' }} />
          <Stack.Screen name="avaliacao/nova" options={{ title: 'Nova Avaliação' }} />
          <Stack.Screen name="avaliacao/[id]" options={{ title: 'Relatórios da Avaliação' }} />
          <Stack.Screen name="perfil" options={{ title: 'Meu Perfil' }} />
          <Stack.Screen name="explore" options={{ title: 'Orientações de Uso' }} />
        </Stack>
      </View>
      <RodapeNavegacao />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  tela: { flex: 1 },
});
