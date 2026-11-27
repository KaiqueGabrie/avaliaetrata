
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import IconeInterface from '../components/icone-interface';
import { apiJson } from '../config/cliente';
import { Aviso } from '../utils/avisos';
import { removerToken } from '../utils/tokenStorage';

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

type Campo = {
  chave: keyof Campos;
  titulo: string;
  dica: string;
  tipo?: 'email-address' | 'numeric' | 'phone-pad';
  limite: number;
};

const dadosPessoais: Campo[] = [
  {
    chave: 'nome',
    titulo: 'Nome completo *',
    dica: 'Informe seu nome completo',
    limite: 150,
  },
  {
    chave: 'email',
    titulo: 'E-mail *',
    dica: 'Digite seu e-mail',
    tipo: 'email-address',
    limite: 150,
  },
  {
    chave: 'cpf',
    titulo: 'CPF *',
    dica: '000.000.000-00',
    tipo: 'numeric',
    limite: 14,
  },
  {
    chave: 'data_nascimento',
    titulo: 'Data de nascimento',
    dica: 'DD/MM/AAAA',
    tipo: 'numeric',
    limite: 10,
  },
  {
    chave: 'telefone',
    titulo: 'Telefone',
    dica: '(00) 00000-0000',
    tipo: 'phone-pad',
    limite: 20,
  },
];

const dadosProfissionais: Campo[] = [
  {
    chave: 'registro_coren',
    titulo: 'Registro profissional (COREN)',
    dica: 'Informe seu registro profissional',
    limite: 30,
  },
  {
    chave: 'instituicao_saude',
    titulo: 'Instituição de saúde',
    dica: 'Informe a instituição',
    limite: 150,
  },
];

function mascaraCpf(valor: string) {
  const d = valor.replace(/\D/g, '').slice(0, 11);

  return d
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3}\.\d{3})(\d)/, '$1.$2')
    .replace(/(\.\d{3})(\d{1,2})$/, '$1-$2');
}

function mascaraTelefone(valor: string) {
  const d = valor.replace(/\D/g, '').slice(0, 11);

  if (d.length <= 2) return d;

  const ddd = d.slice(0, 2);
  const numero = d.slice(2);

  if (numero.length <= 4) {
    return `(${ddd}) ${numero}`;
  }

  const corte = numero.length === 9 ? 5 : 4;

  return (
    `(${ddd}) ${numero.slice(0, corte)}` +
    `-${numero.slice(corte)}`
  );
}

function mascaraData(valor: string) {
  const d = valor.replace(/\D/g, '').slice(0, 8);

  if (d.length <= 2) return d;

  if (d.length <= 4) {
    return `${d.slice(0, 2)}/${d.slice(2)}`;
  }

  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

function formatarData(valor: string | null) {
  if (!valor) return '';

  const partes =
    /^(\d{4})-(\d{2})-(\d{2})/.exec(valor);

  return partes
    ? `${partes[3]}/${partes[2]}/${partes[1]}`
    : valor;
}

function converterData(valor: string): string | null {
  if (!valor.trim()) return null;

  const partes =
    /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(valor);

  if (!partes) {
    throw new Error(
      'Informe a data no formato DD/MM/AAAA.',
    );
  }

  const [, dia, mes, ano] = partes;

  const data = new Date(
    Number(ano),
    Number(mes) - 1,
    Number(dia),
  );

  if (
    data.getDate() !== Number(dia) ||
    data.getMonth() !== Number(mes) - 1 ||
    data.getFullYear() !== Number(ano) ||
    Number(ano) < 1900 ||
    data > new Date()
  ) {
    throw new Error(
      'Informe uma data de nascimento válida.',
    );
  }

  return `${ano}-${mes}-${dia}`;
}

function validarCpf(valor: string) {
  const d = valor.replace(/\D/g, '');

  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) {
    return false;
  }

  for (const tamanho of [9, 10]) {
    let soma = 0;

    for (let i = 0; i < tamanho; i++) {
      soma += Number(d[i]) * (tamanho + 1 - i);
    }

    let digito = (soma * 10) % 11;

    if (digito === 10) digito = 0;

    if (digito !== Number(d[tamanho])) {
      return false;
    }
  }

  return true;
}

