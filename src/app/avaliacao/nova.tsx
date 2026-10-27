
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { File } from 'expo-file-system';
import * as ImagePicker from 'expo-image-picker';
import { useLocalSearchParams } from 'expo-router';
import { fetch as expoFetch } from 'expo/fetch';

import { API_URL } from '../../config/api';
import {
  RespostaEstruturadaIA,
  ResultadoProvedorIA,
} from '../../types/ia';

type Provedor = 'gemini' | 'openai' | 'kimi' | 'todos';

type RespostaAPI = {
  sucesso: boolean;
  mensagem: string;
  imagem_processada_url?: string;
  analise_tecnica?: {
    brilho_medio?: number;
    contraste_global?: number;
  };
  analise_multimodal?: {
    sucesso_geral: boolean;
    data_processamento: string;
    resultados: Record<string, ResultadoProvedorIA>;
  };
};

const PROVEDORES: { valor: Provedor; titulo: string }[] = [
  { valor: 'todos', titulo: 'Todas as IAs' },
  { valor: 'gemini', titulo: 'Gemini' },
  { valor: 'openai', titulo: 'OpenAI' },
  { valor: 'kimi', titulo: 'Kimi' },
];

const TIMES = [
  ['T', 'Tecido'],
  ['I', 'Inflamação / Infecção'],
  ['M', 'Umidade'],
  ['E', 'Bordas'],
  ['S', 'Pele ao redor'],
];

function Lista({
  titulo,
  itens,
}: {
  titulo?: string;
  itens?: string[];
}) {
  if (!itens?.length) return null;

  return (
    <View style={styles.grupo}>
      {titulo ? <Text style={styles.rotulo}>{titulo}</Text> : null}
      {itens.map((item, indice) => (
        <Text key={indice} style={styles.texto}>
          {'\u2022'} {item}
        </Text>
      ))}
    </View>
  );
}

function Secao({
  titulo,
  children,
}: {
  titulo: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.secaoInterna}>
      <Text style={styles.subtitulo}>{titulo}</Text>
      {children}
    </View>
  );
}

function Campo({
  titulo,
  valor,
  alterar,
  multiline = false,
  placeholder,
}: {
  titulo: string;
  valor: string;
  alterar: (valor: string) => void;
  multiline?: boolean;
  placeholder?: string;
}) {
  return (
    <View style={styles.grupo}>
      <Text style={styles.rotulo}>{titulo}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline]}
        value={valor}
        onChangeText={alterar}
        multiline={multiline}
        placeholder={placeholder}
        keyboardType="default"
      />
    </View>
  );
}

