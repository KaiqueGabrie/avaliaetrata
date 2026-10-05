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

import * as ImagePicker from 'expo-image-picker';
import { useLocalSearchParams } from 'expo-router';

import { File } from 'expo-file-system';
import { fetch as expoFetch } from 'expo/fetch';

import { API_URL } from '../../config/api';


export default function NovaAvaliacaoScreen() {

  const { pacienteId } =
    useLocalSearchParams();


  // ============================================================
  // PACIENTE
  // ============================================================

  const nomePacienteMock =
    'Maria Silva Santos (Fictício)';


  // ============================================================
  // DADOS CLÍNICOS
  // ============================================================

  const [localizacao, setLocalizacao] =
    useState('');

  const [comprimento, setComprimento] =
    useState('');

  const [largura, setLargura] =
    useState('');

  const [tipoExsudato, setTipoExsudato] =
    useState('');

  const [odor, setOdor] =
    useState(false);

  const [nivelDor, setNivelDor] =
    useState('');

  const [queixaPrincipal, setQueixaPrincipal] =
    useState('');

  const [observacoes, setObservacoes] =
    useState('');


  // ============================================================
  // IMAGEM
  // ============================================================

  const [imagemUri, setImagemUri] =
    useState<string | null>(null);


  // ============================================================
  // RESULTADO
  // ============================================================

  const [imagemProcessadaUrl, setImagemProcessadaUrl] =
    useState<string | null>(null);

  const [dadosProcessamento, setDadosProcessamento] =
    useState<any | null>(null);


  // ============================================================
  // STATUS
  // ============================================================

  const [carregandoApi, setCarregandoApi] =
    useState(false);

  const [statusApi, setStatusApi] =
    useState<string | null>(null);


  // ============================================================
  // TESTAR CONEXÃO
  // ============================================================

  const handleTestarConexao = async () => {

    setCarregandoApi(true);

    setStatusApi(
      'Testando conexão...'
    );

    try {

      const response =
        await expoFetch(
          `${API_URL}/`,
          {
            method: 'GET',

            headers: {
              Accept: 'application/json',
            },
          }
        );


      if (!response.ok) {

        throw new Error(
          `HTTP ${response.status}`
        );
      }


      const data =
        await response.json();


      setStatusApi(
        `✅ ${data.message || data.status}`
      );


      Alert.alert(
        'Conexão Estabelecida',
        JSON.stringify(
          data,
          null,
          2
        )
      );

    } catch (error: any) {

      setStatusApi(
        '❌ Falha na conexão com a API'
      );


      Alert.alert(
        'Falha de Conexão',
        `Não foi possível conectar à API.\n\n${error.message}`
      );

    } finally {

      setCarregandoApi(false);

    }
  };


  // ============================================================
  // TIRAR FOTO
  // ============================================================

  const handleTirarFoto = async () => {

    const permissao =
      await ImagePicker.requestCameraPermissionsAsync();


    if (!permissao.granted) {

      Alert.alert(
        'Permissão Necessária',
        'Permita o acesso à câmera.'
      );

      return;
    }


    const resultado =
      await ImagePicker.launchCameraAsync({

        mediaTypes: ['images'],

        allowsEditing: true,

        quality: 0.8,

      });


    if (
      !resultado.canceled &&
      resultado.assets?.[0]?.uri
    ) {

      setImagemUri(
        resultado.assets[0].uri
      );

      setImagemProcessadaUrl(null);

      setDadosProcessamento(null);

      setStatusApi(null);
    }
  };


  // ============================================================
  // GALERIA
  // ============================================================

  const handleEscolherGaleria = async () => {

    const permissao =
      await ImagePicker.requestMediaLibraryPermissionsAsync();


    if (!permissao.granted) {

      Alert.alert(
        'Permissão Necessária',
        'Permita o acesso à galeria.'
      );

      return;
    }


    const resultado =
      await ImagePicker.launchImageLibraryAsync({

        mediaTypes: ['images'],

        allowsEditing: true,

        quality: 0.8,

      });


    if (
      !resultado.canceled &&
      resultado.assets?.[0]?.uri
    ) {

      setImagemUri(
        resultado.assets[0].uri
      );

      setImagemProcessadaUrl(null);

      setDadosProcessamento(null);

      setStatusApi(null);
    }
  };


  // ============================================================
  // ENVIAR IMAGEM PARA O BACKEND
  // ============================================================

  const handleEnviarParaAnalise = async () => {

    if (!localizacao.trim()) {

      Alert.alert(
        'Campo Obrigatório',
        'Informe a localização anatômica.'
      );

      return;
    }


    if (!imagemUri) {

      Alert.alert(
        'Imagem Obrigatória',
        'Adicione uma fotografia da lesão.'
      );

      return;
    }


    setCarregandoApi(true);

    setStatusApi(
      'Enviando imagem para o backend...'
    );


    try {

      // ========================================================
      // 1. UTILIZAR O ARQUIVO LOCAL DO EXPO
      // ========================================================

      const arquivoImagem =
        new File(imagemUri);


      if (!arquivoImagem.exists) {

        throw new Error(
          'A imagem selecionada não foi encontrada no dispositivo.'
        );
      }


      // ========================================================
      // 2. CRIAR FORMDATA
      // ========================================================

      const formData =
        new FormData();


      formData.append(
        'file',
        arquivoImagem
      );


      // ========================================================
      // 3. DADOS CLÍNICOS
      // ========================================================

      formData.append(
        'localizacao',
        localizacao
      );

      formData.append(
        'comprimento',
        comprimento
      );

      formData.append(
        'largura',
        largura
      );

      formData.append(
        'tipoExsudato',
        tipoExsudato
      );

      formData.append(
        'odor',
        String(odor)
      );

      formData.append(
        'nivelDor',
        nivelDor
      );

      formData.append(
        'queixaPrincipal',
        queixaPrincipal
      );

      formData.append(
        'observacoes',
        observacoes
      );


      // ========================================================
      // 4. ENVIAR PARA FASTAPI
      // ========================================================
      //
      // NÃO definir Content-Type manualmente.
      // O Expo cria automaticamente o multipart boundary.
      // ========================================================

      const response =
        await expoFetch(
          `${API_URL}/analisar-imagem`,
          {
            method: 'POST',

            headers: {
              Accept: 'application/json',
            },

            body: formData,
          }
        );


      // ========================================================
      // 5. VERIFICAR RESPOSTA
      // ========================================================

      if (!response.ok) {

        let mensagemErro =
          `HTTP ${response.status}`;


        try {

          const erro =
            await response.json();


          if (erro?.detail) {

            mensagemErro =
              erro.detail;
          }

        } catch {

          // Mantém mensagem HTTP.
        }


        throw new Error(
          mensagemErro
        );
      }


      // ========================================================
      // 6. LER RESULTADO
      // ========================================================

      const data =
        await response.json();


      if (!data.sucesso) {

        throw new Error(
          data.mensagem ||
          'O backend não conseguiu processar a imagem.'
        );
      }


      // ========================================================
      // 7. MONTAR URL DA IMAGEM PROCESSADA
      // ========================================================

      const urlProcessada =
        `${API_URL}${data.imagem_processada_url}`;


      setImagemProcessadaUrl(
        urlProcessada
      );


      setDadosProcessamento(
        data
      );


      setStatusApi(
        '✅ Imagem processada com sucesso.'
      );


      Alert.alert(
        'Processamento Concluído',
        'A fotografia foi recebida pelo Python e processada com OpenCV.'
      );


    } catch (error: any) {

      console.error(
        'Erro ao enviar imagem:',
        error
      );


      setStatusApi(
        '❌ Erro no processamento'
      );


      Alert.alert(
        'Erro no Processamento',
        error?.message ||
        'Não foi possível processar a imagem.'
      );


    } finally {

      setCarregandoApi(false);

    }
  };


  // ============================================================
  // INTERFACE
  // ============================================================

  return (

    <ScrollView
      contentContainerStyle={
        styles.container
      }
    >

      {/* ======================================================
          PACIENTE
      ====================================================== */}

      <View style={styles.cardPaciente}>

        <Text style={styles.labelHeader}>
          Paciente Selecionado
        </Text>

        <Text style={styles.nomePaciente}>
          {nomePacienteMock}
        </Text>

        <Text style={styles.idPaciente}>
          ID: {pacienteId || '1'}
        </Text>

      </View>


      {/* ======================================================
          BACKEND
      ====================================================== */}

      <View style={styles.cardTesteConexao}>

        <Text style={styles.labelConexao}>
          Backend Python
        </Text>

        <Text style={styles.urlConexao}>
          {API_URL}
        </Text>

        {statusApi && (

          <Text style={styles.textoStatus}>
            {statusApi}
          </Text>

        )}


        <TouchableOpacity
          style={styles.btnTestarConexao}
          onPress={handleTestarConexao}
          disabled={carregandoApi}
        >

          {carregandoApi ? (

            <ActivityIndicator
              color="#fff"
              size="small"
            />

          ) : (

            <Text style={styles.btnTestarConexaoTexto}>
              🔍 Testar Conexão
            </Text>

          )}

        </TouchableOpacity>

      </View>


      {/* ======================================================
          DADOS CLÍNICOS
      ====================================================== */}

      <Text style={styles.sectionTitle}>
        1. Dados Clínicos da Lesão
      </Text>


      <Text style={styles.label}>
        Localização Anatômica *
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Ex: Calcanhar esquerdo"
        value={localizacao}
        onChangeText={setLocalizacao}
      />


      <View style={styles.row}>

        <View style={styles.col}>

          <Text style={styles.label}>
            Comprimento (cm)
          </Text>

          <TextInput
            style={styles.input}
            keyboardType="numeric"
            value={comprimento}
            onChangeText={setComprimento}
          />

        </View>


        <View style={styles.col}>

          <Text style={styles.label}>
            Largura (cm)
          </Text>

          <TextInput
            style={styles.input}
            keyboardType="numeric"
            value={largura}
            onChangeText={setLargura}
          />

        </View>

      </View>


      <Text style={styles.label}>
        Tipo de Exsudato
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Ex: Seroso"
        value={tipoExsudato}
        onChangeText={setTipoExsudato}
      />


      <View style={styles.switchRow}>

        <Text style={styles.label}>
          Presença de Odor
        </Text>

        <Switch
          value={odor}
          onValueChange={setOdor}
        />

      </View>


      <Text style={styles.label}>
        Nível de Dor (0 a 10)
      </Text>

      <TextInput
        style={styles.input}
        keyboardType="numeric"
        value={nivelDor}
        onChangeText={setNivelDor}
      />


      <Text style={styles.label}>
        Queixa Principal
      </Text>

      <TextInput
        style={[
          styles.input,
          { height: 60 }
        ]}
        multiline
        value={queixaPrincipal}
        onChangeText={setQueixaPrincipal}
      />


      <Text style={styles.label}>
        Observações
      </Text>

      <TextInput
        style={[
          styles.input,
          { height: 60 }
        ]}
        multiline
        value={observacoes}
        onChangeText={setObservacoes}
      />


      {/* ======================================================
          FOTO
      ====================================================== */}

      <Text style={styles.sectionTitle}>
        2. Registro Fotográfico *
      </Text>


      {imagemUri ? (

        <View style={styles.areaImagemPreview}>

          <Text style={styles.labelImagem}>
            Fotografia Capturada:
          </Text>


          <Image
            source={{
              uri: imagemUri
            }}
            style={styles.previewImagem}
          />


          <TouchableOpacity
            style={styles.btnRemoverFoto}
            onPress={() => {

              setImagemUri(null);

              setImagemProcessadaUrl(null);

              setDadosProcessamento(null);

              setStatusApi(null);

            }}
          >

            <Text style={styles.btnRemoverFotoTexto}>
              Remover Imagem
            </Text>

          </TouchableOpacity>

        </View>

      ) : (

        <View style={styles.areaImagemPlaceholder}>

          <TouchableOpacity
            style={styles.btnAdicionarImagem}
            onPress={handleTirarFoto}
          >

            <Text style={styles.btnAdicionarImagemTexto}>
              📷 Tirar Foto
            </Text>

          </TouchableOpacity>


          <TouchableOpacity
            style={[
              styles.btnAdicionarImagem,
              {
                marginTop: 8,
                backgroundColor: '#555'
              }
            ]}
            onPress={handleEscolherGaleria}
          >

            <Text style={styles.btnAdicionarImagemTexto}>
              🖼️ Selecionar da Galeria
            </Text>

          </TouchableOpacity>

        </View>

      )}


      {/* ======================================================
          PROCESSAR
      ====================================================== */}

      <TouchableOpacity
        style={[
          styles.btnContinuar,
          carregandoApi &&
          styles.btnDisabled
        ]}
        onPress={handleEnviarParaAnalise}
        disabled={carregandoApi}
      >

        {carregandoApi ? (

          <ActivityIndicator
            color="#fff"
          />

        ) : (

          <Text style={styles.btnContinuarTexto}>
            🔬 Processar Imagem
          </Text>

        )}

      </TouchableOpacity>


      {/* ======================================================
          RESULTADO
      ====================================================== */}

      {imagemProcessadaUrl &&
        dadosProcessamento && (

        <View style={styles.cardResultado}>

          <Text style={styles.sectionTitleResult}>
            Resultado do Processamento
          </Text>


          <Text style={styles.labelImagem}>
            Imagem pré-processada:
          </Text>


          <Image
            source={{
              uri: imagemProcessadaUrl
            }}
            style={styles.previewImagemProcessada}
          />


          {/* ==================================================
              DIMENSÕES ORIGINAIS
          ================================================== */}

          <View style={styles.infoBox}>

            <Text style={styles.infoTitulo}>
              Informações da imagem
            </Text>


            <Text style={styles.infoText}>
              • Dimensões originais:{' '}
              {
                dadosProcessamento
                  .dimensoes_originais
                  .largura_pixels
              }
              {' × '}
              {
                dadosProcessamento
                  .dimensoes_originais
                  .altura_pixels
              }
              {' px'}
            </Text>


            <Text style={styles.infoText}>
              • Canais: {' '}
              {
                dadosProcessamento
                  .dimensoes_originais
                  .canais
              }
            </Text>


            <Text style={styles.infoText}>
              • Total de pixels: {' '}
              {
                Number(
                  dadosProcessamento
                    .dimensoes_originais
                    .total_pixels
                ).toLocaleString('pt-BR')
              }
            </Text>


            <Text style={styles.infoText}>
              • Dimensões processadas:{' '}
              {
                dadosProcessamento
                  .dimensoes_processadas
                  .largura_pixels
              }
              {' × '}
              {
                dadosProcessamento
                  .dimensoes_processadas
                  .altura_pixels
              }
              {' px'}
            </Text>

          </View>


          {/* ==================================================
              ANÁLISE TÉCNICA
          ================================================== */}

          <View style={styles.infoBox}>

            <Text style={styles.infoTitulo}>
              Análise técnica da imagem
            </Text>


            <Text style={styles.infoText}>
              • Brilho médio:{' '}
              {
                dadosProcessamento
                  .analise_tecnica
                  .brilho_medio
              }
              {' / 255'}
            </Text>


            <Text style={styles.infoText}>
              • Contraste global:{' '}
              {
                dadosProcessamento
                  .analise_tecnica
                  .contraste_global
              }
            </Text>

          </View>


          {/* ==================================================
              PROCESSAMENTO APLICADO
          ================================================== */}

          <View style={styles.infoBox}>

            <Text style={styles.infoTitulo}>
              Processamento realizado
            </Text>


            <Text style={styles.infoText}>
              • Imagem validada:{' '}
              {
                dadosProcessamento
                  .processamento_aplicado
                  .validacao_imagem
                  ? 'Sim'
                  : 'Não'
              }
            </Text>


            <Text style={styles.infoText}>
              • Conversão temporária para escala de cinza:{' '}
              {
                dadosProcessamento
                  .processamento_aplicado
                  .conversao_temporaria_para_escala_de_cinza
                  ? 'Sim'
                  : 'Não'
              }
            </Text>


            <Text style={styles.infoText}>
              • Redimensionamento proporcional:{' '}
              {
                dadosProcessamento
                  .processamento_aplicado
                  .redimensionamento_proporcional
                  ? 'Sim'
                  : 'Não'
              }
            </Text>


            <Text style={styles.infoText}>
              • Dimensão máxima utilizada:{' '}
              {
                dadosProcessamento
                  .processamento_aplicado
                  .dimensao_maxima
              }
              {' px'}
            </Text>

          </View>


          {/* ==================================================
              AVISO
          ================================================== */}

          <Text style={styles.observacaoResultado}>
            Esta etapa realiza o processamento técnico inicial
            da fotografia. Os dados apresentados não representam
            diagnóstico ou conclusão clínica. A análise das
            características da lesão será realizada nas próximas
            etapas do sistema, com apoio dos modelos multimodais
            e validação pelo profissional.
          </Text>

        </View>

      )}

    </ScrollView>
  );
}


