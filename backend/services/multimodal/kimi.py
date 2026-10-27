
import base64
import json
import logging
import mimetypes
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI, APITimeoutError, APIStatusError

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


class KimiProvider(BaseModelProvider):
    """
    Integração com a API Moonshot/Kimi.

    Analisa a imagem e os dados clínicos,
    recebe JSON e normaliza o resultado
    para o formato do Avalia & Trata.
    """

    def __init__(self):
        super().__init__(
            provider_name="kimi",
            api_key_env_var="KIMI_API_KEY",
        )

    @staticmethod
    def _limpar_json(conteudo):
        """
        Converte o conteúdo retornado pelo Kimi
        em um dicionário Python.
        """

        if not conteudo or not conteudo.strip():
            raise ValueError(
                "Kimi retornou uma resposta vazia."
            )

        conteudo = conteudo.strip()

        # Remove possíveis marcações Markdown.
        conteudo = re.sub(
            r"^```(?:json)?\s*",
            "",
            conteudo,
            flags=re.IGNORECASE,
        )

        conteudo = re.sub(
            r"\s*```$",
            "",
            conteudo,
        ).strip()

        dados = json.loads(conteudo)

        if not isinstance(dados, dict):
            raise ValueError(
                "Kimi não retornou um objeto JSON."
            )

        return dados

    def analisar(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> ResultadoProvedor:

        inicio = time.monotonic()

        chave = self._obter_api_key()

        modelo = os.getenv(
            "KIMI_MODEL",
            "kimi-k2.6",
        )

        base_url = os.getenv(
            "KIMI_BASE_URL",
            "https://api.moonshot.ai/v1",
        )

        timeout = float(
            os.getenv(
                "KIMI_TIMEOUT",
                "90",
            )
        )

        max_tokens = int(
            os.getenv(
                "KIMI_MAX_TOKENS",
                "4096",
            )
        )

        def retornar(
            sucesso=False,
            resposta=None,
            erro=None,
        ):
            return ResultadoProvedor(
                provedor="kimi",
                modo="api_real",
                sucesso=sucesso,
                tempo_execucao_segundos=round(
                    time.monotonic() - inicio,
                    3,
                ),
                resposta=resposta,
                mensagem_erro=erro,
            )

        # ------------------------------------
        # 1. VERIFICAR CHAVE DA API
        # ------------------------------------

        if not chave:
            return retornar(
                erro=(
                    "KIMI_API_KEY não configurada "
                    "no arquivo .env."
                )
            )

        try:
            # --------------------------------
            # 2. LOCALIZAR IMAGEM
            # --------------------------------

            caminho = (
                input_data.caminho_imagem_processada
            )

            if not os.path.isfile(caminho):
                caminho = (
                    input_data.caminho_imagem_original
                )

            if not os.path.isfile(caminho):
                return retornar(
                    erro=(
                        "Kimi: imagem não encontrada "
                        "no servidor."
                    )
                )

            # --------------------------------
            # 3. CONVERTER IMAGEM PARA BASE64
            # --------------------------------

            mime = (
                mimetypes.guess_type(caminho)[0]
                or "image/png"
            )

            with open(caminho, "rb") as arquivo:
                imagem_base64 = base64.b64encode(
                    arquivo.read()
                ).decode("utf-8")

            imagem_url = (
                f"data:{mime};base64,{imagem_base64}"
            )

            # --------------------------------
            # 4. PREPARAR PROMPT
            # --------------------------------

            prompt = construir_prompt(input_data)

            logger.info(
                "Kimi: iniciando análise | "
                "modelo=%s | timeout=%ss | "
                "max_tokens=%s | thinking=disabled",
                modelo,
                timeout,
                max_tokens,
            )

            # --------------------------------
            # 5. CHAMAR API DO KIMI
            # --------------------------------

            with OpenAI(
                api_key=chave,
                base_url=base_url,
                timeout=timeout,
                max_retries=0,
            ) as cliente:

                resultado = (
                    cliente.chat.completions.create(
                        model=modelo,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Você auxilia profissionais "
                                    "de enfermagem na documentação "
                                    "descritiva de feridas. "
                                    "Descreva apenas características "
                                    "visíveis na imagem e dados "
                                    "clínicos fornecidos. "
                                    "Organize as informações pelo "
                                    "método T.I.M.E.S. "
                                    "Não confirme diagnóstico, "
                                    "infecção, profundidade, "
                                    "fase de cicatrização ou "
                                    "tipos de tecido apenas "
                                    "pela fotografia. "
                                    "Não prescreva tratamentos. "
                                    "Responda exclusivamente "
                                    "com um objeto JSON válido, "
                                    "sem Markdown."
                                ),
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt,
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": imagem_url,
                                        },
                                    },
                                ],
                            },
                        ],

                        # Solicitar JSON válido.
                        response_format={
                            "type": "json_object"
                        },

                        # ALTERAÇÃO PRINCIPAL:
                        # desativar raciocínio interno.
                        extra_body={
                            "thinking": {
                                "type": "disabled"
                            }
                        },

                        # Aumentar limite de saída.
                        max_tokens=max_tokens,

                        stream=False,
                    )
                )

            # --------------------------------
            # 6. VERIFICAR RESPOSTA
            # --------------------------------

            if not resultado.choices:
                return retornar(
                    erro=(
                        "Kimi não retornou "
                        "nenhuma resposta."
                    )
                )

            escolha = resultado.choices[0]

            logger.info(
                "Kimi: finish_reason=%s",
                escolha.finish_reason,
            )

            logger.info(
                "Kimi: uso de tokens=%s",
                resultado.usage,
            )

            # Se o modelo atingir o limite,
            # informar o valor configurado.
            if escolha.finish_reason == "length":
                return retornar(
                    erro=(
                        "Kimi atingiu o limite "
                        f"de {max_tokens} tokens "
                        "antes de concluir o JSON."
                    )
                )

            if escolha.finish_reason not in (
                "stop",
                None,
            ):
                return retornar(
                    erro=(
                        "Kimi interrompeu a geração. "
                        f"Motivo: {escolha.finish_reason}"
                    )
                )

            # --------------------------------
            # 7. CONVERTER JSON
            # --------------------------------

            conteudo = (
                escolha.message.content
            )

            dados = self._limpar_json(
                conteudo
            )

            # --------------------------------
            # 8. NORMALIZAR RESULTADO
            # --------------------------------

            resposta = normalizar_resposta(
                dados,
                input_data,
            )

            logger.info(
                "Kimi: análise concluída "
                "em %.2f segundos.",
                time.monotonic() - inicio,
            )

            return retornar(
                sucesso=True,
                resposta=resposta,
            )

        except APITimeoutError:

            logger.exception(
                "Kimi: tempo limite excedido."
            )

            return retornar(
                erro=(
                    "Kimi não respondeu dentro "
                    f"de {timeout:.0f} segundos."
                )
            )

        except APIStatusError as erro:

            codigo = erro.status_code

            logger.exception(
                "Kimi: erro HTTP %s",
                codigo,
            )

            if codigo == 400:
                mensagem = (
                    "Kimi: requisição rejeitada (400). "
                    "Verifique o modelo, JSON e "
                    "thinking=disabled."
                )

            elif codigo == 404:
                mensagem = (
                    f"Kimi: modelo '{modelo}' "
                    "não encontrado ou indisponível."
                )

            elif codigo == 429:
                mensagem = (
                    "Kimi: limite de requisições "
                    "ou cota atingida."
                )

            elif codigo in (401, 403):
                mensagem = (
                    "Kimi: chave de API inválida "
                    "ou sem permissão."
                )

            elif codigo in (
                500,
                502,
                503,
                504,
            ):
                mensagem = (
                    "Kimi: servidor temporariamente "
                    f"indisponível (HTTP {codigo})."
                )

            else:
                mensagem = (
                    f"Kimi: erro HTTP {codigo}. "
                    "Consulte o terminal."
                )

            return retornar(
                erro=mensagem
            )

        except json.JSONDecodeError:

            logger.exception(
                "Kimi: resposta JSON inválida."
            )

            return retornar(
                erro=(
                    "Kimi retornou um JSON inválido."
                )
            )

        except Exception as erro:

            logger.exception(
                "Kimi: erro inesperado."
            )

            mensagem = (
                f"{type(erro).__name__}: "
                f"{str(erro)}"
            )

            mensagem = mensagem.replace(
                chave,
                "[CHAVE OCULTADA]",
            )

            return retornar(
                erro=(
                    f"Kimi: {mensagem[:300]}"
                )
            )
