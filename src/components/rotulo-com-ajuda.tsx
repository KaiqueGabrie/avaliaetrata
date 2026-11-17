import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

const explicacoes: Record<string, string> = {
  'Localização anatômica': 'Informe a parte do corpo, o lado e, quando souber, a posição na região. Exemplo: região posterior do calcanhar esquerdo.',
  'Comprimento (cm)': 'Informe o comprimento medido pelo profissional, em centímetros. Deixe em branco se a medida não foi feita.',
  'Largura (cm)': 'Informe a largura medida pelo profissional, em centímetros, transversal ao comprimento. Deixe em branco se a medida não foi feita.',
  'Tipo de exsudato': 'Exsudato é o líquido que pode sair da lesão. Registre o tipo observado pelo profissional. Se avaliou e não havia líquido, registre “ausente”. Se não avaliou, deixe em branco.',
  'Odor informado pelo profissional': 'Selecione “Presente” ou “Ausente” conforme a avaliação presencial. Use “Não avaliado” quando o odor não foi verificado.',
  'Nível de dor (0 a 10)': 'Informe o valor relatado pelo paciente: 0 significa sem dor e 10 indica a maior intensidade da escala. Deixe em branco se a dor não foi avaliada.',
  'Queixa principal': 'Descreva o motivo da avaliação e o que o paciente relata. Exemplo: refere dor no calcanhar ao apoiar o pé.',
  'Observações clínicas': 'Registre o que o profissional observou e o contexto relevante que ainda não foi informado nos demais campos.',
  'Como fotografar': 'Centralize a lesão, mantenha a câmera firme e use iluminação uniforme. Confira o foco antes de enviar. Mantenha rostos, etiquetas e outros identificadores fora da imagem.',
};

export default function RotuloComAjuda({ titulo }: { titulo: string }) {
  const [aberto, setAberto] = useState(false);
  const nome = titulo.replace(/\s*\*$/, '');
  const explicacao = explicacoes[nome];

  return (
    <View style={styles.grupo}>
      <View style={styles.linha}>
        <Text style={styles.rotulo}>{titulo}</Text>
        {explicacao ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={'Ajuda sobre ' + nome}
            accessibilityState={{ expanded: aberto }}
            onPress={() => setAberto(valor => !valor)}
            style={styles.botao}
          >
            <Text style={styles.icone}>ⓘ</Text>
          </Pressable>
        ) : null}
      </View>

      {aberto && explicacao ? (
        <Text accessibilityLiveRegion="polite" style={styles.ajuda}>
          {explicacao}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  grupo: { marginBottom: 4 },
  linha: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 4 },
  rotulo: { color: '#1e293b', fontWeight: '700', fontSize: 13 },
  botao: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  icone: { color: '#005088', fontSize: 20, fontWeight: '700' },
  ajuda: {
    color: '#284359',
    backgroundColor: '#eef6fc',
    padding: 12,
    borderRadius: 8,
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 6,
  },
});
