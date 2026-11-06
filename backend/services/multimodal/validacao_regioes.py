"""Validacao defensiva de poligonos VISUAIS sugeridos por modelos multimodais.

Nao e segmentacao clinica. Coordenadas aceitas sao propostas para revisao
humana, nao medidas de area nem confirmacao de tipo de tecido.
"""
from __future__ import annotations

import math
from typing import Any

from schemas.multimodal import RegiaoIdentificada, PontoImagem

ROTULOS_VISUAIS = {
    "contorno_visual_lesao": "Contorno visual aparente da lesão",
    "superficie_escura": "Superfície de tonalidade escura",
    "superficie_amarelada": "Superfície de tonalidade amarelada",
    "superficie_avermelhada": "Superfície de tonalidade avermelhada",
    "pele_perilesional": "Pele ao redor da lesão",
}


def _area(pontos: list[tuple[float, float]]) -> float:
    return abs(sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(pontos, pontos[1:] + pontos[:1])
    )) / 2.0


def _orientacao(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _entre(a, b, c) -> bool:
    return (min(a[0], c[0]) - 1e-9 <= b[0] <= max(a[0], c[0]) + 1e-9 and
            min(a[1], c[1]) - 1e-9 <= b[1] <= max(a[1], c[1]) + 1e-9)


def _intersecao(a, b, c, d) -> bool:
    o1, o2 = _orientacao(a, b, c), _orientacao(a, b, d)
    o3, o4 = _orientacao(c, d, a), _orientacao(c, d, b)
    if (o1 > 1e-9 and o2 < -1e-9 or o1 < -1e-9 and o2 > 1e-9) and (o3 > 1e-9 and o4 < -1e-9 or o3 < -1e-9 and o4 > 1e-9):
        return True
    return any([
        abs(o1) <= 1e-9 and _entre(a, c, b),
        abs(o2) <= 1e-9 and _entre(a, d, b),
        abs(o3) <= 1e-9 and _entre(c, a, d),
        abs(o4) <= 1e-9 and _entre(c, b, d),
    ])


def _simples(pontos: list[tuple[float, float]]) -> bool:
    n = len(pontos)
    for i in range(n):
        for j in range(i + 1, n):
            # Arestas vizinhas compartilham vertices por definicao.
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _intersecao(pontos[i], pontos[(i + 1) % n], pontos[j], pontos[(j + 1) % n]):
                return False
    return True


def validar_regioes_propostas(dados: Any) -> tuple[list[RegiaoIdentificada], list[str]]:
    """Aceita ate seis regioes bem formadas; descarta as demais sem falhar a IA.

    A confianca autodeclarada nao e confianca calibrada. Nenhuma regiao
    retornada por esta funcao e considerada clinicamente validada.
    """
    if not isinstance(dados, list):
        return [], ["O provedor não retornou uma lista de regiões."] if dados is not None else []
    validas: list[RegiaoIdentificada] = []
    descartadas = 0
    assinaturas: set[tuple] = set()
    for item in dados[:12]:
        if not isinstance(item, dict):
            descartadas += 1
            continue
        tipo = item.get("tipo_regiao")
        confianca = item.get("confianca")
        raw = item.get("pontos")
        if (not isinstance(tipo, str) or tipo not in ROTULOS_VISUAIS or
                confianca not in ("moderada", "alta") or
                not isinstance(raw, list) or not 3 <= len(raw) <= 24):
            descartadas += 1
            continue
        pontos: list[tuple[float, float]] = []
        for p in raw:
            if not isinstance(p, dict):
                break
            x, y = p.get("x"), p.get("y")
            if (isinstance(x, bool) or isinstance(y, bool) or
                    not isinstance(x, (float, int)) or not isinstance(y, (float, int)) or
                    not math.isfinite(x) or not math.isfinite(y) or
                    not 0 <= x <= 1 or not 0 <= y <= 1):
                break
            pontos.append((float(x), float(y)))
        if len(pontos) != len(raw):
            descartadas += 1
            continue
        # Aceita o ultimo ponto igual ao primeiro, mas armazena anel aberto.
        if pontos[-1] == pontos[0]:
            pontos.pop()
        if (len(pontos) < 3 or len(set(pontos)) != len(pontos) or
                not 0.0003 <= _area(pontos) <= 0.75 or not _simples(pontos)):
            descartadas += 1
            continue
        assinatura = (tipo, tuple(pontos))
        if assinatura in assinaturas:
            descartadas += 1
            continue
        descricao = item.get("descricao")
        if not isinstance(descricao, str):
            descricao = ""
        validas.append(RegiaoIdentificada(
            identificador=f"{tipo}-{len(validas) + 1}",
            rotulo=ROTULOS_VISUAIS[tipo],
            descricao=descricao.strip()[:240],
            pontos=[PontoImagem(x=x, y=y) for x, y in pontos],
            confianca_autodeclarada=confianca,
            revisao_profissional_necessaria=True,
        ))
        assinaturas.add(assinatura)
        if len(validas) >= 6:
            break
    descartadas += max(0, len(dados) - 12)
    limitacoes = [
        "Coordenadas propostas por IA, não validadas nem equivalentes a segmentação clínica.",
        "A posição e o contorno devem ser conferidos e corrigidos pelo profissional antes de gerar imagem marcada.",
        "A confiança declarada pelo modelo não representa precisão clínica comprovada.",
    ]
    if descartadas:
        limitacoes.append(f"{descartadas} região(ões) descartada(s) por formato, confiança ou geometria insuficiente.")
    return validas, limitacoes
