import { useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, Text } from 'react-native';

import { apiJson } from '../config/cliente';
import type { RespostaEstruturadaIA } from '../types/ia';
import type { AnaliseResumo, Paciente } from '../types/paciente';
import { formatarData } from '../types/paciente';
import { Aviso } from '../utils/avisos';
import type { MarcacaoIA } from './fotografias-avaliacao';

type Props = {
  analiseId: string;
  pacienteId: string;
  provedor: string;
  aprovadoEm: string | null;
  relatorio: RespostaEstruturadaIA;
};

type DadosEditor = {
  revisao: {
    status: string;
    provedor_base: string;
    imagem_url?: string | null;
    estatisticas?: {
      disponivel: boolean;
      percentuais?: Record<string, number> | null;
    } | null;
  } | null;
};

type RespostaMarcacoes = {
  marcacoes_por_ia?: Record<string, MarcacaoIA>;
};

const modelos: Record<string, { ia: string; provedor: string }> = {
  gemini: { ia: 'Gemini', provedor: 'Google' },
  openai: { ia: 'OpenAI', provedor: 'OpenAI' },
  kimi: { ia: 'Kimi', provedor: 'Moonshot AI' },
};

const nomesTecidos: Record<string, string> = {
  granulacao: 'Granulação',
  esfacelo: 'Esfacelo',
  necrose: 'Necrose',
  nao_classificado: 'Não classificado',
};

const estadosTimes: Record<string, string> = {
  avaliavel: 'Avaliável',
  parcialmente_avaliavel: 'Parcialmente avaliável',
  nao_avaliavel: 'Não avaliável',
};

const entidades: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

