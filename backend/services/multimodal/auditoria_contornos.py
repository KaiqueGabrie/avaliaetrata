
"""Auditoria de coerência geométrica dos contornos propostos por IA.

Compara regiões de superfície ao contorno visual aparente
proposto pelo próprio modelo.

Não confirma segmentação correta, diagnóstico ou tecido.
Não altera nem rejeita os polígonos originais.
"""

from __future__ import annotations

from schemas.multimodal import RegiaoIdentificada


TIPOS_SUPERFICIE = frozenset({
    "superficie_escura",
    "superficie_amarelada",
    "superficie_avermelhada",
})

TIPO_CONTORNO = "contorno_visual_lesao"

LIMIAR_FORA = 0.25
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
    """Teste ponto-polígono pelo método de cruzamentos."""

    dentro = False
    total = len(pontos)

    for indice in range(total):
        x1, y1 = pontos[indice]
        x2, y2 = pontos[(indice + 1) % total]

        # Inclui pontos sobre a borda.
        cruzamento = (
            (y1 > y) != (y2 > y)
        )

        if cruzamento:
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
    """Estima a fração geométrica da superfície fora do contorno.

    É uma aproximação por amostragem de pontos, não uma
    mensuração clínica ou percentual de tecido.
    """

    min_x = min(x for x, _ in superficie)
    max_x = max(x for x, _ in superficie)
    min_y = min(y for _, y in superficie)
    max_y = max(y for _, y in superficie)

    largura = max_x - min_x
    altura = max_y - min_y

    if largura <= 0 or altura <= 0:
        return None

    total_dentro_superficie = 0
    total_fora_contorno = 0

    resolucao = RESOLUCAO_AMOSTRAGEM

    for linha in range(resolucao):
        y = min_y + (
            (linha + 0.5) / resolucao
        ) * altura

        for coluna in range(resolucao):
            x = min_x + (
                (coluna + 0.5) / resolucao
            ) * largura

            if not _ponto_no_poligono(
                x, y, superficie
            ):
                continue

            total_dentro_superficie += 1

            if not _ponto_no_poligono(
                x, y, contorno
            ):
                total_fora_contorno += 1

    if total_dentro_superficie == 0:
        return None

    return (
        total_fora_contorno /
        total_dentro_superficie
    )


def auditar_contornos(
    regioes: list[RegiaoIdentificada],
) -> list[str]:
    """Retorna alertas descritivos sem modificar regiões.

    O contorno utilizado é uma proposta da própria IA,
    não uma referência clínica validada.
    """

    contornos = [
        _pontos(regiao)
        for regiao in regioes
        if _tipo(regiao) == TIPO_CONTORNO
    ]

    if not contornos:
        return []

    alertas: list[str] = []

    for regiao in regioes:
        if _tipo(regiao) not in TIPOS_SUPERFICIE:
            continue

        superficie = _pontos(regiao)

        fracoes = [
            fracao
            for contorno in contornos
            if (
                fracao := _fracao_fora(
                    superficie, contorno
                )
            ) is not None
        ]

        if not fracoes:
            continue

        # Mais de um contorno: usa a comparação menos
        # restritiva, evitando sinalização desnecessária.
        menor_fracao_fora = min(fracoes)

        if menor_fracao_fora > LIMIAR_FORA:
            alertas.append(
                "[AUDITORIA_CONTORNO] "
                f"A região '{regiao.identificador}' "
                "apresenta parte expressiva de sua área "
                "geométrica fora do contorno visual "
                "aparente proposto pela mesma IA. "
                "Verifique o posicionamento e os limites "
                "na fotografia antes de validar."
            )

    return alertas
