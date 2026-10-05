import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity } from 'react-native';

export default function NovoPacienteScreen() {
  const router = useRouter();

  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [dataNascimento, setDataNascimento] = useState('');
  const [telefone, setTelefone] = useState('');
  const [historicoClinico, setHistoricoClinico] = useState('');

  const handleSalvar = () => {
    if (!nome.trim() || !cpf.trim()) {
      Alert.alert('Campos Obrigatórios', 'Por favor, informe pelo menos o Nome e CPF do paciente.');
      return;
    }

    Alert.alert('Sucesso', 'Paciente cadastrado com sucesso!', [
      { text: 'OK', onPress: () => router.back() },
    ]);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Novo Paciente</Text>

      <Text style={styles.label}>Nome Completo *</Text>
      <TextInput style={styles.input} placeholder="Ex: Maria Silva" value={nome} onChangeText={setNome} />

      <Text style={styles.label}>CPF *</Text>
      <TextInput style={styles.input} placeholder="000.000.000-00" keyboardType="numeric" value={cpf} onChangeText={setCpf} />

      <Text style={styles.label}>Data de Nascimento</Text>
      <TextInput style={styles.input} placeholder="DD/MM/AAAA" keyboardType="numeric" value={dataNascimento} onChangeText={setDataNascimento} />

      <Text style={styles.label}>Telefone de Contato</Text>
      <TextInput style={styles.input} placeholder="(00) 00000-0000" keyboardType="phone-pad" value={telefone} onChangeText={setTelefone} />

      <Text style={styles.label}>Histórico Clínico / Comorbidades</Text>
      <TextInput style={[styles.input, { height: 80 }]} placeholder="Diabetes, Hipertensão, Alergias..." multiline value={historicoClinico} onChangeText={setHistoricoClinico} />

      <TouchableOpacity style={styles.btnSalvar} onPress={handleSalvar}>
        <Text style={styles.btnSalvarTexto}>Salvar Cadastro</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#fff', flexGrow: 1 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#0056b3', marginBottom: 16 },
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 6 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, fontSize: 14, backgroundColor: '#fafafa', marginBottom: 14 },
  btnSalvar: { backgroundColor: '#0056b3', paddingVertical: 14, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  btnSalvarTexto: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
});