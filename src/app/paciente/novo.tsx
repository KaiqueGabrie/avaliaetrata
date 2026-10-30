
import { useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
} from 'react-native';

import { API_URL } from '../../config/api';

export default function NovoPacienteScreen() {
  const router = useRouter();

  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [dataNascimento, setDataNascimento] = useState('');
  const [telefone, setTelefone] = useState('');
  const [email, setEmail] = useState('');
  const [diagnostico, setDiagnostico] = useState('');
  const [localLesao, setLocalLesao] = useState('');
  const [salvando, setSalvando] = useState(false);

  const handleSalvar = async () => {
    if (!nome.trim() || !cpf.trim()) {
      Alert.alert(
        'Campos obrigatórios',
        'Informe pelo menos o nome e o CPF do paciente.'
      );
      return;
    }

    let dataFormatada = '';

    if (dataNascimento.trim()) {
      const partes = dataNascimento.trim().split('/');

      if (partes.length !== 3) {
        Alert.alert(
          'Data inválida',
          'Informe a data no formato DD/MM/AAAA.'
        );
        return;
      }

      const [dia, mes, ano] = partes;

      if (
        !/^\d{2}$/.test(dia) ||
        !/^\d{2}$/.test(mes) ||
        !/^\d{4}$/.test(ano)
      ) {
        Alert.alert(
          'Data inválida',
          'Informe a data no formato DD/MM/AAAA.'
        );
        return;
      }

      const data = new Date(
        Number(ano),
        Number(mes) - 1,
        Number(dia)
      );

      if (
        data.getFullYear() !== Number(ano) ||
        data.getMonth() !== Number(mes) - 1 ||
        data.getDate() !== Number(dia)
      ) {
        Alert.alert(
          'Data inválida',
          'Informe uma data de nascimento válida.'
        );
        return;
      }

      dataFormatada = `${ano}-${mes}-${dia}`;
    }

    setSalvando(true);

    try {
      const token = await SecureStore.getItemAsync('access_token');

      if (!token) {
        Alert.alert(
          'Sessão não encontrada',
          'Faça login novamente para cadastrar pacientes.'
        );
        return;
      }

      const paciente = {
        nome_completo: nome.trim(),
        cpf: cpf.trim(),
        data_nascimento: dataFormatada || null,
        telefone: telefone.trim() || null,
        email: email.trim() || null,
        diagnostico: diagnostico.trim() || null,
        local_lesao: localLesao.trim() || null,
        status_evolucao: null,
      };

      const resposta = await fetch(`${API_URL}/pacientes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(paciente),
      });

      if (resposta.status === 401 || resposta.status === 403) {
        Alert.alert(
          'Sessão inválida',
          'Sua sessão expirou ou você não tem permissão. Faça login novamente.'
        );
        return;
      }

      if (!resposta.ok) {
        const mensagem = resposta.status === 409
          ? 'Já existe um cadastro com esses dados.'
          : resposta.status === 422
            ? 'Confira os dados informados e tente novamente.'
            : 'Não foi possível concluir o cadastro. Tente novamente.';
        Alert.alert('Não foi possível cadastrar', mensagem);
        return;
      }

      Alert.alert(
        'Sucesso',
        'Paciente cadastrado com sucesso!',
        [
          {
            text: 'OK',
            onPress: () => router.back(),
          },
        ]
      );
    } catch (erro) {
      console.error('Erro ao cadastrar paciente:', erro);

      Alert.alert(
        'Erro de conexão',
        'Não foi possível concluir o cadastro. Verifique sua conexão e tente novamente.'
      );
    } finally {
      setSalvando(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Novo Paciente</Text>

      <Text style={styles.label}>Nome Completo *</Text>
      <TextInput
        style={styles.input}
        placeholder="Ex: Maria Silva"
        value={nome}
        onChangeText={setNome}
      />

      <Text style={styles.label}>CPF *</Text>
      <TextInput
        style={styles.input}
        placeholder="000.000.000-00"
        keyboardType="numeric"
        value={cpf}
        onChangeText={setCpf}
      />

      <Text style={styles.label}>Data de Nascimento</Text>
      <TextInput
        style={styles.input}
        placeholder="DD/MM/AAAA"
        keyboardType="numeric"
        value={dataNascimento}
        onChangeText={setDataNascimento}
      />

      <Text style={styles.label}>Telefone de Contato</Text>
      <TextInput
        style={styles.input}
        placeholder="(00) 00000-0000"
        keyboardType="phone-pad"
        value={telefone}
        onChangeText={setTelefone}
      />

      <Text style={styles.label}>E-mail</Text>
      <TextInput
        style={styles.input}
        placeholder="paciente@exemplo.com"
        keyboardType="email-address"
        autoCapitalize="none"
        value={email}
        onChangeText={setEmail}
      />

      <Text style={styles.label}>Diagnóstico</Text>
      <TextInput
        style={styles.input}
        placeholder="Informe o diagnóstico, se conhecido"
        value={diagnostico}
        onChangeText={setDiagnostico}
      />

      <Text style={styles.label}>Local da Lesão</Text>
      <TextInput
        style={styles.input}
        placeholder="Ex: Pé direito"
        value={localLesao}
        onChangeText={setLocalLesao}
      />

      <TouchableOpacity
        style={[
          styles.btnSalvar,
          salvando && { opacity: 0.6 },
        ]}
        onPress={handleSalvar}
        disabled={salvando}
      >
        {salvando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnSalvarTexto}>
            Salvar Cadastro
          </Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#fff',
    flexGrow: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 16,
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
  observacao: {
    fontSize: 12,
    color: '#666',
    marginBottom: 12,
  },
  btnSalvar: {
    backgroundColor: '#0056b3',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  btnSalvarTexto: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
});
