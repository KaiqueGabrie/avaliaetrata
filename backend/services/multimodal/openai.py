"""OpenAI: relatório T.I.M.E.S. e segunda passagem visual opcional.

A segunda passagem solicita SOMENTE regiões. Não fabrica contornos, não altera
achados clínicos e não transforma hipóteses visuais em diagnóstico.
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from schemas.multimodal import AnaliseMultimodalInput, RegiaoIdentificada, ResultadoProvedor
from services.multimodal.base import BaseModelProvider
from services.multimodal.prompt_padrao import construir_prompt, normalizar_resposta
from services.multimodal.validacao_regioes import validar_regioes_propostas

load_dotenv()
log = logging.getLogger(__name__)

# Prompt propositalmente curto: o prompt T.I.M.E.S. é extenso e a resposta
# pode ser válida sem que o modelo consiga fornecer coordenadas.
PROMPT_REGIOES = """Você é um assistente de documentação visual para enfermagem.
Observe a fotografia PROCESSADA e retorne APENAS JSON com a chave
"regioes_propostas" (lista de zero a seis objetos).

Sua única tarefa é propor CONTORNOS VISUAIS APROXIMADOS, sujeitos à correção
por enfermeiro. Não diagnostique, não prescreva, não calcule percentuais.
Não invente pontos. Se não identificar limites visuais com clareza,
responda {"regioes_propostas": []}.

Cada objeto deve ter estas sete chaves:
- tipo_regiao: "contorno_visual_lesao", "superficie_escura",
  "superficie_amarelada", "superficie_avermelhada" ou "pele_perilesional".
- descricao: frase breve sobre aparência, sem diagnóstico.
- confianca: "moderada" ou "alta" SOMENTE se o contorno for visível.
- pontos: lista de 3 a 12 objetos com x e y numéricos, de 0 a 1.
- classificacao_tecido_proposta: "granulacao", "esfacelo", "necrose"
  ou "nao_classificado".
- justificativa_classificacao: frase explicando evidências morfológicas
  e limitações; não basta a cor.
- confianca_classificacao: "baixa", "moderada" ou "alta".

