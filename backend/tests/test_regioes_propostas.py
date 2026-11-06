"""Testes offline: nenhum envio a provedores, sem dados de pacientes."""
from schemas.multimodal import AnaliseMultimodalInput, AnaliseTecnicaOpenCVInput, DadosClinicosInput
from services.multimodal.prompt_padrao import construir_prompt, normalizar_resposta
from services.multimodal.validacao_regioes import validar_regioes_propostas


def _entrada():
    return AnaliseMultimodalInput(
        caminho_imagem_original="original.jpg",
        caminho_imagem_processada="processada.png",
        dimensoes_originais={"largura": 640, "altura": 480},
        dimensoes_processadas={"largura": 640, "altura": 480},
        analise_tecnica=AnaliseTecnicaOpenCVInput(brilho_medio=80, contraste_global=50),
        dados_clinicos=DadosClinicosInput(localizacao="calcanhar"),
    )


def _dados(regioes):
    return {
        "descricao": "Área visualmente distinta na fotografia.",
        "times": {k: {"status": "nao_avaliavel", "observacoes": [], "pendencias": [], "limitacoes": []}
                  for k in "TIMES"},
        "regioes_propostas": regioes,
    }


def _regiao(**kw):
    d = {
        "tipo_regiao": "contorno_visual_lesao",
        "descricao": "Contorno aparente",
        "confianca": "moderada",
        "pontos": [{"x": .2, "y": .2}, {"x": .6, "y": .2}, {"x": .6, "y": .6}, {"x": .2, "y": .6}],
    }
    d.update(kw)
    return d


def test_prompt_contem_contrato_e_nao_fabrica():
    texto = construir_prompt(_entrada())
    assert '"regioes_propostas": []' in texto
    assert '"contorno_visual_lesao"' in texto
    assert 'lista vazia' in texto


def test_poligono_valido_vira_proposta_nao_aprovada():
    r = normalizar_resposta(_dados([_regiao()]), _entrada())
    assert len(r.marcacoes_imagem.regioes) == 1
    regiao = r.marcacoes_imagem.regioes[0]
    assert regiao.rotulo == "Contorno visual aparente da lesão"
    assert regiao.revisao_profissional_necessaria is True
    assert regiao.pontos[0].x == .2
    assert r.medidas.area_calculada_cm2 is None
    assert r.avaliacao_tecidos.tecidos == []


def test_sem_regioes_nao_inventa_marcacoes():
    r = normalizar_resposta(_dados([]), _entrada())
    assert r.marcacoes_imagem.regioes == []
    assert any("Nenhuma região" in s for s in r.marcacoes_imagem.limitacoes)


def test_descarta_coordenadas_fora_da_imagem():
    r, _ = validar_regioes_propostas([_regiao(pontos=[{"x": 2, "y": .1}, {"x": .2, "y": .2}, {"x": .3, "y": .5}])])
    assert not r


def test_descarta_baixa_confianca():
    r, _ = validar_regioes_propostas([_regiao(confianca="baixa")])
    assert not r


def test_descarta_auto_intersecao():
    cruzado = [{"x": .1, "y": .1}, {"x": .6, "y": .6}, {"x": .1, "y": .6}, {"x": .6, "y": .1}]
    r, _ = validar_regioes_propostas([_regiao(pontos=cruzado)])
    assert not r


def test_descarta_categorias_diagnosticas():
    r, _ = validar_regioes_propostas([_regiao(tipo_regiao="necrose")])
    assert not r


def test_descarta_coordenadas_booleanas_e_infinitas():
    r, _ = validar_regioes_propostas([_regiao(pontos=[{"x": True, "y": .1}, {"x": .2, "y": .2}, {"x": .3, "y": .5}])])
    assert not r
    r, _ = validar_regioes_propostas([_regiao(pontos=[{"x": float('inf'), "y": .1}, {"x": .2, "y": .2}, {"x": .3, "y": .5}])])
    assert not r


def test_ignora_regioes_duplicadas():
    r, _ = validar_regioes_propostas([_regiao(), _regiao()])
    assert len(r) == 1


def test_fechamento_duplicado_aceito():
    d = _regiao()
    d["pontos"].append(d["pontos"][0])
    r, _ = validar_regioes_propostas([d])
    assert len(r) == 1
    assert len(r[0].pontos) == 4


def test_tipo_malformado_nao_derruba_provedor():
    r, _ = validar_regioes_propostas([_regiao(tipo_regiao={"inesperado": True})])
    assert not r

def test_multiplas_areas_separadas_mesma_cor():
    a = _regiao(tipo_regiao="superficie_escura")
    b = _regiao(tipo_regiao="superficie_escura", pontos=[
        {"x": .7, "y": .7}, {"x": .9, "y": .7}, {"x": .8, "y": .9}
    ])
    r, _ = validar_regioes_propostas([a, b])
    assert len(r) == 2
    assert r[0].identificador != r[1].identificador
