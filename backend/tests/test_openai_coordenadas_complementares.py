"""Testes offline, sem chamadas reais nem fotografias de pacientes."""
import json
import sys
import types
from types import SimpleNamespace

# Ambiente de teste offline pode não ter o SDK opcional instalado.
try:
    import openai  # noqa: F401
except ModuleNotFoundError:
    stub = types.ModuleType('openai')
    stub.OpenAI = object
    sys.modules['openai'] = stub

from schemas.multimodal import AnaliseMultimodalInput, AnaliseTecnicaOpenCVInput, DadosClinicosInput
from services.multimodal.openai import OpenAIProvider
from services.multimodal.validacao_regioes import validar_regioes_propostas
from services.visualizacao_marcacoes import validar_regioes_persistidas
from services.multimodal.complemento_regioes import _regioes_efetivas


def _poligono(tipo='contorno_visual_lesao'):
    return {
        'tipo_regiao': tipo,
        'descricao': 'Contorno visual aparente',
        'confianca': 'moderada',
        'pontos': [
            {'x': .25, 'y': .25}, {'x': .60, 'y': .25},
            {'x': .60, 'y': .65}, {'x': .25, 'y': .65},
        ],
        'classificacao_tecido_proposta': 'nao_classificado',
        'justificativa_classificacao': 'Contorno geral, não representa tecido.',
        'confianca_classificacao': 'baixa',
    }


def _resposta_api(json_data):
    if 'descricao' in json_data and 'times' not in json_data:
        json_data = {**json_data, 'times': {
            letra: {'status': 'nao_avaliavel', 'observacoes': [], 'pendencias': [], 'limitacoes': []}
            for letra in 'TIMES'
        }}
    return SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(content=json.dumps(json_data))
    )])


def _entrada(path):
    return AnaliseMultimodalInput(
        caminho_imagem_original=str(path), caminho_imagem_processada=str(path),
        dimensoes_originais={'largura': 200, 'altura': 200},
        dimensoes_processadas={'largura': 200, 'altura': 200},
        analise_tecnica=AnaliseTecnicaOpenCVInput(brilho_medio=70, contraste_global=35),
        dados_clinicos=DadosClinicosInput(localizacao='região de teste'),
    )


def _fake_client(monkeypatch, respostas):
    import services.multimodal.openai as mod
    chamadas = []
    class Cliente:
        def __init__(self, **kwargs):
            pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @property
        def chat(self): return self
        @property
        def completions(self): return self
        def create(self, **kwargs):
            chamadas.append(kwargs)
            return respostas.pop(0)
    monkeypatch.setattr(mod, 'OpenAI', Cliente)
    monkeypatch.setenv('OPENAI_API_KEY', 'fake_key_for_offline_test')
    return chamadas


def test_segunda_passagem_quando_relatorio_nao_traz_pontos(monkeypatch, tmp_path):
    imagem = tmp_path / 'sintetica.png'
    imagem.write_bytes(b'fake image bytes')
    chamadas = _fake_client(monkeypatch, [
        _resposta_api({'descricao': 'Superfície visível', 'regioes_propostas': []}),
        _resposta_api({'regioes_propostas': [_poligono()]}),
    ])
    resultado = OpenAIProvider().analisar(_entrada(imagem))
    assert resultado.sucesso
    assert resultado.resposta.conteudo_descricao == 'Superfície visível'
    assert len(resultado.resposta.marcacoes_imagem.regioes) == 1
    assert len(chamadas) == 2
    assert chamadas[1]['messages'][1]['content'][1]['image_url']['detail'] == 'high'
    assert not any(x.startswith('Nenhuma região') for x in resultado.resposta.marcacoes_imagem.limitacoes)


def test_sem_passagem_extra_quando_ja_ha_pontos(monkeypatch, tmp_path):
    imagem = tmp_path / 'sintetica.png'
    imagem.write_bytes(b'fake')
    chamadas = _fake_client(monkeypatch, [
        _resposta_api({'descricao': 'Superfície visível', 'regioes_propostas': [_poligono()]}),
    ])
    resultado = OpenAIProvider().analisar(_entrada(imagem))
    assert resultado.sucesso
    assert len(resultado.resposta.marcacoes_imagem.regioes) == 1
    assert len(chamadas) == 1


