import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional

from schemas.multimodal import (
    AnaliseMultimodalInput,
    ResultadoProvedor,
    ResultadoAnaliseMultimodal
)

from services.multimodal.base import BaseModelProvider
from services.multimodal.gemini import GeminiProvider
from services.multimodal.openai import OpenAIProvider
from services.multimodal.kimi import KimiProvider


class MultimodalOrchestrator:
    """
    Responsável por coordenar a execução dos provedores multimodais.

    Cada provedor é executado de forma independente.
    Uma falha em um provedor não impede a execução dos demais.
    """

    def __init__(self):
        self._providers: Dict[str, BaseModelProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "kimi": KimiProvider()
        }

    def executar_analise_comparativa(
        self,
        input_data: AnaliseMultimodalInput,
        provedores_desejados: Optional[List[str]] = None
    ) -> ResultadoAnaliseMultimodal:

        if provedores_desejados is None:
            provedores_desejados = [
                "gemini",
                "openai",
                "kimi"
            ]

        resultados_finais: Dict[str, ResultadoProvedor] = {}

        provedores_para_executar = [
            self._providers[nome]
            for nome in provedores_desejados
            if nome in self._providers
        ]

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(provedores_para_executar) or 1
        ) as executor:

            future_to_provider = {
                executor.submit(
                    prov.analisar,
                    input_data
                ): prov.provider_name
                for prov in provedores_para_executar
            }

            for future in concurrent.futures.as_completed(
                future_to_provider
            ):
                nome_provedor = future_to_provider[future]

                try:
                    resultado_provedor = future.result()

                    resultados_finais[nome_provedor] = (
                        resultado_provedor
                    )

                except Exception as exc:

                    resultados_finais[nome_provedor] = (
                        ResultadoProvedor(
                            provedor=nome_provedor,
                            modo="simulacao",
                            sucesso=False,
                            tempo_execucao_segundos=0.0,
                            resposta=None,
                            mensagem_erro=(
                                "Erro na execução do provedor: "
                                f"{str(exc)}"
                            )
                        )
                    )

        sucesso_geral = any(
            resultado.sucesso
            for resultado in resultados_finais.values()
        )

        return ResultadoAnaliseMultimodal(
            sucesso_geral=sucesso_geral,
            data_processamento=datetime.now().isoformat(),
            resultados=resultados_finais
        )