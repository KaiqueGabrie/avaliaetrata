import { ScrollView, StyleSheet, Text, View } from 'react-native';

const etapas = [
  {
    titulo: '1. Preencha os dados clínicos',
    itens: [
      'Informe a localização anatômica com a região e o lado. Exemplo: região posterior do calcanhar esquerdo.',
      'Se houver medidas, registre comprimento e largura em centímetros. Use o ícone ⓘ para ver o que cada campo pede.',
      'Preencha exsudato, odor e dor conforme o que foi avaliado ou relatado. Registre a queixa do paciente e use as observações clínicas para complementar.',
    ],
  },
  {
    titulo: '2. Envie a fotografia',
    itens: [
      'Centralize a lesão, mantenha a câmera firme e procure iluminação uniforme. Revise o foco e o enquadramento antes de enviar.',
      'Fotografe apenas a região necessária, deixando rostos, etiquetas e outros identificadores fora da imagem.',
      'Se a foto for usada para uma medição posterior, coloque uma régua de referência no mesmo plano da lesão. No navegador, use Selecionar da galeria para enviar o arquivo.',
    ],
  },
  {
    titulo: '3. Compare as análises',
    itens: [
      'Após o processamento, confira a foto, o relatório T.I.M.E.S. e as marcações de cada modelo. A confiança exibida é autodeclarada pela IA.',
      'Se o modelo ficar sem marcações, você ainda pode consultar o relatório e usar o editor para desenhar a região manualmente.',
    ],
  },
  {
    titulo: '4. Revise e consulte o resultado',
    itens: [
      'Escolha a análise que deseja revisar. Corrija a descrição, confira os contornos no editor e salve as alterações.',
      'Confira o relatório antes da aprovação profissional. Você pode voltar ao prontuário e reabrir a avaliação pelo histórico.',
    ],
  },
];

export default function ExploreScreen() {
  return (
    <ScrollView style={styles.pagina} contentContainerStyle={styles.container}>
      <Text accessibilityRole="header" style={styles.titulo}>Como realizar uma avaliação</Text>
      {etapas.map(etapa => (
        <View key={etapa.titulo} style={styles.card}>
          <Text accessibilityRole="header" style={styles.subtitulo}>{etapa.titulo}</Text>
          {etapa.itens.map(item => (
            <Text key={item} style={styles.texto}>• {item}</Text>
          ))}
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  pagina: { backgroundColor: '#f8fafc' },
  container: { width: '100%', maxWidth: 760, alignSelf: 'center', padding: 20, paddingBottom: 28 },
  titulo: { color: '#005088', fontSize: 23, fontWeight: '700', marginBottom: 16 },
  subtitulo: { color: '#005088', fontSize: 17, fontWeight: '700', marginBottom: 6 },
  card: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#dce6ed',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  texto: { color: '#334155', fontSize: 14, lineHeight: 22, marginTop: 5 },
});
