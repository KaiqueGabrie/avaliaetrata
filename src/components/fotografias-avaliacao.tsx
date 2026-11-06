import { useState } from 'react';
import { Image, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { API_URL } from '../config/api';

export type ImagensAvaliacao = {
  imagem_original_url?: string | null;
  imagem_processada_url?: string | null;
  imagem_bordas_url?: string | null;
};

function urlCompleta(url?: string | null): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_URL}${url.startsWith('/') ? '' : '/'}${url}`;
}

function Fotografia({ titulo, url, descricao }: { titulo: string; url?: string | null; descricao: string }) {
  const [falhou, setFalhou] = useState(false);
  const endereco = urlCompleta(url);
  if (!endereco) return null;
  return (
    <View style={styles.bloco}>
      <Text style={styles.subtitulo}>{titulo}</Text>
      <Image
        key={endereco}
        source={{ uri: endereco }}
        style={styles.imagem}
        resizeMode="contain"
        accessibilityLabel={titulo}
        onLoad={() => setFalhou(false)}
        onError={() => setFalhou(true)}
      />
      {falhou ? <Text style={styles.erro}>Não foi possível carregar a imagem. Atualize o acesso às fotografias.</Text> : null}
      <Text style={styles.legenda}>{descricao}</Text>
    </View>
  );
}

export default function FotografiasAvaliacao({ imagens, onAtualizar }: {
  imagens: ImagensAvaliacao;
  onAtualizar?: () => void;
}) {
  const temImagem = !!(imagens.imagem_original_url || imagens.imagem_processada_url || imagens.imagem_bordas_url);
  if (!temImagem) return null;
  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Fotografias da avaliação</Text>
      <Fotografia titulo="Fotografia original" url={imagens.imagem_original_url} descricao="Registro original enviado pelo profissional." />
      <Fotografia titulo="Imagem pré-processada" url={imagens.imagem_processada_url} descricao="Fotografia preparada pelo OpenCV; não é uma classificação de tecidos." />
      <Fotografia titulo="Realce técnico de bordas (OpenCV)" url={imagens.imagem_bordas_url} descricao="Linhas amarelas destacam mudanças de intensidade na fotografia inteira. Não delimitam a ferida nem medem sua área." />
      {!imagens.imagem_bordas_url ? (
        <Text style={styles.legenda}>A visualização de bordas estará disponível nas avaliações criadas após esta atualização.</Text>
      ) : null}
      {onAtualizar ? (
        <TouchableOpacity style={styles.botao} onPress={onAtualizar} accessibilityRole="button">
          <Text style={styles.botaoTexto}>Atualizar acesso às fotografias</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 10, padding: 14, marginBottom: 14 },
  titulo: { color: '#0056b3', fontSize: 17, fontWeight: 'bold', marginBottom: 10 },
  bloco: { marginBottom: 16 },
  subtitulo: { color: '#1e293b', fontWeight: 'bold', marginBottom: 7 },
  imagem: { width: '100%', height: 260, backgroundColor: '#f1f5f9', borderRadius: 8 },
  legenda: { color: '#64748b', fontSize: 12, lineHeight: 18, marginTop: 6 },
  erro: { color: '#b91c1c', fontSize: 12, marginTop: 5 },
  botao: { borderColor: '#0056b3', borderWidth: 1, padding: 11, borderRadius: 8, alignItems: 'center' },
  botaoTexto: { color: '#0056b3', fontWeight: 'bold' },
});
