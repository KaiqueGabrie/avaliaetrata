
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import {
  SafeAreaProvider,
} from 'react-native-safe-area-context';

import RodapeNavegacao from '../components/rodape-navegacao';

export default function Layout() {
  return (
    <SafeAreaProvider style={styles.tela}>
      <StatusBar style="auto" />

      <View style={styles.tela}>
        <Stack
          screenOptions={{
            headerStyle: {
              backgroundColor: '#005088',
            },

            headerTintColor: '#ffffff',

            headerTitleStyle: {
              fontWeight: '700',
            },

            contentStyle: {
              backgroundColor: '#f5f7fa',
            },
          }}
        >
          <Stack.Screen
            name="index"
            options={{
              title: 'Avalia & Trata',
              headerShown: false,
            }}
          />

          <Stack.Screen
            name="home"
            options={{
              title: 'Painel Principal',
            }}
          />

          <Stack.Screen
            name="pacientes"
            options={{
              title: 'Pacientes Cadastrados',
            }}
          />

          <Stack.Screen
            name="paciente/novo"
            options={{
              title: 'Novo Paciente',
            }}
          />

          <Stack.Screen
            name="paciente/[id]"
            options={{
              title: 'Prontuário do Paciente',
            }}
          />

          <Stack.Screen
            name="avaliacao/nova"
            options={{
              title: 'Nova Avaliação',
            }}
          />

          <Stack.Screen
            name="avaliacao/[id]"
            options={{
              title: 'Relatórios da Avaliação',
            }}
          />

          <Stack.Screen
            name="perfil"
            options={{
              title: 'Meu Perfil',
            }}
          />

          <Stack.Screen
            name="explore"
            options={{
              title: 'Orientações de Uso',
            }}
          />
        </Stack>
      </View>

      <RodapeNavegacao />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  tela: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
});
