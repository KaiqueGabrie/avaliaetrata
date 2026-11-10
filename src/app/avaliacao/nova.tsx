
import { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Platform,
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
import { apiJson, mensagemErro, obterToken } from '../../config/cliente';

import ComparacaoConfiancaIA from '../../components/comparacao-confianca-ia';
import EditorMarcacoes from '../../components/editor-marcacoes';
import FotografiasAvaliacao, { ImagensAvaliacao } from '../../components/fotografias-avaliacao';
import RelatorioCompleto from '../../components/relatorio-completo';
import { API_URL } from '../../config/api';
import type { ResultadoProvedorIA } from '../../types/ia';
import { Aviso } from '../../utils/avisos';

type Provedor = 'gemini' | 'openai' | 'kimi' | 'todos';

type RespostaAPI = ImagensAvaliacao & {
  sucesso: boolean;
  mensagem: string;
  analise_id: number;
  comparacao_multimodal?: {
    componentes?: Record<string, {
      nome?: string;
      situacao_descritiva?: string;
      divergencia_status?: boolean;
      observacao_descritiva?: string;
    }>;
    observacao_metodologica?: string;
  };
  imagem_original_url?: string | null;
  imagem_processada_url?: string | null;
  imagem_bordas_url?: string | null;
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
  const [imagemAsset, setImagemAsset] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [provedor, setProvedor] = useState<Provedor>('todos');
  const [resultado, setResultado] = useState<RespostaAPI | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [statusApi, setStatusApi] = useState('');

  const [provedorEscolhido, setProvedorEscolhido] = useState('');
  const [revisao, setRevisao] = useState('');
  const [validado, setValidado] = useState(false);
  const [salvandoRevisao, setSalvandoRevisao] = useState(false);
  const [gerandoMarcacoes, setGerandoMarcacoes] = useState(false);
  const [reprocessandoOpenAI, setReprocessandoOpenAI] = useState(false);

  const resultados = resultado?.analise_multimodal?.resultados || {};

  const limpar = () => {
    setResultado(null);
    setProvedorEscolhido('');
    setRevisao('');
    setValidado(false);
  };

  const selecionarImagem = async (camera: boolean) => {
    try {
      if (Platform.OS === 'web' && camera) {
        Aviso.alert(
          'Câmera',
          'No navegador, selecione a fotografia usando a opção da galeria.'
        );
        return;
      }

      if (Platform.OS !== 'web') {
        const permissao = camera
          ? await ImagePicker.requestCameraPermissionsAsync()
          : await ImagePicker.requestMediaLibraryPermissionsAsync();

        if (!permissao.granted) {
          Aviso.alert('Permissão necessária', 'Autorize o acesso à imagem.');
          return;
        }
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
        setImagemAsset(selecao.assets[0]);
        limpar();
      }
    } catch (erro) {
      Aviso.alert(
        'Erro na imagem',
        erro instanceof Error ? erro.message : 'Erro desconhecido',
      );
    }
  };

  const analisar = async () => {
    if (!pacienteId || !/^\d+$/.test(pacienteId)) {
      Aviso.alert(
        'Paciente obrigatório',
        'Abra a avaliação a partir do prontuário de um paciente.'
      );
      return;
    }

    if (!localizacao.trim() || !imagemUri) {
      Aviso.alert(
        'Dados obrigatórios',
        'Informe a localização e selecione uma fotografia.'
      );
      return;
    }

    if (
      nivelDor.trim() &&
      (
        !Number.isFinite(Number(nivelDor)) ||
        Number(nivelDor) < 0 ||
        Number(nivelDor) > 10
      )
    ) {
      Aviso.alert('Dor inválida', 'Informe um valor entre 0 e 10.');
      return;
    }

    setCarregando(true);
    limpar();
    let analiseId: number | null = null;

    try {
      const token = await obterToken();

      // 1. Cria uma avaliação pendente associada ao paciente.
      setStatusApi('1/3 — Registrando avaliação...');

      const criada = await apiJson<{ id_analise: number }>(
        `/pacientes/${pacienteId}/analises`,
        {
          method: 'POST',
          body: JSON.stringify({
            queixa_principal: queixaPrincipal.trim() || null,
            observacoes_clinicas: observacoes.trim() || null,
            contexto_clinico_json: {
              localizacao: localizacao.trim(),
              comprimento: comprimento.trim(),
              largura: largura.trim(),
              tipoExsudato: tipoExsudato.trim(),
              odor,
              nivelDor: nivelDor.trim(),
            },
          }),
        }
      );

      analiseId = criada.id_analise;

      // 2. Envia a foto; o backend executa OpenCV e vincula a imagem.
      setStatusApi('2/3 — Registrando fotografia...');

      const foto = new FormData();

      const extensao =
        imagemAsset?.fileName?.toLowerCase().split('.').pop() ||
        imagemUri.toLowerCase().split('?')[0].split('.').pop();

      const tipo =
        imagemAsset?.mimeType ||
        (
          extensao === 'png'
            ? 'image/png'
            : extensao === 'webp'
              ? 'image/webp'
              : 'image/jpeg'
        );

      const nomeArquivo = `lesao.${tipo.split('/')[1] || 'jpeg'}`;

      if (Platform.OS === 'web') {
        // O Expo ImagePicker disponibiliza um File real no navegador.
        // O fallback cobre versões que retornam somente URI blob/data.
        const arquivoWeb =
          imagemAsset?.file ??
          await (await fetch(imagemUri)).blob();

        foto.append('file', arquivoWeb, nomeArquivo);
      } else {
        const arquivoNativo = new File(imagemUri);

        if (!arquivoNativo.exists) {
          throw new Error('Arquivo da fotografia não encontrado.');
        }

        foto.append(
          'file',
          arquivoNativo as unknown as Blob,
          nomeArquivo
        );
      }

      const urlFoto =
        `${API_URL}/pacientes/${pacienteId}/analises/${analiseId}/imagem`;

      const opcoesFoto = {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: foto,
      };

      const respostaFoto =
        Platform.OS === 'web'
          ? await fetch(urlFoto, opcoesFoto)
          : await expoFetch(urlFoto, opcoesFoto);

      if (!respostaFoto.ok) {
        throw new Error(await mensagemErro(respostaFoto as Response));
      }

      const dadosFoto = await respostaFoto.json();

      // A fotografia permanece salva mesmo se uma IA falhar.
      setResultado({
        sucesso: false,
        mensagem: 'Fotografia registrada; aguardando as análises das IAs.',
        analise_id: analiseId,
        imagem_original_url: dadosFoto.imagem_original_url ?? null,
        imagem_processada_url: dadosFoto.imagem_processada_url ?? null,
        imagem_bordas_url: dadosFoto.imagem_bordas_url ?? null,
        medidas_geometricas: dadosFoto.medidas_geometricas,
        analise_tecnica: dadosFoto.analise_tecnica,
      });

      // 3. Executa os provedores selecionados.
      setStatusApi(
        '3/3 — Analisando a fotografia. Isso pode levar alguns minutos...'
      );

      const formulario = new FormData();
      formulario.append('localizacao', localizacao.trim());
      formulario.append('comprimento', comprimento.trim());
      formulario.append('largura', largura.trim());
      formulario.append('tipoExsudato', tipoExsudato.trim());
      formulario.append('odor', odor);
      formulario.append('nivelDor', nivelDor.trim());
      formulario.append('queixaPrincipal', queixaPrincipal.trim());
      formulario.append('observacoes', observacoes.trim());
      formulario.append('provedor', provedor);

      const urlAnalise =
        `${API_URL}/analises/${analiseId}/executar-multimodal`;

      const opcoesAnalise = {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: formulario,
      };

      const resposta =
        Platform.OS === 'web'
          ? await fetch(urlAnalise, opcoesAnalise)
          : await expoFetch(urlAnalise, opcoesAnalise);

      if (!resposta.ok) {
        throw new Error(await mensagemErro(resposta as Response));
      }

      const dados = await resposta.json() as RespostaAPI;

      setResultado({
        ...dados,
        analise_id: analiseId,
        imagem_original_url: dadosFoto.imagem_original_url ?? null,
        imagem_processada_url: dadosFoto.imagem_processada_url ?? null,
        imagem_bordas_url: dadosFoto.imagem_bordas_url ?? null,
        medidas_geometricas:
          dados.medidas_geometricas ?? dadosFoto.medidas_geometricas,
        analise_tecnica: dadosFoto.analise_tecnica,
      });

      // Gera imagens dos polígonos já persistidos,
      // sem solicitar novas análises às IAs.
      try {
        setGerandoMarcacoes(true);

        const visualizacoes = await apiJson<{
          marcacoes_por_ia: ImagensAvaliacao['marcacoes_por_ia'];
        }>(
          `/pacientes/${pacienteId}/analises/${analiseId}/marcacoes/gerar`,
          { method: 'POST' }
        );

        setResultado(anterior =>
          anterior ? { ...anterior, ...visualizacoes } : anterior
        );
      } catch {
        // A visualização é opcional e não invalida a análise.
      } finally {
        setGerandoMarcacoes(false);
      }

      const lista = Object.values(
        dados.analise_multimodal?.resultados || {}
      );
      const sucessos = lista.filter(item => item.sucesso).length;

      setStatusApi(
        sucessos > 0
          ? `${sucessos} de ${lista.length} análises concluídas. Confira os resultados abaixo.`
          : 'Não foi possível concluir a análise. Você pode consultar a avaliação no prontuário.'
      );
    } catch (erro) {
      setStatusApi(
        analiseId
          ? 'Não foi possível concluir a análise. Consulte o prontuário antes de tentar novamente.'
          : 'Erro ao criar avaliação.'
      );

      Aviso.alert(
        'Não foi possível concluir',
        'Confira sua conexão e os dados informados. Se o problema continuar, tente novamente mais tarde.'
      );
    } finally {
      setCarregando(false);
    }
  };

  const atualizarFotografias = async () => {
    if (!resultado?.analise_id || !pacienteId) return;

    try {
      const [imagens, visualizacoes] = await Promise.all([
        apiJson<ImagensAvaliacao>(
          `/pacientes/${pacienteId}/analises/${resultado.analise_id}/imagens`
        ),
        apiJson<{
          marcacoes_por_ia: ImagensAvaliacao['marcacoes_por_ia'];
        }>(
          `/pacientes/${pacienteId}/analises/${resultado.analise_id}/marcacoes`
        ).catch(() => null),
      ]);

      setResultado(anterior =>
        anterior
          ? { ...anterior, ...imagens, ...(visualizacoes || {}) }
          : anterior
      );
    } catch (e) {
      Aviso.alert(
        'Fotografias',
        e instanceof Error
          ? e.message
          : 'Não foi possível atualizar as imagens.'
      );
    }
  };

  const gerarMarcacoes = async () => {
    if (!resultado?.analise_id || !pacienteId) return;

    setGerandoMarcacoes(true);

    try {
      const dados = await apiJson<{
        marcacoes_por_ia: ImagensAvaliacao['marcacoes_por_ia'];
      }>(
        `/pacientes/${pacienteId}/analises/${resultado.analise_id}/marcacoes/gerar`,
        { method: 'POST' }
      );

      setResultado(anterior =>
        anterior ? { ...anterior, ...dados } : anterior
      );
    } catch (erro) {
      Aviso.alert(
        'Marcações',
        erro instanceof Error
          ? erro.message
          : 'Não foi possível gerar as imagens.'
      );
    } finally {
      setGerandoMarcacoes(false);
    }
  };

  const reprocessarOpenAI = async () => {
    if (!resultado?.analise_id || !pacienteId) return;

    setReprocessandoOpenAI(true);

    try {
      const resposta = await apiJson<{
        total_regioes: number;
        mensagem: string;
      }>(
        `/pacientes/${pacienteId}/analises/${resultado.analise_id}/marcacoes/openai/reprocessar`,
        { method: 'POST' }
      );

      if (resposta.total_regioes > 0) {
        const imagensMarcadas = await apiJson<{
          marcacoes_por_ia: ImagensAvaliacao['marcacoes_por_ia'];
        }>(
          `/pacientes/${pacienteId}/analises/${resultado.analise_id}/marcacoes/gerar`,
          { method: 'POST' }
        );

        setResultado(anterior =>
          anterior ? { ...anterior, ...imagensMarcadas } : anterior
        );

        await atualizarFotografias();

        Aviso.alert(
          'OpenAI — proposta complementar',
          `${resposta.total_regioes} região(ões) proposta(s). Confira as marcações. Reabra a avaliação antes de importar no editor.`
        );
      } else {
        await atualizarFotografias();
        Aviso.alert('Sem coordenadas', resposta.mensagem);
      }
    } catch (erro) {
      Aviso.alert(
        'OpenAI',
        erro instanceof Error
          ? erro.message
          : 'Falha ao tentar obter contornos.'
      );
    } finally {
      setReprocessandoOpenAI(false);
    }
  };

  const salvarRevisao = async () => {
    if (
      !resultado?.analise_id ||
      !provedorEscolhido ||
      !revisao.trim()
    ) {
      Aviso.alert(
        'Revisão necessária',
        'Selecione uma análise e preencha a descrição revisada.'
      );
      return;
    }

    setSalvandoRevisao(true);

    try {
      await apiJson(
        `/analises/${resultado.analise_id}/relatorios/${provedorEscolhido}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            campo: 'conteudo_descricao',
            novo_valor: revisao.trim(),
          }),
        }
      );

      setValidado(true);
      Aviso.alert('Revisão salva', 'Revisão salva com sucesso.');
    } catch (e) {
      Aviso.alert(
        'Erro ao salvar revisão',
        e instanceof Error ? e.message : 'Falha desconhecida.'
      );
    } finally {
      setSalvandoRevisao(false);
    }
  };

  const selecionarProvedor = (nome: string) => {
    setProvedorEscolhido(nome);
    setValidado(false);

    setRevisao(
      resultados[nome]?.resposta?.conteudo_descricao || ''
    );
  };

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.titulo}>Nova avaliação</Text>
      <Text style={styles.textoMenor}>
        Prontuário nº {pacienteId || 'Não selecionado'}
      </Text>

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

      <Text style={styles.rotulo}>
        Odor informado pelo profissional
      </Text>

      <View style={styles.linha}>
        {[
          { valor: '', titulo: 'Não avaliado' },
          { valor: 'sim', titulo: 'Presente' },
          { valor: 'nao', titulo: 'Ausente' },
        ].map(opcao => (
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
            <Text style={styles.textoMenor}>
              {opcao.titulo}
            </Text>
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
        <Text style={styles.botaoTexto}>
          Tirar fotografia
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.botaoCinza}
        onPress={() => selecionarImagem(false)}
        disabled={carregando}
      >
        <Text style={styles.botaoTexto}>
          Selecionar da galeria
        </Text>
      </TouchableOpacity>

      <Text style={styles.titulo}>
        3. Inteligências artificiais
      </Text>

      {PROVEDORES.map(item => (
        <TouchableOpacity
          key={item.valor}
          style={[
            styles.opcao,
            provedor === item.valor && styles.opcaoAtiva,
          ]}
          onPress={() => setProvedor(item.valor)}
          disabled={carregando}
        >
          <Text style={styles.texto}>
            {item.titulo}
          </Text>
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
            Analisar fotografia
          </Text>
        )}
      </TouchableOpacity>

      {resultado ? (
        <>
          <Text style={styles.titulo}>
            4. Resultados
          </Text>

          <View style={styles.card}>
            <Text style={styles.texto}>
              Confira as análises disponíveis e revise os resultados.
            </Text>
            <Text style={styles.textoMenor}>
              Avaliação nº {resultado.analise_id}
            </Text>
          </View>

          {/* ETAPA 2J: CONFIANÇA DAS TRÊS IAS */}
          <ComparacaoConfiancaIA
            resultados={resultados}
          />

          <FotografiasAvaliacao
            imagens={resultado}
            onAtualizar={atualizarFotografias}
            onGerar={gerarMarcacoes}
            gerando={gerandoMarcacoes}
            onReprocessarOpenAI={reprocessarOpenAI}
            reprocessandoOpenAI={reprocessandoOpenAI}
          />

          {pacienteId && resultado.analise_id ? (
            <EditorMarcacoes
              pacienteId={pacienteId}
              analiseId={resultado.analise_id}
            />
          ) : null}

          {resultado.comparacao_multimodal?.componentes ? (
            <View style={styles.card}>
              <Text style={styles.subtitulo}>
                Comparação das análises T.I.M.E.S.
              </Text>

              {Object.entries(
                resultado.comparacao_multimodal.componentes
              ).map(([letra, componente]) => (
                <View key={letra} style={styles.bloco}>
                  <Text style={styles.rotulo}>
                    {letra} — {componente.nome || ''}
                  </Text>
                  <Text style={styles.texto}>
                    Comparação descritiva:{' '}
                    {componente.situacao_descritiva || 'Inconclusiva'}
                  </Text>
                  <Text style={styles.textoMenor}>
                    Diferença no estado de avaliação:{' '}
                    {componente.divergencia_status ? 'Sim' : 'Não'}
                  </Text>
                  <Text style={styles.textoMenor}>
                    {componente.observacao_descritiva || ''}
                  </Text>
                </View>
              ))}

              <Text style={styles.textoMenor}>
                Comparação auxiliar; não determina diagnóstico
                ou concordância clínica.
              </Text>
            </View>
          ) : null}

          <Text style={styles.titulo}>
            Resultados das IAs
          </Text>

          {Object.entries(resultados).map(([nome, item]) => (
            <View key={nome} style={styles.card}>
              <Text style={styles.subtitulo}>
                {nome.toUpperCase()} —{' '}
                {item.sucesso ? 'SUCESSO' : 'FALHA'}
              </Text>

              {item.sucesso && item.resposta ? (
                <>
                  <RelatorioCompleto resposta={item.resposta} />

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
                  Não foi possível concluir esta análise.
                  Tente novamente mais tarde.
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
                Análise selecionada:{' '}
                {provedorEscolhido.toUpperCase()}
              </Text>

              <Text style={styles.textoMenor}>
                Confira a descrição e faça as correções
                necessárias antes de salvar.
              </Text>

              <TextInput
                style={[styles.input, styles.revisao]}
                value={revisao}
                onChangeText={texto => {
                  setRevisao(texto);
                  setValidado(false);
                }}
                multiline
                textAlignVertical="top"
              />

              <TouchableOpacity
                style={styles.botao}
                onPress={salvarRevisao}
                disabled={salvandoRevisao}
              >
                {salvandoRevisao ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.botaoTexto}>
                    Salvar revisão
                  </Text>
                )}
              </TouchableOpacity>

              {validado ? (
                <Text style={styles.sucesso}>
                  Revisão salva com sucesso.
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
              e as sugestões de cuidado não substituem
              a avaliação presencial do enfermeiro.
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
