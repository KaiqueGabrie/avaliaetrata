from types import SimpleNamespace

from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
)

from services.contexto_anamnese import (
    montar_contexto_anamnese,
)

from services.multimodal.prompt_padrao import (
    construir_prompt,
)


def registro(**alteracoes):
    dados = {
        "tabagismo": None,
        "mobilidade_reduzida": None,
        "possui_varizes": None,
        "historico_amputacao": None,
        "pulsos_perifericos": None,
        "historia_pregressa": "IDENTIFICADOR_FICTICIO_TESTE",
        "outras_patologias": "TEXTO_PRIVADO_TESTE",
    }

    dados.update(alteracoes)

    return SimpleNamespace(**dados)


def test_anamnese_ausente():
    assert montar_contexto_anamnese(None) is None


def test_anamnese_sem_informacoes_estruturadas():
    assert montar_contexto_anamnese(registro()) is None


def test_preserva_respostas_negativas_e_desconhecidas():
    contexto = montar_contexto_anamnese(
        registro(
            tabagismo=1,
            mobilidade_reduzida=0,
        )
    )

    assert contexto.tabagismo is True
    assert contexto.mobilidade_reduzida is False
    assert contexto.possui_varizes is None


def test_nao_transmite_textos_livres():
    contexto = montar_contexto_anamnese(
        registro(tabagismo=1)
    )

    dados = contexto.model_dump_json()

    assert "IDENTIFICADOR_FICTICIO_TESTE" not in dados
    assert "TEXTO_PRIVADO_TESTE" not in dados


def test_pulsos_desconhecidos():
    contexto = montar_contexto_anamnese(
        registro(
            tabagismo=0,
            pulsos_perifericos="valor_invalido",
        )
    )

    assert contexto.pulsos_perifericos is None


def test_contexto_incluido_no_prompt_compartilhado():
    contexto = montar_contexto_anamnese(
        registro(
            tabagismo=1,
            mobilidade_reduzida=0,
        )
    )

    entrada = AnaliseMultimodalInput(
        caminho_imagem_original="original.jpg",
        caminho_imagem_processada="processada.jpg",
        dimensoes_originais={"largura": 800, "altura": 600},
        dimensoes_processadas={"largura": 800, "altura": 600},
        analise_tecnica=AnaliseTecnicaOpenCVInput(
            brilho_medio=100,
            contraste_global=30,
        ),
        dados_clinicos=DadosClinicosInput(
            localizacao="Regiao de teste",
            anamnese_contexto=contexto,
        ),
    )

    prompt = construir_prompt(entrada)

    assert '"tabagismo": true' in prompt
    assert '"mobilidade_reduzida": false' in prompt
    assert "IDENTIFICADOR_FICTICIO_TESTE" not in prompt


def test_contexto_opcional_por_padrao():
    dados = DadosClinicosInput(
        localizacao="Regiao de teste"
    )

    assert dados.anamnese_contexto is None
