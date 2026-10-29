
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
    Integração Gemini do Avalia & Trata.

    Utiliza o mesmo formato JSON definido
    pelo prompt_padrao.py.

    Funcionalidades:
    - Análise de imagem e dados clínicos.
    - Geração de JSON estruturado.
    - Compatibilidade com normalizar_resposta().
    - Até duas tentativas.
    - Tratamento de erros da API.
    - Preservação do contrato do orquestrador.
    """

    MAX_TENTATIVAS = 2

    STATUS = [
        "avaliavel",
        "parcialmente_avaliavel",
        "nao_avaliavel",
    ]

    @classmethod
    def _schema_resposta(cls):
        """
        Schema compatível com o formato solicitado
        por construir_prompt().

        Este não é o schema Pydantic final.
        A conversão ocorre em normalizar_resposta().
        """

        status = {
            "type": "STRING",
            "enum": cls.STATUS,
        }

        lista_textos = {
            "type": "ARRAY",
            "items": {
                "type": "STRING",
            },
        }

        caracteristica = {
            "type": "OBJECT",
            "properties": {
                "nome": {
                    "type": "STRING",
                },
                "descricao": {
                    "type": "STRING",
                },
                "status": status,
            },
            "required": [
                "nome",
                "descricao",
                "status",
            ],
        }

        componente_times = {
            "type": "OBJECT",
            "properties": {
                "status": status,
                "observacoes": lista_textos,
                "pendencias": lista_textos,
                "limitacoes": lista_textos,
            },
            "required": [
                "status",
                "observacoes",
                "pendencias",
                "limitacoes",
            ],
        }

        times = {
            "type": "OBJECT",
            "properties": {
                letra: componente_times
                for letra in ("T", "I", "M", "E", "S")
            },
            "required": [
                "T",
                "I",
                "M",
                "E",
                "S",
            ],
        }

        aparencia_tecido = {
            "type": "OBJECT",
            "properties": {
                "aparencia": {
                    "type": "STRING",
                },
                "justificativa": {
                    "type": "STRING",
                },
            },
            "required": [
                "aparencia",
                "justificativa",
            ],
        }

        return {
            "type": "OBJECT",
            "properties": {
                "descricao": {
                    "type": "STRING",
                },
                "qualidade": status,
                "limitacoes": lista_textos,
                "caracteristicas": {
                    "type": "ARRAY",
                    "items": caracteristica,
                },
                "times": times,
                "aparencias_tecidos": {
                    "type": "ARRAY",
                    "items": aparencia_tecido,
                },
                "pontos_revisao": lista_textos,
            },
            "required": [
                "descricao",
                "qualidade",
                "limitacoes",
                "caracteristicas",
                "times",
                "aparencias_tecidos",
                "pontos_revisao",
            ],
        }

    def __init__(self):
        super().__init__(
            provider_name="gemini",
            api_key_env_var="GEMINI_API_KEY",
        )

    @staticmethod
    def _codigo_http(erro):
        codigo = getattr(
            erro,
            "code",
            None,
        )

        if codigo is None:
            codigo = getattr(
                erro,
                "status_code",
                None,
            )

        try:
            return int(codigo)

        except (TypeError, ValueError):
            texto = str(erro).upper()

            for numero in (
                400,
                401,
                403,
                404,
                429,
                500,
                502,
                503,
                504,
            ):
                if str(numero) in texto:
                    return numero

            return None

    @staticmethod
    def _motivo_finalizacao(resultado):
        try:
            candidatos = getattr(
                resultado,
                "candidates",
                None,
            )

            if not candidatos:
                return "SEM_CANDIDATOS"

            motivo = getattr(
                candidatos[0],
                "finish_reason",
                None,
            )

            if motivo is None:
                return "NAO_INFORMADO"

            nome = getattr(
                motivo,
                "name",
                None,
            )

            if nome:
                return str(nome)

            return str(motivo)

        except Exception:
            return "INDETERMINADO"

    @staticmethod
    def _resposta_interrompida(motivo):
        motivo = str(motivo).upper()

        return (
            "MAX_TOKENS" in motivo
            or "MAX_OUTPUT_TOKENS" in motivo
        )

    @staticmethod
    def _montar_prompt_tentativa(
        prompt_original,
        tentativa,
    ):
        if tentativa == 1:
            return prompt_original

        complemento = """

