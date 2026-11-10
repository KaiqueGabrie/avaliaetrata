
"""Testes offline de auditoria geométrica e anatômica."""

from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
    PontoImagem,
    RegiaoIdentificada,
)

from services.multimodal.auditoria_contornos import (
    auditar_contornos,
)

from services.multimodal.auditoria_anatomica import (
    auditar_localizacao,
    auditar_anatomia_regioes,
)

from services.multimodal.prompt_padrao import (
    normalizar_resposta,
)


def quadrado(x1, y1, x2, y2):
    return [
        PontoImagem(x=x1, y=y1),
        PontoImagem(x=x2, y=y1),
        PontoImagem(x=x2, y=y2),
        PontoImagem(x=x1, y=y2),
    ]


def regiao(tipo, indice, pontos, descricao="Teste"):
    return RegiaoIdentificada(
        identificador=f"{tipo}-{indice}",
        rotulo="Região de teste",
        descricao=descricao,
        pontos=pontos,
        confianca_autodeclarada="moderada",
        revisao_profissional_necessaria=True,
    )


def contorno():
    return regiao(
        "contorno_visual_lesao",
        1,
        quadrado(.20, .20, .50, .50),
    )


def test_perilesional_afastada_gera_alerta():
    pele = regiao(
        "pele_perilesional",
        2,
        quadrado(.75, .75, .95, .95),
    )

    alertas = auditar_contornos([
        contorno(),
        pele,
    ])

    assert len(alertas) == 1
    assert "[AUDITORIA_CONTORNO]" in alertas[0]
    assert "pele_perilesional-2" in alertas[0]


def test_perilesional_proxima_nao_gera_alerta():
    pele = regiao(
        "pele_perilesional",
        2,
        quadrado(.45, .35, .70, .60),
    )

    assert auditar_contornos([
        contorno(),
        pele,
    ]) == []


def test_perilesional_nao_precisa_estar_dentro():
    pele = regiao(
        "pele_perilesional",
        2,
        quadrado(.49, .25, .65, .45),
    )

    assert auditar_contornos([
        contorno(),
        pele,
    ]) == []


def test_auditoria_preserva_poligonos():
    regioes = [
        contorno(),
        regiao(
            "pele_perilesional",
            2,
            quadrado(.75, .75, .95, .95),
        ),
    ]

    antes = [
        r.model_dump(mode="json")
        for r in regioes
    ]

    auditar_contornos(regioes)

    depois = [
        r.model_dump(mode="json")
        for r in regioes
    ]

    assert antes == depois


def test_calcanhar_e_cotovelo_geram_alerta():
    avisos = auditar_localizacao(
        "Calcanhar esquerdo",
        [
            "Área escura central na região do cotovelo.",
        ],
    )

    assert len(avisos) == 1
    assert "[AUDITORIA_ANATOMICA]" in avisos[0]


def test_localizacao_coerente_nao_gera_alerta():
    assert auditar_localizacao(
        "Calcanhar esquerdo",
        [
            "Lesão na região posterior do calcanhar.",
        ],
    ) == []


def test_anatomia_ausente_nao_inventa_erro():
    assert auditar_localizacao(
        "Localização não especificada",
        ["Área escura de bordas irregulares."],
    ) == []


def test_regiao_com_anatomia_incoerente():
    proposta = regiao(
        "contorno_visual_lesao",
        1,
        quadrado(.20, .20, .50, .50),
        "Área escura central na região do cotovelo.",
    )

    avisos = auditar_anatomia_regioes(
        "calcanhar",
        [proposta],
    )

    assert len(avisos) == 1


def test_normalizador_registra_alerta_anatomico():
    entrada = AnaliseMultimodalInput(
        caminho_imagem_original="foto.png",
        caminho_imagem_processada="processada.png",
        dimensoes_originais={
            "largura": 400,
            "altura": 400,
        },
        dimensoes_processadas={
            "largura": 400,
            "altura": 400,
        },
        analise_tecnica=AnaliseTecnicaOpenCVInput(
            brilho_medio=90,
            contraste_global=40,
        ),
        dados_clinicos=DadosClinicosInput(
            localizacao="Calcanhar esquerdo",
        ),
    )

    dados = {
        "descricao": (
            "Área visualmente escura na região "
            "do cotovelo."
        ),
        "times": {
            letra: {
                "status": "nao_avaliavel",
                "observacoes": [],
                "pendencias": [],
                "limitacoes": [],
            }
            for letra in "TIMES"
        },
        "regioes_propostas": [],
    }

    resposta = normalizar_resposta(
        dados,
        entrada,
    )

    assert any(
        "[AUDITORIA_ANATOMICA]" in aviso
        for aviso
        in resposta.pontos_para_revisao_profissional
    )

    assert any(
        "[AUDITORIA_ANATOMICA]" in aviso
        for aviso
        in resposta.marcacoes_imagem.limitacoes
    )
