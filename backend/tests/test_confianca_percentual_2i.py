"""Testes de confiança autodeclarada da avaliação."""

from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
)

from services.multimodal.prompt_padrao import (
    construir_prompt,
    normalizar_resposta,
)


def entrada():
    return AnaliseMultimodalInput(
        caminho_imagem_original="foto.png",
        caminho_imagem_processada="processada.png",
        dimensoes_originais={"largura": 400, "altura": 400},
        dimensoes_processadas={"largura": 400, "altura": 400},
        analise_tecnica=AnaliseTecnicaOpenCVInput(
            brilho_medio=90,
            contraste_global=55,
        ),
        dados_clinicos=DadosClinicosInput(
            localizacao="perna",
        ),
    )


def dados_base():
    return {
        "descricao": "Descrição visual de teste.",
        "times": {
            letra: {
                "status": "nao_avaliavel",
                "observacoes": [],
                "pendencias": [],
                "limitacoes": [],
            }
            for letra in "TIMES"
        },
    }


def test_percentual_valido():
    dados = dados_base()
    dados.update({
        "confianca_avaliacao_percentual": 76.5,
        "justificativa_confianca_avaliacao": (
            "A superfície está parcialmente visível."
        ),
        "limitacoes_confianca_avaliacao": [
            "Iluminação irregular."
        ],
    })

    resposta = normalizar_resposta(dados, entrada())

    assert resposta.confianca_avaliacao_percentual == 76.5
    assert resposta.justificativa_confianca_avaliacao
    assert resposta.limitacoes_confianca_avaliacao == [
        "Iluminação irregular."
    ]


def test_sem_percentual_permanece_nulo():
    resposta = normalizar_resposta(dados_base(), entrada())
    assert resposta.confianca_avaliacao_percentual is None


def test_percentual_fora_do_intervalo():
    dados = dados_base()
    dados.update({
        "confianca_avaliacao_percentual": 150,
        "justificativa_confianca_avaliacao": "Teste.",
    })

    resposta = normalizar_resposta(dados, entrada())
    assert resposta.confianca_avaliacao_percentual is None


def test_percentual_sem_justificativa():
    dados = dados_base()
    dados["confianca_avaliacao_percentual"] = 80

    resposta = normalizar_resposta(dados, entrada())
    assert resposta.confianca_avaliacao_percentual is None


def test_booleano_nao_e_percentual():
    dados = dados_base()
    dados.update({
        "confianca_avaliacao_percentual": True,
        "justificativa_confianca_avaliacao": "Teste.",
    })

    resposta = normalizar_resposta(dados, entrada())
    assert resposta.confianca_avaliacao_percentual is None


def test_prompt_solicita_confianca():
    prompt = construir_prompt(entrada())

    assert "confianca_avaliacao_percentual" in prompt
    assert "justificativa_confianca_avaliacao" in prompt
    assert "limitacoes_confianca_avaliacao" in prompt
    assert "confiança é autodeclarada" in prompt


def test_serializacao_preserva_percentual():
    dados = dados_base()
    dados.update({
        "confianca_avaliacao_percentual": 85,
        "justificativa_confianca_avaliacao": (
            "Imagem com boa visibilidade."
        ),
    })

    resposta = normalizar_resposta(dados, entrada())
    serializado = resposta.model_dump(mode="json")

    assert serializado["confianca_avaliacao_percentual"] == 85
    assert serializado["justificativa_confianca_avaliacao"]
