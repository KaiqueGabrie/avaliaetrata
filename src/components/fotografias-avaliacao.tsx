
import { useState } from 'react';
import {
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';

import { API_URL } from '../config/api';
import ComparacaoTecidosIA from './comparacao-tecidos-ia';

export type MarcacaoIA = {
  status: 'pronta' | 'pendente' | 'sem_regioes' | 'indisponivel';
  url?: string | null;
  total_regioes: number;
  total_hipoteses_tecido?: number;
  detalhes_regioes?: {
    rotulo_visual: string;
    classificacao_proposta: string;
    justificativa: string;
    confianca_autodeclarada?: string | null;
  }[];
  mensagem?: string;
  origem_regioes?:
    | 'relatorio'
    | 'complemento_openai'
    | 'indisponivel';
};

export type MedidasGeometricas = {
  area_retangulo_delimitador_cm2: number | null;
  area_elipse_aproximada_cm2: number | null;
  area_real_segmentada_cm2: number | null;
  metodo: string;
  observacao: string;
};

export type ImagensAvaliacao = {
  imagem_original_url?: string | null;
  imagem_processada_url?: string | null;
  imagem_bordas_url?: string | null;
  marcacoes_por_ia?: Record<string, MarcacaoIA>;
  medidas_geometricas?: MedidasGeometricas;
};

const NOMES = [
  { id: 'openai', nome: 'OpenAI' },
  { id: 'gemini', nome: 'Gemini' },
  { id: 'kimi', nome: 'Kimi' },
];

function urlCompleta(url?: string | null): string | null {
  if (!url) return null;

  if (/^https?:\/\//i.test(url)) return url;

  return `${API_URL}${url.startsWith('/') ? '' : '/'}${url}`;
}

function Fotografia({
  titulo,
  url,
  descricao,
  compacta = false,
}: {
  titulo: string;
  url?: string | null;
  descricao: string;
  compacta?: boolean;
}) {
  const [falhou, setFalhou] = useState(false);
  const endereco = urlCompleta(url);

  if (!endereco) return null;

  return (
    <View style={styles.bloco}>
      <Text style={styles.subtitulo}>{titulo}</Text>

      <Image
        key={endereco}
        source={{ uri: endereco }}
        style={[
          styles.imagem,
          compacta && styles.imagemCompacta,
        ]}
        resizeMode="contain"
        accessibilityLabel={titulo}
        onLoad={() => setFalhou(false)}
        onError={() => setFalhou(true)}
      />

      {falhou ? (
        <Text style={styles.erro}>
          Não foi possível carregar a imagem.
          Atualize o acesso às fotografias.
        </Text>
      ) : null}

      <Text style={styles.legenda}>{descricao}</Text>
    </View>
  );
}

function Botao({
  texto,
  onPress,
  ativo,
  disabled,
}: {
  texto: string;
  onPress: () => void;
  ativo?: boolean;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[
        styles.aba,
        ativo && styles.abaAtiva,
      ]}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
    >
      <Text
        style={[
          styles.abaTexto,
          ativo && styles.abaTextoAtiva,
        ]}
      >
        {texto}
      </Text>
    </TouchableOpacity>
  );
}

function AreaGeometrica({
  dados,
}: {
  dados?: MedidasGeometricas;
}) {
  const [detalhes, setDetalhes] = useState(false);

  if (!dados) return null;

  const fmt = (n: number | null) =>
    n == null
      ? 'Indisponível'
      : `${n.toLocaleString('pt-BR', {
          maximumFractionDigits: 2,
        })} cm²`;

  return (
    <View style={styles.medidas}>
      <Text style={styles.subtitulo}>
        Estimativas geométricas das medidas informadas
      </Text>

      <Text style={styles.texto}>
        Retângulo delimitador:{' '}
        {fmt(dados.area_retangulo_delimitador_cm2)}
      </Text>

      <Text style={styles.texto}>
        Aproximação elíptica:{' '}
        {fmt(dados.area_elipse_aproximada_cm2)}
      </Text>

      <Text style={styles.texto}>
        Área real segmentada:{' '}
        {fmt(dados.area_real_segmentada_cm2)}
      </Text>

      <TouchableOpacity
        onPress={() => setDetalhes(!detalhes)}
        accessibilityRole="button"
      >
        <Text style={styles.link}>
          {detalhes
            ? 'Ocultar método e limitações'
            : 'Ver método e limitações'}
        </Text>
      </TouchableOpacity>

      {detalhes ? (
        <>
          <Text style={styles.legenda}>
            {dados.metodo}
          </Text>

          <Text style={styles.legenda}>
            {dados.observacao}
          </Text>
        </>
      ) : null}
    </View>
  );
}

export default function FotografiasAvaliacao({
  imagens,
  onAtualizar,
  onGerar,
  gerando = false,
  onReprocessarOpenAI,
  reprocessandoOpenAI = false,
}: {
  imagens: ImagensAvaliacao;
  onAtualizar?: () => void;
  onGerar?: () => void;
  gerando?: boolean;
  onReprocessarOpenAI?: () => void;
  reprocessandoOpenAI?: boolean;
}) {
  const [aba, setAba] = useState('gemini');
  const [comparar, setComparar] = useState(false);
  const [mostrarBordas, setMostrarBordas] = useState(false);
  const [mostrarPreprocessada, setMostrarPreprocessada] =
    useState(false);

  const [detalhesAbertos, setDetalhesAbertos] =
    useState<Record<string, boolean>>({});

  const { width } = useWindowDimensions();

  const marcacoes = imagens.marcacoes_por_ia || {};

  const temImagem = !!(
    imagens.imagem_original_url ||
    imagens.imagem_processada_url ||
    imagens.imagem_bordas_url
  );

  if (!temImagem) return null;

  const selecionada =
    NOMES.find(p => p.id === aba) || NOMES[0];

  const mostrar = (
    provedor: { id: string; nome: string },
    compacta = false
  ) => {
    const dados = marcacoes[provedor.id];

    return (
      <View
        key={provedor.id}
        style={[
          styles.marcacao,
          comparar &&
            (width > 1000
              ? styles.marcacaoTerco
              : styles.marcacaoCheia),
        ]}
      >
        {dados?.url ? (
          <>
            <Fotografia
              titulo={`${provedor.nome} — ${dados.total_regioes} região(ões) proposta(s)`}
              url={dados.url}
              descricao="Contornos e hipóteses visuais de tecido propostos pela IA. NÃO são classificação clínica confirmada, nem área real."
              compacta={compacta}
            />

            <Text style={styles.legenda}>
              Hipóteses de tecido:{' '}
              {dados.total_hipoteses_tecido || 0}.
              Sem porcentagens automáticas;
              confirme no editor.
            </Text>

            {dados.origem_regioes ===
            'complemento_openai' ? (
              <Text style={styles.legenda}>
                Contornos obtidos em uma análise visual
                complementar; o relatório T.I.M.E.S.
                original não foi alterado.
              </Text>
            ) : null}

            {dados.detalhes_regioes?.length ? (
              <TouchableOpacity
                accessibilityRole="button"
                onPress={() =>
                  setDetalhesAbertos(anterior => ({
                    ...anterior,
                    [provedor.id]:
                      !anterior[provedor.id],
                  }))
                }
              >
                <Text style={styles.link}>
                  {detalhesAbertos[provedor.id]
                    ? '▾ Ocultar'
                    : '▸ Ver'}{' '}
                  hipóteses e justificativas (
                  {dados.detalhes_regioes.length})
                </Text>
              </TouchableOpacity>
            ) : null}

            {detalhesAbertos[provedor.id]
              ? (dados.detalhes_regioes || []).map(
                  (regiao, i) => (
                    <View
                      key={`${provedor.id}_${i}`}
                      style={styles.detalheRegiao}
                    >
                      <Text style={styles.texto}>
                        {i + 1}. {regiao.rotulo_visual}
                        {' — '}
                        {regiao.classificacao_proposta ===
                        'nao_classificado'
                          ? 'Não classificado'
                          : `Possível ${regiao.classificacao_proposta}`}
                      </Text>

                      {regiao.justificativa ? (
                        <Text style={styles.legenda}>
                          {regiao.justificativa}
                        </Text>
                      ) : null}

                      {regiao.confianca_autodeclarada ? (
                        <Text style={styles.legenda}>
                          Confiança autodeclarada:{' '}
                          {regiao.confianca_autodeclarada}
                        </Text>
                      ) : null}
                    </View>
                  )
                )
              : null}
          </>
        ) : (
          <View style={styles.semMarcacao}>
            <Text style={styles.subtitulo}>
              {provedor.nome}
            </Text>

            <Text style={styles.legenda}>
              {dados?.mensagem ||
                'Execute as IAs e gere as visualizações para consultar as regiões propostas.'}
            </Text>

            {provedor.id === 'openai' &&
            dados?.status === 'sem_regioes' &&
            onReprocessarOpenAI ? (
              <TouchableOpacity
                style={styles.botaoContorno}
                onPress={onReprocessarOpenAI}
                disabled={reprocessandoOpenAI}
                accessibilityRole="button"
              >
                <Text style={styles.botaoContornoTexto}>
                  {reprocessandoOpenAI
                    ? 'Solicitando contornos...'
                    : 'Tentar obter contornos da OpenAI'}
                </Text>
              </TouchableOpacity>
            ) : null}
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>
        Fotografias da avaliação
      </Text>

      <Fotografia
        titulo="Fotografia original"
        url={imagens.imagem_original_url}
        descricao="Registro original enviado pelo profissional, preservado sem marcações."
      />

      <TouchableOpacity
        onPress={() =>
          setMostrarPreprocessada(!mostrarPreprocessada)
        }
        accessibilityRole="button"
      >
        <Text style={styles.link}>
          {mostrarPreprocessada
            ? '▾ Ocultar'
            : '▸ Ver'}{' '}
          fotografia pré-processada (OpenCV)
        </Text>
      </TouchableOpacity>

      {mostrarPreprocessada ? (
        <Fotografia
          titulo="Imagem pré-processada"
          url={imagens.imagem_processada_url}
          descricao="Imagem preparada pelo OpenCV, sem classificação de tecidos."
        />
      ) : null}

      <View style={styles.separador} />

      <Text style={styles.subtitulo}>
        Marcações propostas por IA
      </Text>

      <Text style={styles.legenda}>
        Cada modelo recebe a mesma fotografia e pode
        propor hipóteses independentes de granulação,
        esfacelo ou necrose. O OpenCV desenha apenas
        regiões válidas. Cor isolada não determina tecido.
      </Text>

      <View style={styles.abas}>
        {NOMES.map(p => (
          <Botao
            key={p.id}
            texto={p.nome}
            onPress={() => {
              setAba(p.id);
              setComparar(false);
            }}
            ativo={!comparar && aba === p.id}
          />
        ))}

        <Botao
          texto="Comparar lado a lado"
          onPress={() => setComparar(!comparar)}
          ativo={comparar}
        />
      </View>

      {comparar ? (
        <View style={styles.grade}>
          {NOMES.map(p => mostrar(p, true))}
        </View>
      ) : (
        mostrar(selecionada)
      )}

      {/* ETAPA 2H — COMPARAÇÃO DAS HIPÓTESES */}
      {comparar ? (
        <ComparacaoTecidosIA marcacoes={marcacoes} />
      ) : null}

      {onGerar ? (
        <TouchableOpacity
          style={styles.botao}
          onPress={onGerar}
          disabled={gerando}
          accessibilityRole="button"
        >
          <Text style={styles.botaoTexto}>
            {gerando
              ? 'Gerando visualizações...'
              : 'Gerar / atualizar marcações das IAs'}
          </Text>
        </TouchableOpacity>
      ) : null}

      <Text style={styles.legenda}>
        Nenhuma hipótese é aprovada automaticamente.
        No editor, o enfermeiro pode aceitar, alterar
        ou rejeitar as classes propostas, corrigir
        contornos e validar a imagem.
        Percentuais dependem da delimitação e
        revisão profissional.
      </Text>

      <AreaGeometrica
        dados={imagens.medidas_geometricas}
      />

      {imagens.imagem_bordas_url ? (
        <>
          <TouchableOpacity
            onPress={() =>
              setMostrarBordas(!mostrarBordas)
            }
            accessibilityRole="button"
          >
            <Text style={styles.link}>
              {mostrarBordas
                ? '▾ Ocultar'
                : '▸ Ver'}{' '}
              realce técnico antigo de bordas
            </Text>
          </TouchableOpacity>

          {mostrarBordas ? (
            <Fotografia
              titulo="Realce técnico de bordas (OpenCV)"
              url={imagens.imagem_bordas_url}
              descricao="As linhas amarelas detectam variações de intensidade em toda a cena. Não delimitam a ferida nem medem sua área."
            />
          ) : null}
        </>
      ) : null}

      {onAtualizar ? (
        <TouchableOpacity
          style={styles.botaoContorno}
          onPress={onAtualizar}
          accessibilityRole="button"
        >
          <Text style={styles.botaoContornoTexto}>
            Atualizar acesso às fotografias
          </Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    padding: 14,
    marginBottom: 14,
  },
  titulo: {
    color: '#0056b3',
    fontSize: 17,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  subtitulo: {
    color: '#1e293b',
    fontWeight: 'bold',
    fontSize: 13,
    marginBottom: 7,
  },
  bloco: {
    marginBottom: 16,
  },
  imagem: {
    width: '100%',
    height: 260,
    backgroundColor: '#f1f5f9',
    borderRadius: 8,
  },
  imagemCompacta: {
    height: 215,
  },
  legenda: {
    color: '#64748b',
    fontSize: 12,
    lineHeight: 18,
    marginTop: 6,
  },
  texto: {
    color: '#334155',
    fontSize: 13,
    marginTop: 5,
  },
  erro: {
    color: '#b91c1c',
    fontSize: 12,
    marginTop: 5,
  },
  link: {
    color: '#0056b3',
    fontWeight: '600',
    fontSize: 12,
    paddingVertical: 10,
  },
  abas: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 7,
    marginTop: 12,
    marginBottom: 10,
  },
  aba: {
    borderColor: '#93c5fd',
    borderWidth: 1,
    borderRadius: 7,
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  abaAtiva: {
    backgroundColor: '#dbeafe',
    borderColor: '#0056b3',
  },
  abaTexto: {
    color: '#334155',
    fontSize: 12,
  },
  abaTextoAtiva: {
    color: '#0056b3',
    fontWeight: 'bold',
  },
  separador: {
    borderTopColor: '#e2e8f0',
    borderTopWidth: 1,
    marginVertical: 12,
  },
  grade: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 10,
  },
  marcacao: {
    flexGrow: 1,
  },
  marcacaoTerco: {
    width: '32%',
  },
  marcacaoCheia: {
    width: '100%',
  },
  semMarcacao: {
    minHeight: 130,
    padding: 12,
    backgroundColor: '#f8fafc',
    borderRadius: 8,
    justifyContent: 'center',
  },
  detalheRegiao: {
    padding: 10,
    backgroundColor: '#f8fafc',
    borderRadius: 8,
    marginBottom: 6,
  },
  medidas: {
    backgroundColor: '#f8fafc',
    padding: 12,
    borderRadius: 8,
    marginVertical: 12,
  },
  botao: {
    backgroundColor: '#0056b3',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  botaoTexto: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 13,
  },
  botaoContorno: {
    borderColor: '#0056b3',
    borderWidth: 1,
    padding: 11,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  botaoContornoTexto: {
    color: '#0056b3',
    fontWeight: 'bold',
  },
});
