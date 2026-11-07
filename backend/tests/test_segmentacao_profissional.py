"""Testes com imagens sintéticas, sem fotografias clínicas."""
import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from schemas.revisao_marcacoes import RegiaoManual, SalvarRevisao
from services.segmentacao_profissional import (
    calcular_proporcoes, gerar_visualizacao, validar_geometrias,
)


def regiao(nome, classe, pts):
    return RegiaoManual(id=nome, classe=classe, pontos=[{'x': x, 'y': y} for x, y in pts])


def ret(x1, y1, x2, y2):
    return [(x1,y1), (x2,y1), (x2,y2), (x1,y2)]


def test_contorno_obrigatorio_para_percentuais():
    r = regiao('a', 'granulacao', ret(.1,.1,.4,.4))
    assert calcular_proporcoes([r], 400, 400)['disponivel'] is False


def test_percentuais_com_nao_classificado():
    contorno = regiao('cont', 'contorno_lesao', ret(.1,.1,.9,.9))
    classe = regiao('g', 'granulacao', ret(.1,.1,.5,.9))
    resultado = calcular_proporcoes([contorno, classe], 1000, 1000)
    assert resultado['disponivel']
    assert 49 < resultado['percentuais']['granulacao'] < 51
    assert 49 < resultado['percentuais']['nao_classificado'] < 51
    assert resultado['percentuais']['esfacelo'] == 0
    assert abs(sum(resultado['percentuais'].values()) - 100) <= .03


def test_rejeita_sobreposicao_de_classes():
    contorno = regiao('cont', 'contorno_lesao', ret(.1,.1,.9,.9))
    g = regiao('g', 'granulacao', ret(.2,.2,.7,.7))
    n = regiao('n', 'necrose', ret(.4,.4,.8,.8))
    with pytest.raises(ValueError, match='sobrepostas'):
        calcular_proporcoes([contorno, g, n], 400, 400)


def test_rejeita_geometria_cruzada():
    r = regiao('x', 'necrose', [(0.1,0.1),(0.8,0.8),(0.8,0.1),(0.1,0.8)])
    with pytest.raises(ValueError):
        validar_geometrias([r])


def test_rejeita_classes_inventadas_e_coordenadas_invalidas():
    with pytest.raises(ValidationError):
        regiao('x', 'infeccao_confirmada', ret(.1,.1,.4,.4))
    with pytest.raises(ValidationError):
        regiao('x', 'granulacao', ret(-.1,.1,.4,.4))


def test_desenha_sem_mudar_original(tmp_path):
    entrada = tmp_path / 'entrada.png'
    saida = tmp_path / 'saida.png'
    imagem = np.full((360, 500, 3), 170, dtype=np.uint8)
    cv2.imwrite(str(entrada), imagem)
    regioes = [regiao('cont', 'contorno_lesao', ret(.2,.2,.8,.8)),
               regiao('n', 'necrose', ret(.3,.3,.6,.6))]
    _, estatisticas = gerar_visualizacao(str(entrada), regioes, str(saida), aprovado=False, provedor='gemini')
    assert estatisticas['disponivel']
    assert saida.exists()
    assert np.array_equal(cv2.imread(str(entrada)), imagem)
    assert not np.array_equal(cv2.imread(str(saida)), imagem)


def test_revisao_esperada_nao_negativa():
    with pytest.raises(ValidationError):
        SalvarRevisao(provedor_base='manual', revisao_esperada=-1, regioes=[regiao('c', 'contorno_lesao', ret(.1,.1,.5,.5))])
