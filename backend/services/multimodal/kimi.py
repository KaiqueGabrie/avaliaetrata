
import base64
import mimetypes
import os
import re
import threading
import time
from typing import Optional

from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from pydantic import ValidationError

from services.multimodal.base import BaseModelProvider
from schemas.multimodal import (
    AnaliseMultimodalInput,
    ResultadoProvedor,
    RespostaEstruturadaModelo,
)

load_dotenv()


class KimiProvider(BaseModelProvider):
    """Integração multimodal com a API do Kimi (Moonshot AI)."""

    MODEL_NAME = "kimi-k2.6"
    BASE_URL = "https://api.moonshot.ai/v1"

    TIMEOUT_SEGUNDOS = 35.0
    MAX_TENTATIVAS = 2
    DELAYS_RETRY = (3.0, 6.0)
    TEMPO_MAXIMO_ESPERA_LOCK = 15.0
    TEMPO_MAXIMO_ESPERA_RETRY = 10.0

    _concurrency_lock = threading.Lock()

    def __init__(self):
        super().__init__(
            provider_name="kimi",
            api_key_env_var="KIMI_API_KEY",
        )

    def _construir_prompt(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> str:
        dados = input_data.dados_clinicos
        tecnica = input_data.analise_tecnica

        odor_informado = (
            "Sim"
            if dados.odor
            else "Não ou não informado; o formulário não permite distinguir"
        )

        return f"""
Você é um assistente de apoio à documentação clínica de feridas cutâneas.

OBJETIVO:
Descrever características visuais discerníveis na fotografia e organizar
as informações fornecidas pelo profissional. Não substitua a avaliação
presencial nem o julgamento clínico.

REGRAS:
- Não forneça diagnóstico definitivo.
- Não prescreva medicamentos, tratamentos ou condutas.
- Não invente características, medidas ou informações.
- Diferencie observações da fotografia dos dados informados pelo profissional.
- Descreva somente características visuais discerníveis: leito da ferida,
  tecidos aparentes, coloração, bordas e pele ao redor.
- Se uma característica não puder ser avaliada com segurança, declare a limitação.
- Considere que iluminação, foco, distância e qualidade da fotografia alteram
  a aparência observada.
- Não infira fase de cicatrização, causa, profundidade real ou infecção
  somente pela fotografia.
- Brilho e contraste do OpenCV não comprovam cicatrização.
- Não afirme que a área foi calculada automaticamente.
- Comprimento e largura são medidas informadas pelo profissional.
- O campo de odor não distingue resposta negativa de ausência de preenchimento.
- Não afirme que o odor foi avaliado visualmente.
- A descrição precisa ser validada por um profissional de saúde.
- Responda em português brasileiro.
- Retorne somente JSON válido, sem Markdown, com exatamente estas chaves:
  "status_resposta": string,
  "conteudo_descricao": string,
  "limitacoes_declaradas": lista de strings.
- Use "sucesso" em status_resposta se conseguir produzir uma descrição válida.
- Seja objetivo, sem repetir regras ou dados desnecessariamente.

DADOS CLÍNICOS INFORMADOS:
Localização: {dados.localizacao}
Comprimento informado (cm): {dados.comprimento or "Não informado"}
Largura informada (cm): {dados.largura or "Não informado"}
Tipo de exsudato: {dados.tipoExsudato or "Não informado"}
Presença de odor no formulário: {odor_informado}
Nível de dor: {dados.nivelDor or "Não informado"}
Queixa principal: {dados.queixaPrincipal or "Não informada"}
Observações: {dados.observacoes or "Nenhuma"}

DADOS TÉCNICOS DA IMAGEM:
Dimensões originais: {input_data.dimensoes_originais}
Dimensões processadas: {input_data.dimensoes_processadas}
Brilho médio do OpenCV: {tecnica.brilho_medio}
Contraste global do OpenCV: {tecnica.contraste_global}

Diferencie as observações visuais das informações do formulário.
Inclua somente limitações relevantes. Não invente dados ausentes.
""".strip()

    def _resultado_falha(
        self,
        inicio: float,
        mensagem: str,
    ) -> ResultadoProvedor:
        return ResultadoProvedor(
            provedor=self.provider_name,
            modo="api_real",
            sucesso=False,
            tempo_execucao_segundos=round(time.monotonic() - inicio, 3),
            resposta=None,
            mensagem_erro=mensagem,
        )

    @staticmethod
    def _texto_erro(erro: Exception) -> str:
        return str(erro).lower()

    def _eh_erro_temporario(self, erro: Exception) -> bool:
        texto = self._texto_erro(erro)

        if any(
            termo in texto
            for termo in (
                "insufficient_quota",
                "quota exceeded",
                "billing",
                "insufficient balance",
                "insufficient credits",
                "out of credits",
            )
        ):
            return False

        if isinstance(
            erro,
            (APIConnectionError, APITimeoutError, InternalServerError),
        ):
            return True

        if isinstance(erro, RateLimitError):
            return True

        if isinstance(erro, APIStatusError):
            return erro.status_code in (408, 409, 429) or erro.status_code >= 500

        return False

    def _tempo_espera_sugerido(
        self,
        erro: Exception,
        tentativa: int,
    ) -> float:
        resposta_http = getattr(erro, "response", None)
        cabecalhos = getattr(resposta_http, "headers", {}) or {}
        retry_after = cabecalhos.get("retry-after")

        if retry_after:
            try:
                return min(
                    max(float(retry_after), 0.0) + 0.5,
                    self.TEMPO_MAXIMO_ESPERA_RETRY,
                )
            except (TypeError, ValueError):
                pass

        match = re.search(
            r"after\s+(\d+(?:\.\d+)?)\s+seconds?",
            str(erro).lower(),
        )

        if match:
            try:
                return min(
                    max(float(match.group(1)), 0.0) + 0.5,
                    self.TEMPO_MAXIMO_ESPERA_RETRY,
                )
            except ValueError:
                pass

        indice = min(tentativa, len(self.DELAYS_RETRY) - 1)
        return self.DELAYS_RETRY[indice]

    def _mensagem_erro_segura(
        self,
        erro: Exception,
        api_key: str,
    ) -> str:
        if isinstance(erro, RateLimitError):
            return (
                "Limite de requisições da API Kimi atingido. "
                "Aguarde um pouco e tente novamente."
            )

        if isinstance(erro, APITimeoutError):
            return "A API Kimi demorou demais para responder."

        if isinstance(erro, APIConnectionError):
            return "Não foi possível estabelecer conexão com a API Kimi."

        if isinstance(erro, APIStatusError):
            status = erro.status_code

            if status in (401, 403):
                return "A API Kimi recusou a autenticação ou autorização."

            if status == 400:
                return (
                    "A API Kimi rejeitou os dados enviados. "
                    "Verifique o modelo, a imagem e os parâmetros."
                )

            if status == 404:
                return "O modelo ou endpoint não foi encontrado na API Kimi."

            if status >= 500:
                return f"A API Kimi apresentou uma falha temporária (HTTP {status})."

            return f"A API Kimi retornou um erro HTTP {status}."

        mensagem = str(erro)

        if api_key:
            mensagem = mensagem.replace(api_key, "[CHAVE OCULTADA]")

        return mensagem[:500]

    def analisar(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> ResultadoProvedor:
        inicio = time.monotonic()
        cliente: Optional[OpenAI] = None
        api_key = ""
        adquiriu_lock = False

        try:
            api_key = self._obter_api_key()

            if not api_key:
                return self._resultado_falha(
                    inicio,
                    "A variável KIMI_API_KEY não está configurada.",
                )

            caminho_original = input_data.caminho_imagem_original
            caminho_processado = input_data.caminho_imagem_processada

            if caminho_original and os.path.isfile(caminho_original):
                caminho_imagem = caminho_original
            elif caminho_processado and os.path.isfile(caminho_processado):
                caminho_imagem = caminho_processado
            else:
                return self._resultado_falha(
                    inicio,
                    "Não foi possível localizar a imagem original nem a processada.",
                )

            mime_type, _ = mimetypes.guess_type(caminho_imagem)

            if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
                return self._resultado_falha(
                    inicio,
                    "Formato de imagem não suportado. Utilize JPEG, PNG ou WebP.",
                )

            with open(caminho_imagem, "rb") as arquivo:
                imagem_bytes = arquivo.read()

            if not imagem_bytes:
                return self._resultado_falha(
                    inicio,
                    "O arquivo de imagem está vazio.",
                )

            imagem_base64 = base64.b64encode(imagem_bytes).decode("utf-8")
            imagem_url = f"data:{mime_type};base64,{imagem_base64}"
            prompt = self._construir_prompt(input_data)

            cliente = OpenAI(
                api_key=api_key,
                base_url=self.BASE_URL,
                max_retries=0,
                timeout=self.TIMEOUT_SEGUNDOS,
            )

            adquiriu_lock = self._concurrency_lock.acquire(
                timeout=self.TEMPO_MAXIMO_ESPERA_LOCK
            )

            if not adquiriu_lock:
                return self._resultado_falha(
                    inicio,
                    "O Kimi já está processando outra solicitação neste servidor. "
                    "Aguarde e tente novamente.",
                )

            ultimo_erro: Optional[Exception] = None

            for tentativa in range(self.MAX_TENTATIVAS):
                try:
                    resposta = cliente.chat.completions.create(
                        model=self.MODEL_NAME,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": imagem_url},
                                    },
                                ],
                            }
                        ],
                        response_format={"type": "json_object"},
                        temperature=1,
                        max_tokens=8192,
                    )

                    if not resposta.choices:
                        return self._resultado_falha(
                            inicio,
                            "O Kimi retornou uma resposta sem opções.",
                        )

                    escolha = resposta.choices[0]
                    mensagem = escolha.message
                    motivo = getattr(escolha, "finish_reason", None)
                    conteudo = mensagem.content

                    if getattr(mensagem, "refusal", None):
                        return self._resultado_falha(
                            inicio,
                            "O Kimi recusou a solicitação de análise.",
                        )

                    if motivo == "length":
                        return self._resultado_falha(
                            inicio,
                            "O Kimi atingiu o limite de tokens antes de concluir "
                            "a resposta. A resposta foi interrompida; tente novamente.",
                        )

                    if not conteudo or not conteudo.strip():
                        return self._resultado_falha(
                            inicio,
                            "O Kimi retornou uma resposta vazia. "
                            f"Motivo de encerramento: {motivo or 'não informado'}.",
                        )

                    conteudo = conteudo.strip()
                    conteudo = re.sub(
                        r"^```(?:json)?\s*|\s*```$",
                        "",
                        conteudo,
                        flags=re.IGNORECASE,
                    ).strip()

                    resposta_estruturada = (
                        RespostaEstruturadaModelo.model_validate_json(conteudo)
                    )

                    if resposta_estruturada.status_resposta != "sucesso":
                        return self._resultado_falha(
                            inicio,
                            "A resposta do Kimi não indicou uma análise concluída.",
                        )

                    if not resposta_estruturada.conteudo_descricao.strip():
                        return self._resultado_falha(
                            inicio,
                            "O Kimi retornou uma descrição vazia.",
                        )

                    return ResultadoProvedor(
                        provedor=self.provider_name,
                        modo="api_real",
                        sucesso=True,
                        tempo_execucao_segundos=round(
                            time.monotonic() - inicio,
                            3,
                        ),
                        resposta=resposta_estruturada,
                        mensagem_erro=None,
                    )

                except (ValidationError, ValueError) as erro:
                    return self._resultado_falha(
                        inicio,
                        "O Kimi retornou JSON inválido ou incompatível "
                        f"com o formato esperado: {str(erro)[:300]}",
                    )

                except Exception as erro:
                    ultimo_erro = erro

                    if (
                        not self._eh_erro_temporario(erro)
                        or tentativa >= self.MAX_TENTATIVAS - 1
                    ):
                        break

                    time.sleep(self._tempo_espera_sugerido(erro, tentativa))

            mensagem_erro = self._mensagem_erro_segura(
                ultimo_erro or RuntimeError("Erro desconhecido."),
                api_key,
            )

            return self._resultado_falha(
                inicio,
                f"Falha na API do Kimi após {self.MAX_TENTATIVAS} tentativa(s): "
                f"{mensagem_erro}",
            )

        except Exception as erro:
            mensagem_erro = self._mensagem_erro_segura(erro, api_key)

            return self._resultado_falha(
                inicio,
                f"Erro na integração Kimi: {mensagem_erro}",
            )

        finally:
            if adquiriu_lock:
                self._concurrency_lock.release()

            if cliente is not None:
                try:
                    cliente.close()
                except Exception:
                    pass
