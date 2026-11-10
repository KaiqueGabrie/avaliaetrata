
import { useState } from 'react';
import {
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from 'react-native';

import type {
    RespostaEstruturadaIA,
    ResultadoProvedorIA,
} from '../types/ia';

type EntradaConfianca = {
  provedor: string;
  resposta: RespostaEstruturadaIA | null;
  sucesso: boolean;
};

type Props = {
  resultados?: Record<string, ResultadoProvedorIA>;
  relatorios?: Array<{
    provedor: string;
    conteudo_editavel: RespostaEstruturadaIA;
    conteudo_original?: RespostaEstruturadaIA;
  }>;
};

const PROVEDORES = [
  { chave: 'openai', nome: 'OpenAI' },
  { chave: 'gemini', nome: 'Gemini' },
  { chave: 'kimi', nome: 'Kimi' },
];

function obterPercentual(
  resposta: RespostaEstruturadaIA | null
): number | null {
  const valor = resposta?.confianca_avaliacao_percentual;

  if (
    typeof valor !== 'number' ||
    !Number.isFinite(valor) ||
    valor < 0 ||
    valor > 100
  ) {
    return null;
  }

  return valor;
}

function formatarPercentual(valor: number): string {
  return `${valor.toLocaleString('pt-BR', {
    maximumFractionDigits: 1,
  })}%`;
}

function CartaoConfianca({
  nome,
  entrada,
}: {
  nome: string;
  entrada: EntradaConfianca | undefined;
}) {
  const [expandido, setExpandido] = useState(false);

  const resposta = entrada?.resposta ?? null;
  const percentual = obterPercentual(resposta);

  const justificativa =
    resposta?.justificativa_confianca_avaliacao?.trim() ||
    '';

  const limitacoes = Array.isArray(
    resposta?.limitacoes_confianca_avaliacao
  )
    ? resposta.limitacoes_confianca_avaliacao.filter(
        (item): item is string =>
          typeof item === 'string' &&
          item.trim().length > 0
      )
    : [];

  const temDetalhes =
    justificativa.length > 0 || limitacoes.length > 0;

  return (
    <View style={styles.cartao}>
      <View style={styles.linhaTitulo}>
        <Text style={styles.nome}>{nome}</Text>

        <Text style={styles.percentual}>
          {percentual === null
            ? 'Não informada'
            : formatarPercentual(percentual)}
        </Text>
      </View>

      <View style={styles.trilho}>
        {percentual !== null ? (
          <View
            style={[
              styles.preenchimento,
              { width: `${percentual}%` },
            ]}
          />
        ) : null}
      </View>

      <Text style={styles.legenda}>
        {percentual === null
          ? 'Percentual não disponível para esta análise'
          : 'Confiança autodeclarada'}
      </Text>

      {temDetalhes ? (
        <>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel={
              `${expandido ? 'Ocultar' : 'Ver'} ` +
              `justificativa e limitações de ${nome}`
            }
            onPress={() => setExpandido((anterior) => !anterior)}
            style={styles.botaoDetalhes}
          >
            <Text style={styles.textoBotao}>
              {expandido ? '▾ Ocultar' : '▸ Ver'}{' '}
              justificativa e limitações
            </Text>
          </TouchableOpacity>

          {expandido ? (
            <View style={styles.detalhes}>
              {justificativa ? (
                <>
                  <Text style={styles.rotulo}>
                    Justificativa
                  </Text>
                  <Text style={styles.texto}>
                    {justificativa}
                  </Text>
                </>
              ) : null}

              {limitacoes.length > 0 ? (
                <>
                  <Text style={styles.rotulo}>
                    Limitações identificadas
                  </Text>

                  {limitacoes.map((item, indice) => (
                    <Text
                      key={`${indice}-${item}`}
                      style={styles.texto}
                    >
                      • {item}
                    </Text>
                  ))}
                </>
              ) : null}
            </View>
          ) : null}
        </>
      ) : (
        <Text style={styles.legenda}>
          Justificativa e limitações não disponíveis.
        </Text>
      )}
    </View>
  );
}

export default function ComparacaoConfiancaIA({
  resultados,
  relatorios,
}: Props) {
  const entradas: Record<string, EntradaConfianca> = {};

  if (resultados) {
    Object.entries(resultados).forEach(
      ([chave, resultado]) => {
        const provedor = (
          resultado.provedor || chave
        ).toLowerCase();

        entradas[provedor] = {
          provedor,
          resposta: resultado.resposta,
          sucesso: resultado.sucesso,
        };
      }
    );
  }

  if (relatorios) {
    relatorios.forEach((relatorio) => {
      const provedor = relatorio.provedor.toLowerCase();

      entradas[provedor] = {
        provedor,
        resposta:
          relatorio.conteudo_original ??
          relatorio.conteudo_editavel,
        sucesso: true,
      };
    });
  }

  const temDados = Object.keys(entradas).length > 0;

  if (!temDados) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.titulo}>
        Comparação da confiança das IAs
      </Text>

      <Text style={styles.descricao}>
        Percentuais autodeclarados pelos modelos
        durante a avaliação visual da fotografia.
        Não representam acurácia clínica comprovada.
      </Text>

      <View style={styles.grade}>
        {PROVEDORES.map(({ chave, nome }) => (
          <CartaoConfianca
            key={chave}
            nome={nome}
            entrada={entradas[chave]}
          />
        ))}
      </View>

      <Text style={styles.aviso}>
        Importante: os modelos podem interpretar
        a própria confiança de maneiras diferentes.
        Um percentual maior não demonstra que uma
        IA seja clinicamente mais precisa que outra.
        As análises exigem revisão profissional.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 10,
    padding: 14,
    marginVertical: 14,
    backgroundColor: '#f8fafc',
  },
  titulo: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 6,
  },
  descricao: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 18,
    marginBottom: 14,
  },
  grade: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  cartao: {
    flexGrow: 1,
    flexBasis: 250,
    minWidth: 0,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 9,
    backgroundColor: '#fff',
    padding: 12,
  },
  linhaTitulo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    marginBottom: 10,
  },
  nome: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#0f172a',
  },
  percentual: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#0056b3',
  },
  trilho: {
    width: '100%',
    height: 9,
    backgroundColor: '#e2e8f0',
    borderRadius: 10,
    overflow: 'hidden',
  },
  preenchimento: {
    height: '100%',
    borderRadius: 10,
    backgroundColor: '#2563eb',
  },
  legenda: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 6,
  },
  botaoDetalhes: {
    marginTop: 12,
    paddingVertical: 5,
  },
  textoBotao: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#0056b3',
  },
  detalhes: {
    marginTop: 8,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  rotulo: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#334155',
    marginBottom: 5,
    marginTop: 7,
  },
  texto: {
    fontSize: 12,
    color: '#475569',
    lineHeight: 19,
    marginBottom: 5,
  },
  aviso: {
    fontSize: 11,
    color: '#64748b',
    lineHeight: 17,
    marginTop: 14,
  },
});