function ResultadoEstruturado({
  resposta,
}: {
  resposta: RespostaEstruturadaIA;
}) {
  const tecidos = resposta.avaliacao_tecidos;
  const marcacoes = resposta.marcacoes_imagem;
  const plano = resposta.plano_cuidados_proposto;

  return (
    <View>
      <Secao titulo="Descrição geral">
        <Text style={styles.texto}>
          {resposta.conteudo_descricao || 'Não informada.'}
        </Text>
      </Secao>

      <Secao titulo="Qualidade da fotografia">
        <Text style={styles.texto}>
          Estado: {resposta.qualidade_imagem?.status || 'Não avaliado'}
        </Text>
        <Lista itens={resposta.qualidade_imagem?.observacoes} />
        <Lista
          titulo="Limitações"
          itens={resposta.qualidade_imagem?.limitacoes}
        />
      </Secao>

      <Secao titulo="Características visuais">
        {resposta.caracteristicas_visuais?.length ? (
          resposta.caracteristicas_visuais.map((item, indice) => (
            <View key={indice} style={styles.bloco}>
              <Text style={styles.rotulo}>{item.caracteristica}</Text>
              <Text style={styles.texto}>{item.descricao}</Text>
              <Text style={styles.textoMenor}>
                Avaliação: {item.status}
                {item.confianca_autodeclarada
                  ? ` | Confiança declarada: ${item.confianca_autodeclarada}`
                  : ''}
              </Text>
              {item.justificativa ? (
                <Text style={styles.textoMenor}>
                  {item.justificativa}
                </Text>
              ) : null}
            </View>
          ))
        ) : (
          <Text style={styles.textoMenor}>
            Sem características estruturadas disponíveis.
          </Text>
        )}
      </Secao>

      <Secao titulo="Avaliação T.I.M.E.S.">
        {TIMES.map(([letra, titulo]) => {
          const componente = resposta.avaliacao_times?.find(
            (item) => item.componente === letra,
          );

          return (
            <View key={letra} style={styles.bloco}>
              <Text style={styles.rotulo}>
                {letra} — {titulo}
              </Text>
              <Text style={styles.textoMenor}>
                Estado: {componente?.status || 'Não avaliado'}
              </Text>
              <Lista
                titulo="Observações visuais"
                itens={componente?.observacoes_visuais}
              />
              <Lista
                titulo="Dados clínicos relacionados"
                itens={componente?.dados_clinicos_relacionados}
              />
              <Lista
                titulo="Informações pendentes"
                itens={componente?.informacoes_pendentes}
              />
              <Lista
                titulo="Limitações"
                itens={componente?.limitacoes}
              />
            </View>
          );
        })}
      </Secao>

      <Secao titulo="Caracterização dos tecidos">
        <Text style={styles.textoMenor}>
          Estado: {tecidos?.status || 'Não avaliado'}
        </Text>

        {tecidos?.tecidos?.length ? (
          tecidos.tecidos.map((tecido, indice) => (
            <View key={indice} style={styles.bloco}>
              <Text style={styles.rotulo}>{tecido.tipo}</Text>
              <Text style={styles.texto}>
                {tecido.descricao_visual}
              </Text>
              <Text style={styles.texto}>
                Percentual estimado:{' '}
                {tecido.percentual_estimado == null
                  ? 'Não estimado'
                  : `${tecido.percentual_estimado}%`}
              </Text>
              <Text style={styles.textoMenor}>
                Confiança declarada:{' '}
                {tecido.confianca_autodeclarada || 'Não informada'}
              </Text>
              {tecido.justificativa ? (
                <Text style={styles.textoMenor}>
                  {tecido.justificativa}
                </Text>
              ) : null}
            </View>
          ))
        ) : (
          <Text style={styles.textoMenor}>
            Nenhuma classificação visual de tecido disponível.
          </Text>
        )}

        <Lista itens={tecidos?.limitacoes} />
      </Secao>

      <Secao titulo="Medidas da lesão">
        <Text style={styles.texto}>
          Comprimento informado:{' '}
          {resposta.medidas?.comprimento_informado_cm || '—'} cm
        </Text>
        <Text style={styles.texto}>
          Largura informada:{' '}
          {resposta.medidas?.largura_informada_cm || '—'} cm
        </Text>
        <Text style={styles.texto}>
          Área calculada:{' '}
          {resposta.medidas?.area_calculada_cm2 == null
            ? 'Não calculada'
            : `${resposta.medidas.area_calculada_cm2} cm²`}
        </Text>
        <Text style={styles.textoMenor}>
          Método: {resposta.medidas?.metodo_medicao || 'Não informado'}
        </Text>
        <Lista itens={resposta.medidas?.observacoes} />
      </Secao>

      <Secao titulo="Regiões identificadas na imagem">
        <Text style={styles.textoMenor}>
          Coordenadas normalizadas de 0 a 1, referentes à
          imagem processada. Ainda não representam segmentação
          validada.
        </Text>

        {marcacoes?.regioes?.length ? (
          marcacoes.regioes.map((regiao, indice) => (
            <View key={indice} style={styles.bloco}>
              <Text style={styles.rotulo}>{regiao.rotulo}</Text>
              <Text style={styles.texto}>{regiao.descricao}</Text>
              <Text style={styles.textoMenor}>
                Pontos: {regiao.pontos?.length || 0}
              </Text>
              {regiao.pontos?.map((ponto, i) => (
                <Text key={i} style={styles.textoMenor}>
                  {i + 1}: x={ponto.x.toFixed(3)}, y={ponto.y.toFixed(3)}
                </Text>
              ))}
            </View>
          ))
        ) : (
          <Text style={styles.textoMenor}>
            Nenhuma região delimitada com confiança suficiente.
          </Text>
        )}

        <Lista itens={marcacoes?.limitacoes} />
      </Secao>

      <Secao titulo="Plano de cuidados — rascunho para revisão">
        {plano?.sugestoes?.length ? (
          plano.sugestoes.map((sugestao, indice) => (
            <View key={indice} style={styles.bloco}>
              <Text style={styles.rotulo}>{sugestao.titulo}</Text>
              <Text style={styles.texto}>
                {sugestao.justificativa}
              </Text>
              <Lista
                titulo="Dados a confirmar"
                itens={sugestao.dados_a_confirmar}
              />
            </View>
          ))
        ) : (
          <Text style={styles.textoMenor}>
            Nenhum tópico adicional foi proposto.
          </Text>
        )}
        <Lista itens={plano?.observacoes} />
      </Secao>

      <Secao titulo="Pontos para revisão profissional">
        <Lista itens={resposta.pontos_para_revisao_profissional} />
      </Secao>

      <Secao titulo="Limitações gerais">
        <Lista itens={resposta.limitacoes_declaradas} />
      </Secao>
    </View>
  );
}

