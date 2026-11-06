"""Testes offline de preservacao segura de respostas T.I.M.E.S. parciais."""
import copy
import pytest

from schemas.multimodal import (
    AnaliseMultimodalInput,
    AnaliseTecnicaOpenCVInput,
    DadosClinicosInput,
)
from services.multimodal.prompt_padrao import normalizar_resposta
from services.multimodal.validador import validar_resposta


def entrada():
    return AnaliseMultimodalInput(
        caminho_imagem_original="original.png",
        caminho_imagem_processada="processada.png",
        dimensoes_originais={"largura": 640, "altura": 480},
        dimensoes_processadas={"largura": 640, "altura": 480},
        analise_tecnica=AnaliseTecnicaOpenCVInput(
            brilho_medio=80, contraste_global=50
        ),
        dados_clinicos=DadosClinicosInput(localizacao="calcanhar"),
    )


def dados():
    return {
        "descricao": "Superficie com areas de coloracao distinta.",
        "times": {
            k: {
                "status": "parcialmente_avaliavel",
                "observacoes": [f"Observacao visual do componente {k}."],
                "pendencias": [],
                "limitacoes": [],
            }
            for k in "TIMES"
        },
        "regioes_propostas": [],
    }


def test_todos_componentes_presentes_permanece_sucesso():
    resposta = normalizar_resposta(dados(), entrada())
    assert resposta.status_resposta == "sucesso"
    assert len(resposta.avaliacao_times) == 5


def test_kimi_omite_s_mantem_quatro_componentes_e_sinaliza_revisao():
    original = dados()
    del original["times"]["S"]
    copia = copy.deepcopy(original)
    resposta = normalizar_resposta(original, entrada())
    assert original == copia  # O JSON da API nao deve ser alterado.
    assert resposta.status_resposta == "sucesso_parcial"
    assert [item.componente for item in resposta.avaliacao_times] == list("TIMES")
    por_letra = {item.componente: item for item in resposta.avaliacao_times}
    assert por_letra["S"].status == "nao_avaliavel"
    assert por_letra["S"].observacoes_visuais == []
    assert por_letra["S"].informacoes_pendentes
    assert por_letra["T"].observacoes_visuais == ["Observacao visual do componente T."]
    assert any("S" in aviso and "parcial" in aviso.lower()
               for aviso in resposta.pontos_para_revisao_profissional)
    assert any("S" in aviso for aviso in resposta.limitacoes_declaradas)
    assert resposta.validacao_profissional_necessaria is True


def test_componente_malformado_nao_e_interpretado_como_observacao():
    original = dados()
    original["times"]["M"] = "molhado"
    resposta = normalizar_resposta(original, entrada())
    por_letra = {item.componente: item for item in resposta.avaliacao_times}
    assert resposta.status_resposta == "sucesso_parcial"
    assert por_letra["M"].status == "nao_avaliavel"
    assert por_letra["M"].observacoes_visuais == []


def test_ausencia_total_de_times_nao_passa_como_sucesso():
    original = dados()
    original["times"] = {}
    with pytest.raises(ValueError, match="sem componentes"):
        normalizar_resposta(original, entrada())


def test_resposta_sem_descricao_continua_sendo_rejeitada():
    original = dados()
    original["descricao"] = ""
    with pytest.raises(ValueError, match="descricao"):
        normalizar_resposta(original, entrada())


def test_validador_sinaliza_resposta_parcial_sem_falha_estrutural():
    original = dados()
    del original["times"]["S"]
    resposta = normalizar_resposta(original, entrada())
    relatorio = validar_resposta(resposta)
    assert relatorio.valido_estruturalmente is True
    assert relatorio.requer_revisao is True
    assert any(a.codigo == "RESPOSTA_TIMES_PARCIAL" for a in relatorio.alertas)


def test_dois_ou_menos_componentes_nao_sao_aceitos():
    original = dados()
    original["times"] = {k: v for k, v in original["times"].items() if k in "TI"}
    with pytest.raises(ValueError, match="quantidade suficiente"):
        normalizar_resposta(original, entrada())
