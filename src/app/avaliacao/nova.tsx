import RotuloComAjuda from '../../components/rotulo-com-ajuda';

import { useRef, useState } from 'react';
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
import { router, useLocalSearchParams } from 'expo-router';
import { fetch as expoFetch } from 'expo/fetch';
import { apiJson, mensagemErro, obterToken } from '../../config/cliente';

import ComparacaoConfiancaIA from '../../components/comparacao-confianca-ia';
import EditorMarcacoes from '../../components/editor-marcacoes';
import type { ImagensAvaliacao } from '../../components/fotografias-avaliacao';
import FotografiasAvaliacao from '../../components/fotografias-avaliacao';
import RelatorioCompleto from '../../components/relatorio-completo';
import { API_URL } from '../../config/api';
import type { ResultadoProvedorIA } from '../../types/ia';
import { Aviso } from '../../utils/avisos';

type Etapa = 'clinica' | 'foto' | 'processando' | 'resultados' | 'revisao';

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
      <RotuloComAjuda titulo={titulo} />
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

  const solicitacaoEmAndamento = useRef(false);
  const [etapa, setEtapa] = useState<Etapa>('clinica');
  const [comparacaoAberta, setComparacaoAberta] = useState(false);
  const [avaliacaoIniciada, setAvaliacaoIniciada] = useState<number | null>(null);
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
    setComparacaoAberta(false);
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
    if (solicitacaoEmAndamento.current || avaliacaoIniciada !== null) return;

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

    solicitacaoEmAndamento.current = true;
    setCarregando(true);
    setEtapa('processando');
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
      setAvaliacaoIniciada(analiseId);

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
          ? `${sucessos} de ${lista.length} análises concluídas.`
          : 'Não foi possível concluir a análise. Você pode consultar a avaliação no prontuário.'
      );
      setEtapa('resultados');
    } catch {
      setStatusApi(
        analiseId
          ? 'Não foi possível concluir a análise. Consulte o prontuário antes de tentar novamente.'
          : 'Erro ao criar avaliação.'
      );

      setEtapa(analiseId !== null ? 'resultados' : 'foto');

      Aviso.alert(
        'Não foi possível concluir',
        'Confira sua conexão e os dados informados. Se o problema continuar, tente novamente mais tarde.'
      );
    } finally {
      solicitacaoEmAndamento.current = false;
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
    if (nome !== provedorEscolhido) {
      setProvedorEscolhido(nome);
      setValidado(false);
      setRevisao(resultados[nome]?.resposta?.conteudo_descricao || '');
    }
    setEtapa('revisao');
  };

  const avancarParaFoto = () => {
    if (!localizacao.trim()) {
      Aviso.alert('Localização obrigatória', 'Informe a localização anatômica da lesão.');
      return;
    }
    if (nivelDor.trim() && !(Number(nivelDor) >= 0 && Number(nivelDor) <= 10)) {
      Aviso.alert('Dor inválida', 'Informe um valor entre 0 e 10.');
      return;
    }
    setStatusApi('');
    setEtapa('foto');
  };

  const abrirRelatorio = () => {
    if (!avaliacaoIniciada || !pacienteId) return;
    router.push({
      pathname: '/avaliacao/[id]',
      params: {
        id: String(avaliacaoIniciada),
        pacienteId,
        provedor: provedorEscolhido,
      },
    });
  };

  const tituloDaEtapa: Record<Etapa, string> = {
    clinica: 'Informações Clínicas',
    foto: 'Fotografia',
    processando: 'Analisando a fotografia',
    resultados: 'Resultado das Análises',
    revisao: 'Resultado da Análise',
  };

  const nomesModelos: Record<string, string> = {
    gemini: 'Gemini',
    openai: 'OpenAI',
    kimi: 'Kimi',
  };
  const respostaEscolhida = resultados[provedorEscolhido]?.resposta;
  const cardFoto = (modelo: string) => {
    const marcada = resultado?.marcacoes_por_ia?.[modelo.toLowerCase()];
    const urlMarcada = marcada?.status === 'pronta' ? marcada.url : null;
    const url = urlMarcada || resultado?.imagem_original_url || imagemUri;
    const uri = url?.startsWith('/') ? API_URL + url : url;

    return uri ? (
      <View>
        <Image
          source={{ uri }}
          style={styles.miniatura}
          resizeMode="contain"
          accessibilityLabel={urlMarcada ? 'Fotografia com contornos propostos' : 'Fotografia original'}
        />
        <Text style={styles.textoMenor}>
          {urlMarcada ? 'Proposta de marcação da IA' : 'Fotografia original'}
        </Text>
      </View>
    ) : null;
  };

  return (
    <ScrollView
      key={etapa}
      style={styles.pagina}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.titulo}>{tituloDaEtapa[etapa]}</Text>
      <Text style={styles.textoMenor}>Prontuário nº {pacienteId || 'Não selecionado'}</Text>

      {etapa === 'clinica' ? (
        <>
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

          <RotuloComAjuda titulo="Odor informado pelo profissional" />

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

          <View style={styles.aviso}>
            <Text style={styles.texto}>
              Se for medir a área depois, fotografe uma régua no mesmo plano da lesão.
            </Text>
          </View>
          <TouchableOpacity accessibilityRole="button" style={styles.botao} onPress={avancarParaFoto}>
            <Text style={styles.botaoTexto}>Avançar</Text>
          </TouchableOpacity>
        </>
      ) : null}

      {etapa === 'foto' ? (
        <>
          <TouchableOpacity accessibilityRole="button" onPress={() => setEtapa('clinica')}>
            <Text style={styles.link}>Voltar às informações clínicas</Text>
          </TouchableOpacity>
          <Text style={styles.texto}>Centralize a lesão e confira a iluminação da fotografia.</Text>
          {imagemUri ? (
            <Image
              source={{ uri: imagemUri }}
              style={styles.imagem}
              resizeMode="contain"
              accessibilityLabel="Fotografia selecionada"
            />
          ) : null}

          {Platform.OS !== 'web' ? (
            <TouchableOpacity
              accessibilityRole="button"
              style={styles.botaoCinza}
              onPress={() => selecionarImagem(true)}
            >
              <Text style={styles.botaoTexto}>Tirar fotografia</Text>
            </TouchableOpacity>
          ) : null}

          <RotuloComAjuda titulo="Como fotografar" />
          <TouchableOpacity
            accessibilityRole="button"
            style={styles.botaoCinza}
            onPress={() => selecionarImagem(false)}
          >
            <Text style={styles.botaoTexto}>Selecionar da galeria</Text>
          </TouchableOpacity>

          <Text style={styles.subtitulo}>Modelos da análise</Text>
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

          {statusApi ? <Text style={styles.status}>{statusApi}</Text> : null}
          <TouchableOpacity
            accessibilityRole="button"
            style={[styles.botao, !imagemUri && styles.desabilitado]}
            onPress={analisar}
            disabled={!imagemUri || carregando}
          >
            <Text style={styles.botaoTexto}>Analisar fotografia</Text>
          </TouchableOpacity>
        </>
      ) : null}

      {etapa === 'processando' ? (
        <View style={styles.processando} accessibilityLiveRegion="polite">
          <ActivityIndicator size="large" color="#005088" />
          <Text style={styles.subtitulo}>{statusApi || 'Preparando a avaliação…'}</Text>
        </View>
      ) : null}

      {etapa === 'resultados' || etapa === 'revisao' ? (
        <Text style={styles.status}>{statusApi}</Text>
      ) : null}

      {etapa === 'resultados' ? (
        <>
          {avaliacaoIniciada ? <Text style={styles.textoMenor}>Avaliação nº {avaliacaoIniciada}</Text> : null}
          {Object.keys(resultados).length === 0 ? (
            <Text style={styles.texto}>Nenhuma análise disponível nesta tela.</Text>
          ) : null}
          {Object.entries(resultados).map(([modelo, item]) => {
            const nome = nomesModelos[modelo.toLowerCase()] || modelo.toUpperCase();
            const confianca = item.resposta?.confianca_avaliacao_percentual;
            return (
              <View key={modelo} style={styles.card}>
                <Text style={styles.subtitulo}>{nome}</Text>
                {item.sucesso && item.resposta ? (
                  <>
                    <Text style={styles.textoMenor}>
                      Confiança autodeclarada: {typeof confianca === 'number' && Number.isFinite(confianca)
                        ? `${confianca.toLocaleString('pt-BR')}%`
                        : 'Não informada'}
                    </Text>
                    {cardFoto(modelo)}
                    <TouchableOpacity
                      accessibilityRole="button"
                      style={styles.botao}
                      onPress={() => selecionarProvedor(modelo)}
                    >
                      <Text style={styles.botaoTexto}>Selecionar para revisão</Text>
                    </TouchableOpacity>
                  </>
                ) : <Text style={styles.erro}>Análise indisponível.</Text>}
              </View>
            );
          })}
          {resultado ? (
            <>
              <TouchableOpacity
                accessibilityRole="button"
                accessibilityState={{ expanded: comparacaoAberta }}
                onPress={() => setComparacaoAberta(valor => !valor)}
              >
                <Text style={styles.link}>{comparacaoAberta ? 'Ocultar comparação' : 'Comparar análises, confiança e marcações'}</Text>
              </TouchableOpacity>
              {comparacaoAberta ? (
                <>
                  <ComparacaoConfiancaIA
                    resultados={resultados}
                  />

                  <FotografiasAvaliacao
                    alertasContornos={Object.fromEntries(
                      Object.entries(resultados).map(([nome, item]) => [
                        nome.toLowerCase(),
                        (
                          item.resposta?.marcacoes_imagem?.limitacoes ?? []
                        ).filter(aviso =>
                          aviso.startsWith('[AUDITORIA_CONTORNO]')
                        ),
                      ])
                    )}
                    imagens={resultado}
                    onAtualizar={atualizarFotografias}
                    onGerar={gerarMarcacoes}
                    gerando={gerandoMarcacoes}
                    onReprocessarOpenAI={reprocessarOpenAI}
                    reprocessandoOpenAI={reprocessandoOpenAI}
                  />

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

                </>
              ) : null}
            </>
          ) : null}
          <TouchableOpacity accessibilityRole="button" onPress={abrirRelatorio}>
            <Text style={styles.link}>Abrir avaliação no histórico</Text>
          </TouchableOpacity>
        </>
      ) : null}

      {etapa === 'revisao' && resultado && respostaEscolhida ? (
        <>
          <TouchableOpacity accessibilityRole="button" onPress={() => setEtapa('resultados')} disabled={salvandoRevisao}>
            <Text style={styles.link}>Voltar para as análises</Text>
          </TouchableOpacity>
          <View style={styles.card}>
            <Text style={styles.subtitulo}>{nomesModelos[provedorEscolhido.toLowerCase()] || provedorEscolhido}</Text>
            {cardFoto(provedorEscolhido)}
            <RelatorioCompleto resposta={respostaEscolhida} mostrarDescricao={false} />
          </View>
          {pacienteId && resultado.analise_id ? (
            <EditorMarcacoes
              pacienteId={pacienteId}
              analiseId={resultado.analise_id}
            />
          ) : null}

          {provedorEscolhido ? (
            <View style={styles.card}>
              <Text style={styles.titulo}>
                Revisão profissional
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

          <TouchableOpacity accessibilityRole="button" style={styles.botao} onPress={abrirRelatorio} disabled={salvandoRevisao}>
            <Text style={styles.botaoTexto}>Abrir relatório para aprovação</Text>
          </TouchableOpacity>
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
  pagina: { flex: 1, backgroundColor: '#fff' },
  container: {
    width: '100%',
    maxWidth: 920,
    alignSelf: 'center',
    padding: 18,
    paddingBottom: 60,
    flexGrow: 1,
  },
  link: {
    color: '#005088',
    fontWeight: '600',
    textDecorationLine: 'underline',
    paddingVertical: 12,
  },
  aviso: { backgroundColor: '#fff7ed', padding: 12, borderRadius: 8 },
  processando: { flex: 1, minHeight: 290, gap: 18, justifyContent: 'center', alignItems: 'center' },
  miniatura: { width: '100%', height: 240, backgroundColor: '#eef2f6', borderRadius: 12, marginBottom: 6 },
  desabilitado: { opacity: 0.55 },
  titulo: {
    fontSize: 19,
    fontWeight: 'bold',
    color: '#005088',
    marginTop: 18,
    marginBottom: 12,
  },
  subtitulo: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#005088',
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
    backgroundColor: '#dce6ed',
    borderWidth: 1,
    borderColor: '#809BAE',
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
    borderColor: '#005088',
    backgroundColor: '#dbeafe',
  },
  botao: {
    backgroundColor: '#005088',
    padding: 14,
    borderRadius: 16,
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

