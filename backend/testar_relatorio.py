
from schemas.multimodal import (
    ResultadoAnaliseMultimodal,
    ResultadoProvedor,
    RespostaEstruturadaModelo,
)
from services.multimodal.relatorio import (
    gerar_relatorios,
    selecionar_relatorio,
    editar_campo,
    aprovar_relatorio,
)


def testar_fluxo_relatorio():
    resposta = RespostaEstruturadaModelo(
        conteudo_descricao="Descrição original da análise."
    )

    resultado = ResultadoAnaliseMultimodal(
        sucesso_geral=True,
        data_processamento="2026-10-28T12:00:00",
        resultados={
            "openai": ResultadoProvedor(
                provedor="openai",
                sucesso=True,
                tempo_execucao_segundos=2.0,
                resposta=resposta,
            ),
            "gemini": ResultadoProvedor(
                provedor="gemini",
                sucesso=True,
                tempo_execucao_segundos=3.0,
                resposta=RespostaEstruturadaModelo(
                    conteudo_descricao="Análise Gemini."
                ),
            ),
            "kimi": ResultadoProvedor(
                provedor="kimi",
                sucesso=True,
                tempo_execucao_segundos=4.0,
                resposta=RespostaEstruturadaModelo(
                    conteudo_descricao="Análise Kimi."
                ),
            ),
        },
    )

    conjunto = gerar_relatorios(
        resultado,
        avaliacao_id="teste-001",
    )

    assert len(conjunto.relatorios) == 3

    selecionado = selecionar_relatorio(
        conjunto,
        "openai",
    )

    editado = editar_campo(
        selecionado,
        campo="conteudo_descricao",
        novo_valor="Descrição revisada pelo profissional.",
        profissional_id="enfermeiro-teste",
    )

    assert (
        editado.conteudo_editavel["conteudo_descricao"]
        == "Descrição revisada pelo profissional."
    )

    assert (
        editado.conteudo_original["conteudo_descricao"]
        == "Descrição original da análise."
    )

    assert (
        selecionado.conteudo_editavel["conteudo_descricao"]
        == "Descrição original da análise."
    )

    assert len(editado.historico_edicoes) == 1
    assert editado.status == "em_edicao"

    aprovado = aprovar_relatorio(
        editado,
        profissional_id="enfermeiro-teste",
    )

    assert aprovado.status == "aprovado"
    assert aprovado.data_aprovacao is not None

    try:
        editar_campo(
            aprovado,
            "conteudo_descricao",
            "Nova alteração",
            "enfermeiro-teste",
        )
        raise AssertionError(
            "Relatório aprovado aceitou edição indevida."
        )
    except ValueError:
        pass

    print("[PASSOU] Geração de três relatórios")
    print("[PASSOU] Seleção de análise")
    print("[PASSOU] Edição de texto")
    print("[PASSOU] Preservação do original")
    print("[PASSOU] Histórico de edição")
    print("[PASSOU] Aprovação profissional")
    print("[PASSOU] Bloqueio após aprovação")


if __name__ == "__main__":
    testar_fluxo_relatorio()
