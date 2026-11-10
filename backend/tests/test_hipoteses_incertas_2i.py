
from services.multimodal.validacao_regioes import (
    validar_regioes_propostas,
)


def criar_regiao(
    classe="granulacao",
    confianca="baixa",
    justificativa=None,
):
    return {
        "tipo_regiao": "superficie_avermelhada",
        "descricao": "Área superficial com características visíveis.",
        "confianca": "moderada",
        "pontos": [
            {"x": 0.2, "y": 0.2},
            {"x": 0.5, "y": 0.2},
            {"x": 0.5, "y": 0.5},
            {"x": 0.2, "y": 0.5},
        ],
        "classificacao_tecido_proposta": classe,
        "justificativa_classificacao": (
            justificativa
            if justificativa is not None
            else (
                "Hipótese baseada em características "
                "superficiais descritas, ainda incertas."
            )
        ),
        "confianca_classificacao": confianca,
    }


def test_preserva_hipotese_com_confianca_baixa():
    regioes, _ = validar_regioes_propostas([
        criar_regiao()
    ])

    assert len(regioes) == 1
    assert (
        regioes[0].classificacao_tecido_proposta
        == "granulacao"
    )
    assert (
        regioes[0].confianca_classificacao_autodeclarada
        == "baixa"
    )
    assert regioes[0].revisao_profissional_necessaria is True


def test_descarta_classificacao_sem_justificativa():
    regioes, _ = validar_regioes_propostas([
        criar_regiao(justificativa="Cor vermelha.")
    ])

    assert len(regioes) == 1
    assert (
        regioes[0].classificacao_tecido_proposta
        == "nao_classificado"
    )


def test_preserva_nao_classificado():
    regioes, _ = validar_regioes_propostas([
        criar_regiao(
            classe="nao_classificado",
            justificativa="Imagem insuficiente para classificação.",
        )
    ])

    assert len(regioes) == 1
    assert (
        regioes[0].classificacao_tecido_proposta
        == "nao_classificado"
    )


def test_rejeita_coordenadas_invalidas():
    regiao = criar_regiao()
    regiao["pontos"][0]["x"] = 1.5

    regioes, _ = validar_regioes_propostas([regiao])

    assert regioes == []


def test_contorno_nao_recebe_classe_de_tecido():
    regiao = criar_regiao(classe="necrose")
    regiao["tipo_regiao"] = "contorno_visual_lesao"

    regioes, _ = validar_regioes_propostas([regiao])

    assert len(regioes) == 1
    assert (
        regioes[0].classificacao_tecido_proposta
        == "nao_classificado"
    )


def test_confianca_invalida_nao_e_aceita():
    regioes, _ = validar_regioes_propostas([
        criar_regiao(confianca="certeza_absoluta")
    ])

    assert len(regioes) == 1
    assert (
        regioes[0].classificacao_tecido_proposta
        == "nao_classificado"
    )
