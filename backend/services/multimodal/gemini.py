import os
import time

from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

from services.multimodal.base import BaseModelProvider
from schemas.multimodal import (
    AnaliseMultimodalInput,
    ResultadoProvedor,
    RespostaEstruturadaModelo,
)

load_dotenv()


class GeminiProvider(BaseModelProvider):
    """Integração multimodal com a API do Google Gemini."""

    MODEL_NAME = "gemini-3.8-flash"
    TIMEOUT_MILISSEGUNDOS = 120_000

    def __init__(self):
        super().__init__(
            provider_name="gemini",
            api_key_env_var="GEMINI_API_KEY",
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
- Diferencie o que é observável na fotografia do que foi informado
  pelo profissional.
- Descreva somente características que possam ser observadas com
  segurança, como o aspecto visível do leito, as bordas e a pele
  ao redor da ferida.
- Não determine a fase de cicatrização, a causa, a profundidade real
  ou a presença de infecção somente pela fotografia.
- Não interprete brilho ou contraste global como indicadores clínicos.
- Não afirme que a área da ferida foi calculada automaticamente.
- Comprimento e largura são medidas informadas pelo profissional,
  não medidas extraídas automaticamente pela IA.
- Considere possíveis limitações de iluminação, foco, distância,
  enquadramento e qualidade da imagem.
- Se não for possível avaliar alguma característica, informe essa
  limitação em vez de adivinhar.
- A análise deve ser validada por um profissional de saúde.
- Responda em português brasileiro.

FORMATO OBRIGATÓRIO:
Retorne uma resposta estruturada com estes campos:
- status_resposta: string
- conteudo_descricao: string
- limitacoes_declaradas: lista de strings

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
    def _mensagem_erro(erro: Exception) -> str:
        texto = str(erro)
        texto_upper = texto.upper()

        if (
            "HIGH DEMAND" in texto_upper
            or "UNAVAILABLE" in texto_upper
            or "503" in texto_upper
        ):
            return (
                "O Gemini está temporariamente indisponível "
                "ou com alta demanda. Nenhuma nova tentativa "
                "automática será feita nesta chamada. "
                "Tente novamente mais tarde."
            )

        if (
            "DEADLINE_EXCEEDED" in texto_upper
            or "504" in texto_upper
            or "TIMED OUT" in texto_upper
            or "TIMEOUT" in texto_upper
        ):
            return (
                "O Gemini excedeu o tempo limite de processamento. "
                "Isso pode ocorrer por demora do serviço ou da conexão."
            )

        if (
            "RESOURCE_EXHAUSTED" in texto_upper
            or "429" in texto_upper
            or "RATE LIMIT" in texto_upper
        ):
            return (
                "O Gemini recusou a solicitação por limite de utilização. "
                "Verifique as cotas e o uso da API no projeto Google."
            )

        if (
            "PERMISSION_DENIED" in texto_upper
            or "403" in texto_upper
            or "API KEY" in texto_upper
            or "INVALID_ARGUMENT" in texto_upper
        ):
            return (
                "O Gemini recusou a solicitação. Verifique a chave da API, "
                "as permissões do projeto e os parâmetros enviados."
            )

        if "NOT_FOUND" in texto_upper or "404" in texto_upper:
            return (
                "O modelo ou recurso do Gemini não foi encontrado. "
                "Verifique o identificador do modelo e sua disponibilidade."
            )

        return f"Erro ao executar análise com Gemini: {texto[:700]}"

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
                    "A variável GEMINI_API_KEY não está configurada.",
                )

            # Prioriza a imagem original para preservar
            # as características visuais da fotografia.
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

            prompt = self._construir_prompt(input_data)

            # Uma tentativa configurada no cliente para evitar
            # repetições automáticas excessivas em caso de erro.
            cliente = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=self.TIMEOUT_MILISSEGUNDOS,
                    retry_options=types.HttpRetryOptions(
                        attempts=1,
                    ),
                ),
            )

            with Image.open(caminho_imagem) as imagem:
                imagem.load()

                resposta = cliente.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=[
                        prompt,
                        imagem.copy(),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RespostaEstruturadaModelo,
                        temperature=0.2,
                    ),
                )

            if not resposta.text:
                return self._resultado_falha(
                    inicio,
                    "O Gemini retornou uma resposta vazia.",
                )

            resultado = (
                RespostaEstruturadaModelo.model_validate_json(
                    resposta.text
                )
            )

            if not resultado.conteudo_descricao.strip():
                return self._resultado_falha(
                    inicio,
                    "O Gemini retornou uma descrição vazia.",
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
            mensagem = self._mensagem_erro(erro)

            # Não expõe a chave em mensagens de erro.
            if api_key:
                mensagem = mensagem.replace(
                    api_key,
                    "[CHAVE OCULTADA]",
                )

            return self._resultado_falha(
                inicio,
                mensagem,
            )

        finally:
            if cliente is not None:
                try:
                    cliente.close()
                except Exception:
                    pass