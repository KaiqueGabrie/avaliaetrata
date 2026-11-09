"""Sobreposições de hipóteses visuais de IA na imagem processada.

As classes são propostas não confirmadas. Não calcula percentuais de IA.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from schemas.multimodal import RegiaoIdentificada
from services.multimodal.validacao_regioes import _area, _simples, ROTULOS_VISUAIS

# As cores representam tipos de região VISUAL, não tipos clínicos confirmados.
CORES = {
    'contorno_visual_lesao': (30, 170, 30),
    'superficie_escura': (170, 100, 50),
    'superficie_amarelada': (0, 190, 240),
    'superficie_avermelhada': (70, 70, 220),
    'pele_perilesional': (220, 170, 30),
}
# Cores BGR: cores da legenda, nunca uma classificação automática por cor.
CORES_CLASSES = {
    'granulacao': (55, 55, 220),
    'esfacelo': (20, 205, 235),
    'necrose': (120, 100, 85),
}
ROTULOS_CLASSES = {
    'granulacao': 'POSSIVEL GRANULACAO',
    'esfacelo': 'POSSIVEL ESFACELO',
    'necrose': 'POSSIVEL NECROSE',
}
ROTULOS_CURTOS = {
    'contorno_visual_lesao': 'Contorno aparente',
    'superficie_escura': 'Tonalidade escura',
    'superficie_amarelada': 'Tonalidade amarelada',
    'superficie_avermelhada': 'Tonalidade avermelhada',
    'pele_perilesional': 'Pele ao redor',
}


def validar_regioes_persistidas(conteudo: Any) -> list[RegiaoIdentificada]:
    """Revalida dados persistidos antes de desenhar; jamais infere pontos."""
    if not isinstance(conteudo, dict):
        return []
    marcacoes = conteudo.get('marcacoes_imagem')
    if not isinstance(marcacoes, dict) or marcacoes.get('sistema_coordenadas') != 'normalizado_0_1' or marcacoes.get('imagem_referencia') != 'processada':
        return []
    itens = marcacoes.get('regioes')
    if not isinstance(itens, list):
        return []
    resultado: list[RegiaoIdentificada] = []
    for bruto in itens[:12]:
        try:
            regiao = RegiaoIdentificada.model_validate(bruto)
        except (ValueError, TypeError):
            continue
        tipo = regiao.identificador.rsplit('-', 1)[0]
        if tipo not in ROTULOS_VISUAIS or regiao.rotulo != ROTULOS_VISUAIS[tipo]:
            continue
        if regiao.confianca_autodeclarada not in ('moderada', 'alta'):
            continue
        pontos = [(p.x, p.y) for p in regiao.pontos]
        if (not 3 <= len(pontos) <= 24 or
                len(set(pontos)) != len(pontos) or
                not all(math.isfinite(x) and math.isfinite(y) for x, y in pontos) or
                not 0.0003 <= _area(pontos) <= 0.75 or
                not _simples(pontos)):
            continue
        # O conteúdo persistido é editável: jamais confiar em um rótulo sem
        # evidências específicas, nem aceitar classes para contorno/perilesão.
        classe = regiao.classificacao_tecido_proposta
        if (tipo in ('contorno_visual_lesao', 'pele_perilesional') or
                classe not in CORES_CLASSES or
                len(regiao.justificativa_classificacao.strip()) < 20 or
                regiao.confianca_classificacao_autodeclarada not in ('moderada', 'alta')):
            regiao = regiao.model_copy(update={
                'classificacao_tecido_proposta': 'nao_classificado',
                'confianca_classificacao_autodeclarada': None,
            })
        resultado.append(regiao)
        if len(resultado) >= 6:
            break
    return resultado


def assinatura_regioes(regioes: list[RegiaoIdentificada], caminho_referencia: str) -> str:
    dados = {
        'versao': 2,
        'imagem': caminho_referencia,
        'regioes': [r.model_dump(mode='json') for r in regioes],
    }
    return hashlib.sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


class VisualizacaoMarcacoesService:
    @staticmethod
    def gerar(caminho_imagem: str, regioes: list[RegiaoIdentificada], destino: str, provedor: str) -> Path:
        if not regioes:
            raise ValueError('Nenhuma região válida para desenho.')
        imagem = cv2.imread(str(caminho_imagem), cv2.IMREAD_COLOR)
        if imagem is None:
            raise ValueError('Não foi possível ler a fotografia processada.')
        altura, largura = imagem.shape[:2]
        camada = imagem.copy()
        poligonos: list[tuple[np.ndarray, str, str, tuple[int, int, int]]] = []
        for regiao in regioes:
            tipo = regiao.identificador.rsplit('-', 1)[0]
            pontos = np.array([
                [min(largura - 1, max(0, round(p.x * (largura - 1)))),
                 min(altura - 1, max(0, round(p.y * (altura - 1))))]
                for p in regiao.pontos
            ], dtype=np.int32).reshape((-1, 1, 2))
            classe = regiao.classificacao_tecido_proposta
            cor = CORES_CLASSES.get(classe, CORES[tipo])
            cv2.fillPoly(camada, [pontos], cor)
            poligonos.append((pontos, tipo, classe or 'nao_classificado', cor))
        imagem = cv2.addWeighted(camada, 0.18, imagem, 0.82, 0)
        for indice, (pontos, tipo, classe, cor) in enumerate(poligonos, start=1):
            cv2.polylines(imagem, [pontos], True, cor, thickness=max(2, largura // 420), lineType=cv2.LINE_AA)
            x, y = pontos[:, 0, :].min(axis=0)
            etiqueta = f'{indice}. {ROTULOS_CLASSES.get(classe, ROTULOS_CURTOS[tipo])}'
            escala = max(0.32, min(0.64, largura / 1100))
            # Evita texto extrapolando imagens estreitas.
            while escala > .20 and cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, escala, 1)[0][0] > largura - 20:
                escala -= .04
            (tw, th), _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, escala, 1)
            x = max(0, min(int(x), largura - tw - 12))
            y = max(th + 8, min(int(y) - 5, altura - 6))
            cv2.rectangle(imagem, (x, y - th - 6), (x + tw + 9, y + 5), (0, 0, 0), -1)
            cv2.putText(imagem, etiqueta, (x + 4, y), cv2.FONT_HERSHEY_SIMPLEX, escala, (255, 255, 255), 1, cv2.LINE_AA)
        # Marca d'água explícita, mesmo em relatórios já aprovados (regiões não validadas).
        faixa = max(29, min(45, altura // 18))
        cv2.rectangle(imagem, (0, 0), (largura, faixa), (0, 0, 0), -1)
        texto = f'{provedor.upper()} - PROPOSTA IA / NAO VALIDADA'
        escala = min(0.65, max(0.34, largura / max(700, len(texto) * 15)))
        cv2.putText(imagem, texto, (8, faixa - 10), cv2.FONT_HERSHEY_SIMPLEX, escala, (255, 255, 255), 1, cv2.LINE_AA)
        saida = Path(destino)
        saida.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(saida), imagem):
            raise ValueError('Não foi possível gravar a visualização marcada.')
        return saida
