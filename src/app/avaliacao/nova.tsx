import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Switch,
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

type Provedor = 'gemini' | 'openai' | 'kimi' | 'todos';

type ResultadoProvedor = {
  provedor?: string;
  modo?: string;
  sucesso?: boolean;
  tempo_execucao_segundos?: number;
  mensagem_erro?: string | null;
  resposta?: {
    status_resposta?: string;
    conteudo_descricao?: string;
    limitacoes_declaradas?: string[];
  };
};

type RespostaAnalise = {
  sucesso?: boolean;
  mensagem?: string;
  provedor_selecionado?: string;
  provedores_solicitados?: string[];
  imagem_original_url?: string;
  imagem_processada_url?: string;
  dimensoes_originais?: {
    largura_pixels?: number;
    altura_pixels?: number;
    canais?: number;
    total_pixels?: number;
  };
  dimensoes_processadas?: {
    largura_pixels?: number;
    altura_pixels?: number;
  };
  analise_tecnica?: {
    brilho_medio?: number;
    contraste_global?: number;
  };
  dados_clinicos?: Record<string, unknown>;
  analise_multimodal?: {
    sucesso_geral?: boolean;
    data_processamento?: string;
    resultados?: Record<string, ResultadoProvedor>;
  };
};

const PROVEDORES: { valor: Provedor; titulo: string }[] = [
  { valor: 'todos', titulo: 'Todas as IAs' },
  { valor: 'gemini', titulo: 'Gemini' },
  { valor: 'openai', titulo: 'OpenAI' },
  { valor: 'kimi', titulo: 'Kimi' },
];

