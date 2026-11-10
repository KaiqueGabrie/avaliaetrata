
import { StyleSheet, Text, View } from 'react-native';
import type { MarcacaoIA } from './fotografias-avaliacao';

type Provedor = 'openai' | 'gemini' | 'kimi';
type Classe = 'granulacao' | 'esfacelo' | 'necrose';

type Props = {
  marcacoes: Record<string, MarcacaoIA>;
};

const PROVEDORES: { id: Provedor; nome: string }[] = [
  { id: 'openai', nome: 'OpenAI' },
  { id: 'gemini', nome: 'Gemini' },
  { id: 'kimi', nome: 'Kimi' },
];

const CLASSES: { id: Classe; nome: string }[] = [
  { id: 'granulacao', nome: 'Granulação' },
  { id: 'esfacelo', nome: 'Esfacelo' },
  { id: 'necrose', nome: 'Necrose' },
];

function contarClasse(
  dados: MarcacaoIA | undefined,
  classe: Classe
): number {
  return (dados?.detalhes_regioes ?? []).filter(
    regiao => regiao.classificacao_proposta === classe
  ).length;
}

function possuiDados(dados: MarcacaoIA | undefined): boolean {
  return !!dados && Array.isArray(dados.detalhes_regioes);
}

export default function ComparacaoTecidosIA({
  marcacoes,
}: Props) {
  const disponiveis = PROVEDORES.filter(provedor =>
    possuiDados(marcacoes[provedor.id])
  );

  if (disponiveis.length === 0) return null;

  const divergencias = CLASSES.filter(classe => {
    if (disponiveis.length < 2) return false;

    const quantidades = disponiveis.map(provedor =>
      contarClasse(marcacoes[provedor.id], classe.id)
    );

    return quantidades.some(valor => valor !== quantidades[0]);
  });

  return (
    <View style={styles.container}>
      <Text style={styles.titulo}>
        Comparação das hipóteses de tecido
      </Text>

      <Text style={styles.descricao}>
        Comparação das classificações propostas pelas IAs.
        Os números representam regiões, não porcentagens
        da lesão ou confirmação clínica.
      </Text>

      <View style={styles.tabela}>
        <View style={styles.linhaCabecalho}>
          <Text style={[styles.celula, styles.classe]}>
            Tecido
          </Text>

          {PROVEDORES.map(provedor => (
            <Text
              key={provedor.id}
              style={[styles.celula, styles.cabecalho]}
            >
              {provedor.nome}
            </Text>
          ))}
        </View>

        {CLASSES.map(classe => (
          <View key={classe.id} style={styles.linha}>
            <Text style={[styles.celula, styles.classe]}>
              {classe.nome}
            </Text>

            {PROVEDORES.map(provedor => {
              const dados = marcacoes[provedor.id];
              const disponivel = possuiDados(dados);
              const quantidade = contarClasse(dados, classe.id);

              return (
                <Text key={provedor.id} style={styles.celula}>
                  {!disponivel
                    ? 'Indisp.'
                    : quantidade > 0
                      ? `${quantidade} proposta(s)`
                      : 'Não proposta'}
                </Text>
              );
            })}
          </View>
        ))}
      </View>

      <Text style={styles.subtitulo}>
        Diferenças identificadas
      </Text>

      {disponiveis.length < 2 ? (
        <Text style={styles.descricao}>
          São necessárias propostas de pelo menos duas
          IAs para comparar os resultados.
        </Text>
      ) : divergencias.length > 0 ? (
        divergencias.map(classe => (
          <Text key={classe.id} style={styles.alerta}>
            • {classe.nome}: as IAs apresentaram
            quantidades diferentes de regiões classificadas.
          </Text>
        ))
      ) : (
        <Text style={styles.descricao}>
          Não foram encontradas diferenças nas quantidades
          de regiões classificadas por tecido.
          Isso não comprova concordância clínica ou
          espacial entre os modelos.
        </Text>
      )}

      <Text style={styles.aviso}>
        Atenção: ausência de classificação não significa
        ausência de tecido. As regiões não classificadas,
        os contornos da lesão e a pele ao redor não são
        contabilizados como hipóteses de tecido.
        A validação pertence ao enfermeiro.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 10,
    padding: 14,
    marginTop: 14,
    marginBottom: 12,
  },
  titulo: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 8,
  },
  subtitulo: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#334155',
    marginTop: 14,
    marginBottom: 6,
  },
  descricao: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 18,
    marginBottom: 8,
  },
  tabela: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 6,
    overflow: 'hidden',
    marginTop: 8,
  },
  linhaCabecalho: {
    flexDirection: 'row',
    backgroundColor: '#dbeafe',
    paddingVertical: 10,
  },
  linha: {
    flexDirection: 'row',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    backgroundColor: '#fff',
  },
  celula: {
    flex: 1,
    textAlign: 'center',
    fontSize: 11,
    color: '#334155',
    paddingHorizontal: 3,
  },
  classe: {
    flex: 1.2,
    fontWeight: '600',
    textAlign: 'left',
    paddingLeft: 8,
  },
  cabecalho: {
    fontWeight: 'bold',
    color: '#0056b3',
  },
  alerta: {
    fontSize: 12,
    color: '#92400e',
    marginBottom: 6,
    lineHeight: 18,
  },
  aviso: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 12,
    lineHeight: 17,
  },
});