ATENÇÃO: ESTA É UMA NOVA TENTATIVA.

A resposta anterior não pôde ser processada.

Retorne somente um objeto JSON válido.

Utilize exatamente as seguintes chaves principais:

descricao
qualidade
limitacoes
caracteristicas
times
aparencias_tecidos
pontos_revisao

O objeto "times" deve conter:
T, I, M, E e S.

Cada componente deve conter:
status, observacoes, pendencias, limitacoes.

Não utilize:
conteudo_descricao
qualidade_imagem
caracteristicas_visuais
avaliacao_times
pontos_para_revisao_profissional

Esses nomes pertencem ao formato interno
do sistema e não ao JSON solicitado.

Não invente dados clínicos.
Não faça diagnósticos.
Não prescreva tratamentos.
Não inclua Markdown.
"""

        return (
            prompt_original
            + "\n"
            + complemento
        )

    @staticmethod
    def _validar_json_intermediario(dados):
        """
        Verifica os campos essenciais antes
        de chamar o normalizador.
        """

        if not isinstance(dados, dict):
            raise ValueError(
                "A raiz do JSON não é um objeto."
            )

        descricao = dados.get("descricao")

        if (
            not isinstance(descricao, str)
            or not descricao.strip()
        ):
            raise ValueError(
                "Campo 'descricao' ausente ou vazio."
            )

        times = dados.get("times")

        if not isinstance(times, dict):
            raise ValueError(
                "Campo 'times' ausente ou inválido."
            )

        faltantes = [
            letra
            for letra in ("T", "I", "M", "E", "S")
            if not isinstance(times.get(letra), dict)
        ]

        if faltantes:
            raise ValueError(
                "Componentes T.I.M.E.S. ausentes: "
                + ", ".join(faltantes)
            )

    def analisar(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> ResultadoProvedor:

        inicio = time.monotonic()

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

        try:
            chave = self._obter_api_key()

            if not chave:
                return retornar(
                    erro="GEMINI_API_KEY não configurada."
                )

            modelo = os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            )

            timeout_ms = int(
                os.getenv(
                    "GEMINI_TIMEOUT_MS",
                    "60000",
                )
            )

            max_tokens = int(
                os.getenv(
                    "GEMINI_MAX_OUTPUT_TOKENS",
                    "8192",
                )
            )

            caminho = (
                input_data.caminho_imagem_processada
            )

            if not os.path.isfile(caminho):
                caminho = (
                    input_data.caminho_imagem_original
                )

            if not os.path.isfile(caminho):
                return retornar(
                    erro="Gemini: imagem não encontrada."
                )

            prompt_original = construir_prompt(
                input_data
            )

            with Image.open(caminho) as arquivo:
                imagem = arquivo.copy()
                imagem.load()

            schema = self._schema_resposta()

            logger.warning(
                "Gemini: modelo=%s, timeout=%sms, "
                "max_output_tokens=%s, "
                "schema_intermediario=ativado",
                modelo,
                timeout_ms,
                max_tokens,
            )

            ultimo_erro = None

            with genai.Client(
                api_key=chave,
                http_options=types.HttpOptions(
                    timeout=timeout_ms,
                    retry_options=types.HttpRetryOptions(
                        attempts=1,
                    ),
                ),
            ) as cliente:

                for tentativa in range(
                    1,
                    self.MAX_TENTATIVAS + 1,
                ):

                    logger.warning(
                        "Gemini: iniciando tentativa %s/%s",
                        tentativa,
                        self.MAX_TENTATIVAS,
                    )

                    prompt_tentativa = (
                        self._montar_prompt_tentativa(
                            prompt_original,
                            tentativa,
                        )
                    )

                    try:
                        resultado = (
                            cliente.models.generate_content(
                                model=modelo,
                                contents=[
                                    prompt_tentativa,
                                    imagem,
                                ],
                                config=types.GenerateContentConfig(
                                    response_mime_type=(
                                        "application/json"
                                    ),
                                    response_schema=schema,
                                    temperature=0.1,
                                    max_output_tokens=max_tokens,
                                ),
                            )
                        )

                    except Exception as erro:
                        codigo = self._codigo_http(
                            erro
                        )

                        logger.warning(
                            "Gemini: erro de API na tentativa "
                            "%s/%s: tipo=%s, HTTP=%s",
                            tentativa,
                            self.MAX_TENTATIVAS,
                            type(erro).__name__,
                            codigo,
                        )

                        if (
                            codigo in (500, 502, 503, 504)
                            and tentativa < self.MAX_TENTATIVAS
                        ):
                            time.sleep(2)
                            continue

                        raise

                    motivo = self._motivo_finalizacao(
                        resultado
                    )

                    try:
                        texto_resposta = (
                            resultado.text or ""
                        )

                    except (ValueError, AttributeError):
                        texto_resposta = ""

                    logger.warning(
                        "Gemini: tentativa=%s, "
                        "finish_reason=%s, caracteres=%s",
                        tentativa,
                        motivo,
                        len(texto_resposta),
                    )

                    if self._resposta_interrompida(
                        motivo
                    ):
                        ultimo_erro = (
                            "Gemini interrompeu a geração "
                            "por limite de tokens."
                        )

                        if tentativa < self.MAX_TENTATIVAS:
                            time.sleep(1)
                            continue

                        return retornar(
                            erro=ultimo_erro
                        )

                    if not texto_resposta.strip():
                        ultimo_erro = (
                            "Gemini retornou conteúdo vazio. "
                            f"Finalização: {motivo}."
                        )

                        if tentativa < self.MAX_TENTATIVAS:
                            time.sleep(1)
                            continue

                        return retornar(
                            erro=ultimo_erro
                        )

                    try:
                        dados = json.loads(
                            texto_resposta
                        )

                    except json.JSONDecodeError as erro:
                        ultimo_erro = (
                            "Gemini retornou JSON inválido. "
                            f"Finalização: {motivo}. "
                            f"Erro: {erro.msg} "
                            f"na posição {erro.pos}."
                        )

                        logger.warning(
                            "Gemini: JSON inválido "
                            "na tentativa %s/%s. "
                            "Posição=%s, tamanho=%s",
                            tentativa,
                            self.MAX_TENTATIVAS,
                            erro.pos,
                            len(texto_resposta),
                        )

                        if tentativa < self.MAX_TENTATIVAS:
                            time.sleep(1)
                            continue

                        return retornar(
                            erro=ultimo_erro
                        )

                    try:
                        self._validar_json_intermediario(
                            dados
                        )

                        resposta = normalizar_resposta(
                            dados,
                            input_data,
                        )

                    except Exception as erro:
                        ultimo_erro = (
                            "Gemini retornou JSON, mas "
                            "a normalização falhou. "
                            f"Motivo: {type(erro).__name__}."
                        )

                        logger.exception(
                            "Gemini: erro de normalização "
                            "na tentativa %s/%s",
                            tentativa,
                            self.MAX_TENTATIVAS,
                        )

                        if tentativa < self.MAX_TENTATIVAS:
                            time.sleep(1)
                            continue

                        return retornar(
                            erro=ultimo_erro
                        )

                    logger.warning(
                        "Gemini: análise concluída "
                        "em %.2fs (tentativa %s).",
                        time.monotonic() - inicio,
                        tentativa,
                    )

                    return retornar(
                        sucesso=True,
                        resposta=resposta,
                    )

            return retornar(
                erro=(
                    ultimo_erro
                    or "Gemini: tentativas esgotadas."
                )
            )

        except Exception as erro:
            codigo = self._codigo_http(
                erro
            )

            logger.exception(
                "Gemini: falha na execução."
            )

            if codigo == 503:
                mensagem = (
                    "Gemini: servidor temporariamente "
                    "sobrecarregado (503)."
                )

            elif codigo == 504:
                mensagem = (
                    "Gemini: timeout do servidor (504)."
                )

            elif codigo == 429:
                mensagem = (
                    "Gemini: cota ou limite de "
                    "requisições atingido (429)."
                )

            elif codigo == 404:
                mensagem = (
                    "Gemini: modelo não encontrado "
                    "ou indisponível (404)."
                )

            elif codigo in (401, 403):
                mensagem = (
                    "Gemini: chave inválida "
                    "ou sem permissão."
                )

            elif codigo == 400:
                mensagem = (
                    "Gemini: requisição rejeitada (400). "
                    "Verifique a compatibilidade do "
                    "modelo com o schema JSON."
                )

            else:
                mensagem = (
                    "Gemini: erro na API. "
                    f"Tipo: {type(erro).__name__}."
                )

            return retornar(
                erro=mensagem
            )
