import base64
import json
import mimetypes
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

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
    TIMEOUT_SEGUNDOS = 90.0

    def __init__(self):
        super().__init__(
            provider_name="kimi",
            api_key_env_var="KIMI_API_KEY",
        )

    def _resultado_falha(
        self,
        inicio: float,
        mensagem: str,
    ) -> ResultadoProvedor:
        return ResultadoProvedor(
            provedor=self.provider_name,
            modo="api_real",
            sucesso=False,
            tempo_execucao_segundos=round(
                time.monotonic() - inicio, 3
            ),
            resposta=None,
            mensagem_erro=mensagem,
        )

    @staticmethod
    def _limpar_json(texto: str) -> str:
        """Remove cercas Markdown e valida o JSON retornado."""

        if not texto or not texto.strip():
            raise ValueError(
                "O Kimi retornou uma resposta vazia."
            )

        texto = texto.strip()

        texto = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            texto,
            count=1,
            flags=re.IGNORECASE,
        )

        texto = re.sub(
            r"\s*```\s*$",
            "",
            texto,
            count=1,
        )

        texto = texto.strip()

        if not texto.startswith("{"):
            inicio_json = texto.find("{")

            if inicio_json == -1:
                raise ValueError(
                    "A resposta do Kimi não contém um objeto JSON."
                )

            texto = texto[inicio_json:]

        json.loads(texto)

        return texto

    def _construir_prompt(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> str:
        dados = input_data.dados_clinicos
        tecnica = input_data.analise_tecnica

        odor_informado = (
            "Sim"
            if dados.odor
            else "Não ou não informado no formulário"
        )

        return f"""
Você é um assistente de apoio à documentação clínica de feridas
cutâneas, destinado a apoiar o trabalho de profissionais de saúde.

OBJETIVO:
Descrever características visuais da fotografia e organizar as
informações fornecidas pelo profissional. Esta análise não substitui
a avaliação presencial nem o julgamento clínico.

REGRAS OBRIGATÓRIAS:
- Não forneça diagnóstico definitivo.
- Não prescreva medicamentos, tratamentos ou condutas.
- Não invente características, medidas ou informações.
- Diferencie observações visuais de informações do formulário.
- Descreva com cautela o aspecto visível do leito da ferida,
  suas bordas e a pele ao redor, quando for possível observá-los.
- Não determine a fase de cicatrização, a causa, a profundidade real
  ou a presença de infecção somente pela fotografia.
- Não interprete brilho ou contraste global como indicadores clínicos.
- Não afirme que a área da ferida foi calculada automaticamente.
- Comprimento e largura são medidas informadas pelo profissional,
  não medidas extraídas automaticamente pela IA.
- Considere limitações de iluminação, foco, distância,
  enquadramento e qualidade da imagem.
- Se não for possível avaliar uma característica, informe a limitação.
- A análise deve ser validada por um profissional de saúde.
- Responda em português brasileiro.
- Seja objetivo e evite repetições.
- Não produza etapas de raciocínio.
- Retorne somente o JSON solicitado, sem comentários adicionais.

FORMATO OBRIGATÓRIO:
Retorne um único objeto JSON válido, sem Markdown, com os campos:
- "status_resposta": string
- "conteudo_descricao": string
- "limitacoes_declaradas": lista de strings

DADOS CLÍNICOS INFORMADOS:

Localização anatômica: {dados.localizacao}
Comprimento informado (cm): {dados.comprimento or "Não informado"}
Largura informada (cm): {dados.largura or "Não informado"}
Tipo de exsudato: {dados.tipoExsudato or "Não informado"}
Presença de odor: {odor_informado}
Nível de dor: {dados.nivelDor or "Não informado"}
Queixa principal: {dados.queixaPrincipal or "Não informada"}
Observações complementares: {dados.observacoes or "Nenhuma"}

DADOS TÉCNICOS DA IMAGEM:

Dimensões originais: {input_data.dimensoes_originais}
Dimensões processadas: {input_data.dimensoes_processadas}
Brilho médio calculado pelo OpenCV: {tecnica.brilho_medio}
Contraste global calculado pelo OpenCV: {tecnica.contraste_global}

Descreva somente o que puder ser observado com cautela.
Diferencie observações visuais de informações do formulário.
Não invente dados ausentes.
""".strip()

    @staticmethod
    def _extrair_conteudo(mensagem) -> str:
        """Extrai o texto de uma resposta do modelo."""

        conteudo = getattr(mensagem, "content", None)

        if isinstance(conteudo, str):
            return conteudo.strip()

        if isinstance(conteudo, list):
            partes = []

            for bloco in conteudo:
                if isinstance(bloco, dict):
                    texto = bloco.get("text")
                else:
                    texto = getattr(bloco, "text", None)

                if texto:
                    partes.append(str(texto))

            return "\n".join(partes).strip()

        return ""

    def analisar(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> ResultadoProvedor:
        inicio = time.monotonic()
        api_key = self._obter_api_key()
        cliente = None

        try:
            if not api_key:
                return self._resultado_falha(
                    inicio,
                    "A variável KIMI_API_KEY não está configurada.",
                )

            caminho_original = input_data.caminho_imagem_original
            caminho_processado = input_data.caminho_imagem_processada

            if (
                caminho_original
                and os.path.isfile(caminho_original)
            ):
                caminho_imagem = caminho_original

            elif (
                caminho_processado
                and os.path.isfile(caminho_processado)
            ):
                caminho_imagem = caminho_processado

            else:
                return self._resultado_falha(
                    inicio,
                    "Não foi possível localizar a imagem original "
                    "nem a imagem processada.",
                )

            mime_type, _ = mimetypes.guess_type(caminho_imagem)

            if mime_type not in (
                "image/jpeg",
                "image/png",
                "image/webp",
            ):
                return self._resultado_falha(
                    inicio,
                    "Formato de imagem não suportado. "
                    "Utilize JPEG, PNG ou WebP.",
                )

            with open(caminho_imagem, "rb") as arquivo:
                imagem_base64 = base64.b64encode(
                    arquivo.read()
                ).decode("utf-8")

            imagem_url = (
                f"data:{mime_type};base64,{imagem_base64}"
            )

            prompt = self._construir_prompt(input_data)

            cliente = OpenAI(
                api_key=api_key,
                base_url=self.BASE_URL,
                timeout=self.TIMEOUT_SEGUNDOS,
                max_retries=0,
            )

            resposta = cliente.chat.completions.create(
                model=self.MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Responda diretamente à solicitação. "
                            "Não produza etapas de raciocínio. "
                            "Retorne somente o JSON solicitado, "
                            "em português brasileiro. Seja objetivo, "
                            "não invente informações e respeite "
                            "as limitações descritas no prompt."
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
                response_format={"type": "json_object"},
                temperature=1,
                max_tokens=4000,
            )

            if not resposta.choices:
                return self._resultado_falha(
                    inicio,
                    "O Kimi retornou uma resposta sem opções.",
                )

            escolha = resposta.choices[0]
            mensagem = escolha.message

            if getattr(mensagem, "refusal", None):
                return self._resultado_falha(
                    inicio,
                    "O Kimi recusou a solicitação de análise.",
                )

            conteudo = self._extrair_conteudo(mensagem)

            if not conteudo:
                motivo = getattr(escolha, "finish_reason", None)
                uso = getattr(resposta, "usage", None)

                if uso is not None:
                    if hasattr(uso, "model_dump"):
                        uso = uso.model_dump()
                    else:
                        uso = str(uso)

                detalhes = {
                    "finish_reason": str(motivo),
                    "model": getattr(resposta, "model", None),
                    "usage": uso,
                }

                return self._resultado_falha(
                    inicio,
                    "O Kimi retornou conteúdo vazio. "
                    f"Detalhes para diagnóstico: {detalhes}",
                )

            try:
                texto_json = self._limpar_json(conteudo)

            except (ValueError, json.JSONDecodeError) as erro:
                return self._resultado_falha(
                    inicio,
                    "Não foi possível interpretar o JSON retornado "
                    f"pelo Kimi: {str(erro)[:500]}. "
                    f"Início da resposta recebida: {conteudo[:500]}",
                )

            try:
                resultado = (
                    RespostaEstruturadaModelo.model_validate_json(
                        texto_json
                    )
                )

            except Exception as erro:
                return self._resultado_falha(
                    inicio,
                    "O JSON do Kimi não corresponde ao formato "
                    f"esperado: {str(erro)[:500]}",
                )

            if not resultado.conteudo_descricao.strip():
                return self._resultado_falha(
                    inicio,
                    "O Kimi retornou uma descrição vazia.",
                )

            resultado.status_resposta = "sucesso"

            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="api_real",
                sucesso=True,
                tempo_execucao_segundos=round(
                    time.monotonic() - inicio, 3
                ),
                resposta=resultado,
                mensagem_erro=None,
            )

        except Exception as erro:
            mensagem = str(erro)

            if api_key:
                mensagem = mensagem.replace(
                    api_key,
                    "[CHAVE OCULTADA]",
                )

            texto_erro = mensagem.lower()

            if (
                "insufficient_quota" in texto_erro
                or "insufficient balance" in texto_erro
                or "insufficient credits" in texto_erro
                or "out of credits" in texto_erro
            ):
                mensagem = (
                    "A API do Kimi informou que a cota, o saldo "
                    "ou os créditos disponíveis são insuficientes. "
                    "Verifique o uso e o faturamento da conta."
                )

            elif "429" in texto_erro or "rate limit" in texto_erro:
                mensagem = (
                    "A API do Kimi atingiu um limite de utilização. "
                    "Aguarde antes de tentar novamente e verifique "
                    "as cotas da conta."
                )

            elif (
                "503" in texto_erro
                or "service unavailable" in texto_erro
            ):
                mensagem = (
                    "A API do Kimi está temporariamente indisponível. "
                    "Tente novamente mais tarde."
                )

            else:
                mensagem = (
                    f"Falha na análise com Kimi: {mensagem[:900]}"
                )

            return self._resultado_falha(inicio, mensagem)

        finally:
            if cliente is not None:
                try:
                    cliente.close()
                except Exception:
                    pass