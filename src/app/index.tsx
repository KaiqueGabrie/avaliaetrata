
import { useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { API_URL } from '../config/api';

export default function WelcomeScreen() {
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [carregando, setCarregando] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !senha) {
      Alert.alert(
        'Campos obrigatórios',
        'Informe seu e-mail e sua senha.'
      );
      return;
    }

    setCarregando(true);

    try {
      const resposta = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          senha,
        }),
      });

      if (!resposta.ok) {
        if (resposta.status === 401 || resposta.status === 403) {
          Alert.alert('Erro no login', 'E-mail ou senha inválidos.');
        } else {
          Alert.alert(
            'Erro no login',
            'Não foi possível entrar no momento. Tente novamente.'
          );
        }
        return;
      }

      const dados = await resposta.json();

      if (!dados.access_token) {
        Alert.alert(
          'Erro',
          'Não foi possível concluir o acesso. Tente novamente.'
        );
        return;
      }

      await SecureStore.setItemAsync(
        'access_token',
        dados.access_token
      );

      router.replace('/home');
    } catch (erro) {
      console.error('Erro ao realizar login:', erro);

      Alert.alert(
        'Erro de conexão',
        'Não foi possível acessar o sistema. Verifique sua conexão e tente novamente.'
      );
    } finally {
      setCarregando(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Avalia & Trata</Text>

        <Text style={styles.subtitle}>
          Sistema inteligente de triagem, registro clínico e análise de lesões corporais.
        </Text>

        <Text style={styles.label}>E-mail</Text>
        <TextInput
          style={styles.input}
          placeholder="Digite seu e-mail"
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
          value={email}
          onChangeText={setEmail}
          editable={!carregando}
        />

        <Text style={styles.label}>Senha</Text>
        <TextInput
          style={styles.input}
          placeholder="Digite sua senha"
          secureTextEntry
          value={senha}
          onChangeText={setSenha}
          editable={!carregando}
        />

        <TouchableOpacity
          style={[
            styles.button,
            carregando && styles.buttonDisabled,
          ]}
          activeOpacity={0.8}
          onPress={handleLogin}
          disabled={carregando}
        >
          {carregando ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.buttonText}>
              Acessar o Sistema
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0056b3',
    justifyContent: 'center',
    padding: 24,
  },
  content: {
    backgroundColor: '#ffffff',
    padding: 28,
    borderRadius: 12,
    elevation: 4,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 12,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 15,
    color: '#555',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    backgroundColor: '#fafafa',
    marginBottom: 14,
  },
  button: {
    backgroundColor: '#0056b3',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
});
