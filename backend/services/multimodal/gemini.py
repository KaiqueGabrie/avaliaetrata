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
    RespostaEstruturadaModelo
)


load_dotenv()


class GeminiProvider(BaseModelProvider):
    """
    Provedor responsável pela integração real
    com a API do Gemini.
    """

    MODEL_NAME = "gemini-3.8-flash"

    MAX_TENTATIVAS = 3

    DELAYS_RETRY = {
        1: 2,
        2: 4
    }

    def __init__(self):
        super().__init__(
            provider_name="gemini",
            api_key_env_var="GEMINI_API_KEY"
        )

    # ========================================================
    # PROMPT
    # ========================================================

    def _construir_prompt(
        self,
        input_data: AnaliseMultimodalInput
    ) -> str:

        dados_clinicos = input_data.dados_clinicos
        analise_tecnica = input_data.analise_tecnica

        prompt = f"""
Você é um assistente especialista em análise visual descritiva
de lesões de pele para auxílio em enfermagem.

DIRETRIZES OBRIGATÓRIAS:

1. Esta análise é um apoio descritivo à avaliação profissional
e não substitui a avaliação, o julgamento ou a decisão do
profissional de saúde.

2. NÃO emita diagnóstico definitivo.

3. NÃO prescreva tratamentos ou medicamentos.

4. NÃO invente informações, características ou métricas que
não estejam presentes na imagem ou nos dados fornecidos.

5. Analise descritivamente a fotografia considerando, quando
visíveis, características gerais do leito da lesão, bordas e
pele ao redor da lesão, sempre em conjunto com os dados
fornecidos pelo profissional.

DADOS CLÍNICOS PREENCHIDOS PELO PROFISSIONAL:

- Localização anatômica:
  {dados_clinicos.localizacao}

- Dimensões informadas:
  Comprimento: {dados_clinicos.comprimento or 'Não informado'}
  Largura: {dados_clinicos.largura or 'Não informado'}

- Tipo de exsudato:
  {dados_clinicos.tipoExsudato or 'Não informado'}

- Presença de odor:
  {'Sim' if dados_clinicos.odor else 'Não'}

- Nível de dor:
  {dados_clinicos.nivelDor or 'Não informado'}

- Queixa principal:
  {dados_clinicos.queixaPrincipal or 'Não informada'}

- Observações complementares:
  {dados_clinicos.observacoes or 'Nenhuma'}

DADOS TÉCNICOS EXTRAÍDOS DA IMAGEM PELO OPENCV:

- Brilho médio:
  {analise_tecnica.brilho_medio:.2f}

- Contraste global:
  {analise_tecnica.contraste_global:.2f}

TAREFA:

Forneça uma descrição objetiva das características visuais
observáveis na imagem, relacionando-as aos dados fornecidos,
sem extrapolar informações que não possam ser observadas ou
confirmadas.

A resposta deve ser estruturada conforme o schema fornecido.

Defina `status_resposta` como "sucesso" quando a análise puder
ser realizada normalmente.

Em `limitacoes_declaradas`, informe limitações relevantes,
como iluminação, qualidade da fotografia, enquadramento,
ausência de informações clínicas ou necessidade de validação
pelo profissional.

Não apresente a análise como diagnóstico definitivo.
"""

        return prompt.strip()

    # ========================================================
    # IDENTIFICAÇÃO DE ERROS TEMPORÁRIOS
    # ========================================================

    def _eh_erro_temporario(
        self,
        erro: Exception
    ) -> bool:

        mensagem = str(erro).upper()

        indicadores = (
            "503",
            "UNAVAILABLE",
            "429",
            "RESOURCE_EXHAUSTED",
            "HIGH DEMAND",
            "TOO MANY REQUESTS",
            "RATE LIMIT"
        )

        return any(
            indicador in mensagem
            for indicador in indicadores
        )

    # ========================================================
    # EXECUÇÃO DA ANÁLISE
    # ========================================================

    def analisar(
        self,
        input_data: AnaliseMultimodalInput
    ) -> ResultadoProvedor:

        inicio = time.time()

        # ====================================================
        # 1. OBTER API KEY
        # ====================================================

        api_key = self._obter_api_key()

        if not api_key:

            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="api_real",
                sucesso=False,
                tempo_execucao_segundos=round(
                    time.time() - inicio,
                    3
                ),
                resposta=None,
                mensagem_erro=(
                    "Chave de API "
                    "(GEMINI_API_KEY) não configurada "
                    "no ambiente."
                )
            )

        # ====================================================
        # 2. DEFINIR IMAGEM
        # ====================================================

        caminho_imagem = (
            input_data.caminho_imagem_processada
            or input_data.caminho_imagem_original
        )

        if not os.path.isfile(caminho_imagem):

            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="api_real",
                sucesso=False,
                tempo_execucao_segundos=round(
                    time.time() - inicio,
                    3
                ),
                resposta=None,
                mensagem_erro=(
                    "Arquivo de imagem não encontrado "
                    f"no caminho: {caminho_imagem}"
                )
            )

        try:

            # =================================================
            # 3. CRIAR CLIENTE GEMINI
            # =================================================

            client = genai.Client(
                api_key=api_key
            )

            # =================================================
            # 4. CONSTRUIR PROMPT
            # =================================================

            prompt_texto = (
                self._construir_prompt(
                    input_data
                )
            )

            # =================================================
            # 5. CONFIGURAÇÃO DA RESPOSTA
            # =================================================

            config_geracao = (
                types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=(
                        RespostaEstruturadaModelo
                    ),
                    temperature=0.2
                )
            )

            # =================================================
            # 6. TENTATIVAS COM RETRY
            # =================================================

            ultimo_erro = None

            for tentativa in range(
                1,
                self.MAX_TENTATIVAS + 1
            ):

                try:

                    with Image.open(
                        caminho_imagem
                    ) as imagem:

                        imagem.load()

                        response = (
                            client.models
                            .generate_content(
                                model=self.MODEL_NAME,
                                contents=[
                                    imagem,
                                    prompt_texto
                                ],
                                config=config_geracao
                            )
                        )

                    # =========================================
                    # 7. VALIDAR RESPOSTA
                    # =========================================

                    if not response.text:

                        return ResultadoProvedor(
                            provedor=self.provider_name,
                            modo="api_real",
                            sucesso=False,
                            tempo_execucao_segundos=round(
                                time.time() - inicio,
                                3
                            ),
                            resposta=None,
                            mensagem_erro=(
                                "A API do Gemini retornou "
                                "uma resposta vazia."
                            )
                        )

                    # =========================================
                    # 8. VALIDAR JSON COM PYDANTIC
                    # =========================================

                    resposta_estruturada = (
                        RespostaEstruturadaModelo
                        .model_validate_json(
                            response.text
                        )
                    )

                    # =========================================
                    # 9. SUCESSO
                    # =========================================

                    return ResultadoProvedor(
                        provedor=self.provider_name,
                        modo="api_real",
                        sucesso=True,
                        tempo_execucao_segundos=round(
                            time.time() - inicio,
                            3
                        ),
                        resposta=resposta_estruturada,
                        mensagem_erro=None
                    )

                except Exception as erro_tentativa:

                    ultimo_erro = erro_tentativa

                    # =========================================
                    # 10. VERIFICAR RETRY
                    # =========================================

                    erro_temporario = (
                        self._eh_erro_temporario(
                            erro_tentativa
                        )
                    )

                    ultima_tentativa = (
                        tentativa
                        >= self.MAX_TENTATIVAS
                    )

                    if (
                        erro_temporario
                        and not ultima_tentativa
                    ):

                        tempo_espera = (
                            self.DELAYS_RETRY
                            .get(tentativa, 4)
                        )

                        print(
                            "Gemini temporariamente "
                            "indisponível. "
                            f"Tentativa {tentativa}/"
                            f"{self.MAX_TENTATIVAS}. "
                            f"Nova tentativa em "
                            f"{tempo_espera}s."
                        )

                        time.sleep(
                            tempo_espera
                        )

                        continue

                    # =========================================
                    # ERRO PERMANENTE OU ÚLTIMA TENTATIVA
                    # =========================================

                    break

            # =================================================
            # 11. TODAS AS TENTATIVAS FALHARAM
            # =================================================

            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="api_real",
                sucesso=False,
                tempo_execucao_segundos=round(
                    time.time() - inicio,
                    3
                ),
                resposta=None,
                mensagem_erro=(
                    "Erro ao executar análise com Gemini "
                    f"após {self.MAX_TENTATIVAS} tentativa(s): "
                    f"{str(ultimo_erro)}"
                )
            )

        except Exception as erro:

            # =================================================
            # 12. ERRO GERAL
            # =================================================

            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="api_real",
                sucesso=False,
                tempo_execucao_segundos=round(
                    time.time() - inicio,
                    3
                ),
                resposta=None,
                mensagem_erro=(
                    "Erro ao executar análise com Gemini: "
                    f"{str(erro)}"
                )
            )