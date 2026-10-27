import base64, mimetypes, os, json, logging, time
from dotenv import load_dotenv
from openai import OpenAI
from schemas.multimodal import AnaliseMultimodalInput, ResultadoProvedor
from services.multimodal.base import BaseModelProvider
from services.multimodal.prompt_padrao import construir_prompt, normalizar_resposta
load_dotenv(); log=logging.getLogger(__name__)
class OpenAIProvider(BaseModelProvider):
    def __init__(self):super().__init__('openai','OPENAI_API_KEY')
    def analisar(self,input_data:AnaliseMultimodalInput)->ResultadoProvedor:
        inicio=time.monotonic()
        def saida(ok=False,r=None,erro=None):return ResultadoProvedor(provedor='openai',modo='api_real',sucesso=ok,tempo_execucao_segundos=round(time.monotonic()-inicio,3),resposta=r,mensagem_erro=erro)
        chave=self._obter_api_key()
        if not chave:return saida(erro='OPENAI_API_KEY ausente')
        try:
            caminho=input_data.caminho_imagem_processada
            if not os.path.isfile(caminho):caminho=input_data.caminho_imagem_original
            mime=mimetypes.guess_type(caminho)[0] or 'image/png'
            with open(caminho,'rb') as f: b64=base64.b64encode(f.read()).decode()
            with OpenAI(api_key=chave,timeout=45,max_retries=0) as cli:
                result=cli.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),response_format={'type':'json_object'},max_tokens=1800,temperature=0.2,messages=[{'role':'system','content':'Responda somente JSON válido. Apoio documental, sem diagnóstico.'},{'role':'user','content':[{'type':'text','text':construir_prompt(input_data)},{'type':'image_url','image_url':{'url':f'data:{mime};base64,{b64}'}}]}])
            if result.choices[0].finish_reason=='length':return saida(erro='OpenAI: saída truncada; aumente OPENAI_MAX_TOKENS')
            texto=result.choices[0].message.content
            return saida(True,normalizar_resposta(json.loads(texto),input_data))
        except Exception as e:
            log.exception('OpenAI falhou')
            return saida(erro=f'OpenAI: {type(e).__name__}: {str(e).replace(chave,"[REDACTED]")[:250]}')