function camposDoPerfil(perfil: Perfil): Campos {
  const telefone = perfil.telefone || '';
  const digitos = telefone.replace(/\D/g, '');

  return {
    nome: perfil.nome || '',
    email: perfil.email || '',
    cpf: mascaraCpf(perfil.cpf || ''),
    data_nascimento: formatarData(perfil.data_nascimento),
    telefone:
      digitos.length === 10 || digitos.length === 11
        ? mascaraTelefone(telefone)
        : telefone,
    registro_coren: perfil.registro_coren || '',
    instituicao_saude: perfil.instituicao_saude || '',
  };
}

export default function PerfilScreen() {
  const router = useRouter();

  const bloqueado = useRef(false);

  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [campos, setCampos] = useState<Campos | null>(null);

  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [saindo, setSaindo] = useState(false);
  const [erroCarga, setErroCarga] = useState('');
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    const requisicao = new AbortController();
    const { signal } = requisicao;

    setCarregando(true);
    setErroCarga('');

    async function carregar() {
      try {
        const dados = await apiJson<Perfil>(
          '/auth/me',
          { signal, cache: 'no-store' },
        );

        if (signal.aborted) return;

        setPerfil(dados);
        setCampos(camposDoPerfil(dados));
      } catch (e) {
        if (!signal.aborted) {
          setErroCarga(
            e instanceof Error
              ? e.message
              : 'Não foi possível carregar o perfil.',
          );
        }
      } finally {
        if (!signal.aborted) {
          setCarregando(false);
        }
      }
    }

    void carregar();

    return () => requisicao.abort();
  }, [tentativa]);

  function atualizar(chave: keyof Campos, valor: string) {
    if (chave === 'cpf') {
      valor = mascaraCpf(valor);
    }

    if (chave === 'data_nascimento') {
      valor = mascaraData(valor);
    }

    if (chave === 'telefone') {
      valor = mascaraTelefone(valor);
    }

    setCampos(anterior =>
      anterior
        ? { ...anterior, [chave]: valor }
        : anterior,
    );

    setErro('');
    setSucesso('');
  }

  async function salvar() {
    if (!campos || bloqueado.current) return;

    setErro('');
    setSucesso('');

    if (campos.nome.trim().length < 3) {
      setErro('Informe seu nome completo.');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(campos.email.trim())) {
      setErro('Informe um endereço de e-mail válido.');
      return;
    }

    if (!validarCpf(campos.cpf)) {
      setErro('Informe um CPF válido.');
      return;
    }

    let nascimento: string | null;

    try {
      nascimento = converterData(campos.data_nascimento);
    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Data inválida.',
      );
      return;
    }

    bloqueado.current = true;
    setSalvando(true);

    try {
      const dados = await apiJson<Perfil>(
        '/auth/me',
        {
          method: 'PATCH',
          body: JSON.stringify({
            nome: campos.nome.trim(),
            email: campos.email.trim().toLowerCase(),
            cpf: campos.cpf.replace(/\D/g, ''),
            data_nascimento: nascimento,
            telefone: campos.telefone.trim() || null,
            registro_coren:
              campos.registro_coren.trim() || null,
            instituicao_saude:
              campos.instituicao_saude.trim() || null,
          }),
        },
      );

      setPerfil(dados);
      setCampos(camposDoPerfil(dados));
      setSucesso('Suas informações foram atualizadas.');
    } catch (e) {
      setErro(
        e instanceof Error
          ? e.message
          : 'Não foi possível salvar o perfil.',
      );
    } finally {
      bloqueado.current = false;
      setSalvando(false);
    }
  }

  function sair() {
    if (bloqueado.current) return;

    Aviso.alert(
      'Sair da conta',
      'Deseja encerrar sua sessão neste dispositivo?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Sair',
          style: 'destructive',
          onPress: async () => {
            if (bloqueado.current) return;

            bloqueado.current = true;
            setSaindo(true);

            try {
              await removerToken('access_token');

              setCampos(null);
              setPerfil(null);

              if (router.canGoBack()) {
                router.dismissAll();
              }

              router.replace('/');
            } catch {
              Aviso.alert(
                'Erro',
                'Não foi possível encerrar a sessão.',
              );
            } finally {
              bloqueado.current = false;
              setSaindo(false);
            }
          },
        },
      ],
    );
  }

  function renderizarCampos(lista: Campo[]) {
    if (!campos) return null;

    return lista.map(campo => (
      <View key={campo.chave} style={styles.campo}>
        <Text style={styles.label}>
          {campo.titulo}
        </Text>

        <TextInput
          accessibilityLabel={campo.titulo}
          style={styles.input}
          placeholder={campo.dica}
          placeholderTextColor="#64748b"
          value={campos[campo.chave]}
          onChangeText={valor =>
            atualizar(campo.chave, valor)
          }
          keyboardType={campo.tipo || 'default'}
          autoCapitalize={
            campo.chave === 'email'
              ? 'none'
              : campo.chave === 'registro_coren'
                ? 'characters'
                : 'words'
          }
          autoCorrect={false}
          maxLength={campo.limite}
          editable={!salvando && !saindo}
        />
      </View>
    ));
  }

  return (
    <ScrollView
      style={styles.tela}
      contentContainerStyle={styles.scroll}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.container}>
        <View style={styles.cabecalho}>
          <View style={styles.avatar}>
            <IconeInterface
              nome="perfil"
              tamanho={36}
              cor="#ffffff"
            />
          </View>

          <View style={styles.textos}>
            <Text style={styles.titulo}>
              Meu perfil profissional
            </Text>

            {perfil ? (
              <Text style={styles.nome}>
                {perfil.nome}
              </Text>
            ) : null}

            <Text style={styles.subtituloCabecalho}>
              Gerencie as informações da sua conta.
            </Text>
          </View>
        </View>

        {carregando ? (
          <ActivityIndicator
            size="large"
            color="#005088"
            style={{ marginVertical: 32 }}
          />
        ) : erroCarga || !campos ? (
          <View style={styles.card}>
            <Text style={styles.erro}>
              {erroCarga || 'Perfil indisponível.'}
            </Text>

            <TouchableOpacity
              style={styles.botao}
              onPress={() => setTentativa(v => v + 1)}
            >
              <Text style={styles.textoBotao}>
                Tentar novamente
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            <View style={styles.card}>
              <View style={styles.tituloSecao}>
                <IconeInterface nome="perfil" tamanho={23} />

                <Text style={styles.tituloCard}>
                  Dados pessoais
                </Text>
              </View>

              {renderizarCampos(dadosPessoais)}
            </View>

            <View style={styles.card}>
              <View style={styles.tituloSecao}>
                <IconeInterface nome="avaliacao" tamanho={23} />

                <Text style={styles.tituloCard}>
                  Dados profissionais
                </Text>
              </View>

              {renderizarCampos(dadosProfissionais)}

              <Text style={styles.observacao}>
                Mantenha seu registro profissional e sua
                instituição atualizados.
              </Text>
            </View>

            {erro ? (
              <View style={styles.caixaErro}>
                <Text
                  accessibilityLiveRegion="polite"
                  style={styles.erro}
                >
                  {erro}
                </Text>
              </View>
            ) : null}

            {sucesso ? (
              <View style={styles.caixaSucesso}>
                <IconeInterface
                  nome="confirmar"
                  tamanho={22}
                  cor="#15803d"
                />

                <Text
                  accessibilityLiveRegion="polite"
                  style={styles.sucesso}
                >
                  {sucesso}
                </Text>
              </View>
            ) : null}

            <TouchableOpacity
              accessibilityRole="button"
              disabled={salvando || saindo}
              style={[
                styles.botao,
                (salvando || saindo) && styles.desabilitado,
              ]}
              onPress={() => void salvar()}
            >
              {salvando ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text style={styles.textoBotao}>
                  Salvar alterações
                </Text>
              )}
            </TouchableOpacity>

            <Text style={styles.observacao}>
              * Campos obrigatórios.
            </Text>
          </>
        )}

        <View style={styles.secaoSessao}>
          <Text style={styles.tituloCard}>
            Sessão e acesso
          </Text>

          <Text style={styles.observacao}>
            Encerre sua sessão ao utilizar dispositivos
            compartilhados.
          </Text>

          <TouchableOpacity
            accessibilityRole="button"
            disabled={salvando || saindo}
            style={styles.botaoSair}
            onPress={sair}
          >
            {saindo ? (
              <ActivityIndicator color="#b91c1c" />
            ) : (
              <IconeInterface
                nome="sair"
                tamanho={22}
                cor="#b91c1c"
              />
            )}

            <Text style={styles.textoSair}>
              Sair da conta
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  tela: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  scroll: {
    flexGrow: 1,
    alignItems: 'center',
  },
  container: {
    width: '100%',
    maxWidth: 760,
    padding: 20,
    paddingBottom: 36,
  },
  cabecalho: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    padding: 22,
    backgroundColor: '#005088',
    borderRadius: 14,
    marginBottom: 20,
  },
  avatar: {
    width: 66,
    height: 66,
    borderRadius: 33,
    backgroundColor: '#ffffff20',
    borderWidth: 1,
    borderColor: '#78a5c2',
    justifyContent: 'center',
    alignItems: 'center',
  },
  textos: {
    flex: 1,
    minWidth: 0,
  },
  titulo: {
    color: '#ffffff',
    fontSize: 21,
    fontWeight: '700',
    marginBottom: 6,
  },
  nome: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
  },
  subtituloCabecalho: {
    color: '#dce9f2',
    fontSize: 13,
    lineHeight: 20,
  },
  card: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 14,
    padding: 18,
    marginBottom: 18,
  },
  tituloSecao: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    marginBottom: 20,
  },
  tituloCard: {
    fontSize: 17,
    color: '#005088',
    fontWeight: '700',
  },
  campo: {
    marginBottom: 16,
  },
  label: {
    color: '#1e293b',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#f1f5f9',
    borderWidth: 1,
    borderColor: '#b7c9d5',
    borderRadius: 9,
    minHeight: 48,
    paddingHorizontal: 13,
    paddingVertical: 12,
    fontSize: 14,
    color: '#1e293b',
  },
  observacao: {
    color: '#64748b',
    fontSize: 12,
    lineHeight: 19,
    marginTop: 10,
  },
  botao: {
    minHeight: 52,
    borderRadius: 10,
    padding: 14,
    backgroundColor: '#005088',
    alignItems: 'center',
    justifyContent: 'center',
  },
  textoBotao: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
  },
  desabilitado: {
    opacity: 0.6,
  },
  caixaErro: {
    backgroundColor: '#fef2f2',
    borderRadius: 9,
    padding: 14,
    marginBottom: 15,
  },
  erro: {
    color: '#b91c1c',
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 6,
  },
  caixaSucesso: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#dcfce7',
    borderRadius: 9,
    padding: 14,
    marginBottom: 15,
  },
  sucesso: {
    flex: 1,
    color: '#15803d',
    fontSize: 13,
    fontWeight: '600',
  },
  secaoSessao: {
    marginTop: 22,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 14,
    padding: 18,
  },
  botaoSair: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    minHeight: 48,
    padding: 12,
    borderWidth: 1,
    borderColor: '#dc2626',
    borderRadius: 9,
    marginTop: 16,
  },
  textoSair: {
    color: '#b91c1c',
    fontSize: 14,
    fontWeight: '700',
  },
});
