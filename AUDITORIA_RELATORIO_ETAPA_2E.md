# Auditoria do relatório — Avalia & Trata (Etapa 2E)

Base: estrutura `RespostaEstruturadaModelo`, normalização do `prompt_padrao.py`, telas `nova.tsx` e `[id].tsx`, e relatório da avaliação nº 16 enviado pelo usuário.

| Campo | Observação técnica | Alteração nesta etapa |
|---|---|---|
| `conteudo_descricao` | Descrição geral já preenchida; na tela de edição era repetida no campo de texto e no resumo. | Exibir uma única vez na edição; manter o original consultável separadamente. |
| `qualidade_imagem.observacoes` | O normalizador não popula esse campo automaticamente; pode ficar vazio. | Exibir quando houver, sem criar observações fictícias. |
| `qualidade_imagem.limitacoes` e `limitacoes_declaradas` | O normalizador copia as limitações gerais para a qualidade, produzindo textos repetidos. | Manter os dois campos íntegros, mas recolher os detalhes em seções independentes. |
| `caracteristicas_visuais.confianca_autodeclarada` e `justificativa` | O normalizador pode não preencher esses campos. | Exibir apenas quando houver; descrição e status permanecem visíveis. |
| `avaliacao_times` | Todos os cinco componentes aparecem; alguns podem não ter observações, apenas pendências. | Manter todas as listas, com estado, dados clínicos, pendências e limitações. |
| `avaliacao_tecidos.metodo_estimativa` e `percentual_estimado` | Frequentemente não preenchidos por ausência de segmentação validada. | Não inventar percentuais; mostrar status, justificativas e método quando houver. |
| `medidas.area_calculada_cm2` | Nulo por não haver planimetria real validada. | Preservar como área real não calculada; acrescentar **áreas geométricas** separadas. |
| `marcacoes_imagem.regioes` | Pode estar vazio; regiões propostas podem ter coordenadas sem aparecer na interface. | Exibir contagem, coordenadas e imagens independentes por IA quando válidas. |
| `plano_cuidados_proposto.sugestoes` | O normalizador não cria sugestões estruturadas; fica vazio mesmo quando há `pontos_para_revisao_profissional`. | Unificar a apresentação em **Pontos de atenção para validação profissional**, preservando as duas fontes separadas. |
| `pontos_para_revisao_profissional` | Contém itens efetivos das IAs e alertas do validador. | Preservar todos, sem duplicá-los em um plano de cuidados inventado. |
| `dados_clinicos_organizados` | Presente no JSON, mas omitido na tela anterior. | Acrescentar seção completa, incluindo dados não informados. |
| `status_resposta`, `validacao_profissional_necessaria` | Nem sempre visíveis na tela anterior. | Exibir explicitamente no resumo. |
| `alertas_validacao` | Persistidos separadamente do conteúdo da IA. | Exibir na tela de relatório persistido quando disponíveis. |
| `conteudo_original` | Persistido separadamente da versão editável. | Acrescentar opção de consultar relatório original na tela de detalhes. |
| `comparacao_multimodal.divergencia_status` | Texto anterior podia sugerir divergência clínica quando havia apenas estados de avaliação diferentes. | Rótulo alterado para **Diferença no estado de avaliação**. |

## Política de preservação

Nenhuma lista clínica, observação, pendência, limitação, justificativa, campo técnico, coordenada, versão original ou dado de auditoria foi apagado do banco ou do JSON. A atualização altera a **apresentação**, não o histórico. Os detalhes extensos ficam recolhidos por padrão, com controles para consulta.

## Limitações de validação

O relatório nº 16 mostra resultados das três IAs, mas não permite verificar a exatidão espacial dos polígonos apenas pelo texto. A geometria é revalidada no backend antes do desenho, mas a correção clínica depende de revisão humana. Não usar essas imagens para diagnóstico ou mensuração real da área da ferida.