export default function NovaAvaliacaoScreen() {
  const { pacienteId } = useLocalSearchParams<{
    pacienteId?: string;
  }>();

  // Identificação do paciente.
  // Posteriormente, podemos buscar esses dados no cadastro real.
  const nomePacienteMock = 'Maria Silva Santos (Fictício)';

  // Dados clínicos.
  const [localizacao, setLocalizacao] = useState('');
  const [comprimento, setComprimento] = useState('');
  const [largura, setLargura] = useState('');
  const [tipoExsudato, setTipoExsudato] = useState('');
  const [odor, setOdor] = useState(false);
  const [nivelDor, setNivelDor] = useState('');
  const [queixaPrincipal, setQueixaPrincipal] = useState('');
  const [observacoes, setObservacoes] = useState('');

  // Fotografia.
  const [imagemUri, setImagemUri] = useState<string | null>(null);

  // Provedor selecionado.
  const [provedor, setProvedor] = useState<Provedor>('todos');

  // Resposta da API.
  const [resultado, setResultado] = useState<RespostaAnalise | null>(null);
  const [imagemProcessadaUrl, setImagemProcessadaUrl] =
    useState<string | null>(null);

  // Estados de carregamento.
  const [carregando, setCarregando] = useState(false);
  const [testandoConexao, setTestandoConexao] = useState(false);
  const [statusApi, setStatusApi] = useState<string | null>(null);

  // ============================================================
  // TESTAR CONEXÃO COM O BACK-END
  // ============================================================

  const handleTestarConexao = async () => {
    setTestandoConexao(true);
    setStatusApi('Testando conexão com o back-end...');

    try {
      const response = await expoFetch(`${API_URL}/`, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`O servidor respondeu com HTTP ${response.status}.`);
      }

      const data = await response.json();

      setStatusApi('Conexão com o back-end estabelecida.');

      Alert.alert(
        'Conexão estabelecida',
        data.message || data.status || 'O servidor está respondendo.',
      );
    } catch (error: unknown) {
      const mensagem =
        error instanceof Error ? error.message : 'Erro desconhecido.';

      setStatusApi('Não foi possível conectar ao back-end.');

      Alert.alert(
        'Falha na conexão',
        `${mensagem}\n\nVerifique se o Python está executando e se o celular consegue acessar o endereço configurado em API_URL.`,
      );
    } finally {
      setTestandoConexao(false);
    }
  };

  // ============================================================
  // LIMPAR RESULTADOS ANTERIORES
  // ============================================================

  const limparResultado = () => {
    setResultado(null);
    setImagemProcessadaUrl(null);
    setStatusApi(null);
  };

  // ============================================================
  // TIRAR FOTOGRAFIA
  // ============================================================

  const handleTirarFoto = async () => {
    try {
      const permissao =
        await ImagePicker.requestCameraPermissionsAsync();

      if (!permissao.granted) {
        Alert.alert(
          'Permissão necessária',
          'Permita o acesso à câmera para fotografar a lesão.',
        );
        return;
      }

      const selecao = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        quality: 0.8,
      });

      if (!selecao.canceled && selecao.assets[0]?.uri) {
        setImagemUri(selecao.assets[0].uri);
        limparResultado();
      }
    } catch (error: unknown) {
      const mensagem =
        error instanceof Error ? error.message : 'Erro desconhecido.';

      Alert.alert('Erro ao abrir a câmera', mensagem);
    }
  };

  // ============================================================
  // SELECIONAR FOTOGRAFIA DA GALERIA
  // ============================================================

  const handleEscolherGaleria = async () => {
    try {
      const permissao =
        await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permissao.granted) {
        Alert.alert(
          'Permissão necessária',
          'Permita o acesso à galeria para selecionar uma fotografia.',
        );
        return;
      }

      const selecao = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        quality: 0.8,
      });

      if (!selecao.canceled && selecao.assets[0]?.uri) {
        setImagemUri(selecao.assets[0].uri);
        limparResultado();
      }
    } catch (error: unknown) {
      const mensagem =
        error instanceof Error ? error.message : 'Erro desconhecido.';

      Alert.alert('Erro ao abrir a galeria', mensagem);
    }
  };

  // ============================================================
  // ENVIAR FOTOGRAFIA E DADOS PARA ANÁLISE MULTIMODAL
  // ============================================================

  const handleEnviarParaAnalise = async () => {
    if (!localizacao.trim()) {
      Alert.alert(
        'Campo obrigatório',
        'Informe a localização anatômica da lesão.',
      );
      return;
    }

    if (!imagemUri) {
      Alert.alert(
        'Fotografia obrigatória',
        'Tire uma fotografia ou selecione uma imagem da galeria.',
      );
      return;
    }

    const dorNumerica = Number(nivelDor);

    if (
      nivelDor.trim() !== '' &&
      (!Number.isFinite(dorNumerica) ||
        dorNumerica < 0 ||
        dorNumerica > 10)
    ) {
      Alert.alert(
        'Nível de dor inválido',
        'Informe um valor numérico entre 0 e 10.',
      );
      return;
    }

    setCarregando(true);
    limparResultado();
    setStatusApi(
      provedor === 'todos'
        ? 'Enviando dados e consultando os três provedores. Isso pode levar alguns minutos...'
        : `Enviando dados para análise pelo ${provedor}...`,
    );

    try {
      // 1. Obter o arquivo de imagem selecionado.
      const arquivoImagem = new File(imagemUri);

      if (!arquivoImagem.exists) {
        throw new Error(
          'A imagem selecionada não foi encontrada no dispositivo.',
        );
      }

      // 2. Criar formulário multipart.
      const formData = new FormData();

      formData.append('file', arquivoImagem as unknown as Blob);

      // 3. Adicionar os dados clínicos.
      formData.append('localizacao', localizacao.trim());
      formData.append('comprimento', comprimento.trim());
      formData.append('largura', largura.trim());
      formData.append('tipoExsudato', tipoExsudato.trim());
      formData.append('odor', String(odor));
      formData.append('nivelDor', nivelDor.trim());
      formData.append('queixaPrincipal', queixaPrincipal.trim());
      formData.append('observacoes', observacoes.trim());

      // 4. Selecionar o provedor ou executar todos.
      formData.append('provedor', provedor);

      // Não definir Content-Type manualmente.
      // O Expo deve montar o multipart boundary.
      const response = await expoFetch(
        `${API_URL}/preparar-analise-multimodal`,
        {
          method: 'POST',
          headers: {
            Accept: 'application/json',
          },
          body: formData,
        },
      );

      // 5. Interpretar possíveis erros da API.
      if (!response.ok) {
        let mensagemErro = `Erro HTTP ${response.status}.`;

        try {
          const erro = await response.json();

          if (typeof erro.detail === 'string') {
            mensagemErro = erro.detail;
          } else if (Array.isArray(erro.detail)) {
            mensagemErro = erro.detail
              .map((item: { msg?: string }) => item.msg || 'Campo inválido')
              .join('\n');
          } else if (erro.mensagem) {
            mensagemErro = erro.mensagem;
          }
        } catch {
          // Mantém a mensagem HTTP caso a resposta não seja JSON.
        }

        throw new Error(mensagemErro);
      }

      // 6. Receber o resultado multimodal.
      const data = (await response.json()) as RespostaAnalise;

      if (!data.sucesso) {
        throw new Error(
          data.mensagem || 'O back-end não conseguiu concluir a análise.',
        );
      }

      // 7. Preparar URL da imagem processada.
      if (data.imagem_processada_url) {
        const caminho = data.imagem_processada_url.startsWith('/')
          ? data.imagem_processada_url
          : `/${data.imagem_processada_url}`;

        setImagemProcessadaUrl(`${API_URL}${caminho}`);
      }

      setResultado(data);

      const resultados = data.analise_multimodal?.resultados || {};
      const provedores = Object.values(resultados);
      const quantidadeSucesso = provedores.filter(
        (item) => item.sucesso,
      ).length;

      const quantidadeFalha = provedores.length - quantidadeSucesso;

      setStatusApi(
        `Análise concluída: ${quantidadeSucesso} provedor(es) com sucesso${
          quantidadeFalha > 0
            ? ` e ${quantidadeFalha} com falha`
            : ''
        }.`,
      );
    } catch (error: unknown) {
      const mensagem =
        error instanceof Error ? error.message : 'Erro desconhecido.';

      setStatusApi('Falha ao realizar a análise multimodal.');

      Alert.alert(
        'Erro na análise',
        `${mensagem}\n\nVerifique a conexão com o back-end e tente novamente.`,
      );
    } finally {
      setCarregando(false);
    }
  };

  // ============================================================
  // EXIBIR RESULTADO DE CADA PROVEDOR
  // ============================================================

  const renderResultadoProvedor = (
    nome: string,
    item: ResultadoProvedor,
  ) => {
    const sucesso = item.sucesso === true;
    const resposta = item.resposta;

    return (
      <View
        key={nome}
        style={[
          styles.cardProvedor,
          sucesso ? styles.cardProvedorSucesso : styles.cardProvedorErro,
        ]}
      >
        <View style={styles.provedorHeader}>
          <Text style={styles.provedorTitulo}>
            {nome.toUpperCase()}
          </Text>

          <Text
            style={[
              styles.provedorStatus,
              { color: sucesso ? '#15803d' : '#b91c1c' },
            ]}
          >
            {sucesso ? 'SUCESSO' : 'FALHA'}
          </Text>
        </View>

        {item.modo ? (
          <Text style={styles.textoSecundario}>
            Modo: {item.modo}
          </Text>
        ) : null}

        {typeof item.tempo_execucao_segundos === 'number' ? (
          <Text style={styles.textoSecundario}>
            Tempo de resposta:{' '}
            {item.tempo_execucao_segundos.toFixed(2)} segundos
          </Text>
        ) : null}

        {sucesso && resposta?.conteudo_descricao ? (
          <>
            <Text style={styles.subtituloCard}>
              Descrição da análise
            </Text>

            <Text style={styles.textoResultado}>
              {resposta.conteudo_descricao}
            </Text>

            {resposta.limitacoes_declaradas &&
              resposta.limitacoes_declaradas.length > 0 && (
                <>
                  <Text style={styles.subtituloCard}>
                    Limitações declaradas
                  </Text>

                  {resposta.limitacoes_declaradas.map(
                    (limitacao, indice) => (
                      <Text
                        key={`${nome}-limitacao-${indice}`}
                        style={styles.itemLimitacao}
                      >
                        {'\u2022'} {limitacao}
                      </Text>
                    ),
                  )}
                </>
              )}
          </>
        ) : (
          <Text style={styles.textoErro}>
            {item.mensagem_erro ||
              'O provedor não retornou uma análise válida.'}
          </Text>
        )}
      </View>
    );
  };

  // ============================================================
  // INTERFACE
  // ============================================================

  const resultados = resultado?.analise_multimodal?.resultados || {};

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      {/* PACIENTE */}

      <View style={styles.cardPaciente}>
        <Text style={styles.labelHeader}>
          Paciente selecionado
        </Text>

        <Text style={styles.nomePaciente}>
          {nomePacienteMock}
        </Text>

        <Text style={styles.idPaciente}>
          ID: {pacienteId || '1'}
        </Text>

        <Text style={styles.avisoFicticio}>
          Identificação demonstrativa: os dados do paciente ainda não
          são carregados de um banco de dados.
        </Text>
      </View>

      {/* CONEXÃO */}

      <View style={styles.cardConexao}>
        <Text style={styles.tituloCard}>
          Conexão com o back-end
        </Text>

        <Text style={styles.urlConexao}>
          {API_URL}
        </Text>

        {statusApi ? (
          <Text style={styles.statusApi}>{statusApi}</Text>
        ) : null}

        <TouchableOpacity
          style={[
            styles.btnConexao,
            testandoConexao && styles.btnDesabilitado,
          ]}
          onPress={handleTestarConexao}
          disabled={testandoConexao || carregando}
        >
          {testandoConexao ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.textoBotao}>
              Testar conexão
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {/* DADOS CLÍNICOS */}

      <Text style={styles.tituloSecao}>
        1. Dados clínicos da lesão
      </Text>

      <Text style={styles.label}>
        Localização anatômica *
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Ex.: Calcanhar esquerdo"
        value={localizacao}
        onChangeText={setLocalizacao}
      />

      <View style={styles.linha}>
        <View style={styles.coluna}>
          <Text style={styles.label}>Comprimento (cm)</Text>
          <TextInput
            style={styles.input}
            placeholder="Ex.: 7"
            keyboardType="decimal-pad"
            value={comprimento}
            onChangeText={setComprimento}
          />
        </View>

        <View style={styles.coluna}>
          <Text style={styles.label}>Largura (cm)</Text>
          <TextInput
            style={styles.input}
            placeholder="Ex.: 5"
            keyboardType="decimal-pad"
            value={largura}
            onChangeText={setLargura}
          />
        </View>
      </View>

      <Text style={styles.label}>Tipo de exsudato</Text>

      <TextInput
        style={styles.input}
        placeholder="Ex.: Seroso, purulento ou não informado"
        value={tipoExsudato}
        onChangeText={setTipoExsudato}
      />

      <View style={styles.linhaSwitch}>
        <View style={styles.coluna}>
          <Text style={styles.label}>Presença de odor</Text>
          <Text style={styles.textoSecundario}>
            Ative se o profissional observar odor.
          </Text>
        </View>

        <Switch
          value={odor}
          onValueChange={setOdor}
          trackColor={{ false: '#cbd5e1', true: '#93c5fd' }}
          thumbColor={odor ? '#0056b3' : '#f4f4f5'}
        />
      </View>

      <Text style={styles.label}>Nível de dor (0 a 10)</Text>

      <TextInput
        style={styles.input}
        placeholder="Deixe vazio se não foi informado"
        keyboardType="numeric"
        value={nivelDor}
        onChangeText={setNivelDor}
      />

      <Text style={styles.label}>Queixa principal</Text>

      <TextInput
        style={[styles.input, styles.inputMultiline]}
        placeholder="Descreva a queixa relatada pelo paciente."
        multiline
        value={queixaPrincipal}
        onChangeText={setQueixaPrincipal}
      />

      <Text style={styles.label}>Observações clínicas</Text>

      <TextInput
        style={[styles.input, styles.inputMultiline]}
        placeholder="Outras informações relevantes."
        multiline
        value={observacoes}
        onChangeText={setObservacoes}
      />

      {/* FOTOGRAFIA */}

      <Text style={styles.tituloSecao}>
        2. Registro fotográfico
      </Text>

      {imagemUri ? (
        <View style={styles.cardImagem}>
          <Text style={styles.label}>Fotografia selecionada</Text>

          <Image
            source={{ uri: imagemUri }}
            style={styles.imagemPreview}
          />

          <TouchableOpacity
            style={styles.btnRemover}
            onPress={() => {
              setImagemUri(null);
              limparResultado();
            }}
            disabled={carregando}
          >
            <Text style={styles.textoBotao}>
              Remover fotografia
            </Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.cardSelecionarImagem}>
          <Text style={styles.textoSecundario}>
            Registre a lesão ou selecione uma fotografia existente.
          </Text>

          <TouchableOpacity
            style={styles.btnPrincipal}
            onPress={handleTirarFoto}
            disabled={carregando}
          >
            <Text style={styles.textoBotao}>
              Tirar fotografia
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.btnSecundario}
            onPress={handleEscolherGaleria}
            disabled={carregando}
          >
            <Text style={styles.textoBotao}>
              Selecionar da galeria
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* SELEÇÃO DE IA */}

      <Text style={styles.tituloSecao}>
        3. Provedor de inteligência artificial
      </Text>

      <Text style={styles.textoSecundario}>
        Escolha uma IA ou execute as três para comparar as respostas.
        A execução conjunta pode demorar mais e consumir créditos das APIs.
      </Text>

      <View style={styles.listaProvedores}>
        {PROVEDORES.map((item) => {
          const selecionado = provedor === item.valor;

          return (
            <TouchableOpacity
              key={item.valor}
              style={[
                styles.opcaoProvedor,
                selecionado && styles.opcaoProvedorSelecionada,
              ]}
              onPress={() => {
                setProvedor(item.valor);
                limparResultado();
              }}
              disabled={carregando}
            >
              <Text
                style={[
                  styles.textoOpcaoProvedor,
                  selecionado && styles.textoOpcaoProvedorSelecionada,
                ]}
              >
                {selecionado ? '✓ ' : ''}
                {item.titulo}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* EXECUTAR ANÁLISE */}

      <TouchableOpacity
        style={[
          styles.btnPrincipal,
          carregando && styles.btnDesabilitado,
        ]}
        onPress={handleEnviarParaAnalise}
        disabled={carregando || testandoConexao}
      >
        {carregando ? (
          <View style={styles.carregandoLinha}>
            <ActivityIndicator color="#fff" />
            <Text style={styles.textoBotaoCarregando}>
              Processando análise...
            </Text>
          </View>
        ) : (
          <Text style={styles.textoBotao}>
            Executar análise multimodal
          </Text>
        )}
      </TouchableOpacity>

      {carregando ? (
        <Text style={styles.avisoEspera}>
          Aguarde a resposta do back-end. Se selecionar todas as IAs,
          a análise poderá levar alguns minutos. Mantenha o aplicativo
          aberto enquanto o processamento acontece.
        </Text>
      ) : null}

      {/* RESULTADOS */}

      {resultado ? (
        <View style={styles.areaResultados}>
          <Text style={styles.tituloSecao}>
            4. Resultados da análise
          </Text>

          <View style={styles.cardResumo}>
            <Text style={styles.tituloCard}>
              Resumo do processamento
            </Text>

            <Text style={styles.textoResultado}>
              {resultado.mensagem ||
                'O back-end retornou uma resposta.'}
            </Text>

            <Text style={styles.textoSecundario}>
              Provedor selecionado: {resultado.provedor_selecionado || provedor}
            </Text>

            {resultado.analise_multimodal?.data_processamento ? (
              <Text style={styles.textoSecundario}>
                Data do processamento:{' '}
                {resultado.analise_multimodal.data_processamento}
              </Text>
            ) : null}
          </View>

          {/* IMAGEM PROCESSADA */}

          {imagemProcessadaUrl ? (
            <View style={styles.cardResultado}>
              <Text style={styles.subtituloCard}>
                Imagem processada pelo OpenCV
              </Text>

              <Image
                source={{ uri: imagemProcessadaUrl }}
                style={styles.imagemProcessada}
              />

              <Text style={styles.textoSecundario}>
                A imagem processada é um resultado técnico do sistema
                e não representa, por si só, uma avaliação clínica.
              </Text>
            </View>
          ) : null}

          {/* INFORMAÇÕES TÉCNICAS */}

          {resultado.dimensoes_originais ||
          resultado.analise_tecnica ? (
            <View style={styles.cardResultado}>
              <Text style={styles.subtituloCard}>
                Informações técnicas da imagem
              </Text>

              {resultado.dimensoes_originais ? (
                <>
                  <Text style={styles.textoResultado}>
                    Dimensões originais:{' '}
                    {resultado.dimensoes_originais.largura_pixels ?? '—'}
                    {' × '}
                    {resultado.dimensoes_originais.altura_pixels ?? '—'}
                    {' pixels'}
                  </Text>

                  <Text style={styles.textoResultado}>
                    Canais de imagem:{' '}
                    {resultado.dimensoes_originais.canais ?? '—'}
                  </Text>

                  <Text style={styles.textoResultado}>
                    Total de pixels:{' '}
                    {resultado.dimensoes_originais.total_pixels?.toLocaleString(
                      'pt-BR',
                    ) ?? '—'}
                  </Text>
                </>
              ) : null}

              {resultado.analise_tecnica ? (
                <>
                  <Text style={styles.textoResultado}>
                    Brilho médio:{' '}
                    {resultado.analise_tecnica.brilho_medio ?? '—'}
                    {' / 255'}
                  </Text>

                  <Text style={styles.textoResultado}>
                    Contraste global:{' '}
                    {resultado.analise_tecnica.contraste_global ?? '—'}
                  </Text>
                </>
              ) : null}
            </View>
          ) : null}

          {/* RESPOSTAS DOS PROVEDORES */}

          <Text style={styles.subtituloResultados}>
            Comparação das análises
          </Text>

          {Object.keys(resultados).length > 0 ? (
            Object.entries(resultados).map(([nome, item]) =>
              renderResultadoProvedor(nome, item),
            )
          ) : (
            <View style={styles.cardResultado}>
              <Text style={styles.textoResultado}>
                A API não retornou resultados individuais dos provedores.
              </Text>
            </View>
          )}

          {/* AVISO CLÍNICO */}

          <View style={styles.cardAviso}>
            <Text style={styles.tituloAviso}>
              Atenção: validação profissional
            </Text>

            <Text style={styles.textoAviso}>
              As respostas das inteligências artificiais são descrições
              automatizadas e podem divergir entre si. Não constituem
              diagnóstico e não substituem a avaliação presencial.
              O profissional de saúde deve revisar as informações e
              registrar sua própria avaliação antes de utilizá-las
              na assistência ao paciente.
            </Text>
          </View>
        </View>
      ) : null}
    </ScrollView>
  );
}

// ============================================================
// ESTILOS
// ============================================================

const styles = StyleSheet.create({
  container: {
    padding: 18,
    paddingBottom: 40,
    backgroundColor: '#f8fafc',
    flexGrow: 1,
  },

  cardPaciente: {
    backgroundColor: '#eef6ff',
    padding: 15,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#0056b3',
    marginBottom: 16,
  },

  labelHeader: {
    fontSize: 12,
    color: '#64748b',
    textTransform: 'uppercase',
    fontWeight: 'bold',
  },

  nomePaciente: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#0056b3',
    marginTop: 4,
  },

  idPaciente: {
    fontSize: 13,
    color: '#475569',
    marginTop: 3,
  },

  avisoFicticio: {
    fontSize: 12,
    color: '#92400e',
    marginTop: 8,
    lineHeight: 17,
  },

  cardConexao: {
    backgroundColor: '#f0fdf4',
    borderWidth: 1,
    borderColor: '#bbf7d0',
    padding: 14,
    borderRadius: 10,
    marginBottom: 20,
  },

  tituloCard: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#166534',
    marginBottom: 6,
  },

  urlConexao: {
    fontSize: 12,
    color: '#15803d',
    marginBottom: 8,
  },

  statusApi: {
    fontSize: 13,
    color: '#334155',
    marginBottom: 8,
    lineHeight: 19,
  },

  tituloSecao: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#0056b3',
    marginTop: 10,
    marginBottom: 14,
  },

  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 6,
  },

  input: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    color: '#1e293b',
    backgroundColor: '#fff',
    marginBottom: 14,
  },

  inputMultiline: {
    minHeight: 85,
    textAlignVertical: 'top',
  },

  linha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },

  coluna: {
    flex: 1,
  },

  linhaSwitch: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },

  textoSecundario: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 18,
    marginBottom: 6,
  },

  cardSelecionarImagem: {
    padding: 16,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 10,
    marginBottom: 18,
  },

  cardImagem: {
    padding: 12,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    marginBottom: 18,
  },

  imagemPreview: {
    width: '100%',
    height: 240,
    borderRadius: 8,
    resizeMode: 'contain',
    backgroundColor: '#f1f5f9',
    marginVertical: 8,
  },

  imagemProcessada: {
    width: '100%',
    height: 240,
    borderRadius: 8,
    resizeMode: 'contain',
    backgroundColor: '#f1f5f9',
    marginVertical: 8,
  },

  btnPrincipal: {
    backgroundColor: '#0056b3',
    paddingVertical: 14,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
    marginBottom: 10,
  },

  btnSecundario: {
    backgroundColor: '#475569',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },

  btnConexao: {
    backgroundColor: '#15803d',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
  },

  btnRemover: {
    backgroundColor: '#b91c1c',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },

  btnDesabilitado: {
    backgroundColor: '#94a3b8',
  },

  textoBotao: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },

  carregandoLinha: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },

  textoBotaoCarregando: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
    marginLeft: 8,
  },

  listaProvedores: {
    marginBottom: 14,
    gap: 8,
  },

  opcaoProvedor: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 13,
  },

  opcaoProvedorSelecionada: {
    borderColor: '#0056b3',
    backgroundColor: '#eff6ff',
  },

  textoOpcaoProvedor: {
    fontSize: 14,
    color: '#334155',
    fontWeight: '500',
  },

  textoOpcaoProvedorSelecionada: {
    color: '#0056b3',
    fontWeight: 'bold',
  },

  avisoEspera: {
    fontSize: 12,
    color: '#92400e',
    backgroundColor: '#fffbeb',
    padding: 12,
    borderRadius: 8,
    lineHeight: 18,
    marginBottom: 14,
  },

  areaResultados: {
    marginTop: 18,
  },

  cardResumo: {
    backgroundColor: '#eff6ff',
    borderWidth: 1,
    borderColor: '#bfdbfe',
    padding: 14,
    borderRadius: 10,
    marginBottom: 14,
  },

  cardResultado: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 14,
    borderRadius: 10,
    marginBottom: 14,
  },

  subtituloResultados: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#1e293b',
    marginTop: 12,
    marginBottom: 12,
  },

  cardProvedor: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderRadius: 10,
    padding: 14,
    marginBottom: 14,
  },

  cardProvedorSucesso: {
    borderColor: '#bbf7d0',
  },

  cardProvedorErro: {
    borderColor: '#fecaca',
  },

  provedorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },

  provedorTitulo: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1e293b',
  },

  provedorStatus: {
    fontSize: 11,
    fontWeight: 'bold',
  },

  subtituloCard: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#0056b3',
    marginTop: 10,
    marginBottom: 6,
  },

  textoResultado: {
    fontSize: 13,
    color: '#334155',
    lineHeight: 20,
    marginBottom: 7,
  },

  itemLimitacao: {
    fontSize: 12,
    color: '#475569',
    lineHeight: 19,
    marginBottom: 5,
  },

  textoErro: {
    fontSize: 13,
    color: '#b91c1c',
    lineHeight: 19,
    marginTop: 8,
  },

  cardAviso: {
    backgroundColor: '#fffbeb',
    borderWidth: 1,
    borderColor: '#fcd34d',
    padding: 14,
    borderRadius: 10,
    marginTop: 4,
  },

  tituloAviso: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#92400e',
    marginBottom: 8,
  },

  textoAviso: {
    fontSize: 12,
    color: '#78350f',
    lineHeight: 19,
  },
});