Regras:
- x=0 é a borda ESQUERDA; y=0 é a borda SUPERIOR.
- Os pontos percorrem o contorno em ordem, sem se cruzar.
- Use a imagem completa recebida como referência, não um recorte mental.
- NÃO marque lençol, chão ou pele normal como leito da lesão.
- Contorno geral e pele perilesional sempre "nao_classificado".
- Se houver somente tonalidade ou dúvida, use "nao_classificado".
- Uma classificação de tecido é apenas hipótese, nunca confirmação.
- Não force uma região só para preencher a lista.
- Retorne JSON válido sem texto externo.
"""


class OpenAIProvider(BaseModelProvider):
    def __init__(self):
        super().__init__('openai', 'OPENAI_API_KEY')

    @staticmethod
    def _imagem_base64(caminho: str) -> dict:
        arquivo = Path(caminho)
        if not arquivo.is_file():
            raise FileNotFoundError('Fotografia processada indisponível para a OpenAI.')
        mime = mimetypes.guess_type(str(arquivo))[0] or 'image/png'
        if mime not in ('image/png', 'image/jpeg', 'image/webp'):
            raise ValueError('Formato da fotografia não suportado.')
        codificado = base64.b64encode(arquivo.read_bytes()).decode('ascii')
        return {'url': f'data:{mime};base64,{codificado}', 'detail': 'high'}

    def propor_regioes_isoladas(self, caminho_imagem_processada: str) -> list[RegiaoIdentificada]:
        """Uma chamada focada em coordenadas, sem reexecutar T.I.M.E.S.

        Pode retornar [] legitimamente. Falhas da API são propagadas ao chamador.
        """
        chave = self._obter_api_key()
        if not chave:
            raise RuntimeError('OPENAI_API_KEY ausente')
        modelo = os.getenv('OPENAI_REGIOES_MODEL', 'gpt-4o').strip() or 'gpt-4o'
        with OpenAI(api_key=chave, timeout=60, max_retries=0) as cli:
            resultado = cli.chat.completions.create(
                model=modelo,
                response_format={'type': 'json_object'},
                max_tokens=2000,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': 'Retorne somente JSON. Não invente coordenadas ou diagnóstico.'},
                    {'role': 'user', 'content': [
                        {'type': 'text', 'text': PROMPT_REGIOES},
                        {'type': 'image_url', 'image_url': self._imagem_base64(caminho_imagem_processada)},
                    ]},
                ],
            )
        if not resultado.choices or resultado.choices[0].finish_reason == 'length':
            raise ValueError('A resposta de coordenadas da OpenAI foi truncada.')
        texto = resultado.choices[0].message.content
        if not texto:
            return []
        dados = json.loads(texto)
        if not isinstance(dados, dict):
            return []
        candidatos = dados.get('regioes_propostas', [])
        regioes, limitacoes = validar_regioes_propostas(candidatos)
        log.info('OpenAI coordenadas: candidatos=%d, aceitos=%d, descartados=%s',
                 len(candidatos) if isinstance(candidatos, list) else 0,
                 len(regioes), any('descartada' in item for item in limitacoes))
        return regioes

    def analisar(self, input_data: AnaliseMultimodalInput) -> ResultadoProvedor:
        inicio = time.monotonic()

        def saida(ok=False, r=None, erro=None):
            return ResultadoProvedor(
                provedor='openai', modo='api_real', sucesso=ok,
                tempo_execucao_segundos=round(time.monotonic() - inicio, 3),
                resposta=r, mensagem_erro=erro,
            )

        chave = self._obter_api_key()
        if not chave:
            return saida(erro='OPENAI_API_KEY ausente')
        try:
            caminho = input_data.caminho_imagem_processada
            if not os.path.isfile(caminho):
                caminho = input_data.caminho_imagem_original
            with OpenAI(api_key=chave, timeout=45, max_retries=0) as cli:
                resultado = cli.chat.completions.create(
                    model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                    response_format={'type': 'json_object'},
                    max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '3200')),
                    temperature=0.2,
                    messages=[
                        {'role': 'system', 'content': 'Responda somente JSON válido. Apoio documental, sem diagnóstico.'},
                        {'role': 'user', 'content': [
                            {'type': 'text', 'text': construir_prompt(input_data)},
                            {'type': 'image_url', 'image_url': self._imagem_base64(caminho)},
                        ]},
                    ],
                )
            if resultado.choices[0].finish_reason == 'length':
                return saida(erro='OpenAI: saída truncada; aumente OPENAI_MAX_TOKENS')
            texto = resultado.choices[0].message.content
            resposta = normalizar_resposta(json.loads(texto), input_data)
            if not resposta.marcacoes_imagem.regioes:
                try:
                    regioes = self.propor_regioes_isoladas(caminho)
                    if regioes:
                        resposta.marcacoes_imagem.regioes = regioes
                        resposta.marcacoes_imagem.limitacoes = [
                            item for item in resposta.marcacoes_imagem.limitacoes
                            if not item.startswith('Nenhuma região com geometria suficiente')
                        ]
                        resposta.marcacoes_imagem.limitacoes.append(
                            'Coordenadas obtidas em segunda passagem visual da OpenAI; não validadas.'
                        )
                        if any(r.classificacao_tecido_proposta in ('granulacao', 'esfacelo', 'necrose') for r in regioes):
                            resposta.avaliacao_tecidos.status = 'parcialmente_avaliavel'
                            resposta.avaliacao_tecidos.limitacoes.append(
                                'Há hipótese visual complementar vinculada a polígonos; requer revisão profissional.'
                            )
                except Exception:
                    # Não perde o relatório T.I.M.E.S. quando a chamada complementar falha.
                    log.warning('OpenAI: segunda passagem de coordenadas falhou; relatório preservado.', exc_info=True)
                    resposta.marcacoes_imagem.limitacoes.append(
                        'Não foi possível concluir a segunda passagem de coordenadas; desenho manual disponível.'
                    )
            return saida(True, resposta)
        except Exception as erro:
            log.exception('OpenAI falhou')
            return saida(erro=f'OpenAI: {type(erro).__name__}: {str(erro).replace(chave, "[REDACTED]")[:250]}')
