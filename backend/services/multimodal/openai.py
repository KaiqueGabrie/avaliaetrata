
import base64
import os
import time

from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)

from services.multimodal.base import BaseModelProvider
from schemas.multimodal import (
    AnaliseMultimodalInput,
    ResultadoProvedor,
    RespostaEstruturadaModelo,
)

load_dotenv()


class OpenAIProvider(BaseModelProvider):
    """
    Integração real com a API multimodal da OpenAI.
    A resposta é utilizada como apoio descritivo,
    sem substituir a avaliação do profissional de saúde.
    """

    MODEL_NAME = "gpt-4o-mini"
    MAX_TENTATIVAS = 3
    DELAYS_RETRY = (2, 4)

    MIME_TYPES = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    def __init__(self):
        super().__init__(
            provider_name="openai",
            api_key_env_var="OPENAI_API_KEY",
        )

    def _obter_caminho_imagem(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> str:
        """
        Prioriza a imagem processada. Caso ela não exista,
        utiliza a imagem original.
        """
        caminho_processado = input_data.caminho_imagem_processada
        caminho_original = input_data.caminho_imagem_original

        if caminho_processado and os.path.isfile(caminho_processado):
            return caminho_processado

        if caminho_original and os.path.isfile(caminho_original):
            return caminho_original

        raise FileNotFoundError(
            "Não foi encontrada a imagem processada nem a original."
        )

    def _codificar_imagem(
        self,
        caminho_imagem: str,
    ) -> str:
        """
        Converte a imagem para uma URL de dados Base64,
        identificando o formato pelo arquivo.
        """
        extensao = os.path.splitext(caminho_imagem)[1].lower()
        mime_type = self.MIME_TYPES.get(extensao)

        if not mime_type:
            raise ValueError(
                "Formato não suportado. Utilize JPG, JPEG, PNG ou WEBP."
            )

        with open(caminho_imagem, "rb") as arquivo:
            conteudo = arquivo.read()

        if not conteudo:
            raise ValueError("O arquivo de imagem está vazio.")

        imagem_base64 = base64.b64encode(conteudo).decode("utf-8")

        return f"data:{mime_type};base64,{imagem_base64}"

    def _construir_prompt(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> str:
        dados = input_data.dados_clinicos
        tecnica = input_data.analise_tecnica

        comprimento = dados.comprimento or "Não informado"
        largura = dados.largura or "Não informada"
        exsudato = dados.tipoExsudato or "Não informado"
        dor = dados.nivelDor or "Não informada"
        queixa = dados.queixaPrincipal or "Não informada"
        observacoes = dados.observacoes or "Nenhuma"
        odor = "Sim" if dados.odor else "Não"

        return f"""
Você é um assistente que realiza análise visual descritiva
de fotografias de lesões cutâneas para apoiar a avaliação
de profissionais de enfermagem.

REGRAS OBRIGATÓRIAS:

1. A resposta serve apenas como apoio à avaliação profissional.
2. Não apresente diagnóstico definitivo.
3. Não prescreva tratamentos ou medicamentos.
4. Não invente características que não possam ser observadas
   na fotografia nem informações ausentes dos dados clínicos.
5. Diferencie características visíveis de informações relatadas
   pelo profissional ou paciente.
6. Se uma característica não puder ser avaliada com segurança
   pela fotografia, informe essa limitação.
7. Não afirme que a fotografia permite confirmar a causa,
   a profundidade real ou a fase de cicatrização da lesão.
8. Não trate os valores de brilho ou contraste como indicadores
   de diagnóstico ou de qualidade clínica definitiva.
9. As dimensões abaixo foram informadas pelo profissional
   em centímetros. Não foram medidas automaticamente pela IA.
10. A avaliação deve ser validada pelo profissional responsável.

DADOS CLÍNICOS INFORMADOS:

- Identificador da avaliação: {input_data.avaliacao_id or "Não informado"}
- Localização anatômica: {dados.localizacao}
- Comprimento informado: {comprimento} cm
- Largura informada: {largura} cm
- Tipo de exsudato informado: {exsudato}
- Presença de odor informada: {odor}
- Nível de dor informado: {dor}
- Queixa principal: {queixa}
- Observações: {observacoes}

DADOS TÉCNICOS DA IMAGEM — OPENCV:

- Brilho médio: {tecnica.brilho_medio:.2f}
- Contraste global: {tecnica.contraste_global:.2f}
- Dimensões originais: {input_data.dimensoes_originais}
- Dimensões processadas: {input_data.dimensoes_processadas}

TAREFA:

Analise a fotografia enviada e produza uma descrição objetiva
das características visuais que realmente possam ser observadas.

Quando possível, descreva a aparência geral, a coloração visível,
as bordas e a pele ao redor da lesão. Não presuma que todas essas
características estarão visíveis em toda fotografia.

Relacione os dados clínicos à descrição sem transformar relatos
em constatações visuais.

A resposta deve seguir exatamente o schema estruturado fornecido.

- status_resposta: "sucesso" quando a descrição for produzida.
- conteudo_descricao: descrição visual objetiva e cautelosa.
- limitacoes_declaradas: limitações relevantes da imagem,
  informações ausentes e necessidade de validação profissional.

Não forneça recomendações terapêuticas nem diagnóstico definitivo.
""".strip()

    @staticmethod
    def _eh_erro_temporario(erro: Exception) -> bool:
        """
        Identifica erros que podem justificar uma nova tentativa.
        """
        if isinstance(
            erro,
            (
                RateLimitError,
                InternalServerError,
                APIConnectionError,
                APITimeoutError,
            ),
        ):
            return True

        if isinstance(erro, APIStatusError):
            return erro.status_code in (408, 409, 429, 500, 502, 503, 504)

        return False

    def analisar(
        self,
        input_data: AnaliseMultimodalInput,
    ) -> ResultadoProvedor:
        inicio = time.time()

        def resultado_falha(mensagem: str) -> ResultadoProvedor:
            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="api_real",
                sucesso=False,
                tempo_execucao_segundos=round(time.time() - inicio, 3),
                resposta=None,
                mensagem_erro=mensagem,
            )

        api_key = self._obter_api_key()

        if not api_key:
            return resultado_falha(
                "Chave OPENAI_API_KEY não configurada no ambiente."
            )

        try:
            caminho_imagem = self._obter_caminho_imagem(input_data)
            imagem_url = self._codificar_imagem(caminho_imagem)
            prompt = self._construir_prompt(input_data)

        except (FileNotFoundError, ValueError, OSError) as erro:
            return resultado_falha(
                f"Não foi possível preparar a imagem: {erro}"
            )

        try:
            # Desativa os retries automáticos do SDK para que
            # o número de tentativas seja controlado neste método.
            cliente = OpenAI(
                api_key=api_key,
                max_retries=0,
                timeout=60.0,
            )

        except Exception as erro:
            return resultado_falha(
                f"Não foi possível inicializar o cliente OpenAI: {erro}"
            )

        try:
            for tentativa in range(1, self.MAX_TENTATIVAS + 1):
                try:
                    completion = (
                        cliente.beta.chat.completions.parse(
                            model=self.MODEL_NAME,
                            messages=[
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
                                                "detail": "high",
                                            },
                                        },
                                    ],
                                }
                            ],
                            response_format=RespostaEstruturadaModelo,
                            temperature=0.2,
                        )
                    )

                    if not completion.choices:
                        return resultado_falha(
                            "A API da OpenAI não retornou nenhuma escolha."
                        )

                    mensagem = completion.choices[0].message

                    if mensagem.refusal:
                        return resultado_falha(
                            "A solicitação foi recusada pelo modelo."
                        )

                    resposta = mensagem.parsed

                    if resposta is None:
                        return resultado_falha(
                            "A resposta da OpenAI não pôde ser validada "
                            "no schema Pydantic esperado."
                        )

                    # Confirma que o objeto recebido possui a estrutura
                    # esperada pelo restante do backend.
                    resposta = RespostaEstruturadaModelo.model_validate(
                        resposta.model_dump()
                    )

                    return ResultadoProvedor(
                        provedor=self.provider_name,
                        modo="api_real",
                        sucesso=True,
                        tempo_execucao_segundos=round(
                            time.time() - inicio, 3
                        ),
                        resposta=resposta,
                        mensagem_erro=None,
                    )

                except Exception as erro:
                    if (
                        self._eh_erro_temporario(erro)
                        and tentativa < self.MAX_TENTATIVAS
                    ):
                        espera = self.DELAYS_RETRY[tentativa - 1]

                        print(
                            "OpenAI temporariamente indisponível. "
                            f"Tentativa {tentativa}/"
                            f"{self.MAX_TENTATIVAS}. "
                            f"Nova tentativa em {espera}s."
                        )

                        time.sleep(espera)
                        continue

                    # Não repete erros permanentes.
                    return resultado_falha(
                        "Erro ao executar a análise na OpenAI "
                        f"(tentativa {tentativa}/"
                        f"{self.MAX_TENTATIVAS}): "
                        f"{type(erro).__name__}: {erro}"
                    )

            return resultado_falha(
                "A análise não foi concluída após as tentativas disponíveis."
            )

        finally:
            cliente.close()