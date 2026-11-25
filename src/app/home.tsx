
import { useRouter } from 'expo-router';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';

import IconeInterface, {
  type NomeIcone,
} from '../components/icone-interface';

type Destino =
  | '/pacientes'
  | '/paciente/novo'
  | '/perfil'
  | '/explore';

type Atalho = {
  titulo: string;
  descricao: string;
  icone: NomeIcone;
  destino: Destino;
};

const atalhos: Atalho[] = [
  {
    titulo: 'Lista de pacientes',
    descricao:
      'Consulte os prontuários e acompanhe as avaliações realizadas.',
    icone: 'pacientes',
    destino: '/pacientes',
  },
  {
    titulo: 'Cadastrar paciente',
    descricao:
      'Registre as informações de um novo paciente.',
    icone: 'novo-paciente',
    destino: '/paciente/novo',
  },
  {
    titulo: 'Nova avaliação clínica',
    descricao:
      'Selecione um paciente para registrar uma avaliação.',
    icone: 'avaliacao',
    destino: '/pacientes',
  },
  {
    titulo: 'Meu perfil',
    descricao:
      'Consulte e atualize seus dados profissionais.',
    icone: 'perfil',
    destino: '/perfil',
  },
];

export default function HomeScreen() {
  const router = useRouter();
  const { width } = useWindowDimensions();

  const telaLarga = width >= 760;

  return (
    <ScrollView
      style={styles.tela}
      contentContainerStyle={styles.scroll}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.container}>
        <View style={styles.cabecalho}>
          <View style={styles.marca}>
            <View style={styles.logo}>
              <IconeInterface
                nome="avaliacao"
                tamanho={28}
                cor="#ffffff"
              />
            </View>

            <Text style={styles.nomeSistema}>
              Avalia & Trata
            </Text>
          </View>

          <Text style={styles.bemVindo}>
            Bem-vindo!
          </Text>

          <Text style={styles.descricaoCabecalho}>
            Avaliação de lesões cutâneas,
            registro clínico e acompanhamento de pacientes.
          </Text>
        </View>

        <Text style={styles.tituloSecao}>
          Acesso rápido
        </Text>

        <Text style={styles.subtituloSecao}>
          Selecione uma funcionalidade para continuar.
        </Text>

        <View style={styles.grade}>
          {atalhos.map(atalho => (
            <TouchableOpacity
              key={atalho.titulo}
              accessibilityRole="button"
              accessibilityLabel={atalho.titulo}
              activeOpacity={0.75}
              style={[
                styles.card,
                telaLarga && styles.cardLargo,
              ]}
              onPress={() => router.push(atalho.destino)}
            >
              <View style={styles.linhaCard}>
                <View style={styles.caixaIcone}>
                  <IconeInterface
                    nome={atalho.icone}
                    tamanho={28}
                  />
                </View>

                <View style={styles.textosCard}>
                  <Text style={styles.tituloCard}>
                    {atalho.titulo}
                  </Text>

                  <Text style={styles.descricaoCard}>
                    {atalho.descricao}
                  </Text>
                </View>

                <IconeInterface
                  nome="seta"
                  tamanho={18}
                  cor="#809bae"
                />
              </View>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={styles.tituloSecao}>
          Suporte ao profissional
        </Text>

        <TouchableOpacity
          accessibilityRole="button"
          style={styles.cardAjuda}
          activeOpacity={0.75}
          onPress={() => router.push('/explore')}
        >
          <View style={styles.caixaIcone}>
            <IconeInterface nome="livro" tamanho={27} />
          </View>

          <View style={styles.textosCard}>
            <Text style={styles.tituloCard}>
              Orientações de uso
            </Text>

            <Text style={styles.descricaoCard}>
              Saiba como registrar, fotografar e revisar
              uma avaliação com segurança.
            </Text>
          </View>

          <IconeInterface
            nome="seta"
            tamanho={18}
            cor="#809bae"
          />
        </TouchableOpacity>

        <View style={styles.aviso}>
          <IconeInterface
            nome="escudo"
            tamanho={25}
            cor="#005088"
          />

          <View style={styles.textosCard}>
            <Text style={styles.tituloAviso}>
              Apoio à avaliação profissional
            </Text>

            <Text style={styles.textoAviso}>
              Os resultados das inteligências artificiais
              exigem revisão profissional e não substituem
              a avaliação clínica presencial.
            </Text>
          </View>
        </View>

        <Text style={styles.versao}>
          Avalia & Trata • Versão 1.0
        </Text>
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
    maxWidth: 1120,
    padding: 20,
  },

  cabecalho: {
    backgroundColor: '#005088',
    borderRadius: 16,
    padding: 24,
    marginBottom: 28,
  },

  marca: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 20,
  },

  logo: {
    width: 44,
    height: 44,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#78a5c2',
    backgroundColor: '#ffffff15',
    alignItems: 'center',
    justifyContent: 'center',
  },

  nomeSistema: {
    fontSize: 18,
    fontWeight: '700',
    color: '#ffffff',
  },

  bemVindo: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 8,
  },

  descricaoCabecalho: {
    color: '#dce9f2',
    fontSize: 14,
    lineHeight: 22,
    maxWidth: 620,
  },

  tituloSecao: {
    color: '#172c3c',
    fontSize: 19,
    fontWeight: '700',
    marginBottom: 6,
  },

  subtituloSecao: {
    color: '#64748b',
    fontSize: 14,
    lineHeight: 21,
    marginBottom: 16,
  },

  grade: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 14,
  },

  card: {
    width: '100%',
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 12,
    padding: 18,
    marginBottom: 14,
    minHeight: 110,
    justifyContent: 'center',
  },

  cardLargo: {
    width: '49%',
    minHeight: 130,
  },

  linhaCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },

  caixaIcone: {
    width: 52,
    height: 52,
    borderRadius: 12,
    backgroundColor: '#e5eff6',
    alignItems: 'center',
    justifyContent: 'center',
  },

  textosCard: {
    flex: 1,
    minWidth: 0,
  },

  tituloCard: {
    fontSize: 16,
    fontWeight: '700',
    color: '#172c3c',
    marginBottom: 6,
  },

  descricaoCard: {
    fontSize: 13,
    color: '#64748b',
    lineHeight: 20,
  },

  cardAjuda: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#dbe4ec',
    borderRadius: 12,
    padding: 18,
    marginTop: 10,
    marginBottom: 20,
  },

  aviso: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    backgroundColor: '#eaf2f8',
    borderWidth: 1,
    borderColor: '#ccdfec',
    borderRadius: 10,
    padding: 16,
    marginBottom: 20,
  },

  tituloAviso: {
    fontSize: 14,
    fontWeight: '700',
    color: '#005088',
    marginBottom: 6,
  },

  textoAviso: {
    color: '#475569',
    fontSize: 13,
    lineHeight: 20,
  },

  versao: {
    textAlign: 'center',
    fontSize: 12,
    color: '#64748b',
    marginVertical: 12,
  },
});
