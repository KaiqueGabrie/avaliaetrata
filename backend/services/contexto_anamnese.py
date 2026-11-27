from schemas.multimodal import AnamneseContextoIA


def montar_contexto_anamnese(anamnese):
    """Extrai apenas dados estruturados e relevantes.

    Nao inclui nome, CPF, telefone, datas,
    identificadores ou campos de texto livre.
    """

    if anamnese is None:
        return None

    def booleano(valor):
        if valor is None:
            return None

        if valor in (0, 1):
            return bool(valor)

        return None

    pulsos = anamnese.pulsos_perifericos

    if pulsos not in (
        "presentes",
        "diminuidos",
        "ausentes",
    ):
        pulsos = None

    contexto = AnamneseContextoIA(
        tabagismo=booleano(anamnese.tabagismo),
        mobilidade_reduzida=booleano(
            anamnese.mobilidade_reduzida
        ),
        possui_varizes=booleano(anamnese.possui_varizes),
        historico_amputacao=booleano(
            anamnese.historico_amputacao
        ),
        pulsos_perifericos=pulsos,
    )

    if all(
        valor is None
        for valor in contexto.model_dump().values()
    ):
        return None

    return contexto