def test_sem_pontos_continua_sem_pontos(monkeypatch, tmp_path):
    imagem = tmp_path / 'sintetica.png'
    imagem.write_bytes(b'fake')
    chamadas = _fake_client(monkeypatch, [
        _resposta_api({'descricao': 'Sem limite definido', 'regioes_propostas': []}),
        _resposta_api({'regioes_propostas': []}),
    ])
    resultado = OpenAIProvider().analisar(_entrada(imagem))
    assert resultado.sucesso
    assert resultado.resposta.marcacoes_imagem.regioes == []
    assert len(chamadas) == 2


def test_falha_passagem_extra_nao_apaga_relatorio(monkeypatch, tmp_path):
    imagem = tmp_path / 'sintetica.png'
    imagem.write_bytes(b'fake')
    chamadas = _fake_client(monkeypatch, [
        _resposta_api({'descricao': 'Relatório preservado', 'regioes_propostas': []}),
    ])
    import services.multimodal.openai as mod
    class FakeFalha:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @property
        def chat(self): return self
        @property
        def completions(self): return self
        def create(self, **kwargs):
            if not chamadas:
                chamadas.append(kwargs)
                return _resposta_api({'descricao': 'Relatório preservado', 'regioes_propostas': []})
            raise RuntimeError('API indisponível')
    monkeypatch.setattr(mod, 'OpenAI', FakeFalha)
    resultado = OpenAIProvider().analisar(_entrada(imagem))
    assert resultado.sucesso
    assert resultado.resposta.conteudo_descricao == 'Relatório preservado'
    assert resultado.resposta.marcacoes_imagem.regioes == []


def test_complemento_reaproveitado_sem_alterar_relatorio():
    regioes, _ = validar_regioes_propostas([_poligono()])
    relatorio = SimpleNamespace(conteudo_editavel={
        'marcacoes_imagem': {'sistema_coordenadas': 'normalizado_0_1',
                            'imagem_referencia': 'processada', 'regioes': []},
    })
    analise = SimpleNamespace(contexto_clinico_json={
        'regioes_openai_complementares': {
            'imagem_referencia': 'supabase:processadas/teste.png',
            'regioes': [r.model_dump(mode='json') for r in regioes],
        }
    })
    recebidas, origem = _regioes_efetivas(analise, relatorio, 'openai', 'supabase:processadas/teste.png')
    assert origem == 'complemento_openai'
    assert len(recebidas) == 1
    assert relatorio.conteudo_editavel['marcacoes_imagem']['regioes'] == []
    erradas, _ = _regioes_efetivas(analise, relatorio, 'openai', 'supabase:processadas/outra.png')
    assert erradas == []


def test_hipoteses_nao_sao_inferidas_da_cor():
    regiao = _poligono('superficie_escura')
    regiao['classificacao_tecido_proposta'] = 'necrose'
    regiao['justificativa_classificacao'] = 'Escura'
    regiao['confianca_classificacao'] = 'alta'
    aceitas, _ = validar_regioes_propostas([regiao])
    assert len(aceitas) == 1
    assert aceitas[0].classificacao_tecido_proposta == 'nao_classificado'


def test_relatorio_original_tem_preferencia_sobre_complemento():
    originais, _ = validar_regioes_propostas([_poligono('superficie_amarelada')])
    complemento, _ = validar_regioes_propostas([_poligono('superficie_escura')])
    relatorio = SimpleNamespace(conteudo_editavel={
        'marcacoes_imagem': {
            'sistema_coordenadas': 'normalizado_0_1', 'imagem_referencia': 'processada',
            'regioes': [r.model_dump(mode='json') for r in originais],
        }
    })
    analise = SimpleNamespace(contexto_clinico_json={
        'regioes_openai_complementares': {
            'imagem_referencia': 'supabase:processadas/teste.png',
            'regioes': [r.model_dump(mode='json') for r in complemento],
        }
    })
    efetivas, origem = _regioes_efetivas(analise, relatorio, 'openai', 'supabase:processadas/teste.png')
    assert origem == 'relatorio'
    assert len(efetivas) == 1
    assert efetivas[0].identificador.startswith('superficie_amarelada')
