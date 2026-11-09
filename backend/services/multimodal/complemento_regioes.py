"""Regiões complementares separadas do relatório T.I.M.E.S. persistido."""
from __future__ import annotations

from services.visualizacao_marcacoes import validar_regioes_persistidas


def _regioes_efetivas(analise, relatorio, provedor: str, caminho_processada: str):
    """Prioriza relatório original; complemento OpenAI não modifica T.I.M.E.S."""
    if relatorio is None:
        return [], 'indisponivel'
    originais = validar_regioes_persistidas(relatorio.conteudo_editavel)
    if originais or provedor != 'openai':
        return originais, 'relatorio'
    complemento = (analise.contexto_clinico_json or {}).get('regioes_openai_complementares')
    if not isinstance(complemento, dict) or complemento.get('imagem_referencia') != caminho_processada:
        return [], 'relatorio'
    estrutura = {
        'marcacoes_imagem': {
            'sistema_coordenadas': 'normalizado_0_1',
            'imagem_referencia': 'processada',
            'regioes': complemento.get('regioes', []),
        }
    }
    return validar_regioes_persistidas(estrutura), 'complemento_openai'

