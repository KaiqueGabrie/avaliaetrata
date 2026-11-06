"""Desenho com geometria sintética: nenhuma imagem de paciente."""
import cv2
import numpy as np
import pytest
from schemas.multimodal import PontoImagem, RegiaoIdentificada
from services.visualizacao_marcacoes import (
    VisualizacaoMarcacoesService, assinatura_regioes, validar_regioes_persistidas,
)


def _regiao():
    return RegiaoIdentificada(
        identificador='contorno_visual_lesao-1', rotulo='Contorno visual aparente da lesão',
        descricao='Região sintética', confianca_autodeclarada='moderada',
        pontos=[PontoImagem(x=.2, y=.2), PontoImagem(x=.7, y=.2),
                PontoImagem(x=.7, y=.7), PontoImagem(x=.2, y=.7)],
    )


def test_valida_persistido_e_rejeita_invalido():
    conteudo = {'marcacoes_imagem': {'sistema_coordenadas': 'normalizado_0_1',
                                    'imagem_referencia': 'processada',
                                    'regioes': [_regiao().model_dump(mode='json')]}}
    assert len(validar_regioes_persistidas(conteudo)) == 1
    conteudo['marcacoes_imagem']['regioes'][0]['pontos'][0]['x'] = 9
    assert validar_regioes_persistidas(conteudo) == []


def test_rejeita_falta_de_coordenadas():
    assert validar_regioes_persistidas({'marcacoes_imagem': {'regioes': []}}) == []
    with pytest.raises(ValueError):
        VisualizacaoMarcacoesService.gerar('nao_existe.png', [], '/tmp/nada.png', 'gemini')


def test_desenha_sem_alterar_original(tmp_path):
    original = tmp_path / 'original.png'
    saida = tmp_path / 'proposta.png'
    img = np.full((400, 600, 3), 180, dtype=np.uint8)
    cv2.imwrite(str(original), img)
    regioes = [_regiao()]
    VisualizacaoMarcacoesService.gerar(str(original), regioes, str(saida), 'gemini')
    assert saida.exists()
    desenhada = cv2.imread(str(saida))
    assert desenhada.shape == img.shape
    assert np.any(desenhada != img)
    assert np.array_equal(cv2.imread(str(original)), img)
    assert assinatura_regioes(regioes, 'supabase:processadas/a') != assinatura_regioes(regioes, 'supabase:processadas/b')
