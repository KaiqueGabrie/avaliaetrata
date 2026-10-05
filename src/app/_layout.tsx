import { Stack } from 'expo-router';

export default function Layout() {
  return (
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
      <Stack.Screen name="explore" options={{ title: 'Explorar Recursos' }} />
    </Stack>
  );
}