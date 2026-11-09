import { useState, type ReactNode } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { RespostaEstruturadaIA } from '../types/ia';

const NOMES: Record<string, string> = {
  T: 'Tecido', I: 'Inflamação / Infecção', M: 'Umidade', E: 'Bordas', S: 'Pele ao redor',
};

function Lista({ titulo, itens }: { titulo?: string; itens?: string[] | null }) {
  if (!itens?.length) return null;
  return <View style={styles.grupo}>
    {titulo ? <Text style={styles.rotulo}>{titulo}</Text> : null}
    {itens.map((item, indice) => <Text key={`${indice}-${item}`} style={styles.texto}>• {item}</Text>)}
  </View>;
}
function Linha({ titulo, valor }: { titulo: string; valor: string | number | null | undefined }) {
  return <Text style={styles.texto}><Text style={styles.rotulo}>{titulo}: </Text>{valor === null || valor === undefined || valor === '' ? 'Não informado' : String(valor)}</Text>;
}
function Secao({ titulo, children, quantidade }: { titulo: string; children: ReactNode; quantidade?: number }) {
  const [aberta, setAberta] = useState(false);
  return <View style={styles.secao}>
    <TouchableOpacity accessibilityRole="button" accessibilityLabel={`${aberta ? 'Recolher' : 'Expandir'} ${titulo}`} onPress={() => setAberta(!aberta)} style={styles.cabecalho}>
      <Text style={styles.subtitulo}>{aberta ? '▾' : '▸'} {titulo}{quantidade !== undefined ? ` (${quantidade})` : ''}</Text>
      <Text style={styles.indicador}>{aberta ? 'Recolher' : 'Ver detalhes'}</Text>
    </TouchableOpacity>
    {aberta ? <View style={styles.conteudo}>{children}</View> : null}
  </View>;
}
function Bloco({ children }: { children: ReactNode }) {
  return <View style={styles.bloco}>{children}</View>;
}
function fmtArea(valor: number | null | undefined) {
  return valor == null ? 'Não calculada' : `${valor.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} cm²`;
}

