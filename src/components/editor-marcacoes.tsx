import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import {
  ActivityIndicator, Image, ScrollView, StyleSheet, Text, TouchableOpacity,
  useWindowDimensions, View,
} from 'react-native';
import { API_URL } from '../config/api';
import { apiJson, obterToken } from '../config/cliente';
import { Aviso } from '../utils/avisos';

type Classe = 'contorno_lesao' | 'granulacao' | 'esfacelo' | 'necrose' | 'pele_perilesional' | 'nao_classificado';
type Provedor = 'openai' | 'gemini' | 'kimi' | 'manual';
type Ponto = { x: number; y: number };
type Regiao = { id: string; classe: Classe; pontos: Ponto[]; origem: 'ia' | 'profissional'; descricao: string };
type Estatisticas = {
  disponivel: boolean;
  motivo?: string | null;
  percentuais?: Record<string, number> | null;
  cobertura_classificada_percentual?: number | null;
  metodo: string;
};
type Revisao = {
  versao: number; status: 'rascunho' | 'aprovado'; provedor_base: Provedor;
  regioes: Regiao[]; estatisticas: Estatisticas | null;
  imagem_url?: string | null; atualizado_em?: string; aprovado_em?: string | null;
};
type DadosEditor = {
  imagem_processada_url: string;
  regioes_propostas_ia: Record<string, Regiao[]>;
  revisao: Revisao | null;
};
const CLASSES: { id: Classe; nome: string; cor: string }[] = [
  { id: 'contorno_lesao', nome: 'Contorno da lesão', cor: '#16a34a' },
  { id: 'granulacao', nome: 'Granulação', cor: '#dc2626' },
  { id: 'esfacelo', nome: 'Esfacelo', cor: '#eab308' },
  { id: 'necrose', nome: 'Necrose', cor: '#64748b' },
  { id: 'pele_perilesional', nome: 'Pele ao redor', cor: '#2563eb' },
  { id: 'nao_classificado', nome: 'Não classificado', cor: '#a855f7' },
];
const PROVEDORES: { id: Provedor; nome: string }[] = [
  { id: 'gemini', nome: 'Gemini' }, { id: 'kimi', nome: 'Kimi' },
  { id: 'openai', nome: 'OpenAI' }, { id: 'manual', nome: 'Desenhar do zero' },
];
const cor = (classe: Classe) => CLASSES.find(c => c.id === classe)?.cor || '#64748b';
const nome = (classe: Classe) => CLASSES.find(c => c.id === classe)?.nome || classe;

function Botao({ texto, onPress, ativo, desabilitado = false }: {
  texto: string; onPress: () => void; ativo?: boolean; desabilitado?: boolean;
}) {
  return <TouchableOpacity onPress={onPress} disabled={desabilitado}
    accessibilityRole="button" style={[styles.botao, ativo && styles.botaoAtivo, desabilitado && styles.desabilitado]}>
    <Text style={[styles.botaoTexto, ativo && styles.botaoTextoAtivo]}>{texto}</Text>
  </TouchableOpacity>;
}

// Segmentos em Views nativas: sem biblioteca gráfica adicional, compatível com Expo Web e Android.
function Segmento({ a, b, largura, altura, corLinha, espessura = 3 }: {
  a: Ponto; b: Ponto; largura: number; altura: number; corLinha: string; espessura?: number;
}) {
  const x1 = a.x * largura, y1 = a.y * altura, x2 = b.x * largura, y2 = b.y * altura;
  const distancia = Math.hypot(x2 - x1, y2 - y1);
  const angulo = Math.atan2(y2 - y1, x2 - x1);
  return <View pointerEvents="none" style={{ position: 'absolute',
    left: (x1 + x2 - distancia) / 2, top: (y1 + y2 - espessura) / 2,
    width: distancia, height: espessura, backgroundColor: corLinha,
    transform: [{ rotate: `${angulo}rad` }],
  }} />;
}

async function enviar<T>(caminho: string, metodo: 'PUT' | 'POST', corpo: object): Promise<T> {
  const token = await obterToken();
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  });
  const json = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = typeof json.detail === 'string' ? json.detail : 'Não foi possível salvar a revisão.';
    throw new Error(detalhe);
  }
  return json as T;
}

