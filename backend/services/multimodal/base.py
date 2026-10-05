from abc import ABC, abstractmethod
import os
from schemas.multimodal import AnaliseMultimodalInput, ResultadoProvedor

class BaseModelProvider(ABC):
    """
    Contrato base/interface que todos os provedores multimodais devem implementar.
    """

    def __init__(self, provider_name: str, api_key_env_var: str):
        self.provider_name = provider_name
        self.api_key_env_var = api_key_env_var

    @abstractmethod
    def analisar(self, input_data: AnaliseMultimodalInput) -> ResultadoProvedor:
        """
        Método obrigatório para processar a entrada unificada e retornar um ResultadoProvedor.
        """
        pass

    def _obter_api_key(self) -> str:
        """
        Recupera a chave de API das variáveis de ambiente.
        """
        return os.getenv(self.api_key_env_var, "")