"""Avalia & Trata — testes locais do Validador 2.2.1.
Execute na pasta backend: python testar_validador.py
Não utiliza APIs nem pytest.
"""
from schemas.multimodal import RespostaEstruturadaModelo
from services.multimodal.validador import validar_resposta, adicionar_alertas_revisao

NOMES = {"T": "Tecido", "I": "Inflamação/infecção", "M": "Umidade", "E": "Bordas", "S": "Pele ao redor"}


def resposta(descricao="", caracteristicas=None, status=None, observacoes=None, medidas=None, regioes=None):
    status = status or {}
    observacoes = observacoes or {}
    dados = {
        "conteudo_descricao": descricao,
        "caracteristicas_visuais": caracteristicas or [],
        "avaliacao_times": [
            {"componente": letra, "nome": nome,
             "status": status.get(letra, "nao_avaliavel"),
             "observacoes_visuais": observacoes.get(letra, [])}
            for letra, nome in NOMES.items()
        ],
    }
    if medidas is not None:
        dados["medidas"] = medidas
    if regioes is not None:
        dados["marcacoes_imagem"] = {"regioes": regioes}
    return RespostaEstruturadaModelo.model_validate(dados)


def codigos(r):
    return {a.codigo for a in validar_resposta(r).alertas}


def teste_cenario_original():
    r = resposta(
        descricao="Lesão com superfície escura e coloração avermelhada ao redor.",
        caracteristicas=[
            {"caracteristica": "pele ao redor", "descricao": "Pele adjacente intacta, sem alterações visíveis.", "status": "avaliavel"},
            {"caracteristica": "bordas", "descricao": "Bordas irregulares.", "status": "avaliavel"},
        ],
    )
    rel = validar_resposta(r)
    assert "POSSIVEL_CONTRADICAO_PELE" in {a.codigo for a in rel.alertas}, rel.model_dump()
    assert {a.componente for a in rel.alertas if a.codigo == "CARACTERISTICA_SEM_TIMES"} == {"S", "E"}
    assert rel.valido_estruturalmente and rel.requer_revisao
    assert rel.total_alertas == len(rel.alertas)
    original = r.model_dump()
    revisada = adicionar_alertas_revisao(r, rel)
    assert r.model_dump() == original, "A resposta original foi alterada"
    assert any("POSSIVEL_CONTRADICAO_PELE" in p for p in revisada.pontos_para_revisao_profissional)
    novamente = adicionar_alertas_revisao(revisada, rel)
    assert novamente.pontos_para_revisao_profissional == revisada.pontos_para_revisao_profissional


def teste_sem_contradicao_quando_regioes_distintas():
    r = resposta(
        descricao="Coloração avermelhada no leito da lesão.",
        caracteristicas=[{"caracteristica": "pele ao redor", "descricao": "Pele adjacente sem alterações.", "status": "avaliavel"}],
    )
    assert "POSSIVEL_CONTRADICAO_PELE" not in codigos(r)


def teste_negacao_de_vermelhidao():
    r = resposta(
        descricao="Pele ao redor sem eritema.",
        caracteristicas=[{"caracteristica": "pele ao redor", "descricao": "Pele adjacente sem alterações.", "status": "avaliavel"}],
    )
    assert "POSSIVEL_CONTRADICAO_PELE" not in codigos(r)


def teste_propriedade_fisica_afirmativa():
    r = resposta(descricao="Material escuro, firme e enrugado.")
    assert "PROPRIEDADE_NAO_VISUAL_CONSISTENCIA_FISICA" in codigos(r)


def teste_propriedade_fisica_incerteza():
    r = resposta(descricao="Não é possível confirmar se o material está firme apenas pela fotografia.")
    assert "PROPRIEDADE_NAO_VISUAL_CONSISTENCIA_FISICA" not in codigos(r)


def teste_leito_encoberto_e_t_avaliavel():
    r = resposta(
        caracteristicas=[{"caracteristica": "leito", "descricao": "Leito encoberto.", "status": "nao_avaliavel"}],
        status={"T": "avaliavel"}, observacoes={"T": ["Superfície visível escura."]},
    )
    assert "LEITO_NAO_VISIVEL_T_AVALIAVEL" in codigos(r)


def teste_area_sem_calibracao():
    r = resposta(medidas={"area_calculada_cm2": 10.0, "metodo_medicao": "estimativa visual sem referência de escala"})
    rel = validar_resposta(r)
    assert any("AREA" in a.codigo or "MEDICAO" in a.codigo for a in rel.alertas), rel.model_dump()


def teste_poligono_incompleto():
    r = resposta(regioes=[{"identificador": "r1", "rotulo": "região simulada", "pontos": [{"x": 0.1, "y": 0.2}, {"x": 0.3, "y": 0.4}]}])
    assert "POLIGONO_INCOMPLETO" in codigos(r)


if __name__ == "__main__":
    import sys
    testes = [(n, f) for n, f in list(globals().items()) if n.startswith("teste_") and callable(f)]
    falhas = 0
    print("\n=== AVALIA & TRATA — TESTES DO VALIDADOR 2.2.1 ===\n")
    for nome, teste in testes:
        try:
            teste()
            print(f"[PASSOU] {nome}")
        except Exception as erro:
            falhas += 1
            print(f"[FALHOU] {nome}: {erro}")
    print(f"\nTotal: {len(testes)} | Aprovados: {len(testes)-falhas} | Reprovados: {falhas}")
    sys.exit(1 if falhas else 0)