export default function NovaAvaliacaoScreen() {
  const { pacienteId } = useLocalSearchParams<{
    pacienteId?: string;
  }>();

  const [localizacao, setLocalizacao] = useState('');
  const [comprimento, setComprimento] = useState('');
  const [largura, setLargura] = useState('');
  const [tipoExsudato, setTipoExsudato] = useState('');
  const [odor, setOdor] = useState<'sim' | 'nao' | ''>('');
  const [nivelDor, setNivelDor] = useState('');
  const [queixaPrincipal, setQueixaPrincipal] = useState('');
  const [observacoes, setObservacoes] = useState('');

  const [imagemUri, setImagemUri] = useState<string | null>(null);
  const [provedor, setProvedor] = useState<Provedor>('todos');
  const [resultado, setResultado] = useState<RespostaAPI | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [statusApi, setStatusApi] = useState('');

  const [provedorEscolhido, setProvedorEscolhido] = useState('');
  const [revisao, setRevisao] = useState('');
  const [validado, setValidado] = useState(false);

  const resultados = resultado?.analise_multimodal?.resultados || {};

  const limpar = () => {
    setResultado(null);
    setProvedorEscolhido('');
    setRevisao('');
    setValidado(false);
  };

  const selecionarImagem = async (camera: boolean) => {
    try {
      const permissao = camera
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permissao.granted) {
        Alert.alert('Permissão necessária', 'Autorize o acesso à imagem.');
        return;
      }

      const selecao = camera
        ? await ImagePicker.launchCameraAsync({
            mediaTypes: ['images'],
            quality: 0.8,
            allowsEditing: true,
          })
        : await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ['images'],
            quality: 0.8,
            allowsEditing: true,
          });

      if (!selecao.canceled && selecao.assets[0]?.uri) {
        setImagemUri(selecao.assets[0].uri);
        limpar();
      }
    } catch (erro) {
      Alert.alert(
        'Erro na imagem',
        erro instanceof Error ? erro.message : 'Erro desconhecido',
      );
    }
  };

  const testarConexao = async () => {
    try {
      const resposta = await expoFetch(`${API_URL}/`);
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      setStatusApi('Backend conectado.');
      Alert.alert('Conexão', 'API disponível.');
    } catch (erro) {
      setStatusApi('Falha na conexão.');
      Alert.alert(
        'Conexão',
        erro instanceof Error ? erro.message : 'Falha desconhecida',
      );
    }
  };

  const analisar = async () => {
    if (!localizacao.trim() || !imagemUri) {
      Alert.alert(
        'Dados obrigatórios',
        'Informe a localização e selecione uma fotografia.',
      );
      return;
    }

    if (
      nivelDor.trim() &&
      (!Number.isFinite(Number(nivelDor)) ||
        Number(nivelDor) < 0 ||
        Number(nivelDor) > 10)
    ) {
      Alert.alert('Dor inválida', 'Informe um valor entre 0 e 10.');
      return;
    }

    setCarregando(true);
    limpar();
    setStatusApi('Executando análise multimodal...');

    try {
      const arquivo = new File(imagemUri);

      if (!arquivo.exists) {
        throw new Error('Arquivo da fotografia não encontrado.');
      }

      const formulario = new FormData();
      formulario.append('file', arquivo as unknown as Blob);
      formulario.append('localizacao', localizacao.trim());
      formulario.append('comprimento', comprimento.trim());
      formulario.append('largura', largura.trim());
      formulario.append('tipoExsudato', tipoExsudato.trim());
      formulario.append('odor', odor);
      formulario.append('nivelDor', nivelDor.trim());
      formulario.append('queixaPrincipal', queixaPrincipal.trim());
      formulario.append('observacoes', observacoes.trim());
      formulario.append('provedor', provedor);

      const resposta = await expoFetch(
        `${API_URL}/preparar-analise-multimodal`,
        {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: formulario,
        },
      );

      const dados = await resposta.json();

      if (!resposta.ok) {
        const detalhe =
          typeof dados.detail === 'string'
            ? dados.detail
            : `Erro HTTP ${resposta.status}`;
        throw new Error(detalhe);
      }

      const analise = dados as RespostaAPI;

      // Mesmo quando todos os provedores falham, preserva
      // os erros individuais para apresentação na tela.
      setResultado(analise);

      const lista = Object.values(
        analise.analise_multimodal?.resultados || {},
      );

      const sucessos = lista.filter((item) => item.sucesso).length;

      setStatusApi(
        `${sucessos} de ${lista.length} provedores concluíram a análise.`,
      );
    } catch (erro) {
      setStatusApi('Erro ao executar a análise.');
      Alert.alert(
        'Erro',
        erro instanceof Error ? erro.message : 'Falha desconhecida.',
      );
    } finally {
      setCarregando(false);
    }
  };

  const selecionarProvedor = (nome: string) => {
    setProvedorEscolhido(nome);
    setValidado(false);
    setRevisao(
      resultados[nome]?.resposta?.conteudo_descricao || '',
    );
  };

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.titulo}>Nova avaliação</Text>
      <Text style={styles.textoMenor}>
        Paciente ID: {pacienteId || 'Não selecionado'}
      </Text>
      <Text style={styles.textoMenor}>
        O cadastro do paciente ainda não está integrado ao backend.
      </Text>

      <TouchableOpacity style={styles.botaoCinza} onPress={testarConexao}>
        <Text style={styles.botaoTexto}>Testar conexão</Text>
      </TouchableOpacity>

      {statusApi ? (
        <Text style={styles.status}>{statusApi}</Text>
      ) : null}

      <Text style={styles.titulo}>1. Dados clínicos</Text>

      <Campo
        titulo="Localização anatômica *"
        valor={localizacao}
        alterar={setLocalizacao}
      />
      <Campo
        titulo="Comprimento (cm)"
        valor={comprimento}
        alterar={setComprimento}
      />
      <Campo
        titulo="Largura (cm)"
        valor={largura}
        alterar={setLargura}
      />
      <Campo
        titulo="Tipo de exsudato"
        valor={tipoExsudato}
        alterar={setTipoExsudato}
      />

      <Text style={styles.rotulo}>Odor informado pelo profissional</Text>
      <View style={styles.linha}>
        {[
          { valor: '', titulo: 'Não avaliado' },
          { valor: 'sim', titulo: 'Presente' },
          { valor: 'nao', titulo: 'Ausente' },
        ].map((opcao) => (
          <TouchableOpacity
            key={opcao.titulo}
            style={[
              styles.opcao,
              odor === opcao.valor && styles.opcaoAtiva,
            ]}
            onPress={() =>
              setOdor(opcao.valor as 'sim' | 'nao' | '')
            }
          >
            <Text style={styles.textoMenor}>{opcao.titulo}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Campo
        titulo="Nível de dor (0 a 10)"
        valor={nivelDor}
        alterar={setNivelDor}
      />
      <Campo
        titulo="Queixa principal"
        valor={queixaPrincipal}
        alterar={setQueixaPrincipal}
        multiline
      />
      <Campo
        titulo="Observações clínicas"
        valor={observacoes}
        alterar={setObservacoes}
        multiline
      />

      <Text style={styles.titulo}>2. Fotografia</Text>

      {imagemUri ? (
        <Image
          source={{ uri: imagemUri }}
          style={styles.imagem}
          resizeMode="contain"
        />
      ) : null}

      <TouchableOpacity
        style={styles.botaoCinza}
        onPress={() => selecionarImagem(true)}
        disabled={carregando}
      >
        <Text style={styles.botaoTexto}>Tirar fotografia</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.botaoCinza}
        onPress={() => selecionarImagem(false)}
        disabled={carregando}
      >
        <Text style={styles.botaoTexto}>Selecionar da galeria</Text>
      </TouchableOpacity>

      <Text style={styles.titulo}>3. Inteligências artificiais</Text>

      {PROVEDORES.map((item) => (
        <TouchableOpacity
          key={item.valor}
          style={[
            styles.opcao,
            provedor === item.valor && styles.opcaoAtiva,
          ]}
          onPress={() => setProvedor(item.valor)}
          disabled={carregando}
        >
          <Text style={styles.texto}>{item.titulo}</Text>
        </TouchableOpacity>
      ))}

      <TouchableOpacity
        style={styles.botao}
        onPress={analisar}
        disabled={carregando}
      >
        {carregando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.botaoTexto}>
            Executar análise multimodal
          </Text>
        )}
      </TouchableOpacity>

      {resultado ? (
        <>
          <Text style={styles.titulo}>4. Resultados</Text>

          <View style={styles.card}>
            <Text style={styles.texto}>{resultado.mensagem}</Text>
            <Text style={styles.textoMenor}>
              {resultado.analise_multimodal?.data_processamento}
            </Text>

            {resultado.analise_tecnica ? (
              <Text style={styles.textoMenor}>
                Brilho: {resultado.analise_tecnica.brilho_medio ?? '—'}
                {' | '}
                Contraste:{' '}
                {resultado.analise_tecnica.contraste_global ?? '—'}
              </Text>
            ) : null}
          </View>

          {resultado.imagem_processada_url ? (
            <View style={styles.card}>
              <Text style={styles.subtitulo}>Imagem processada</Text>
              <Image
                source={{
                  uri:
                    API_URL +
                    (resultado.imagem_processada_url.startsWith('/')
                      ? ''
                      : '/') +
                    resultado.imagem_processada_url,
                }}
                style={styles.imagem}
                resizeMode="contain"
              />
            </View>
          ) : null}

          <Text style={styles.titulo}>Comparação das análises</Text>

          {Object.entries(resultados).map(([nome, item]) => (
            <View key={nome} style={styles.card}>
              <Text style={styles.subtitulo}>
                {nome.toUpperCase()} —{' '}
                {item.sucesso ? 'SUCESSO' : 'FALHA'}
              </Text>

              <Text style={styles.textoMenor}>
                Tempo: {item.tempo_execucao_segundos?.toFixed(2) || '—'}s
              </Text>

              {item.sucesso && item.resposta ? (
                <>
                  <ResultadoEstruturado resposta={item.resposta} />

                  <TouchableOpacity
                    style={styles.botao}
                    onPress={() => selecionarProvedor(nome)}
                  >
                    <Text style={styles.botaoTexto}>
                      Selecionar para revisão
                    </Text>
                  </TouchableOpacity>
                </>
              ) : (
                <Text style={styles.erro}>
                  {item.mensagem_erro || 'Falha sem detalhes.'}
                </Text>
              )}
            </View>
          ))}

          {provedorEscolhido ? (
            <View style={styles.card}>
              <Text style={styles.titulo}>
                5. Revisão profissional
              </Text>
              <Text style={styles.texto}>
                Análise selecionada: {provedorEscolhido.toUpperCase()}
              </Text>
              <Text style={styles.textoMenor}>
                Revise e corrija a descrição antes de confirmar.
                Esta revisão é local e ainda não é salva no servidor.
              </Text>

              <TextInput
                style={[styles.input, styles.revisao]}
                value={revisao}
                onChangeText={(texto) => {
                  setRevisao(texto);
                  setValidado(false);
                }}
                multiline
                textAlignVertical="top"
              />

              <TouchableOpacity
                style={styles.botao}
                onPress={() => {
                  if (!revisao.trim()) {
                    Alert.alert(
                      'Revisão necessária',
                      'Preencha a avaliação revisada.',
                    );
                    return;
                  }
                  setValidado(true);
                  Alert.alert(
                    'Revisão registrada nesta sessão',
                    'A avaliação foi marcada como revisada localmente. ' +
                      'Ainda não foi persistida em prontuário.',
                  );
                }}
              >
                <Text style={styles.botaoTexto}>
                  Confirmar revisão local
                </Text>
              </TouchableOpacity>

              {validado ? (
                <Text style={styles.sucesso}>
                  Revisão confirmada nesta sessão.
                </Text>
              ) : null}
            </View>
          ) : null}

          <View style={styles.card}>
            <Text style={styles.subtitulo}>
              Validação profissional obrigatória
            </Text>
            <Text style={styles.texto}>
              As respostas automatizadas podem conter erros.
              As classificações de tecidos, os percentuais,
              as coordenadas e os tópicos de cuidado não
              substituem a avaliação presencial do enfermeiro.
            </Text>
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 18,
    paddingBottom: 60,
    backgroundColor: '#f8fafc',
  },
  titulo: {
    fontSize: 19,
    fontWeight: 'bold',
    color: '#0056b3',
    marginTop: 18,
    marginBottom: 12,
  },
  subtitulo: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 8,
  },
  rotulo: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#334155',
    marginBottom: 6,
  },
  texto: {
    fontSize: 13,
    color: '#334155',
    lineHeight: 20,
    marginBottom: 5,
  },
  textoMenor: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 18,
    marginBottom: 5,
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    marginBottom: 12,
    color: '#1e293b',
  },
  multiline: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  revisao: {
    minHeight: 180,
  },
  linha: {
    flexDirection: 'row',
    gap: 7,
    marginBottom: 12,
  },
  opcao: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#cbd5e1',
    backgroundColor: '#fff',
    marginBottom: 7,
  },
  opcaoAtiva: {
    borderColor: '#0056b3',
    backgroundColor: '#dbeafe',
  },
  botao: {
    backgroundColor: '#0056b3',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginVertical: 10,
  },
  botaoCinza: {
    backgroundColor: '#475569',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginVertical: 5,
  },
  botaoTexto: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  card: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    padding: 14,
    marginBottom: 14,
  },
  secaoInterna: {
    marginTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    paddingTop: 10,
  },
  grupo: {
    marginBottom: 10,
  },
  bloco: {
    padding: 10,
    backgroundColor: '#f8fafc',
    borderRadius: 8,
    marginBottom: 8,
  },
  imagem: {
    width: '100%',
    height: 250,
    backgroundColor: '#e2e8f0',
    borderRadius: 8,
    marginVertical: 10,
  },
  status: {
    color: '#475569',
    marginVertical: 8,
  },
  erro: {
    color: '#b91c1c',
    fontSize: 13,
    marginTop: 10,
  },
  sucesso: {
    color: '#15803d',
    fontWeight: 'bold',
    marginTop: 8,
  },
});
