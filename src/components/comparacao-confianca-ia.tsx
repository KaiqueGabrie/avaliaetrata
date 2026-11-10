
import { useState } from 'react';
import {
    StyleSheet,
    Text,
    TouchableOpacity,
    useWindowDimensions,
    View,
} from 'react-native';

import type { RespostaEstruturadaIA } from '../types/ia';

type DadosConfianca = {
  resposta?: RespostaEstruturadaIA | null;
  sucesso?: boolean;
};

type Props = {
  resultados: Record<string, DadosConfianca | undefined>;
};

const PROVEDORES = [
  { id: 'openai', nome: 'OpenAI' },
  { id: 'gemini', nome: 'Gemini' },
  { id: 'kimi', nome: 'Kimi' },
] as const;

function percentualValido(
  valor: number | null | undefined
): valor is number {
  return (
    typeof valor === 'number' &&
    Number.isFinite(valor) &&
    valor >= 0 &&
    valor <= 100
  );
}

export default function ComparacaoConfiancaIA({
  resultados,
}: Props) {
  const [detalhes, setDetalhes] = useState<
    Record<string, boolean>
  >({});

  const { width } = useWindowDimensions();
  const horizontal = width >= 900;

  const possuiResultados = PROVEDORES.some(
    provedor => resultados[provedor.id]?.resposta
  );

  if (!possuiResultados) return null;

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
        {PROVEDORES.map(provedor => {
          const resultado = resultados[provedor.id];
          const resposta = resultado?.resposta;

          const valor =
            resposta?.confianca_avaliacao_percentual;

          const valido = percentualValido(valor);
          const aberto = !!detalhes[provedor.id];

          const justificativa =
            resposta?.justificativa_confianca_avaliacao;

          const limitacoes =
            resposta?.limitacoes_confianca_avaliacao ?? [];

          return (
            <View
              key={provedor.id}
              style={[
                styles.cartao,
                horizontal
                  ? styles.cartaoHorizontal
                  : styles.cartaoVertical,
              ]}
            >
              <View style={styles.cabecalho}>
                <Text style={styles.nome}>
                  {provedor.nome}
                </Text>

                <Text style={styles.percentual}>
                  {valido
                    ? `${valor.toLocaleString('pt-BR', {
                        maximumFractionDigits: 1,
                      })}%`
                    : '—'}
                </Text>
              </View>

              <View style={styles.trilho}>
                <View
                  style={[
                    styles.preenchimento,
                    {
                      width: valido
                        ? `${valor}%`
                        : '0%',
                    },
                  ]}
                />
              </View>

              <Text style={styles.estado}>
                {!resposta
                  ? 'Avaliação indisponível'
                  : valido
                    ? 'Confiança autodeclarada'
                    : 'Percentual não informado'}
              </Text>

              {resposta &&
              (justificativa || limitacoes.length > 0) ? (
                <>
                  <TouchableOpacity
                    accessibilityRole="button"
                    accessibilityLabel={
                      `${aberto ? 'Ocultar' : 'Ver'} ` +
                      `justificativa de ${provedor.nome}`
                    }
                    onPress={() =>
                      setDetalhes(anterior => ({
                        ...anterior,
                        [provedor.id]: !aberto,
                      }))
                    }
                    style={styles.botaoDetalhes}
                  >
                    <Text style={styles.link}>
                      {aberto ? '▾ Ocultar' : '▸ Ver'}{' '}
                      justificativa e limitações
                    </Text>
                  </TouchableOpacity>

                  {aberto ? (
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
                            Limitações declaradas
                          </Text>

                          {limitacoes.map((item, indice) => (
                            <Text
                              key={`${provedor.id}-${indice}`}
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
              ) : null}
            </View>
          );
        })}
      </View>

      <Text style={styles.aviso}>
        Importante: os modelos podem interpretar a
        própria confiança de maneiras diferentes.
        Um percentual maior não demonstra que uma IA
        seja clinicamente mais precisa que outra.
        As análises exigem revisão profissional.
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
    marginVertical: 12,
  },
  titulo: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#0056b3',
    marginBottom: 7,
  },
  descricao: {
    color: '#64748b',
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 14,
  },
  grade: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  cartao: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 9,
    padding: 14,
    minWidth: 0,
  },
  cartaoHorizontal: {
    flexBasis: '30%',
    flexGrow: 1,
  },
  cartaoVertical: {
    width: '100%',
  },
  cabecalho: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  nome: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#1e293b',
  },
  percentual: {
    fontSize: 25,
    fontWeight: 'bold',
    color: '#0056b3',
  },
  trilho: {
    height: 10,
    borderRadius: 8,
    backgroundColor: '#e2e8f0',
    overflow: 'hidden',
    marginTop: 12,
  },
  preenchimento: {
    height: '100%',
    backgroundColor: '#2563eb',
    borderRadius: 8,
  },
  estado: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 7,
  },
  botaoDetalhes: {
    paddingVertical: 11,
    marginTop: 5,
  },
  link: {
    fontSize: 12,
    fontWeight: '600',
    color: '#0056b3',
  },
  detalhes: {
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    paddingTop: 10,
    gap: 5,
  },
  rotulo: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#334155',
    marginTop: 6,
  },
  texto: {
    fontSize: 12,
    color: '#475569',
    lineHeight: 18,
  },
  aviso: {
    color: '#64748b',
    fontSize: 11,
    lineHeight: 17,
    marginTop: 14,
  },
});
