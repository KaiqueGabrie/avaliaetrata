
import { Link, usePathname } from 'expo-router';
import {
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import IconeInterface, {
  type NomeIcone,
} from './icone-interface';

const atalhos = [
  {
    destino: '/home',
    titulo: 'Início',
    icone: 'inicio',
  },
  {
    destino: '/pacientes',
    titulo: 'Pacientes',
    icone: 'pacientes',
  },
  {
    destino: '/explore',
    titulo: 'Ajuda',
    icone: 'ajuda',
  },
  {
    destino: '/perfil',
    titulo: 'Perfil',
    icone: 'perfil',
  },
] as const;

export default function RodapeNavegacao() {
  const rota = usePathname();

  const prontuario = /^\/paciente\/\d+\/?$/.test(rota);

  const visivel =
    prontuario ||
    atalhos.some(atalho => atalho.destino === rota);

  if (!visivel) return null;

  return (
    <SafeAreaView
      edges={['bottom']}
      style={styles.fundo}
    >
      <View style={styles.linha}>
        {atalhos.map(atalho => {
          const nestaTela = rota === atalho.destino;

          const ativo =
            nestaTela ||
            (prontuario &&
              atalho.destino === '/pacientes');

          const corIcone = ativo
            ? '#005088'
            : '#64748b';

          return (
            <Link
              key={atalho.destino}
              href={atalho.destino}
              asChild
            >
              <Pressable
                accessibilityRole="link"
                accessibilityLabel={atalho.titulo}
                accessibilityState={{
                  selected: ativo,
                  disabled: nestaTela,
                }}
                disabled={nestaTela}
                style={StyleSheet.flatten([
                  styles.atalho,
                  ativo && styles.ativo,
                ])}
              >
                <IconeInterface
                  nome={atalho.icone as NomeIcone}
                  tamanho={23}
                  cor={corIcone}
                />

                <Text
                  style={[
                    styles.texto,
                    ativo && styles.textoAtivo,
                  ]}
                >
                  {atalho.titulo}
                </Text>
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
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#dce6ed',
  },

  linha: {
    flexDirection: 'row',
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    paddingHorizontal: 8,
    paddingVertical: 6,
    gap: 4,
  },

  atalho: {
    flex: 1,
    minWidth: 0,
    minHeight: 60,
    paddingVertical: 7,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    gap: 5,
  },

  ativo: {
    backgroundColor: '#e5eff6',
  },

  texto: {
    fontSize: 12,
    fontWeight: '500',
    color: '#64748b',
    textAlign: 'center',
  },

  textoAtivo: {
    color: '#005088',
    fontWeight: '700',
  },
});
