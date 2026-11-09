"""Adapta hipóteses visuais de IA para o editor, sem validá-las clinicamente.

Mantém a classificação original em campo separado, para permitir retificação
sem apagar a origem da proposta. Nenhuma classe é inferida da tonalidade.
"""
from __future__ import annotations

from schemas.multimodal import RegiaoIdentificada

CLASSES_TECIDO = frozenset({'granulacao', 'esfacelo', 'necrose'})


def regioes_para_editor(regioes: list[RegiaoIdentificada], provedor: str) -> list[dict]:
    resultado = []
    for indice, regiao in enumerate(regioes, start=1):
        tipo = regiao.identificador.rsplit('-', 1)[0]
        if tipo == 'contorno_visual_lesao':
            classe = 'contorno_lesao'
        elif tipo == 'pele_perilesional':
            classe = 'pele_perilesional'
        elif regiao.classificacao_tecido_proposta in CLASSES_TECIDO:
            classe = regiao.classificacao_tecido_proposta
        else:
            classe = 'nao_classificado'
        resultado.append({
            'id': f'{provedor}_{indice}',
            'classe': classe,
            'classe_proposta_ia': classe,
            'justificativa_classificacao_ia': regiao.justificativa_classificacao,
            'confianca_classificacao_ia': regiao.confianca_classificacao_autodeclarada,
            'origem': 'ia',
            'descricao': f'{regiao.rotulo}: {regiao.descricao}'[:240],
            'pontos': [p.model_dump() for p in regiao.pontos],
        })
    return resultado


def detalhes_propostas(regioes: list[RegiaoIdentificada]) -> list[dict]:
    return [{
        'rotulo_visual': regiao.rotulo,
        'classificacao_proposta': (
            regiao.classificacao_tecido_proposta
            if regiao.classificacao_tecido_proposta in CLASSES_TECIDO
            else 'nao_classificado'
        ),
        'justificativa': regiao.justificativa_classificacao,
        'confianca_autodeclarada': regiao.confianca_classificacao_autodeclarada,
    } for regiao in regioes]
