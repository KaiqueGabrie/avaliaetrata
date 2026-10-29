"""Avalia & Trata — testes locais do Comparador Multimodal v1.2.

Execute a partir da pasta backend: python testar_comparador.py
Sem chamadas às APIs e sem dependência de pytest.
"""
from datetime import datetime
from schemas.multimodal import ResultadoAnaliseMultimodal, ResultadoProvedor, RespostaEstruturadaModelo
from services.multimodal.comparador import comparar_resultados

NOMES = {"T": "Tecido", "I": "Inflamação/infecção", "M": "Umidade", "E": "Bordas", "S": "Pele ao redor"}
STATUS_PADRAO = "parcialmente_avaliavel"


def resposta(status=None, observacoes=None, caracteristicas=None):
    status = status or {}
    observacoes = observacoes or {}
    itens = [
        {"componente": letra, "nome": nome,
         "status": status.get(letra, STATUS_PADRAO),
         "observacoes_visuais": observacoes.get(letra, []),
         "dados_clinicos_relacionados": [], "informacoes_pendentes": [], "limitacoes": []}
        for letra, nome in NOMES.items()
    ]
    return RespostaEstruturadaModelo.model_validate({
        "status_resposta": "sucesso", "avaliacao_times": itens,
        "caracteristicas_visuais": caracteristicas or [],
        "validacao_profissional_necessaria": True,
    })


def comparar(cenarios):
    """cenarios: {provedor: resposta | None}; None simula indisponibilidade."""
    resultados = {}
    for nome, resp in cenarios.items():
        resultados[nome] = ResultadoProvedor(
            provedor=nome, modo="teste_local", sucesso=resp is not None,
            tempo_execucao_segundos=0.01, resposta=resp,
            mensagem_erro=None if resp is not None else "Indisponível no teste",
        )
    return comparar_resultados(ResultadoAnaliseMultimodal(
        sucesso_geral=any(r is not None for r in cenarios.values()),
        data_processamento=datetime.now().isoformat(), resultados=resultados,
    ))


def executar(nome, teste):
    try:
        teste()
    except Exception as erro:
        print(f"[FALHOU] {nome}: {type(erro).__name__}: {erro}")
        return False
    print(f"[PASSOU] {nome}")
    return True


def teste_status_original():
    r = comparar({
        "openai": resposta(status={"T": "avaliavel"}),
        "gemini": resposta(status={"T": "parcialmente_avaliavel"}),
        "kimi": resposta(status={"T": "avaliavel"}),
    })
    assert r.versao == "1.2"
    assert r.componentes_com_status_divergente == ["T"]
    assert set(r.componentes_com_status_concordante) == {"I", "M", "E", "S"}
    assert len(r.provedores_comparados) == 3
    assert r.validacao_profissional_necessaria is True
    assert r.total_divergencias_descritivas == 0


def teste_umidade_contraditoria():
    r = comparar({
        "openai": resposta(observacoes={"M": ["Aparência úmida na superfície da lesão."]}),
        "gemini": resposta(observacoes={"M": ["Superfície com aspecto predominantemente seco."]}),
        "kimi": resposta(observacoes={"M": ["Superfície do material com aparência predominantemente seca."]}),
    })
    c = r.componentes["M"]
    assert c.divergencia_descritiva, c.model_dump()
    assert "UMIDADE_SUPERFICIAL" in [d.codigo for d in c.divergencias_descritivas]
    assert {e.provedor for e in c.divergencias_descritivas[0].evidencias} == {"openai", "gemini", "kimi"}
    assert "M" in r.componentes_com_divergencia_descritiva


def teste_bordas_contraditorias():
    r = comparar({
        "openai": resposta(observacoes={"E": ["As bordas da lesão são irregulares."]}),
        "gemini": resposta(observacoes={"E": ["Bordas delimitadas, regulares, com faixa amarelada."]},
                           caracteristicas=[{"caracteristica": "bordas", "descricao": "Bordas bem delimitadas, contorno regular a ovalado.", "status": "avaliavel"}]),
        "kimi": resposta(observacoes={"E": ["Bordas com contorno definido e relativamente regular."]}),
    })
    c = r.componentes["E"]
    assert c.divergencia_descritiva, c.model_dump()
    assert "BORDAS_REGULARIDADE" in [d.codigo for d in c.divergencias_descritivas]
    assert c.concordancia_status  # Mesmo status, mas descrições incompatíveis.
    assert all(d.requer_revisao_profissional for d in c.divergencias_descritivas)
# ============================================================
# EXECUÇÃO AUTOMÁTICA DOS TESTES
# ============================================================

if __name__ == "__main__":
    import inspect
    import sys

    testes = [
        (nome, funcao)
        for nome, funcao in globals().items()
        if nome.startswith("teste_")
        and inspect.isfunction(funcao)
    ]

    aprovados = 0
    reprovados = 0

    print("\n=== AVALIA & TRATA — TESTES DO COMPARADOR V1.2 ===\n")

    for nome, funcao in testes:
        try:
            funcao()
            print(f"[PASSOU] {nome}")
            aprovados += 1

        except Exception as erro:
            print(f"[FALHOU] {nome}")
            print(f"Motivo: {erro}\n")
            reprovados += 1

    print("\n======================================")
    print(f"Total de testes: {len(testes)}")
    print(f"Aprovados: {aprovados}")
    print(f"Reprovados: {reprovados}")
    print("======================================")

    if reprovados:
        sys.exit(1)
