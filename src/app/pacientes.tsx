import { useRouter } from 'expo-router';
import { useState } from 'react';
import { FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Paciente } from '../types/paciente';

const pacientesMock: Paciente[] = [
  { id: '1', nome: 'Maria Silva Santos', cpf: '123.456.789-00', dataNascimento: '15/04/1965', telefone: '(11) 98765-4321' },
  { id: '2', nome: 'João Pedro Oliveira', cpf: '987.654.321-11', dataNascimento: '20/08/1980', telefone: '(11) 91234-5678' },
  { id: '3', nome: 'Ana Clara Souza', cpf: '456.789.123-22', dataNascimento: '10/01/1992', telefone: '(11) 95555-4444' },
];

export default function PacientesScreen() {
  const router = useRouter();
  const [busca, setBusca] = useState('');

  const pacientesFiltrados = pacientesMock.filter((p) =>
    p.nome.toLowerCase().includes(busca.toLowerCase()) || p.cpf.includes(busca)
  );

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.inputBusca}
        placeholder="🔍 Buscar paciente por nome ou CPF..."
        value={busca}
        onChangeText={setBusca}
      />

      <FlatList
        data={pacientesFiltrados}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.cardPaciente}
            activeOpacity={0.7}
            onPress={() => router.push(`/paciente/${item.id}`)}
          >
            <View>
              <Text style={styles.nome}>{item.nome}</Text>
              <Text style={styles.detalhe}>CPF: {item.cpf}</Text>
              <Text style={styles.detalhe}>Data de Nasc.: {item.dataNascimento}</Text>
            </View>

            <Text style={styles.seta}>➔</Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <Text style={styles.emptyText}>Nenhum paciente encontrado com essa busca.</Text>
        }
      />

      <TouchableOpacity
        style={styles.btnNovoPaciente}
        activeOpacity={0.8}
        onPress={() => router.push('/paciente/novo')}
      >
        <Text style={styles.btnNovoPacienteTexto}>+ Cadastrar Paciente</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  inputBusca: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8, padding: 12, backgroundColor: '#fff', fontSize: 14, marginBottom: 16 },
  cardPaciente: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 8, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 10 },
  nome: { fontSize: 16, fontWeight: 'bold', color: '#0056b3', marginBottom: 4 },
  detalhe: { fontSize: 13, color: '#64748b' },
  seta: { fontSize: 18, color: '#0056b3', fontWeight: 'bold' },
  emptyText: { textAlign: 'center', color: '#94a3b8', marginTop: 24, fontSize: 14 },
  btnNovoPaciente: { backgroundColor: '#0056b3', paddingVertical: 14, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  btnNovoPacienteTexto: { color: '#fff', fontWeight: 'bold', fontSize: 15 },
});