/** Mantém todas as informações do JSON; apenas recolhe seções extensas. */
export default function RelatorioCompleto({ resposta, mostrarDescricao = true }: { resposta: RespostaEstruturadaIA; mostrarDescricao?: boolean }) {
  const tecidos = resposta.avaliacao_tecidos;
  const marcacoes = resposta.marcacoes_imagem;
  const plano = resposta.plano_cuidados_proposto;
  const medidas = resposta.medidas;
  const dados = resposta.dados_clinicos_organizados;
  const pontos = resposta.pontos_para_revisao_profissional || [];
  const sugestoes = plano?.sugestoes || [];

  return <View>
    <View style={styles.descricao}>
      {mostrarDescricao ? <>
        <Text style={styles.rotulo}>Descrição geral</Text>
        <Text style={styles.texto}>{resposta.conteudo_descricao || 'Não informada.'}</Text>
      </> : null}
      <Linha titulo="Estado da resposta" valor={resposta.status_resposta} />
      <Linha titulo="Revisão profissional necessária" valor={resposta.validacao_profissional_necessaria ? 'Sim' : 'Não'} />
    </View>

    <Secao titulo="Qualidade da fotografia">
      <Linha titulo="Estado" valor={resposta.qualidade_imagem?.status} />
      <Lista titulo="Observações" itens={resposta.qualidade_imagem?.observacoes} />
      <Lista titulo="Limitações da fotografia" itens={resposta.qualidade_imagem?.limitacoes} />
    </Secao>

    <Secao titulo="Características visuais" quantidade={resposta.caracteristicas_visuais?.length || 0}>
      {resposta.caracteristicas_visuais?.length ? resposta.caracteristicas_visuais.map((item, i) => <Bloco key={i}>
        <Text style={styles.rotulo}>{item.caracteristica}</Text>
        <Text style={styles.texto}>{item.descricao}</Text>
        <Linha titulo="Estado" valor={item.status} />
        {item.confianca_autodeclarada ? <Linha titulo="Confiança declarada" valor={item.confianca_autodeclarada} /> : null}
        {item.justificativa ? <Linha titulo="Justificativa" valor={item.justificativa} /> : null}
      </Bloco>) : <Text style={styles.texto}>Sem características estruturadas disponíveis.</Text>}
    </Secao>

    <Secao titulo="Avaliação T.I.M.E.S." quantidade={5}>
      {Object.entries(NOMES).map(([letra, nome]) => {
        const componente = resposta.avaliacao_times?.find(item => item.componente === letra);
        return <Bloco key={letra}>
          <Text style={styles.rotulo}>{letra} — {componente?.nome || nome}</Text>
          <Linha titulo="Estado" valor={componente?.status || 'Não avaliado'} />
          <Lista titulo="Observações visuais" itens={componente?.observacoes_visuais} />
          <Lista titulo="Dados clínicos relacionados" itens={componente?.dados_clinicos_relacionados} />
          <Lista titulo="Informações pendentes" itens={componente?.informacoes_pendentes} />
          <Lista titulo="Limitações específicas" itens={componente?.limitacoes} />
        </Bloco>;
      })}
    </Secao>

    <Secao titulo="Caracterização visual dos tecidos" quantidade={tecidos?.tecidos?.length || 0}>
      <Linha titulo="Estado" valor={tecidos?.status} />
      {tecidos?.metodo_estimativa ? <Linha titulo="Método informado" valor={tecidos.metodo_estimativa} /> : null}
      {tecidos?.tecidos?.length ? tecidos.tecidos.map((item, i) => <Bloco key={i}>
        <Linha titulo="Tipo registrado" valor={item.tipo} />
        <Linha titulo="Descrição visual" valor={item.descricao_visual} />
        <Linha titulo="Percentual estimado" valor={item.percentual_estimado == null ? 'Não estimado' : `${item.percentual_estimado}%`} />
        <Linha titulo="Confiança declarada" valor={item.confianca_autodeclarada} />
        {item.justificativa ? <Linha titulo="Justificativa" valor={item.justificativa} /> : null}
        <Linha titulo="Revisão necessária" valor={item.revisao_profissional_necessaria ? 'Sim' : 'Não'} />
      </Bloco>) : <Text style={styles.texto}>{marcacoes?.regioes?.some(r => r.classificacao_tecido_proposta && r.classificacao_tecido_proposta !== 'nao_classificado')
        ? 'Existem hipóteses de tecido propostas pela IA na seção “Regiões propostas na fotografia”. Sem percentuais automáticos.'
        : 'Nenhuma classificação visual de tecido disponível.'}</Text>}
      <Lista titulo="Limitações" itens={tecidos?.limitacoes} />
    </Secao>

    <Secao titulo="Medidas e cálculos">
      <Linha titulo="Comprimento informado" valor={medidas?.comprimento_informado_cm ? `${medidas.comprimento_informado_cm} cm` : null} />
      <Linha titulo="Largura informada" valor={medidas?.largura_informada_cm ? `${medidas.largura_informada_cm} cm` : null} />
      <Linha titulo="Área real medida/segmentada" valor={medidas?.area_calculada_cm2 == null ? 'Não calculada' : fmtArea(medidas.area_calculada_cm2)} />
      {medidas?.area_retangulo_delimitador_cm2 != null ? <Linha titulo="Área do retângulo delimitador (estimativa)" valor={fmtArea(medidas.area_retangulo_delimitador_cm2)} /> : null}
      {medidas?.area_elipse_aproximada_cm2 != null ? <Linha titulo="Área elíptica aproximada (estimativa)" valor={fmtArea(medidas.area_elipse_aproximada_cm2)} /> : null}
      <Linha titulo="Método de medição real" valor={medidas?.metodo_medicao} />
      <Lista titulo="Observações" itens={medidas?.observacoes} />
    </Secao>

    <Secao titulo="Regiões propostas na fotografia" quantidade={marcacoes?.regioes?.length || 0}>
      <Linha titulo="Sistema de coordenadas" valor={marcacoes?.sistema_coordenadas} />
      <Linha titulo="Imagem de referência" valor={marcacoes?.imagem_referencia} />
      {marcacoes?.regioes?.length ? marcacoes.regioes.map((regiao, i) => <Bloco key={i}>
        <Linha titulo="Região" valor={regiao.rotulo} />
        <Linha titulo="Identificador" valor={regiao.identificador} />
        <Linha titulo="Descrição" valor={regiao.descricao} />
        <Linha titulo="Hipótese de tecido proposta pela IA" valor={regiao.classificacao_tecido_proposta || 'Não classificado'} />
        {regiao.justificativa_classificacao ? <Linha titulo="Evidências e limitações da hipótese" valor={regiao.justificativa_classificacao} /> : null}
        {regiao.confianca_classificacao_autodeclarada ? <Linha titulo="Confiança autodeclarada na hipótese" valor={regiao.confianca_classificacao_autodeclarada} /> : null}
        <Linha titulo="Confiança declarada" valor={regiao.confianca_autodeclarada} />
        <Linha titulo="Revisão necessária" valor={regiao.revisao_profissional_necessaria ? 'Sim' : 'Não'} />
        <Text style={styles.menor}>Coordenadas propostas ({regiao.pontos?.length || 0} pontos): {(regiao.pontos || []).map(p => `(${p.x.toFixed(3)}, ${p.y.toFixed(3)})`).join(' · ') || 'Não informadas'}</Text>
      </Bloco>) : <Text style={styles.texto}>Nenhuma região delimitada com geometria suficiente.</Text>}
      <Lista titulo="Limitações das marcações" itens={marcacoes?.limitacoes} />
    </Secao>

    <Secao titulo="Pontos de atenção para validação profissional" quantidade={pontos.length + sugestoes.length}>
      <Linha titulo="Situação das sugestões estruturadas" valor={plano?.status || 'Não informado'} />
      {sugestoes.length ? <>
        <Text style={styles.rotulo}>Sugestões estruturadas para conferência (não são prescrições)</Text>
        {sugestoes.map((item, i) => <Bloco key={i}>
          <Linha titulo="Título" valor={item.titulo} />
          <Linha titulo="Justificativa" valor={item.justificativa} />
          <Lista titulo="Dados a confirmar" itens={item.dados_a_confirmar} />
          <Linha titulo="Depende de validação profissional" valor={item.depende_validacao_profissional ? 'Sim' : 'Não'} />
        </Bloco>)}
      </> : <Text style={styles.menor}>Nenhuma sugestão de cuidado estruturada foi retornada.</Text>}
      <Lista titulo="Observações sobre as sugestões" itens={plano?.observacoes} />
      <Lista titulo="Questões e alertas para revisão" itens={pontos} />
      {!pontos.length && !sugestoes.length && !plano?.observacoes?.length ? <Text style={styles.menor}>Nenhum tópico adicional registrado.</Text> : null}
    </Secao>

    <Secao titulo="Dados clínicos organizados">
      {dados ? <>
        <Linha titulo="Localização" valor={dados.localizacao} />
        <Linha titulo="Comprimento" valor={dados.comprimento} />
        <Linha titulo="Largura" valor={dados.largura} />
        <Linha titulo="Tipo de exsudato" valor={dados.tipo_exsudato} />
        <Linha titulo="Odor informado" valor={dados.odor == null ? 'Não informado' : dados.odor ? 'Presente' : 'Ausente'} />
        <Linha titulo="Nível de dor" valor={dados.nivel_dor} />
        <Linha titulo="Queixa principal" valor={dados.queixa_principal} />
        <Linha titulo="Observações clínicas" valor={dados.observacoes} />
        <Lista titulo="Campos não informados" itens={dados.dados_nao_informados} />
      </> : <Text style={styles.menor}>Não disponíveis.</Text>}
    </Secao>

    <Secao titulo="Limitações gerais" quantidade={resposta.limitacoes_declaradas?.length || 0}>
      <Lista itens={resposta.limitacoes_declaradas} />
      {!resposta.limitacoes_declaradas?.length ? <Text style={styles.menor}>Nenhuma limitação geral adicional informada.</Text> : null}
      <Text style={styles.menor}>Limitações específicas permanecem integralmente registradas nas respectivas seções acima.</Text>
    </Secao>
  </View>;
}

const styles = StyleSheet.create({
  descricao: { backgroundColor: '#f8fafc', padding: 12, borderRadius: 8, marginTop: 8 },
  secao: { borderTopWidth: 1, borderTopColor: '#e2e8f0', marginTop: 8 },
  cabecalho: { paddingVertical: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' },
  conteudo: { paddingBottom: 10 },
  subtitulo: { color: '#0056b3', fontWeight: 'bold', fontSize: 13, flexShrink: 1 },
  indicador: { color: '#64748b', fontSize: 11 },
  rotulo: { color: '#334155', fontSize: 12, fontWeight: 'bold' },
  texto: { color: '#334155', fontSize: 12, lineHeight: 19, marginTop: 4 },
  menor: { color: '#64748b', fontSize: 11, lineHeight: 17, marginTop: 5 },
  grupo: { marginTop: 8 },
  bloco: { backgroundColor: '#f1f5f9', padding: 10, borderRadius: 7, marginVertical: 5 },
});
