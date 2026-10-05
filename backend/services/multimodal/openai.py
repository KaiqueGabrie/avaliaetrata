import time
from services.multimodal.base import BaseModelProvider
from schemas.multimodal import (
    AnaliseMultimodalInput, 
    ResultadoProvedor, 
    RespostaEstruturadaModelo
)

class OpenAIProvider(BaseModelProvider):
    """
    Provedor responsável pela integração com o modelo OpenAI.
    """

    def __init__(self):
        super().__init__(provider_name="openai", api_key_env_var="OPENAI_API_KEY")

    def analisar(self, input_data: AnaliseMultimodalInput) -> ResultadoProvedor:
        inicio = time.time()
        
        try:
            resposta_neutra = RespostaEstruturadaModelo(
                status_resposta="estrutura_pronta",
                conteudo_descricao=f"Módulo OpenAI preparado para receber a imagem {input_data.caminho_imagem_processada} e os dados da região: {input_data.dados_clinicos.localizacao}.",
                limitacoes_declaradas=[
                    "Execução em modo de validação de arquitetura.",
                    "Chamada real de API desativada nesta etapa."
                ]
            )

            tempo_execucao = round(time.time() - inicio, 3)

            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="simulacao",
                sucesso=True,
                tempo_execucao_segundos=tempo_execucao,
                resposta=resposta_neutra,
                mensagem_erro=None
            )

        except Exception as e:
            tempo_execucao = round(time.time() - inicio, 3)
            return ResultadoProvedor(
                provedor=self.provider_name,
                modo="simulacao",
                sucesso=False,
                tempo_execucao_segundos=tempo_execucao,
                resposta=None,
                mensagem_erro=f"Erro na estrutura do provedor OpenAI: {str(e)}"
            )