import os
import socket
import time
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

from schemas.multimodal import (
    AnaliseMultimodalInput,
    RespostaEstruturadaModelo,
    ResultadoProvedor,
)
from services.multimodal.base import BaseModelProvider

load_dotenv()


class GeminiProvider(BaseModelProvider):
    MODEL_NAME = "gemini-3.8-flash"
    MAX_TENTATIVAS = 3
    DELAYS_RETRY = (2, 4)
    TIMEOUT_MS = 45000

    def __init__(self):
        super().__init__(
            provider_name="gemini",
            api_key_env_var="GEMINI_API_KEY",
        )

    def _construir_prompt(self, input_data: AnaliseMultimodalInput) -> str:
        dados = input_data.dados_clinicos
        tecnica = input_data.analise_tecnica

        return f"""
Você é um assistente de apoio à documentação de avaliação de feridas
cutâneas por profissionais de saúde.
Sua tarefa é descrever características que possam ser observadas na
fotografia, considerando também as informações clínicas fornecidas.
REGRAS OBRIGATÓRIAS:
- Não forneça diagnóstico definitivo.
- Não prescreva medicamentos ou tratamentos.
- Não invente características que não estejam visíveis ou informadas.
- Diferencie observações visuais das informações relatadas pelo profissional.
- Não determine a causa da ferida apenas pela imagem.
- Não afirme profundidade, estágio ou fase de cicatrização quando
- não houver evidências suficientes.
- Informe limitações relacionadas à qualidade, iluminação ou enquadramento.
- A análise deve ser validada pelo profissional de saúde responsável.
- Responda em português brasileiro.
- Retorne somente os dados compatíveis com o formato estruturado solicitado.
INFORMAÇÕES CLÍNICAS:
Localização: {dados.localizacao}
Comprimento informado: {dados.comprimento or "Não informado"}
Largura informada: {dados.largura or "Não informado"}
Tipo de exsudato informado: {dados.tipoExsudato or "Não informado"}
Odor informado: {"Sim" if dados.odor else "Não informado"}
Nível de dor informado: {dados.nivelDor or "Não informado"}
Queixa principal: {dados.queixaPrincipal or "Não informada"}
Observações: {dados.observacoes or "Nenhuma observação informada"}
INFORMAÇÕES TÉCNICAS DA IMAGEM:
Dimensões originais: {input_data.dimensoes_originais}
Dimensões processadas: {input_data.dimensoes_processadas}
Brilho médio calculado pelo OpenCV: {tecnica.brilho_medio}
Contraste global calculated pelo OpenCV: {tecnica.contraste_global}
Descreva apenas características que possam ser avaliadas com cautela.
Não interprete os valores técnicos da imagem como indicadores clínicos
ou como confirmação de uma fase de cicatrização.
"""

    def _eh_erro_temporario(self, erro: Exception) -> bool:
        if isinstance(
            erro,
            (TimeoutError, socket.timeout, ConnectionError),
        ):
            return True

        nome_erro = type(erro).__name__.lower()
        mensagem = str(erro).lower()

        marcadores_temporarios = (
            "timeout",
            "timed out",
            "503",
            "unavailable",
            "429",
            "resource_exhausted",
            "high demand",
            "too many requests",
            "rate limit",
            "connection reset",
            "connection error",
            "internal server error",
        )

        return any(
            marcador in nome_erro for marcador in marcadores_temporarios
        ) or any(marcador in mensagem for marcador in marcadores_temporarios)

    def _resultado_falha(
        self,
        inicio: float,
        mensagem: str,
    ) -> ResultadoProvedor:
        return ResultadoProvedor(
            provedor="gemini",
            modo="api_real",
            sucesso=False,
            tempo_execucao_segundos=round(time.time() - inicio, 2),
            resposta=None,
            mensagem_erro=mensagem,
        )

    def analisar(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> ResultadoProvedor:
        inicio = time.time()
        cliente = None
        ultimo_erro = None

        try:
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                return self._resultado_falha(
                    inicio,
                    "A variável GEMINI_API_KEY não está configurada.",
                )

            caminho_imagem = input_data.caminho_imagem_processada

            if not caminho_imagem or not os.path.isfile(caminho_imagem):
                caminho_imagem = input_data.caminho_imagem_original

            if not caminho_imagem or not os.path.isfile(caminho_imagem):
                return self._resultado_falha(
                    inicio,
                    "Não foi possível localizar o arquivo da imagem.",
                )

            prompt_texto = self._construir_prompt(input_data)

            http_options = types.HttpOptions(
                timeout=self.TIMEOUT_MS,
            )

            cliente = genai.Client(
                api_key=api_key,
                http_options=http_options,
            )

            config_geracao = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RespostaEstruturadaModelo,
                temperature=0.2,
            )

            with Image.open(caminho_imagem) as imagem_aberta:
                imagem = imagem_aberta.copy()

            try:
                for tentativa in range(self.MAX_TENTATIVAS):
                    try:
                        response = cliente.models.generate_content(
                            model=self.MODEL_NAME,
                            contents=[imagem, prompt_texto],
                            config=config_geracao,
                        )

                        if not response or not response.text:
                            return self._resultado_falha(
                                inicio,
                                "O Gemini retornou uma resposta vazia.",
                            )

                        resposta_estruturada = (
                            RespostaEstruturadaModelo.model_validate_json(
                                response.text
                            )
                        )

                        return ResultadoProvedor(
                            provedor="gemini",
                            modo="api_real",
                            sucesso=True,
                            tempo_execucao_segundos=round(
                                time.time() - inicio,
                                2,
                            ),
                            resposta=resposta_estruturada,
                            mensagem_erro=None,
                        )

                    except Exception as erro:
                        ultimo_erro = erro

                        if (
                            not self._eh_erro_temporario(erro)
                            or tentativa >= self.MAX_TENTATIVAS - 1
                        ):
                            break

                        time.sleep(self.DELAYS_RETRY[tentativa])

            finally:
                imagem.close()

            mensagem_erro = str(ultimo_erro or "Erro desconhecido.")

            if api_key:
                mensagem_erro = mensagem_erro.replace(
                    api_key,
                    "[CHAVE OCULTADA]",
                )

            return self._resultado_falha(
                inicio,
                (
                    "Erro ao executar análise com Gemini após "
                    f"{self.MAX_TENTATIVAS} tentativa(s): {mensagem_erro}"
                ),
            )

        except Exception as erro:
            mensagem_erro = str(erro)
            api_key = os.getenv("GEMINI_API_KEY")

            if api_key:
                mensagem_erro = mensagem_erro.replace(
                    api_key,
                    "[CHAVE OCULTADA]",
                )

            return self._resultado_falha(
                inicio,
                f"Falha na integração com Gemini: {mensagem_erro}",
            )

        finally:
            if cliente is not None:
                try:
                    cliente.close()
                except Exception:
                    pass