import { Link, usePathname } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

const atalhos = [
  { destino: '/home', titulo: 'Início' },
  { destino: '/pacientes', titulo: 'Pacientes' },
  { destino: '/explore', titulo: 'Ajuda' },
  { destino: '/perfil', titulo: 'Perfil' },
] as const;

export default function RodapeNavegacao() {
  const rota = usePathname();
  const prontuario = /^\/paciente\/\d+\/?$/.test(rota);
  const visivel = prontuario || atalhos.some(atalho => atalho.destino === rota);

  if (!visivel) return null;

  return (
    <SafeAreaView edges={['bottom']} style={styles.fundo}>
      <View style={styles.linha}>
        {atalhos.map(atalho => {
          const nestaTela = rota === atalho.destino;
          const ativo = nestaTela || (prontuario && atalho.destino === '/pacientes');

          return (
            <Link key={atalho.destino} href={atalho.destino} asChild>
              <Pressable
                accessibilityRole="link"
                accessibilityState={{ selected: ativo, disabled: nestaTela }}
                disabled={nestaTela}
                style={StyleSheet.flatten([
                  styles.atalho,
                  ativo && styles.ativo,
                ])}
              >
                <Text style={styles.texto}>{atalho.titulo}</Text>
              </Pressable>
            </Link>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fundo: {
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#dce6ed',
  },
  linha: {
    flexDirection: 'row',
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    paddingHorizontal: 6,
    paddingVertical: 4,
  },
  atalho: {
    flex: 1,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
  },
  ativo: {
    backgroundColor: '#e5f1fa',
  },
  texto: {
    color: '#005088',
    fontWeight: '700',
    fontSize: 13,
  },
});