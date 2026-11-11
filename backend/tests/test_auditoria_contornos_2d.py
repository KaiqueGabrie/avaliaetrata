"""Testes offline da Etapa 2J — Parte 2D."""

from schemas.multimodal import (
    PontoImagem,
    RegiaoIdentificada,
)

from services.multimodal.auditoria_contornos import (
    auditar_contornos,
)

from services.multimodal.validacao_regioes import (
    ROTULOS_VISUAIS,
    validar_regioes_propostas,
)

from services.visualizacao_marcacoes import (
    validar_regioes_persistidas,
)

from services.propostas_tecidos import (
    detalhes_propostas,
)


def poligono(coordenadas):
    return [
        PontoImagem(x=x, y=y)
        for x, y in coordenadas
    ]


def criar_regiao(tipo, indice, coordenadas):
    return RegiaoIdentificada(
        identificador=f"{tipo}-{indice}",
        rotulo=ROTULOS_VISUAIS[tipo],
        descricao="Região sintética de teste.",
        pontos=poligono(coordenadas),
        confianca_autodeclarada="moderada",
        revisao_profissional_necessaria=True,
    )


def criar_conteudo(regioes):
    return {
        "marcacoes_imagem": {
            "sistema_coordenadas": "normalizado_0_1",
            "imagem_referencia": "processada",
            "regioes": [
                regiao.model_dump(mode="json")
                for regiao in regioes
            ],
        }
    }


def test_preserva_hipotese_com_baixa_confianca():
    dados = [{
        "tipo_regiao": "superficie_amarelada",
        "descricao": "Superfície de teste.",
        "confianca": "moderada",
        "pontos": [
            {"x": .2, "y": .2},
            {"x": .5, "y": .2},
            {"x": .5, "y": .5},
            {"x": .2, "y": .5},
        ],
        "classificacao_tecido_proposta": "esfacelo",
        "justificativa_classificacao": (
            "Textura e distribuição observáveis, "
            "com limitações e incerteza visual."
        ),
        "confianca_classificacao": "baixa",
    }]

    regioes, _ = validar_regioes_propostas(dados)

    assert len(regioes) == 1
    assert (
        regioes[0].classificacao_tecido_proposta
        == "esfacelo"
    )

    recuperadas = validar_regioes_persistidas(
        criar_conteudo(regioes)
    )

    assert len(recuperadas) == 1

    assert (
        recuperadas[0].classificacao_tecido_proposta
        == "esfacelo"
    )

    assert (
        recuperadas[0].confianca_classificacao_autodeclarada
        == "baixa"
    )

    detalhes = detalhes_propostas(recuperadas)

    assert (
        detalhes[0]["classificacao_proposta"]
        == "esfacelo"
    )


def test_rejeita_classificacao_sem_justificativa():
    regiao = criar_regiao(
        "superficie_amarelada",
        1,
        [
            (.2, .2),
            (.5, .2),
            (.5, .5),
            (.2, .5),
        ],
    )

    regiao = regiao.model_copy(update={
        "classificacao_tecido_proposta": "esfacelo",
        "confianca_classificacao_autodeclarada": "baixa",
        "justificativa_classificacao": "Cor.",
    })

    recuperadas = validar_regioes_persistidas(
        criar_conteudo([regiao])
    )

    assert len(recuperadas) == 1

    assert (
        recuperadas[0].classificacao_tecido_proposta
        == "nao_classificado"
    )


def test_perilesional_ampla_gera_alerta():
    principal = criar_regiao(
        "contorno_visual_lesao",
        1,
        [
            (.40, .30),
            (.60, .30),
            (.65, .50),
            (.60, .70),
            (.40, .70),
            (.35, .50),
        ],
    )

    perilesional = criar_regiao(
        "pele_perilesional",
        2,
        [
            (.30, .20),
            (.70, .20),
            (.75, .50),
            (.70, .80),
            (.30, .80),
            (.25, .50),
        ],
    )

    alertas = auditar_contornos([
        principal,
        perilesional,
    ])

    assert any(
        "consideravelmente maior" in alerta
        for alerta in alertas
    )


def test_perilesional_proxima_nao_e_descartada():
    principal = criar_regiao(
        "contorno_visual_lesao",
        1,
        [
            (.20, .20),
            (.50, .20),
            (.50, .50),
            (.20, .50),
        ],
    )

    perilesional = criar_regiao(
        "pele_perilesional",
        2,
        [
            (.48, .25),
            (.60, .25),
            (.60, .45),
            (.48, .45),
        ],
    )

    antes = [
        r.model_dump(mode="json")
        for r in [principal, perilesional]
    ]

    alertas = auditar_contornos([
        principal,
        perilesional,
    ])

    depois = [
        r.model_dump(mode="json")
        for r in [principal, perilesional]
    ]

    assert alertas == []
    assert antes == depois


def test_auditoria_nao_classifica_tecidos():
    principal = criar_regiao(
        "contorno_visual_lesao",
        1,
        [
            (.40, .30),
            (.60, .30),
            (.65, .50),
            (.60, .70),
            (.40, .70),
            (.35, .50),
        ],
    )

    perilesional = criar_regiao(
        "pele_perilesional",
        2,
        [
            (.30, .20),
            (.70, .20),
            (.75, .50),
            (.70, .80),
            (.30, .80),
            (.25, .50),
        ],
    )

    regioes = [principal, perilesional]

    auditar_contornos(regioes)

    assert all(
        regiao.classificacao_tecido_proposta is None
        for regiao in regioes
    )
