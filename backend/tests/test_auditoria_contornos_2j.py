
"""Testes offline da auditoria de contornos da Etapa 2J."""

from schemas.multimodal import (
    PontoImagem,
    RegiaoIdentificada,
)

from services.multimodal.auditoria_contornos import (
    auditar_contornos,
)


def criar_regiao(
    tipo: str,
    numero: int,
    coordenadas: list[tuple[float, float]],
    classe: str = "nao_classificado",
) -> RegiaoIdentificada:
    return RegiaoIdentificada(
        identificador=f"{tipo}-{numero}",
        rotulo="Região de teste",
        descricao="Região sintética para teste.",
        pontos=[
            PontoImagem(x=x, y=y)
            for x, y in coordenadas
        ],
        confianca_autodeclarada="moderada",
        classificacao_tecido_proposta=classe,
        justificativa_classificacao=(
            "Região sintética para auditoria geométrica."
        ),
        revisao_profissional_necessaria=True,
    )


def quadrado(
    esquerda: float,
    topo: float,
    direita: float,
    base: float,
) -> list[tuple[float, float]]:
    return [
        (esquerda, topo),
        (direita, topo),
        (direita, base),
        (esquerda, base),
    ]


def contorno():
    return criar_regiao(
        "contorno_visual_lesao",
        1,
        quadrado(0.25, 0.25, 0.65, 0.65),
    )


def superficie(
    coordenadas: list[tuple[float, float]],
):
    return criar_regiao(
        "superficie_escura",
        2,
        coordenadas,
        classe="necrose",
    )


def test_regiao_contida_nao_gera_alerta():
    regioes = [
        contorno(),
        superficie(
            quadrado(0.35, 0.35, 0.55, 0.55)
        ),
    ]

    assert auditar_contornos(regioes) == []


def test_regiao_fora_gera_alerta():
    regioes = [
        contorno(),
        superficie(
            quadrado(0.70, 0.70, 0.90, 0.90)
        ),
    ]

    alertas = auditar_contornos(regioes)

    assert len(alertas) == 1
    assert "AUDITORIA_CONTORNO" in alertas[0]
    assert "superficie_escura-2" in alertas[0]


def test_regiao_parcialmente_fora_gera_alerta():
    regioes = [
        contorno(),
        superficie(
            quadrado(0.50, 0.35, 0.85, 0.55)
        ),
    ]

    assert len(auditar_contornos(regioes)) == 1


def test_sem_contorno_nao_inventa_referencia():
    regioes = [
        superficie(
            quadrado(0.30, 0.30, 0.50, 0.50)
        )
    ]

    assert auditar_contornos(regioes) == []


def test_pele_perilesional_ampla_e_sinalizada_sem_descarte():
    pele = criar_regiao(
        "pele_perilesional",
        2,
        quadrado(0.10, 0.10, 0.90, 0.90),
    )

    regioes = [
        contorno(),
        pele,
    ]

    antes = [
        regiao.model_dump(mode="json")
        for regiao in regioes
    ]

    alertas = auditar_contornos(regioes)

    depois = [
        regiao.model_dump(mode="json")
        for regiao in regioes
    ]

    # Regiões perilesionais excessivamente amplas
    # devem ser sinalizadas para revisão profissional.
    assert len(alertas) == 1
    assert "[AUDITORIA_CONTORNO]" in alertas[0]
    assert "consideravelmente maior" in alertas[0]

    # A auditoria não remove ou modifica os polígonos.
    assert antes == depois
    assert len(regioes) == 2


def test_auditoria_nao_modifica_regioes():
    regioes = [
        contorno(),
        superficie(
            quadrado(0.70, 0.70, 0.90, 0.90)
        ),
    ]

    antes = [
        regiao.model_dump(mode="json")
        for regiao in regioes
    ]

    auditar_contornos(regioes)

    depois = [
        regiao.model_dump(mode="json")
        for regiao in regioes
    ]

    assert depois == antes
    assert (
        regioes[1].classificacao_tecido_proposta
        == "necrose"
    )
