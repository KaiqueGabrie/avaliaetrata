
import concurrent.futures
import time
from datetime import datetime
from typing import Dict, List, Optional

from schemas.multimodal import (
    AnaliseMultimodalInput,
    ResultadoProvedor,
    ResultadoAnaliseMultimodal,
)

from services.multimodal.base import BaseModelProvider
from services.multimodal.gemini import GeminiProvider
from services.multimodal.openai import OpenAIProvider
from services.multimodal.kimi import KimiProvider


class MultimodalOrchestrator:
    """
    Coordena a execução dos provedores multimodais.

    Cada provedor é executado de forma independente.
    Uma falha ou demora de um provedor não deve impedir
    o retorno dos resultados dos demais.
    """

    MAX_ESPERA_SEGUNDOS = 70

    def __init__(self):
        self._providers: Dict[str, BaseModelProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "kimi": KimiProvider(),
        }

    def executar_analise_comparativa(
        self,
        input_data: AnaliseMultimodalInput,
        provedores_desejados: Optional[List[str]] = None,
    ) -> ResultadoAnaliseMultimodal:

        if provedores_desejados is None:
            provedores_desejados = [
                "gemini",
                "openai",
                "kimi",
            ]

        # Remove nomes repetidos, preservando a ordem.
        provedores_desejados = list(dict.fromkeys(provedores_desejados))

        resultados_finais: Dict[str, ResultadoProvedor] = {}

        provedores_para_executar = [
            self._providers[nome]
            for nome in provedores_desejados
            if nome in self._providers
        ]

        if not provedores_para_executar:
            return ResultadoAnaliseMultimodal(
                sucesso_geral=False,
                data_processamento=datetime.now().isoformat(),
                resultados={},
            )

        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=len(provedores_para_executar)
        )

        inicio_por_provedor = {}
        future_to_provider = {}

        try:
            # Inicia os provedores de forma concorrente.
            for provedor in provedores_para_executar:
                inicio_por_provedor[provedor.provider_name] = time.monotonic()

                future = executor.submit(
                    provedor.analisar,
                    input_data,
                )

                future_to_provider[future] = provedor.provider_name

            # Espera somente até o limite definido.
            concluidas, pendentes = concurrent.futures.wait(
                future_to_provider.keys(),
                timeout=self.MAX_ESPERA_SEGUNDOS,
                return_when=concurrent.futures.ALL_COMPLETED,
            )

            # Registra os resultados que terminaram.
            for future in concluidas:
                nome_provedor = future_to_provider[future]

                try:
                    resultado_provedor = future.result()

                    resultados_finais[nome_provedor] = resultado_provedor

                except Exception as erro:
                    resultados_finais[nome_provedor] = ResultadoProvedor(
                        provedor=nome_provedor,
                        modo="erro",
                        sucesso=False,
                        tempo_execucao_segundos=round(
                            time.monotonic()
                            - inicio_por_provedor[nome_provedor],
                            3,
                        ),
                        resposta=None,
                        mensagem_erro=(
                            "Erro inesperado durante a execução: "
                            f"{str(erro)}"
                        ),
                    )

            # Registra falhas por tempo excedido sem esperar indefinidamente.
            for future in pendentes:
                nome_provedor = future_to_provider[future]

                resultados_finais[nome_provedor] = ResultadoProvedor(
                    provedor=nome_provedor,
                    modo="timeout",
                    sucesso=False,
                    tempo_execucao_segundos=round(
                        time.monotonic()
                        - inicio_por_provedor[nome_provedor],
                        3,
                    ),
                    resposta=None,
                    mensagem_erro=(
                        "O provedor excedeu o limite de espera de "
                        f"{self.MAX_ESPERA_SEGUNDOS} segundos. "
                        "Verifique a conexão, a disponibilidade da API "
                        "e a configuração de timeout do provedor."
                    ),
                )

                # Cancela tarefas que ainda não começaram.
                # Uma tarefa já em execução não pode ser interrompida
                # à força pelo Future.cancel().
                future.cancel()

        finally:
            # Não bloqueia a resposta HTTP esperando uma tarefa pendente.
            # Os timeouts dos próprios provedores também devem estar ativos.
            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )

        sucesso_geral = any(
            resultado.sucesso
            for resultado in resultados_finais.values()
        )

        return ResultadoAnaliseMultimodal(
            sucesso_geral=sucesso_geral,
            data_processamento=datetime.now().isoformat(),
            resultados=resultados_finais,
        )

