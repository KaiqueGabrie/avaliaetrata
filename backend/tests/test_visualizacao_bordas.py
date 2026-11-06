"""Teste local sem dados de pacientes: python -m pytest tests/test_visualizacao_bordas.py"""
from pathlib import Path
import cv2
import numpy as np

from services.visualizacao_bordas import VisualizacaoBordasService


def test_gera_visualizacao_sem_alterar_imagem_original(tmp_path: Path):
    entrada = tmp_path / "original.png"
    imagem = np.full((180, 240, 3), 160, dtype=np.uint8)
    cv2.rectangle(imagem, (40, 40), (200, 140), (40, 40, 40), 3)
    assert cv2.imwrite(str(entrada), imagem)
    original_bytes = entrada.read_bytes()

    saida = VisualizacaoBordasService.gerar(str(entrada), str(tmp_path))
    assert saida.exists()
    assert saida.suffix == ".png"
    assert saida.name.startswith("bordas_")
    visualizacao = cv2.imread(str(saida))
    assert visualizacao.shape == imagem.shape
    assert np.any(np.all(visualizacao == [0, 200, 255], axis=2))
    assert entrada.read_bytes() == original_bytes
