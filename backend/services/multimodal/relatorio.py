
"""Avalia & Trata — Relatórios individuais editáveis.

Preserva as análises originais das IAs.
As edições são realizadas em uma cópia separada.
A aprovação exige uma ação explícita do profissional.
"""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from schemas.multimodal import ResultadoAnaliseMultimodal
from schemas.relatorio import (
    ConjuntoRelatorios,
    EdicaoRelatorio,
    RelatorioIndividual,
)
from services.multimodal.comparador import comparar_resultados
from services.multimodal.validador import validar_resposta


def gerar_relatorios(
    resultado: ResultadoAnaliseMultimodal,
    avaliacao_id: Optional[str] = None,
) -> ConjuntoRelatorios:
    """Gera um relatório individual por provedor disponível."""

    relatorios: Dict[str, RelatorioIndividual] = {}
    indisponiveis = []

    for nome, provedor in resultado.resultados.items():
        if not provedor.sucesso or provedor.resposta is None:
            indisponiveis.append(nome)
            continue

        resposta = provedor.resposta

        conteudo_original = resposta.model_dump(mode="json")

        validacao = validar_resposta(resposta)

        relatorios[nome] = RelatorioIndividual(
            avaliacao_id=avaliacao_id,
            provedor=nome,
            data_processamento=resultado.data_processamento,
            conteudo_original=deepcopy(conteudo_original),
            conteudo_editavel=deepcopy(conteudo_original),
            alertas_validacao=[
                alerta.model_dump(mode="json")
                for alerta in validacao.alertas
            ],
        )

    comparacao = comparar_resultados(resultado)

    return ConjuntoRelatorios(
        avaliacao_id=avaliacao_id,
        data_processamento=resultado.data_processamento,
        relatorios=relatorios,
        provedores_indisponiveis=indisponiveis,
        comparacao=comparacao.model_dump(mode="json"),
    )


def selecionar_relatorio(
    conjunto: ConjuntoRelatorios,
    provedor: str,
) -> RelatorioIndividual:
    """Obtém a análise escolhida pelo profissional."""

    if provedor not in conjunto.relatorios:
        raise ValueError(
            f"Não existe relatório disponível para '{provedor}'."
        )

    return conjunto.relatorios[provedor]


def _localizar_campo(
    conteudo: Dict[str, Any],
    caminho: str,
):
    """Localiza um campo usando caminhos como 'medidas.observacoes'."""

    partes = caminho.split(".")

    if not partes or any(not parte for parte in partes):
        raise ValueError("Caminho de campo inválido.")

    atual: Any = conteudo

    for parte in partes[:-1]:
        if isinstance(atual, dict):
            if parte not in atual:
                raise ValueError(f"Campo inexistente: {caminho}")
            atual = atual[parte]
        elif isinstance(atual, list) and parte.isdecimal():
            indice = int(parte)
            if indice >= len(atual):
                raise ValueError(f"Índice inválido: {caminho}")
            atual = atual[indice]
        else:
            raise ValueError(f"Caminho inválido: {caminho}")

    ultima = partes[-1]

    if isinstance(atual, dict):
        if ultima not in atual:
            raise ValueError(f"Campo inexistente: {caminho}")
        return atual, ultima

    if isinstance(atual, list) and ultima.isdecimal():
        indice = int(ultima)
        if indice >= len(atual):
            raise ValueError(f"Índice inválido: {caminho}")
        return atual, indice

    raise ValueError(f"Caminho inválido: {caminho}")


def editar_campo(
    relatorio: RelatorioIndividual,
    campo: str,
    novo_valor: Any,
    profissional_id: str,
) -> RelatorioIndividual:
    """Edita texto preservando original e registrando a alteração."""

    if relatorio.status == "aprovado":
        raise ValueError(
            "Um relatório aprovado não pode ser editado diretamente."
        )

    if not profissional_id.strip():
        raise ValueError("Identificação profissional obrigatória.")

    # Trabalha em cópia para evitar alterações parciais.
    atualizado = relatorio.model_copy(deep=True)

    destino, chave = _localizar_campo(
        atualizado.conteudo_editavel,
        campo,
    )

    valor_anterior = deepcopy(destino[chave])

    # Primeira versão: apenas campos textuais.
    # Campos técnicos, numéricos e de controle permanecem protegidos.
    if not isinstance(valor_anterior, str):
        raise ValueError(
            "Este campo não é textual. "
            "A edição estruturada será implementada separadamente."
        )

    if not isinstance(novo_valor, str):
        raise ValueError("O novo valor deve ser texto.")

    if valor_anterior == novo_valor:
        return atualizado

    destino[chave] = novo_valor

    atualizado.historico_edicoes.append(
        EdicaoRelatorio(
            campo=campo,
            valor_anterior=valor_anterior,
            valor_novo=novo_valor,
            profissional_id=profissional_id,
        )
    )

    atualizado.status = "em_edicao"
    atualizado.profissional_responsavel = profissional_id

    return atualizado


def aprovar_relatorio(
    relatorio: RelatorioIndividual,
    profissional_id: str,
) -> RelatorioIndividual:
    """Registra a aprovação explícita do relatório selecionado."""

    if not profissional_id.strip():
        raise ValueError("Identificação profissional obrigatória.")

    if relatorio.status == "aprovado":
        raise ValueError("Este relatório já foi aprovado.")

    aprovado = relatorio.model_copy(deep=True)

    aprovado.status = "aprovado"
    aprovado.profissional_responsavel = profissional_id
    aprovado.data_aprovacao = datetime.now(timezone.utc)
    aprovado.revisao_profissional_necessaria = False

    return aprovado