// ============================================================
// ESTILOS
// ============================================================

const styles = StyleSheet.create({

  container: {
    padding: 20,
    backgroundColor: '#fff',
    flexGrow: 1,
  },

  cardPaciente: {
    backgroundColor: '#eef6ff',
    padding: 14,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#0056b3',
    marginBottom: 16,
  },

  labelHeader: {
    fontSize: 12,
    color: '#666',
    textTransform: 'uppercase',
    fontWeight: 'bold',
  },

  nomePaciente: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0056b3',
    marginTop: 2,
  },

  idPaciente: {
    fontSize: 13,
    color: '#555',
    marginTop: 2,
  },

  cardTesteConexao: {
    backgroundColor: '#f0fdf4',
    borderWidth: 1,
    borderColor: '#bbf7d0',
    padding: 14,
    borderRadius: 8,
    marginBottom: 20,
  },

  labelConexao: {
    fontSize: 12,
    color: '#166534',
    fontWeight: 'bold',
  },

  urlConexao: {
    fontSize: 13,
    color: '#15803d',
    marginVertical: 4,
  },

  textoStatus: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#166534',
    marginVertical: 4,
  },

  btnTestarConexao: {
    backgroundColor: '#16a34a',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 6,
    alignItems: 'center',
    marginTop: 6,
  },

  btnTestarConexaoTexto: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 13,
  },

  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 12,
    marginTop: 10,
  },

  sectionTitleResult: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#15803d',
    marginBottom: 12,
  },

  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 6,
  },

  labelImagem: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#444',
    marginBottom: 6,
  },

  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    backgroundColor: '#fafafa',
    marginBottom: 14,
  },

  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },

  col: {
    flex: 0.48,
  },

  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },

  areaImagemPlaceholder: {
    borderWidth: 2,
    borderColor: '#ccc',
    borderStyle: 'dashed',
    borderRadius: 8,
    padding: 20,
    alignItems: 'center',
    backgroundColor: '#f9f9f9',
    marginBottom: 24,
  },

  btnAdicionarImagem: {
    backgroundColor: '#0056b3',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 6,
  },

  btnAdicionarImagemTexto: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },

  areaImagemPreview: {
    alignItems: 'center',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    padding: 12,
    backgroundColor: '#fafafa',
  },

  previewImagem: {
    width: '100%',
    height: 220,
    borderRadius: 8,
    resizeMode: 'cover',
  },

  previewImagemProcessada: {
    width: '100%',
    height: 220,
    borderRadius: 8,
    resizeMode: 'contain',
    backgroundColor: '#f3f4f6',
    marginBottom: 4,
  },

  btnRemoverFoto: {
    backgroundColor: '#dc3545',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    marginTop: 12,
  },

  btnRemoverFotoTexto: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 13,
  },

  btnContinuar: {
    backgroundColor: '#0056b3',
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 20,
  },

  btnDisabled: {
    backgroundColor: '#a0c4e8',
  },

  btnContinuarTexto: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },

  cardResultado: {
    backgroundColor: '#f0fdf4',
    borderWidth: 1,
    borderColor: '#86efac',
    padding: 16,
    borderRadius: 10,
    marginBottom: 30,
  },

  infoBox: {
    marginTop: 12,
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },

  infoTitulo: {
    fontSize: 14,
    color: '#166534',
    fontWeight: 'bold',
    marginBottom: 6,
  },

  infoText: {
    fontSize: 13,
    color: '#334155',
    marginVertical: 3,
    fontWeight: '500',
  },

  observacaoResultado: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 18,
    marginTop: 14,
  },

});