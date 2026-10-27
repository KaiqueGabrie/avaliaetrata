
import json
import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from schemas.multimodal import (
    AnaliseMultimodalInput,
    ResultadoProvedor,
)
from services.multimodal.base import BaseModelProvider
from services.multimodal.prompt_padrao import (
    construir_prompt,
    normalizar_resposta,
)

load_dotenv()

logger = logging.getLogger(__name__)


class GeminiProvider(BaseModelProvider):
    """
    Integração Gemini para o Avalia & Trata.
    Mantém o contrato utilizado pelo orchestrator.py.
    """

    def __init__(self):
        super().__init__(
            provider_name="gemini",
            api_key_env_var="GEMINI_API_KEY",
        )

    @staticmethod
    def _codigo_http(erro):
        codigo = getattr(erro, "code", None)

        if codigo is None:
            codigo = getattr(erro, "status_code", None)

        try:
            return int(codigo)
        except (TypeError, ValueError):
            texto = str(erro).upper()

            for numero in (400, 401, 403, 404, 429, 503, 504):
                if str(numero) in texto:
                    return numero

            return None

    def analisar(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> ResultadoProvedor:

        inicio = time.monotonic()
        chave = self._obter_api_key()

        modelo = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.8-flash",
        )

        timeout_ms = int(
            os.getenv("GEMINI_TIMEOUT_MS", "30000")
        )

        def retornar(
            sucesso=False,
            resposta=None,
            erro=None,
        ):
            return ResultadoProvedor(
                provedor="gemini",
                modo="api_real",
                sucesso=sucesso,
                tempo_execucao_segundos=round(
                    time.monotonic() - inicio,
                    3,
                ),
                resposta=resposta,
                mensagem_erro=erro,
            )

        if not chave:
            return retornar(
                erro="GEMINI_API_KEY não configurada."
            )

        try:
            caminho = input_data.caminho_imagem_processada

            if not os.path.isfile(caminho):
                caminho = input_data.caminho_imagem_original

            if not os.path.isfile(caminho):
                return retornar(
                    erro="Gemini: imagem não encontrada."
                )

            prompt = construir_prompt(input_data)

            with Image.open(caminho) as arquivo:
                imagem = arquivo.copy()
                imagem.load()

            logger.info(
                "Gemini: modelo=%s, timeout=%sms",
                modelo,
                timeout_ms,
            )

            with genai.Client(
                api_key=chave,
                http_options=types.HttpOptions(
                    timeout=timeout_ms,
                    retry_options=types.HttpRetryOptions(
                        attempts=1,
                    ),
                ),
            ) as cliente:

                for tentativa in range(1, 3):
                    try:
                        logger.info(
                            "Gemini: tentativa %s/2",
                            tentativa,
                        )

                        resultado = (
                            cliente.models.generate_content(
                                model=modelo,
                                contents=[
                                    prompt,
                                    imagem,
                                ],
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    temperature=0.2,
                                    max_output_tokens=2600,
                                ),
                            )
                        )

                        if not resultado.text:
                            return retornar(
                                erro="Gemini retornou conteúdo vazio."
                            )

                        dados = json.loads(resultado.text)

                        resposta = normalizar_resposta(
                            dados,
                            input_data,
                        )

                        logger.info(
                            "Gemini concluído em %.2fs",
                            time.monotonic() - inicio,
                        )

                        return retornar(
                            sucesso=True,
                            resposta=resposta,
                        )

                    except Exception as erro:
                        codigo = self._codigo_http(erro)

                        logger.warning(
                            "Gemini: tentativa %s, erro=%s, HTTP=%s",
                            tentativa,
                            type(erro).__name__,
                            codigo,
                        )

                        if (
                            codigo not in (503, 504)
                            or tentativa == 2
                        ):
                            raise

                        time.sleep(2)

        except Exception as erro:
            codigo = self._codigo_http(erro)

            logger.exception(
                "Gemini: falha no modelo %s",
                modelo,
            )

            if codigo == 503:
                mensagem = (
                    "Gemini: servidor temporariamente "
                    "sobrecarregado (503)."
                )
            elif codigo == 504:
                mensagem = (
                    "Gemini: tempo limite do servidor "
                    "excedido (504)."
                )
            elif codigo == 429:
                mensagem = (
                    "Gemini: limite de requisições "
                    "ou cota atingida (429)."
                )
            elif codigo == 404:
                mensagem = (
                    f"Gemini: modelo '{modelo}' "
                    "não encontrado ou indisponível."
                )
            elif codigo in (401, 403):
                mensagem = (
                    "Gemini: chave inválida "
                    "ou sem permissão."
                )
            elif isinstance(erro, json.JSONDecodeError):
                mensagem = "Gemini retornou JSON inválido."
            else:
                mensagem = (
                    "Gemini: erro na API ou validação. "
                    f"Tipo: {type(erro).__name__}."
                )

            return retornar(erro=mensagem)