export default function EditorMarcacoes({ pacienteId, analiseId }: {
  pacienteId: string; analiseId: number | string;
}) {
  const { width: larguraJanela } = useWindowDimensions();
  const [aberto, setAberto] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [dados, setDados] = useState<DadosEditor | null>(null);
  const [regioes, setRegioes] = useState<Regiao[]>([]);
  const [provedor, setProvedor] = useState<Provedor>('gemini');
  const [classeNova, setClasseNova] = useState<Classe>('contorno_lesao');
  const [pontosNovos, setPontosNovos] = useState<Ponto[]>([]);
  const [selecionada, setSelecionada] = useState<number | null>(null);
  const [verticeSelecionado, setVerticeSelecionado] = useState<number | null>(null);
  const [modo, setModo] = useState<'desenhar' | 'mover' | 'inserir'>('desenhar');
  const [versao, setVersao] = useState(0);
  const [status, setStatus] = useState<'novo' | 'rascunho' | 'aprovado'>('novo');
  const [tamanho, setTamanho] = useState({ largura: 800, altura: 800 });
  const [erro, setErro] = useState('');
  const [alterado, setAlterado] = useState(false);
  const bloqueado = status === 'aprovado';
  const caminho = `/pacientes/${pacienteId}/analises/${analiseId}/marcacoes/editor`;

  const carregar = useCallback(async () => {
    setCarregando(true); setErro('');
    try {
      const recebido = await apiJson<DadosEditor>(caminho);
      setDados(recebido);
      const rev = recebido.revisao;
      setRegioes(rev?.regioes || []);
      setVersao(rev?.versao || 0);
      setStatus(rev?.status || 'novo');
      setProvedor(rev?.provedor_base || 'gemini');
      setSelecionada(null); setVerticeSelecionado(null); setPontosNovos([]); setAlterado(false);
      Image.getSize(recebido.imagem_processada_url,
        (w, h) => setTamanho({ largura: w, altura: h }),
        () => setErro('Não foi possível identificar o tamanho da imagem. Atualize o acesso.'),
      );
    } catch (e) { setErro(e instanceof Error ? e.message : 'Falha ao carregar editor.'); }
    finally { setCarregando(false); }
  }, [caminho]);

  // Recupera a revisão persistida ao entrar/voltar ao relatório, mesmo com o editor fechado.
  useFocusEffect(useCallback(() => { void carregar(); }, [carregar]));
  const largura = Math.max(200, Math.min(560, larguraJanela - 65, 620 * tamanho.largura / tamanho.altura));
  const altura = largura * tamanho.altura / tamanho.largura;

  const importar = () => {
    if (bloqueado || !dados) return;
    const sugestoes = dados.regioes_propostas_ia[provedor] || [];
    if (!sugestoes.length) { Aviso.alert('Sem coordenadas', 'Esta IA não forneceu polígonos válidos. Você pode desenhar manualmente.'); return; }
    const aplicar = () => {
      setRegioes(sugestoes.map(r => ({ ...r, pontos: r.pontos.map(p => ({ ...p })) })));
      setPontosNovos([]); setSelecionada(null); setAlterado(true);
    };
    if (regioes.length) {
      Aviso.alert('Substituir edição?', 'Isso descarta alterações locais ainda não salvas. O relatório original da IA não será alterado.', [
        { text: 'Cancelar', style: 'cancel' }, { text: 'Substituir', onPress: aplicar },
      ]);
    } else aplicar();
  };

  const toque = (px: number, py: number) => {
    if (bloqueado || !Number.isFinite(px) || !Number.isFinite(py)) return;
    const ponto = { x: Math.max(0, Math.min(1, px / largura)), y: Math.max(0, Math.min(1, py / altura)) };
    if (modo === 'desenhar') {
      if (pontosNovos.length >= 60) { Aviso.alert('Limite', 'Cada polígono pode ter até 60 pontos.'); return; }
      setPontosNovos(prev => [...prev, ponto]); setAlterado(true); return;
    }
    if (selecionada == null) return;
    const regiao = regioes[selecionada];
    if (!regiao) return;
    if (modo === 'inserir') {
      if (regiao.pontos.length >= 60) { Aviso.alert('Limite', 'Este polígono já possui 60 pontos.'); return; }
      let melhor = -1, distancia = 24;
      regiao.pontos.forEach((a, i) => {
        const b = regiao.pontos[(i + 1) % regiao.pontos.length];
        const ax = a.x * largura, ay = a.y * altura, bx = b.x * largura, by = b.y * altura;
        const dx = bx - ax, dy = by - ay;
        const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy || 1)));
        const d = Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
        if (d < distancia) { distancia = d; melhor = i; }
      });
      if (melhor >= 0) {
        setRegioes(prev => prev.map((r, i) => i !== selecionada ? r : ({
          ...r, pontos: [...r.pontos.slice(0, melhor + 1), ponto, ...r.pontos.slice(melhor + 1)],
        })));
        setAlterado(true);
      }
      return;
    }
    if (verticeSelecionado != null) {
      setRegioes(prev => prev.map((r, i) => i !== selecionada ? r : ({
        ...r, pontos: r.pontos.map((p, j) => j === verticeSelecionado ? ponto : p),
      })));
      setVerticeSelecionado(null); setAlterado(true);
      return;
    }
    let maisProximo = -1, distancia = 18;
    regiao.pontos.forEach((p, i) => {
      const d = Math.hypot((p.x - ponto.x) * largura, (p.y - ponto.y) * altura);
      if (d < distancia) { distancia = d; maisProximo = i; }
    });
    if (maisProximo >= 0) setVerticeSelecionado(maisProximo);
  };

  const fecharPoligono = () => {
    if (bloqueado || pontosNovos.length < 3) { Aviso.alert('Polígono incompleto', 'Marque pelo menos três pontos.'); return; }
    if (classeNova === 'contorno_lesao' && regioes.some(r => r.classe === 'contorno_lesao')) {
      Aviso.alert('Contorno existente', 'Edite ou exclua o contorno atual antes de desenhar outro.'); return;
    }
    const novo: Regiao = {
      id: `manual_${Date.now()}`, classe: classeNova,
      origem: 'profissional', descricao: 'Delimitação manual do profissional', pontos: pontosNovos,
    };
    setRegioes(prev => [...prev, novo]); setSelecionada(regioes.length);
    setPontosNovos([]); setAlterado(true);
  };

  const mudarClasse = (classe: Classe) => {
    if (bloqueado || selecionada == null) return;
    if (classe === 'contorno_lesao' && regioes.some((r, i) => i !== selecionada && r.classe === 'contorno_lesao')) {
      Aviso.alert('Contorno existente', 'Só pode existir um contorno principal da lesão.'); return;
    }
    setRegioes(prev => prev.map((r, i) => i === selecionada ? { ...r, classe } : r));
    setAlterado(true);
  };

  const salvar = async () => {
    if (!regioes.length || pontosNovos.length) {
      Aviso.alert('Revisão incompleta', 'Conclua o polígono em desenho e mantenha pelo menos uma região.'); return;
    }
    setSalvando(true); setErro('');
    try {
      const resposta = await enviar<{ revisao: Revisao }>(caminho, 'PUT', {
        provedor_base: provedor, revisao_esperada: versao, regioes,
      });
      // Não declarar sucesso até confirmar que o GET recupera a versão salva.
      const confirmado = await apiJson<DadosEditor>(caminho);
      if (confirmado.revisao?.versao !== resposta.revisao.versao ||
          confirmado.revisao.regioes.length !== regioes.length) {
        throw new Error('O servidor respondeu ao salvamento, mas não confirmou a revisão ao consultar novamente. Verifique os logs do Render.');
      }
      setDados(confirmado);
      setRegioes(confirmado.revisao.regioes);
      setVersao(confirmado.revisao.versao); setStatus(confirmado.revisao.status); setAlterado(false);
      Aviso.alert('Rascunho salvo', `Revisão ${confirmado.revisao.versao} confirmada no banco. Abra novamente o relatório para conferir.`);
    } catch (e) { setErro(e instanceof Error ? e.message : 'Falha ao salvar.'); }
    finally { setSalvando(false); }
  };

  const aprovar = () => {
    if (alterado || pontosNovos.length) {
      Aviso.alert('Salve primeiro', 'Salve as alterações antes de aprovar a imagem.'); return;
    }
    if (status !== 'rascunho' || !regioes.some(r => r.classe === 'contorno_lesao')) {
      Aviso.alert('Falta contorno', 'Salve um rascunho com o contorno da lesão antes da aprovação.'); return;
    }
    Aviso.alert('Aprovação profissional', 'Você conferiu os contornos e as classificações? Esta ação bloqueia a edição e registra a versão aprovada. Não substitui a avaliação presencial.', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Confirmar aprovação', onPress: async () => {
        setSalvando(true); setErro('');
        try {
          const resposta = await enviar<{ revisao: Revisao }>(`${caminho}/aprovar`, 'POST', { revisao_esperada: versao });
          const confirmado = await apiJson<DadosEditor>(caminho);
          if (confirmado.revisao?.versao !== resposta.revisao.versao || confirmado.revisao.status !== 'aprovado') {
            throw new Error('A aprovação não pôde ser confirmada ao consultar novamente o servidor.');
          }
          setVersao(confirmado.revisao.versao); setStatus('aprovado');
          setDados(confirmado);
          Aviso.alert('Imagem aprovada', 'A versão aprovada foi confirmada no banco e armazenada separadamente da fotografia original.');
        } catch (e) { setErro(e instanceof Error ? e.message : 'Falha ao aprovar.'); }
        finally { setSalvando(false); }
      } },
    ]);
  };

  const retificar = () => {
    Aviso.alert('Criar retificação', 'A versão aprovada será preservada no histórico. Uma nova versão editável será criada para revisão.', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Criar nova versão', onPress: async () => {
        setSalvando(true); setErro('');
        try {
          const resposta = await enviar<{ revisao: Revisao }>(`${caminho}/retificar`, 'POST', { revisao_esperada: versao });
          setVersao(resposta.revisao.versao); setStatus('rascunho'); setAlterado(false);
          setDados(prev => prev ? { ...prev, revisao: resposta.revisao } : prev);
        } catch (e) { setErro(e instanceof Error ? e.message : 'Falha ao abrir retificação.'); }
        finally { setSalvando(false); }
      } },
    ]);
  };

  const rev = dados?.revisao;
  return <View style={styles.card}>
    <TouchableOpacity onPress={() => setAberto(v => !v)} accessibilityRole="button">
      <Text style={styles.titulo}>{aberto ? '▾ Ocultar editor de marcações' : '▸ Editar imagem e validar tecidos (enfermeiro)'}</Text>
    </TouchableOpacity>
    {!aberto ? <View>
      <Text style={styles.legenda}>Corrigir contornos, atribuir classes e salvar uma imagem revisada sem alterar a fotografia original.</Text>
      {carregando ? <ActivityIndicator size="small" color="#0056b3" /> : null}
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {rev ? <View style={styles.estatisticas}>
        <Text style={styles.subtitulo}>Imagem revisada pelo profissional — {rev.status === 'aprovado' ? 'APROVADA' : 'RASCUNHO'}</Text>
        <Text style={styles.legenda}>Versão {rev.versao} • {rev.regioes.length} região(ões) • Fonte: {rev.provedor_base}.</Text>
        {rev.imagem_url ? <Image source={{ uri: rev.imagem_url }} style={{ width: '100%', height: 280 }} resizeMode="contain" />
          : <Text style={styles.erro}>A revisão está registrada, mas a imagem não está disponível. Abra o editor e atualize o acesso.</Text>}
        <Text style={styles.legenda}>Esta é a imagem corrigida pelo enfermeiro. As imagens acima continuam mostrando as propostas originais das IAs.</Text>
        <Botao texto="Atualizar imagem revisada" onPress={() => void carregar()} desabilitado={carregando} />
      </View> : !carregando && !erro ? <Text style={styles.legenda}>Ainda não existe revisão profissional salva nesta avaliação.</Text> : null}
    </View> : null}
    {aberto ? <View>
      {carregando ? <ActivityIndicator size="large" color="#0056b3" /> : null}
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {dados ? <>
        <Text style={styles.legenda}>Estado: {status === 'aprovado' ? 'Aprovado pelo profissional' : status === 'rascunho' ? `Rascunho salvo (versão ${versao})` : 'Sem revisão salva'}. Nenhuma classificação é atribuída automaticamente a partir da cor da fotografia.</Text>
        <Text style={styles.subtitulo}>Relatório de referência</Text>
        <View style={styles.linha}>{PROVEDORES.map(p => <Botao key={p.id} texto={p.nome} ativo={provedor === p.id}
          desabilitado={bloqueado} onPress={() => { setProvedor(p.id); setAlterado(true); }} />)}</View>
        {!bloqueado ? <Botao texto="Carregar polígonos propostos pela IA selecionada" onPress={importar} /> : null}
        <Text style={styles.subtitulo}>Ferramentas de edição</Text>
        <View style={styles.linha}>
          <Botao texto="Desenhar novo polígono" ativo={modo === 'desenhar'} desabilitado={bloqueado}
            onPress={() => { setModo('desenhar'); setVerticeSelecionado(null); }} />
          <Botao texto="Mover vértice" ativo={modo === 'mover'} desabilitado={bloqueado}
            onPress={() => { setModo('mover'); setPontosNovos([]); }} />
          <Botao texto="Inserir vértice" ativo={modo === 'inserir'} desabilitado={bloqueado}
            onPress={() => { setModo('inserir'); setPontosNovos([]); setVerticeSelecionado(null); }} />
        </View>
        {modo === 'desenhar' && !bloqueado ? <>
          <Text style={styles.legenda}>Selecione a classe e toque na fotografia para marcar os vértices. Depois clique em Concluir polígono.</Text>
          <View style={styles.linha}>{CLASSES.map(c => <Botao key={c.id} texto={c.nome} ativo={classeNova === c.id} onPress={() => setClasseNova(c.id)} />)}</View>
          <View style={styles.linha}>
            <Botao texto={`Concluir polígono (${pontosNovos.length} pontos)`} onPress={fecharPoligono} />
            <Botao texto="Desfazer ponto" onPress={() => setPontosNovos(p => p.slice(0, -1))} />
            <Botao texto="Cancelar desenho" onPress={() => setPontosNovos([])} />
          </View>
        </> : null}
        {modo === 'mover' && !bloqueado ? <Text style={styles.legenda}>Selecione uma região na lista, toque em um vértice na fotografia e depois no local para onde deseja movê-lo.</Text> : null}
        {modo === 'inserir' && !bloqueado ? <Text style={styles.legenda}>Selecione uma região e toque perto de uma de suas linhas para acrescentar um vértice.</Text> : null}
        <View style={[styles.fotoArea, { width: largura, height: altura }]}
          onStartShouldSetResponder={() => !bloqueado}
          onResponderRelease={e => toque(e.nativeEvent.locationX, e.nativeEvent.locationY)}>
          <Image source={{ uri: dados.imagem_processada_url }} style={styles.foto} resizeMode="stretch" pointerEvents="none" />
          {regioes.map((r, i) => r.pontos.map((p, j) => <Segmento key={`${r.id}_${j}`}
            a={p} b={r.pontos[(j + 1) % r.pontos.length]} largura={largura} altura={altura}
            corLinha={cor(r.classe)} espessura={selecionada === i ? 4 : 2} />))}
          {pontosNovos.map((p, j) => j > 0 ? <Segmento key={`novo_${j}`} a={pontosNovos[j - 1]} b={p}
            largura={largura} altura={altura} corLinha="#ffffff" /> : null)}
          {regioes.map((r, i) => selecionada === i ? r.pontos.map((p, j) => <View pointerEvents="none"
            key={`vertice_${j}`} style={[styles.vertice, { left: p.x * largura - 7, top: p.y * altura - 7,
              borderColor: verticeSelecionado === j ? '#ffffff' : cor(r.classe) }]} />) : null)}
          {pontosNovos.map((p, j) => <View key={`ponto_novo_${j}`} pointerEvents="none"
            style={[styles.vertice, { left: p.x * largura - 7, top: p.y * altura - 7, borderColor: '#ffffff' }]} />)}
        </View>
        <Text style={styles.legenda}>Linhas são propostas/revisões geométricas. A fotografia original é preservada. Evite sobrepor polígonos de classes diferentes.</Text>
        <Text style={styles.subtitulo}>Regiões ({regioes.length})</Text>
        <View style={styles.linha}>{regioes.map((r, i) => <Botao key={r.id} texto={`${i + 1}. ${nome(r.classe)}`}
          ativo={selecionada === i} onPress={() => { setSelecionada(i); setVerticeSelecionado(null); }} />)}</View>
        {selecionada != null && regioes[selecionada] && !bloqueado ? <View style={styles.selecionada}>
          <Text style={styles.subtitulo}>Alterar classe da região {selecionada + 1}</Text>
          <View style={styles.linha}>{CLASSES.map(c => <Botao key={c.id} texto={c.nome}
            ativo={regioes[selecionada].classe === c.id} onPress={() => mudarClasse(c.id)} />)}</View>
          {verticeSelecionado != null && regioes[selecionada].pontos.length > 3 ?
            <Botao texto="Remover vértice selecionado" onPress={() => {
              setRegioes(prev => prev.map((r, i) => i !== selecionada ? r : ({
                ...r, pontos: r.pontos.filter((_, j) => j !== verticeSelecionado),
              })));
              setVerticeSelecionado(null); setAlterado(true);
            }} /> : null}
          <Botao texto="Excluir região selecionada" onPress={() => {
            setRegioes(prev => prev.filter((_, i) => i !== selecionada));
            setSelecionada(null); setVerticeSelecionado(null); setAlterado(true);
          }} />
        </View> : null}
        {rev?.estatisticas ? <View style={styles.estatisticas}>
          <Text style={styles.subtitulo}>Proporções da última versão salva</Text>
          {rev.estatisticas.disponivel && rev.estatisticas.percentuais ? Object.entries(rev.estatisticas.percentuais).map(([classe, percentual]) =>
            <Text key={classe} style={styles.legenda}>{nome(classe as Classe)}: {percentual.toLocaleString('pt-BR')}%</Text>)
            : <Text style={styles.legenda}>{rev.estatisticas.motivo || 'Sem contorno delimitado.'}</Text>}
          <Text style={styles.legenda}>{rev.estatisticas.metodo}</Text>
        </View> : null}
        {rev?.imagem_url ? <View style={styles.estatisticas}>
          <Text style={styles.subtitulo}>Imagem salva — {rev.status}</Text>
          <Image source={{ uri: rev.imagem_url }} style={{ width: '100%', height: 250 }} resizeMode="contain" />
        </View> : null}
        {!bloqueado ? <View style={styles.linha}>
          <Botao texto={salvando ? 'Salvando...' : 'Salvar rascunho e gerar imagem'} onPress={() => void salvar()} desabilitado={salvando} />
          <Botao texto="Aprovar imagem revisada" onPress={aprovar} desabilitado={salvando || status !== 'rascunho'} />
          <Botao texto="Descartar mudanças locais" onPress={() => void carregar()} desabilitado={salvando} />
        </View> : <View><Text style={styles.aprovado}>Imagem aprovada. Versões anteriores preservadas no histórico de auditoria.</Text><Botao texto="Criar retificação da imagem aprovada" onPress={retificar} desabilitado={salvando} /></View>}
        <Text style={styles.legenda}>A aprovação da imagem é independente da aprovação do relatório T.I.M.E.S. Não se calculam cm² a partir desses polígonos sem referência de escala validada.</Text>
      </> : null}
    </View> : null}
  </View>;
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderColor: '#cbd5e1', borderWidth: 1, borderRadius: 10, padding: 14, marginBottom: 14 },
  titulo: { fontWeight: 'bold', fontSize: 16, color: '#0056b3', marginBottom: 9 },
  subtitulo: { fontWeight: 'bold', fontSize: 13, color: '#1e293b', marginTop: 14, marginBottom: 7 },
  legenda: { fontSize: 12, color: '#475569', lineHeight: 18, marginTop: 6, marginBottom: 6 },
  linha: { flexDirection: 'row', flexWrap: 'wrap', gap: 7, marginBottom: 8 },
  botao: { borderWidth: 1, borderColor: '#93c5fd', borderRadius: 7, paddingHorizontal: 10, paddingVertical: 9, marginBottom: 2 },
  botaoAtivo: { backgroundColor: '#dbeafe', borderColor: '#0056b3' },
  botaoTexto: { fontSize: 12, color: '#0056b3', fontWeight: '600' },
  botaoTextoAtivo: { color: '#1d4ed8' },
  desabilitado: { opacity: .45 },
  fotoArea: { position: 'relative', alignSelf: 'center', backgroundColor: '#e2e8f0', overflow: 'hidden', marginTop: 10, marginBottom: 10 },
  foto: { width: '100%', height: '100%', position: 'absolute' },
  vertice: { position: 'absolute', width: 14, height: 14, borderRadius: 7, borderWidth: 3, backgroundColor: '#111827' },
  selecionada: { backgroundColor: '#f8fafc', padding: 10, borderRadius: 8 },
  estatisticas: { backgroundColor: '#f8fafc', borderRadius: 8, padding: 12, marginTop: 10 },
  erro: { color: '#b91c1c', fontSize: 13, marginBottom: 10 },
  aprovado: { color: '#15803d', fontWeight: 'bold', marginTop: 10 },
});
