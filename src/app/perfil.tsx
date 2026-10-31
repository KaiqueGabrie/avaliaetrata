import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import {
  ActivityIndicator, Alert, ScrollView, StyleSheet, Text, TextInput,
  TouchableOpacity, View,
} from 'react-native';
import { apiJson } from '../config/cliente';

type Perfil = {
  id_enfermeiro: number;
  nome: string;
  email: string;
  cpf: string;
  data_nascimento: string | null;
  telefone: string | null;
  registro_coren: string | null;
  instituicao_saude: string | null;
};

type Campos = {
  nome: string;
  email: string;
  cpf: string;
  data_nascimento: string;
  telefone: string;
  registro_coren: string;
  instituicao_saude: string;
};

function camposDoPerfil(perfil: Perfil): Campos {
  return {
    nome: perfil.nome ?? '',
    email: perfil.email ?? '',
    cpf: perfil.cpf ?? '',
    data_nascimento: perfil.data_nascimento ?? '',
    telefone: perfil.telefone ?? '',
    registro_coren: perfil.registro_coren ?? '',
    instituicao_saude: perfil.instituicao_saude ?? '',
  };
}

export default function PerfilScreen() {
  const router = useRouter();
  const [campos, setCampos] = useState<Campos | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    let ativo = true;
    async function carregar() {
      try {
        const perfil = await apiJson<Perfil>('/auth/me');
        if (ativo) setCampos(camposDoPerfil(perfil));
      } catch (erro) {
        if (ativo) Alert.alert('Não foi possível carregar o perfil', erro instanceof Error ? erro.message : 'Tente novamente.');
      } finally {
        if (ativo) setCarregando(false);
      }
    }
    carregar();
    return () => { ativo = false; };
  }, []);

  function atualizar(campo: keyof Campos, valor: string) {
    setCampos(anterior => anterior ? { ...anterior, [campo]: valor } : anterior);
  }

  async function salvar() {
    if (!campos || salvando) return;
    if (!campos.nome.trim() || !campos.email.trim() || !campos.cpf.trim()) {
      Alert.alert('Campos obrigatórios', 'Preencha nome, e-mail e CPF.');
      return;
    }
    if (campos.data_nascimento.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(campos.data_nascimento.trim())) {
      Alert.alert('Data inválida', 'Informe a data de nascimento no formato AAAA-MM-DD.');
      return;
    }
    setSalvando(true);
    try {
      const perfil = await apiJson<Perfil>('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          nome: campos.nome.trim(),
          email: campos.email.trim().toLowerCase(),
          cpf: campos.cpf.trim(),
          data_nascimento: campos.data_nascimento.trim() || null,
          telefone: campos.telefone.trim() || null,
          registro_coren: campos.registro_coren.trim() || null,
          instituicao_saude: campos.instituicao_saude.trim() || null,
        }),
      });
      setCampos(camposDoPerfil(perfil));
      Alert.alert('Perfil atualizado', 'Suas informações foram salvas com sucesso.');
    } catch (erro) {
      Alert.alert('Não foi possível salvar', erro instanceof Error ? erro.message : 'Tente novamente.');
    } finally {
      setSalvando(false);
    }
  }

  function sair() {
    Alert.alert('Sair da conta', 'Deseja encerrar sua sessão neste dispositivo?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Sair', style: 'destructive',
        onPress: async () => {
          try {
            await SecureStore.deleteItemAsync('access_token');
            router.dismissAll();
            router.replace('/');
          } catch {
            Alert.alert('Erro', 'Não foi possível encerrar a sessão. Tente novamente.');
          }
        },
      },
    ]);
  }

  if (carregando) {
    return <View style={styles.center}><ActivityIndicator size="large" color="#0056b3" /><Text style={styles.helper}>Carregando seus dados...</Text></View>;
  }
  if (!campos) {
    return <View style={styles.center}><Text>Perfil indisponível. Volte e tente novamente.</Text></View>;
  }

  const camposFormulario: { chave: keyof Campos; titulo: string; dica?: string; tipo?: 'email-address' | 'numeric' | 'phone-pad' }[] = [
    { chave: 'nome', titulo: 'Nome completo' },
    { chave: 'email', titulo: 'E-mail', tipo: 'email-address' },
    { chave: 'cpf', titulo: 'CPF (11 dígitos)', tipo: 'numeric' },
    { chave: 'data_nascimento', titulo: 'Data de nascimento', dica: 'AAAA-MM-DD' },
    { chave: 'telefone', titulo: 'Telefone', tipo: 'phone-pad' },
    { chave: 'registro_coren', titulo: 'Registro profissional (COREN)' },
    { chave: 'instituicao_saude', titulo: 'Instituição de saúde' },
  ];

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>Meu perfil profissional</Text>
      <Text style={styles.subtitle}>Confira seus dados e mantenha seu cadastro atualizado.</Text>
      <View style={styles.card}>
        {camposFormulario.map(({ chave, titulo, dica, tipo }) => (
          <View key={chave} style={styles.field}>
            <Text style={styles.label}>{titulo}</Text>
            <TextInput
              style={styles.input}
              value={campos[chave]}
              onChangeText={valor => atualizar(chave, valor)}
              placeholder={dica || `Informe ${titulo.toLowerCase()}`}
              keyboardType={tipo || 'default'}
              autoCapitalize={chave === 'email' ? 'none' : 'sentences'}
              autoCorrect={false}
              editable={!salvando}
            />
          </View>
        ))}
        <Text style={styles.helper}>Seu CPF deve ser válido. Alterações ficam vinculadas à sua conta.</Text>
        <TouchableOpacity style={[styles.button, salvando && styles.disabled]} disabled={salvando} onPress={salvar}>
          {salvando ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Salvar alterações</Text>}
        </TouchableOpacity>
      </View>
      <TouchableOpacity style={styles.logout} onPress={sair} disabled={salvando}>
        <Text style={styles.logoutText}>Sair da conta</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#f8fafc' },
  container: { padding: 20, paddingBottom: 36 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20 },
  title: { fontSize: 22, fontWeight: '700', color: '#0056b3', marginBottom: 6 },
  subtitle: { color: '#64748b', fontSize: 14, marginBottom: 18 },
  card: { backgroundColor: '#fff', borderColor: '#e2e8f0', borderWidth: 1, borderRadius: 12, padding: 18 },
  field: { marginBottom: 15 },
  label: { color: '#334155', fontWeight: '600', fontSize: 14, marginBottom: 6 },
  input: { backgroundColor: '#f8fafc', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8, padding: 12, fontSize: 15, color: '#0f172a' },
  helper: { color: '#64748b', fontSize: 12, marginTop: 6, marginBottom: 12 },
  button: { backgroundColor: '#0056b3', padding: 15, borderRadius: 8, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  disabled: { opacity: 0.6 },
  logout: { marginTop: 18, padding: 14, borderWidth: 1, borderColor: '#dc2626', borderRadius: 8, alignItems: 'center' },
  logoutText: { color: '#b91c1c', fontWeight: '700' },
});
