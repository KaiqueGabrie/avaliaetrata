
import concurrent.futures
import logging
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

from services.multimodal.validador import (
    validar_resposta,
    adicionar_alertas_revisao,
)


logger = logging.getLogger(__name__)


class MultimodalOrchestrator:
    """
    Executa provedores multimodais em paralelo.

    Cada provedor funciona independentemente.

    Após receber uma resposta bem-sucedida,
    executa a validação de consistência.

    Os alertas são adicionados aos pontos
    de revisão profissional, sem modificar
    os achados visuais produzidos pela IA.

    O resultado poderá ser utilizado pelo
    módulo comparador multimodal.
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

    @staticmethod
    def _validar_resultado(
        resultado: ResultadoProvedor,
    ) -> ResultadoProvedor:
        """
        Valida uma resposta normalizada.

        Se houver inconsistências, acrescenta
        alertas à cópia da resposta.

        Problemas no validador não devem
        apagar uma análise já recebida.
        """

        if not resultado.sucesso:
            return resultado

        if resultado.resposta is None:
            logger.warning(
                "Provedor %s informou sucesso "
                "sem uma resposta estruturada.",
                resultado.provedor,
            )
            return resultado

        try:
            relatorio = validar_resposta(
                resultado.resposta
            )

            print(
                f"\n[VALIDADOR EXECUTADO] "
                f"Provedor: {resultado.provedor} | "
                f"Estrutura válida: "
                f"{relatorio.valido_estruturalmente} | "
                f"Revisão necessária: "
                f"{relatorio.requer_revisao} | "
                f"Alertas: {relatorio.total_alertas}",
                flush=True,
            )

            logger.info(
                "Validação de %s: "
                "estrutura=%s, revisão=%s, "
                "alertas=%d",
                resultado.provedor,
                relatorio.valido_estruturalmente,
                relatorio.requer_revisao,
                relatorio.total_alertas,
            )

            for alerta in relatorio.alertas:
                logger.warning(
                    "[%s] %s (%s): %s",
                    resultado.provedor,
                    alerta.codigo,
                    alerta.severidade,
                    alerta.mensagem,
                )

            if relatorio.total_alertas > 0:
                resultado.resposta = (
                    adicionar_alertas_revisao(
                        resultado.resposta,
                        relatorio,
                    )
                )

        except Exception:
            logger.exception(
                "Falha na validação da resposta "
                "do provedor %s.",
                resultado.provedor,
            )

            if resultado.resposta is not None:
                aviso = (
                    "A validação automática de "
                    "consistência não foi concluída. "
                    "Revisão profissional necessária."
                )

                if (
                    aviso not in
                    resultado.resposta.pontos_para_revisao_profissional
                ):
                    resultado.resposta.pontos_para_revisao_profissional.append(
                        aviso
                    )

        return resultado

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

        provedores_desejados = list(
            dict.fromkeys(provedores_desejados)
        )

        resultados_finais: Dict[str, ResultadoProvedor] = {}

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

        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=len(provedores_para_executar)
        )

        inicio_por_provedor = {}
        future_to_provider = {}

        try:
            for provedor in provedores_para_executar:
                nome = provedor.provider_name

                inicio_por_provedor[nome] = (
                    time.monotonic()
                )

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

            for future in concluidas:
                nome = future_to_provider[future]

                tempo = (
                    time.monotonic()
                    - inicio_por_provedor[nome]
                )

                try:
                    resultado = future.result()

                    if not isinstance(
                        resultado,
                        ResultadoProvedor,
                    ):
                        resultados_finais[nome] = self._falha(
                            nome,
                            "O provedor retornou um resultado "
                            "em formato inesperado.",
                            tempo,
                        )
                        continue

                    resultado = self._validar_resultado(
                        resultado
                    )

                    resultados_finais[nome] = resultado

                except Exception as erro:
                    logger.exception(
                        "Erro inesperado no provedor %s.",
                        nome,
                    )

                    resultados_finais[nome] = self._falha(
                        nome,
                        "Erro inesperado durante a execução: "
                        f"{type(erro).__name__}: {erro}",
                        tempo,
                    )

            for future in pendentes:
                nome = future_to_provider[future]

                tempo = (
                    time.monotonic()
                    - inicio_por_provedor[nome]
                )

                resultados_finais[nome] = self._falha(
                    nome,
                    "O provedor excedeu o limite geral "
                    f"de {self.MAX_ESPERA_SEGUNDOS} segundos. "
                    "Verifique o timeout individual, "
                    "a conexão e a disponibilidade da API.",
                    tempo,
                    modo="timeout",
                )

                future.cancel()

        finally:
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
