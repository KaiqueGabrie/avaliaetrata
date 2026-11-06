"""Visualizacao de bordas da fotografia, sem segmentacao da lesao.

O Canny destaca transicoes de intensidade de TODA a imagem. Essas bordas
nao identificam, classificam ou delimitam clinicamente a ferida.
"""
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np


class VisualizacaoBordasService:
    @staticmethod
    def gerar(caminho_imagem: str, pasta_destino: str) -> Path:
        origem = Path(caminho_imagem)
        destino = Path(pasta_destino)
        destino.mkdir(parents=True, exist_ok=True)

        imagem = cv2.imread(str(origem), cv2.IMREAD_COLOR)
        if imagem is None:
            raise ValueError("Nao foi possivel ler a imagem para realce de bordas.")

        # Usamos a imagem ja redimensionada pelo processamento existente.
        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        suavizada = cv2.GaussianBlur(cinza, (5, 5), 0)
        mediana = float(np.median(suavizada))
        limiar_inferior = max(20, int(0.66 * mediana))
        limiar_superior = min(255, max(limiar_inferior + 1, int(1.33 * mediana)))
        bordas = cv2.Canny(suavizada, limiar_inferior, limiar_superior)

        # Destaca as transicoes de intensidade, sem inferir onde esta a lesao.
        visualizacao = imagem.copy()
        visualizacao[bordas > 0] = (0, 200, 255)  # BGR: amarelo/ambar

        caminho_saida = destino / f"bordas_{uuid4().hex}.png"
        if not cv2.imwrite(str(caminho_saida), visualizacao):
            raise ValueError("Falha ao gravar a visualizacao tecnica de bordas.")
        return caminho_saida