function textoHtml(valor: string | number | null | undefined) {
  return String(valor ?? 'Não informado')
    .replace(/[&<>"']/g, caractere => entidades[caractere]);
}

function listaHtml(titulo: string, itens?: string[]) {
  if (!itens?.length) return '';

  const linhas = itens.map(item => `<li>${textoHtml(item)}</li>`).join('');

  return `<p><strong>${textoHtml(titulo)}</strong></p><ul>${linhas}</ul>`;
}

function urlDaImagem(url?: string | null) {
  if (!url) return null;

  try {
    const endereco = new URL(url);
    return endereco.protocol === 'https:' ? endereco.href : null;
  } catch {
    return null;
  }
}

async function buscarMarcacao(caminho: string, provedor: string) {
  const resposta = await apiJson<RespostaMarcacoes>(`${caminho}/marcacoes`);
  const marcacao = resposta.marcacoes_por_ia?.[provedor];

  if (marcacao?.status !== 'pendente') return marcacao;

  const geradas = await apiJson<RespostaMarcacoes>(
    `${caminho}/marcacoes/gerar`,
    { method: 'POST' },
  );

  return geradas.marcacoes_por_ia?.[provedor];
}

function montarRelatorio(
  props: Props,
  paciente: Paciente,
  dataAvaliacao: string | null,
  revisao: DadosEditor['revisao'],
  marcacao?: MarcacaoIA,
) {
  const { analiseId, aprovadoEm, relatorio } = props;
  const chave = props.provedor.trim().toLowerCase();
  const identidade = modelos[chave] ?? {
    ia: props.provedor,
    provedor: props.provedor,
  };

  const urlRevisada = urlDaImagem(revisao?.imagem_url);
  const urlProposta = marcacao?.status === 'pronta'
    ? urlDaImagem(marcacao.url)
    : null;
  const imagem = urlRevisada ?? urlProposta;

  const legendaImagem = urlRevisada
    ? 'Imagem revisada e aprovada pelo profissional.'
    : `Proposta de marcação da IA ${identidade.ia}. Os contornos aguardam validação profissional.`;

  const estatisticas = revisao?.estatisticas;
  const percentuais = Object.entries(
    estatisticas?.disponivel ? estatisticas.percentuais ?? {} : {},
  ).filter(([, valor]) => Number.isFinite(valor) && valor >= 0 && valor <= 100);

  const tabela = percentuais.length
    ? `<table>
        <thead><tr><th>Tecido</th><th>Proporção em pixels</th></tr></thead>
        <tbody>${percentuais.map(([classe, valor]) => `
          <tr>
            <td>${textoHtml(nomesTecidos[classe] ?? classe)}</td>
            <td>${textoHtml(valor.toLocaleString('pt-BR'))}%</td>
          </tr>
        `).join('')}</tbody>
      </table>`
    : '<p>Percentuais indisponíveis sem segmentação aprovada.</p>';

  const confianca = relatorio.confianca_avaliacao_percentual;
  const confiancaValida =
    typeof confianca === 'number' &&
    Number.isFinite(confianca) &&
    confianca >= 0 && confianca <= 100;

  const confiancaTexto = confiancaValida
    ? `${confianca.toLocaleString('pt-BR')}%`
    : 'Não informada';

  const dados = relatorio.dados_clinicos_organizados;
  const componentes = (relatorio.avaliacao_times ?? []).map(item => `
    <article>
      <h3>${textoHtml(item.componente)} — ${textoHtml(item.nome)}</h3>
      <p>${textoHtml(estadosTimes[item.status] ?? item.status)}</p>
      ${listaHtml('Observações visuais', item.observacoes_visuais)}
      ${listaHtml('Dados clínicos relacionados', item.dados_clinicos_relacionados)}
      ${listaHtml('Informações pendentes', item.informacoes_pendentes)}
      ${listaHtml('Limitações', item.limitacoes)}
    </article>
  `).join('');

  const sugestoes = relatorio.plano_cuidados_proposto?.sugestoes ?? [];
  const plano = sugestoes.map(item => `
    <article>
      <h3>${textoHtml(item.titulo)}</h3>
      <p>${textoHtml(item.justificativa)}</p>
      ${listaHtml('Dados a confirmar', item.dados_a_confirmar)}
    </article>
  `).join('');

  return `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Avalia &amp; Trata — Avaliação ${textoHtml(analiseId)}</title>
  <style>
    @page { size: A4; margin: 15mm; }
    body { margin: 0; font: 11pt Arial, sans-serif; color: #243746; overflow-wrap: anywhere; }
    header { border-bottom: 2px solid #005088; padding-bottom: 8px; }
    h1 { font-size: 20pt; color: #005088; margin: 4px 0; }
    h2 { font-size: 13pt; color: #005088; border-left: 3px solid #23817a;
         padding-left: 8px; margin: 18px 0 8px; break-after: avoid; }
    h3 { font-size: 11pt; margin: 10px 0 3px; break-after: avoid; }
    p, ul { margin: 4px 0 8px; line-height: 1.4; }
    p { white-space: pre-wrap; }
    img { display: block; max-width: 100%; max-height: 90mm; object-fit: contain; }
    figure { margin: 8px 0 12px; break-inside: avoid; }
    figcaption { margin-top: 6px; font-size: 10pt; color: #475569; }
    table { width: 100%; border-collapse: collapse; }
    td, th { padding: 6px; text-align: left; border-bottom: 1px solid #dce6ed; }
    tr, .assinatura { break-inside: avoid; }
  </style>
</head>
<body>
  <header>
    <strong>Avalia &amp; Trata</strong>
    <h1>Relatório de Análise Clínica</h1>
    <p>Avaliação #${textoHtml(analiseId)}</p>
  </header>

  <h2>Dados do paciente</h2>
  <p><strong>Paciente:</strong> ${textoHtml(paciente.nome_completo)}</p>
  <p><strong>Prontuário:</strong> ${textoHtml(paciente.id_paciente)}</p>
  <p><strong>Data da avaliação:</strong> ${textoHtml(formatarData(dataAvaliacao))}</p>
  <p><strong>Diagnóstico de base:</strong> ${textoHtml(paciente.diagnostico)}</p>
  <p><strong>Localização da lesão:</strong> ${textoHtml(dados?.localizacao ?? paciente.local_lesao)}</p>

  <h2>Identificação da análise por IA</h2>
  <p><strong>IA utilizada:</strong> ${textoHtml(identidade.ia)}</p>
  <p><strong>Provedor:</strong> ${textoHtml(identidade.provedor)}</p>
  <p><strong>Confiança autodeclarada:</strong> ${textoHtml(confiancaTexto)}</p>
  ${relatorio.justificativa_confianca_avaliacao
    ? `<p><strong>Justificativa:</strong> ${textoHtml(relatorio.justificativa_confianca_avaliacao)}</p>`
    : ''}
  ${listaHtml('Limitações da confiança', relatorio.limitacoes_confianca_avaliacao)}

  <h2>Imagem com marcações</h2>
  ${imagem
    ? `<figure>
        <img src="${textoHtml(imagem)}" alt="${textoHtml(legendaImagem)}">
        <figcaption>${textoHtml(legendaImagem)}</figcaption>
      </figure>`
    : '<p>Imagem com marcações indisponível para a análise selecionada.</p>'}
  ${tabela}

  <h2>Descrição revisada</h2>
  <p>${textoHtml(relatorio.conteudo_descricao)}</p>

  <h2>Avaliação T.I.M.E.S.</h2>
  ${componentes || '<p>Componentes indisponíveis neste relatório.</p>'}

  <h2>Plano de cuidados sugerido pela IA</h2>
  ${plano || '<p>Nenhuma sugestão registrada.</p>'}

  <section class="assinatura">
    <h2>Validação profissional</h2>
    <p><strong>Aprovação do relatório no sistema:</strong> ${textoHtml(formatarData(aprovadoEm))}</p>
    <p>A análise automatizada auxilia o registro e exige revisão profissional. A confiança autodeclarada não representa acurácia clínica.</p>
    <p>Assinatura: __________________________________________________</p>
    <p>Carimbo/COREN: __________________________ Data: ____/____/________</p>
  </section>
</body>
</html>`;
}

function aguardarImagem(imagem: HTMLImageElement) {
  return new Promise<boolean>(resolve => {
    const concluir = (carregou: boolean) => {
      window.clearTimeout(limite);
      imagem.onload = null;
      imagem.onerror = null;
      resolve(carregou);
    };

    const limite = window.setTimeout(() => concluir(false), 12000);
    imagem.onload = () => concluir(true);
    imagem.onerror = () => concluir(false);

    if (imagem.complete) concluir(imagem.naturalWidth > 0);
  });
}

async function imprimirRelatorio(html: string) {
  const quadro = document.createElement('iframe');
  quadro.title = 'Relatório para impressão';
  quadro.style.cssText =
    'position:fixed;left:-10000px;top:0;width:794px;height:1123px;border:0';
  document.body.appendChild(quadro);

  try {
    const janela = quadro.contentWindow;
    const pagina = quadro.contentDocument;

    if (!janela || !pagina) {
      throw new Error('Não foi possível preparar a página de impressão.');
    }

    pagina.open();
    pagina.write(html);
    pagina.close();

    const imagem = pagina.querySelector('img');

    if (imagem && !(await aguardarImagem(imagem))) {
      throw new Error(
        'A imagem marcada não carregou. Atualize o acesso às fotografias e gere o PDF novamente.',
      );
    }

    janela.addEventListener('afterprint', () => quadro.remove(), { once: true });
    janela.focus();
    janela.print();
  } catch (erro) {
    quadro.remove();
    throw erro;
  }
}

export default function BotaoRelatorioPdf(props: Props) {
  const [gerando, setGerando] = useState(false);
  const emAndamento = useRef(false);

  if (Platform.OS !== 'web') return null;

  async function gerar() {
    if (emAndamento.current) return;

    emAndamento.current = true;
    setGerando(true);

    const pacienteUrl = `/pacientes/${props.pacienteId}`;
    const avaliacoesUrl = `${pacienteUrl}/analises`;
    const caminho = `${avaliacoesUrl}/${props.analiseId}`;
    const provedor = props.provedor.trim().toLowerCase();

    try {
      const [paciente, avaliacoes, editor] = await Promise.all([
        apiJson<Paciente>(pacienteUrl),
        apiJson<AnaliseResumo[]>(avaliacoesUrl),
        apiJson<DadosEditor>(`${caminho}/marcacoes/editor`)
          .catch((): DadosEditor => ({ revisao: null })),
      ]);

      const avaliacao = avaliacoes.find(
        item => String(item.id_analise) === props.analiseId,
      );

      if (!avaliacao) {
        throw new Error('A avaliação não foi localizada no histórico deste paciente.');
      }

      const revisao = editor.revisao;
      const imagemAprovada =
        revisao?.status === 'aprovado' &&
        (revisao.provedor_base === provedor || revisao.provedor_base === 'manual') &&
        urlDaImagem(revisao.imagem_url)
          ? revisao
          : null;

      const marcacao = imagemAprovada
        ? undefined
        : await buscarMarcacao(caminho, provedor);

      await imprimirRelatorio(
        montarRelatorio(props, paciente, avaliacao.data_analise, imagemAprovada, marcacao),
      );
    } catch (erro) {
      Aviso.alert(
        'Falha ao preparar o PDF',
        erro instanceof Error ? erro.message : 'Tente novamente.',
      );
    } finally {
      emAndamento.current = false;
      setGerando(false);
    }
  }

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: gerando, busy: gerando }}
      onPress={() => void gerar()}
      disabled={gerando}
      style={[styles.botao, gerando && styles.desabilitado]}
    >
      <Text style={styles.texto}>{gerando ? 'Preparando relatório…' : 'Gerar PDF'}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  botao: {
    backgroundColor: '#005088',
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 14,
    marginVertical: 10,
  },
  desabilitado: { opacity: 0.6 },
  texto: { color: '#fff', fontWeight: '700' },
});