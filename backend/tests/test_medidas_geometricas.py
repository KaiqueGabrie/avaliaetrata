"""Testes determinísticos, sem dados reais nem serviços externos."""
from services.medidas_geometricas import calcular_estimativas
from schemas.multimodal import AnaliseMultimodalInput, AnaliseTecnicaOpenCVInput, DadosClinicosInput
from services.multimodal.prompt_padrao import normalizar_resposta


def test_area_retangulo_e_elipse():
    r = calcular_estimativas('7', '5')
    assert r['area_retangulo_delimitador_cm2'] == 35.0
    assert r['area_elipse_aproximada_cm2'] == 27.49
    assert r['area_real_segmentada_cm2'] is None


def test_decimal_virgula():
    r = calcular_estimativas('2,5', '1,5')
    assert r['area_retangulo_delimitador_cm2'] == 3.75
    assert r['area_elipse_aproximada_cm2'] == 2.95


def test_rejeita_dados_invalidos():
    for c, l in [('0', '5'), ('abc', '4'), ('-1', '2'), ('NaN', '3'), ('1e9999', '2'), ('7', None)]:
        r = calcular_estimativas(c, l)
        assert r['area_retangulo_delimitador_cm2'] is None
        assert r['area_real_segmentada_cm2'] is None


def test_normalizacao_inclui_estimativas_sem_area_real():
    entrada = AnaliseMultimodalInput(
        caminho_imagem_original='orig.png', caminho_imagem_processada='proc.png',
        dimensoes_originais={'largura': 100, 'altura': 100},
        dimensoes_processadas={'largura': 100, 'altura': 100},
        analise_tecnica=AnaliseTecnicaOpenCVInput(brilho_medio=60, contraste_global=20),
        dados_clinicos=DadosClinicosInput(localizacao='teste', comprimento='7', largura='5'),
    )
    dados = {
        'descricao': 'Fotografia sintética de teste.',
        'times': {k: {'status': 'nao_avaliavel', 'observacoes': [], 'pendencias': []} for k in 'TIMES'},
    }
    r = normalizar_resposta(dados, entrada)
    assert r.medidas.area_retangulo_delimitador_cm2 == 35
    assert r.medidas.area_elipse_aproximada_cm2 == 27.49
    assert r.medidas.area_calculada_cm2 is None
