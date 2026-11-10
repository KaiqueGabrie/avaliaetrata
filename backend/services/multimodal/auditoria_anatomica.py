
"""Auditoria conservadora de contradições anatômicas explícitas.

Não infere anatomia da fotografia. Compara apenas termos
textuais conhecidos e sinaliza possíveis contradições
para revisão profissional.
"""

from __future__ import annotations

import re
import unicodedata

from schemas.multimodal import RegiaoIdentificada


GRUPOS_ANATOMICOS = {
    "calcanhar": (
        "calcanhar",
        "calcaneo",
    ),
    "cotovelo": (
        "cotovelo",
    ),
    "joelho": (
        "joelho",
    ),
    "tornozelo": (
        "tornozelo",
    ),
    "ombro": (
        "ombro",
    ),
    "punho": (
        "punho",
    ),
    "mao": (
        "mao",
    ),
    "pe": (
        "pe",
    ),
}

# Relações que podem descrever a mesma região geral.
# Evita alertas simplesmente por termos associados.
COMPATIVEIS = {
    frozenset(("calcanhar", "pe")),
    frozenset(("calcanhar", "tornozelo")),
    frozenset(("tornozelo", "pe")),
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return texto.casefold()


def _regioes_mencionadas(texto: str) -> set[str]:
    normalizado = _normalizar(texto)
    encontradas = set()

    for grupo, termos in GRUPOS_ANATOMICOS.items():
        for termo in termos:
            if re.search(
                rf"(?<!\w){re.escape(termo)}(?!\w)",
                normalizado,
            ):
                encontradas.add(grupo)
                break

    return encontradas


def auditar_localizacao(
    localizacao_informada: str | None,
    descricoes: list[str],
) -> list[str]:
    """Compara localidades explicitamente mencionadas.

    Não produz alerta quando não reconhece a localização.
    """

    if not localizacao_informada:
        return []

    locais_informados = _regioes_mencionadas(
        localizacao_informada
    )

    if not locais_informados:
        return []

    contraditorios = set()

    for descricao in descricoes:
        if not isinstance(descricao, str):
            continue

        for local_ia in _regioes_mencionadas(descricao):
            if all(
                local_ia != local_informado
                and frozenset((
                    local_ia,
                    local_informado,
                )) not in COMPATIVEIS
                for local_informado in locais_informados
            ):
                contraditorios.add(local_ia)

    if not contraditorios:
        return []

    return [
        "[AUDITORIA_ANATOMICA] "
        "Possível inconsistência entre a localização "
        "informada pelo profissional "
        f"('{localizacao_informada}') e a referência "
        "anatômica encontrada no texto da IA "
        f"('{local_ia}'). Confira a descrição "
        "antes de validar o relatório."
        for local_ia in sorted(contraditorios)
    ]


def auditar_anatomia_regioes(
    localizacao_informada: str | None,
    regioes: list[RegiaoIdentificada],
) -> list[str]:
    """Audita descrições de regiões propostas pela IA."""

    return auditar_localizacao(
        localizacao_informada,
        [
            regiao.descricao
            for regiao in regioes
        ],
    )
