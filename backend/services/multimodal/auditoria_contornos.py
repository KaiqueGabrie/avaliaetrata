
"""Auditoria geométrica de regiões propostas por IA.

Detecta inconsistências internas entre polígonos.
Não determina o limite verdadeiro da lesão, não confirma
tecidos e não modifica as coordenadas propostas.
"""

from __future__ import annotations

from schemas.multimodal import RegiaoIdentificada


TIPOS_SUPERFICIE = frozenset({
    "superficie_escura",
    "superficie_amarelada",
    "superficie_avermelhada",
})

TIPO_CONTORNO = "contorno_visual_lesao"
TIPO_PERILESIONAL = "pele_perilesional"

LIMIAR_FORA = 0.25
LIMIAR_AFASTAMENTO = 0.10
RESOLUCAO_AMOSTRAGEM = 35


def _tipo(regiao: RegiaoIdentificada) -> str:
    return regiao.identificador.rsplit("-", 1)[0]


def _pontos(
    regiao: RegiaoIdentificada,
) -> list[tuple[float, float]]:
    return [(p.x, p.y) for p in regiao.pontos]


def _ponto_no_poligono(
    x: float,
    y: float,
    pontos: list[tuple[float, float]],
) -> bool:
    dentro = False

    for indice in range(len(pontos)):
        x1, y1 = pontos[indice]
        x2, y2 = pontos[(indice + 1) % len(pontos)]

        if (y1 > y) != (y2 > y):
            intersecao_x = (
                x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            )

            if x < intersecao_x:
                dentro = not dentro

    return dentro


def _fracao_fora(
    superficie: list[tuple[float, float]],
    contorno: list[tuple[float, float]],
) -> float | None:
    min_x = min(x for x, _ in superficie)
    max_x = max(x for x, _ in superficie)
    min_y = min(y for _, y in superficie)
    max_y = max(y for _, y in superficie)

    largura = max_x - min_x
    altura = max_y - min_y

    if largura <= 0 or altura <= 0:
        return None

    total = 0
    fora = 0

    for linha in range(RESOLUCAO_AMOSTRAGEM):
        y = min_y + (
            (linha + 0.5) / RESOLUCAO_AMOSTRAGEM
        ) * altura

        for coluna in range(RESOLUCAO_AMOSTRAGEM):
            x = min_x + (
                (coluna + 0.5) / RESOLUCAO_AMOSTRAGEM
            ) * largura

            if not _ponto_no_poligono(
                x, y, superficie
            ):
                continue

            total += 1

            if not _ponto_no_poligono(
                x, y, contorno
            ):
                fora += 1

    return fora / total if total else None


def _caixa(
    pontos: list[tuple[float, float]],
) -> tuple[float, float, float, float]:
    return (
        min(x for x, _ in pontos),
        min(y for _, y in pontos),
        max(x for x, _ in pontos),
        max(y for _, y in pontos),
    )


def _afastamento_caixas(
    primeira: list[tuple[float, float]],
    segunda: list[tuple[float, float]],
) -> float:
    """Distância mínima entre caixas normalizadas.

    Uma caixa sobreposta ou encostada resulta em zero.
    Essa medida não é uma distância física em centímetros.
    """
    ax1, ay1, ax2, ay2 = _caixa(primeira)
    bx1, by1, bx2, by2 = _caixa(segunda)

    distancia_x = max(
        0.0,
        bx1 - ax2,
        ax1 - bx2,
    )

    distancia_y = max(
        0.0,
        by1 - ay2,
        ay1 - by2,
    )

    return (
        distancia_x ** 2 + distancia_y ** 2
    ) ** 0.5


def auditar_contornos(
    regioes: list[RegiaoIdentificada],
) -> list[str]:
    """Produz alertas sem modificar nenhuma região.

    A referência é o contorno aparente da própria IA,
    e não uma segmentação validada pelo enfermeiro.
    """

    contornos = [
        _pontos(regiao)
        for regiao in regioes
        if _tipo(regiao) == TIPO_CONTORNO
        and len(regiao.pontos) >= 3
    ]

    if not contornos:
        return []

    alertas: list[str] = []

    for regiao in regioes:
        tipo = _tipo(regiao)

        if len(regiao.pontos) < 3:
            continue

        pontos = _pontos(regiao)

        if tipo in TIPOS_SUPERFICIE:
            fracoes = [
                fracao
                for contorno in contornos
                if (
                    fracao := _fracao_fora(
                        pontos,
                        contorno,
                    )
                ) is not None
            ]

            if (
                fracoes
                and min(fracoes) > LIMIAR_FORA
            ):
                alertas.append(
                    "[AUDITORIA_CONTORNO] "
                    f"A região '{regiao.identificador}' "
                    "apresenta parte expressiva de sua "
                    "área geométrica fora do contorno "
                    "visual aparente proposto pela mesma IA. "
                    "Confira o posicionamento e os limites "
                    "na fotografia antes da validação."
                )

        elif tipo == TIPO_PERILESIONAL:
            menor_distancia = min(
                _afastamento_caixas(
                    pontos,
                    contorno,
                )
                for contorno in contornos
            )

            if menor_distancia > LIMIAR_AFASTAMENTO:
                alertas.append(
                    "[AUDITORIA_CONTORNO] "
                    f"A região '{regiao.identificador}', "
                    "identificada como pele perilesional, "
                    "está geometricamente afastada do "
                    "contorno principal proposto pela IA. "
                    "Confirme se realmente corresponde "
                    "à pele adjacente à lesão."
                )

    return alertas
