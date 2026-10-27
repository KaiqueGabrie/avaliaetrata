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
    Executa provedores multimodais em paralelo.

    A falha de um provedor não deve impedir o retorno
    dos resultados dos outros.
    """

    MAX_ESPERA_SEGUNDOS = 135

    def __init__(self):
        self._providers: Dict[str, BaseModelProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "kimi": KimiProvider(),
        }

    @staticmethod
    def _falha(
        nome: str,
        mensagem: str,
        tempo: float = 0.0,
        modo: str = "erro",
    ) -> ResultadoProvedor:
        return ResultadoProvedor(
            provedor=nome,
            modo=modo,
            sucesso=False,
            tempo_execucao_segundos=round(tempo, 3),
            resposta=None,
            mensagem_erro=mensagem,
        )

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

        # Remove nomes repetidos sem alterar a ordem.
        provedores_desejados = list(
            dict.fromkeys(provedores_desejados)
        )

        resultados_finais: Dict[str, ResultadoProvedor] = {}

        # Informa explicitamente os nomes desconhecidos.
        for nome in provedores_desejados:
            if nome not in self._providers:
                resultados_finais[nome] = self._falha(
                    nome,
                    f"Provedor '{nome}' não está configurado.",
                )

        provedores_para_executar = [
            self._providers[nome]
            for nome in provedores_desejados
            if nome in self._providers
        ]

        if not provedores_para_executar:
            return ResultadoAnaliseMultimodal(
                sucesso_geral=False,
                data_processamento=datetime.now().isoformat(),
                resultados=resultados_finais,
            )

        inicio_geral = time.monotonic()
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=len(provedores_para_executar)
        )

        inicio_por_provedor = {}
        future_to_provider = {}

        try:
            # Inicia os provedores concorrentemente.
            for provedor in provedores_para_executar:
                nome = provedor.provider_name
                inicio_por_provedor[nome] = time.monotonic()

                future = executor.submit(
                    provedor.analisar,
                    input_data,
                )

                future_to_provider[future] = nome

            concluidas, pendentes = concurrent.futures.wait(
                future_to_provider.keys(),
                timeout=self.MAX_ESPERA_SEGUNDOS,
                return_when=concurrent.futures.ALL_COMPLETED,
            )

            # Processa as chamadas concluídas.
            for future in concluidas:
                nome = future_to_provider[future]
                tempo = (
                    time.monotonic()
                    - inicio_por_provedor[nome]
                )

                try:
                    resultado = future.result()

                    if not isinstance(resultado, ResultadoProvedor):
                        resultados_finais[nome] = self._falha(
                            nome,
                            "O provedor retornou um resultado "
                            "em formato inesperado.",
                            tempo,
                        )
                    else:
                        resultados_finais[nome] = resultado

                except Exception as erro:
                    resultados_finais[nome] = self._falha(
                        nome,
                        "Erro inesperado durante a execução: "
                        f"{type(erro).__name__}: {erro}",
                        tempo,
                    )

            # Registra provedores que excederam o limite geral.
            for future in pendentes:
                nome = future_to_provider[future]
                tempo = (
                    time.monotonic()
                    - inicio_por_provedor[nome]
                )

                resultados_finais[nome] = self._falha(
                    nome,
                    "O provedor excedeu o limite geral de espera "
                    f"de {self.MAX_ESPERA_SEGUNDOS} segundos. "
                    "Verifique o timeout individual, a conexão "
                    "e a disponibilidade da API.",
                    tempo,
                    modo="timeout",
                )

                # Cancela tarefas que ainda não começaram.
                # Uma chamada já em execução não pode ser interrompida
                # à força por Future.cancel().
                future.cancel()

        finally:
            # Não bloqueia o retorno esperando tarefas pendentes.
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