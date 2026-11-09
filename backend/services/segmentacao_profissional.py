"""Desenho e contagem de pixels de regiões REVISADAS manualmente.

Não realiza classificação de tecidos por IA, diagnóstico nem mensuração em cm².
As proporções são relativas aos pixels dentro do contorno revisado da lesão.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from schemas.revisao_marcacoes import RegiaoManual
from services.multimodal.validacao_regioes import _area, _simples

# OpenCV usa BGR. Cores são legendas, não diagnóstico.
CORES = {
    'contorno_lesao': (35, 175, 35),
    'granulacao': (55, 55, 220),
    'esfacelo': (20, 205, 235),
    'necrose': (120, 100, 85),
    'pele_perilesional': (215, 145, 60),
    'nao_classificado': (180, 180, 180),
}
ROTULOS = {
    'contorno_lesao': 'Contorno da lesao',
    'granulacao': 'Granulacao (revisao profissional)',
    'esfacelo': 'Esfacelo (revisao profissional)',
    'necrose': 'Necrose (revisao profissional)',
    'pele_perilesional': 'Pele ao redor',
    'nao_classificado': 'Nao classificado',
}
CLASSES_TECIDO = ('granulacao', 'esfacelo', 'necrose', 'nao_classificado')


def validar_geometrias(regioes: list[RegiaoManual]) -> None:
    if len({r.id for r in regioes}) != len(regioes):
        raise ValueError('Há regiões com identificadores repetidos.')
    if sum(r.classe == 'contorno_lesao' for r in regioes) > 1:
        raise ValueError('Use apenas um polígono para o contorno principal da lesão.')
    for regiao in regioes:
        pontos = [(p.x, p.y) for p in regiao.pontos]
        if not all(math.isfinite(x) and math.isfinite(y) for x, y in pontos):
            raise ValueError('Uma região contém coordenadas não finitas.')
        if len(set(pontos)) != len(pontos):
            raise ValueError(f'A região {regiao.id} contém pontos duplicados.')
        if not 0.0001 <= _area(pontos) <= 0.95 or not _simples(pontos):
            raise ValueError(f'A região {regiao.id} tem polígono inválido ou cruzado.')


def mascara_regiao(regiao: RegiaoManual, largura: int, altura: int) -> np.ndarray:
    pontos = np.asarray([
        (round(p.x * (largura - 1)), round(p.y * (altura - 1)))
        for p in regiao.pontos
    ], dtype=np.int32)
    mascara = np.zeros((altura, largura), dtype=np.uint8)
    cv2.fillPoly(mascara, [pontos], 1)
    return mascara.astype(bool)


def calcular_proporcoes(regioes: list[RegiaoManual], largura: int, altura: int) -> dict:
    """Não converte pixels em cm² e não estima tecido não observável."""
    validar_geometrias(regioes)
    contorno = next((r for r in regioes if r.classe == 'contorno_lesao'), None)
    if contorno is None:
        return {
            'disponivel': False, 'motivo': 'Delimite primeiro o contorno da lesão.',
            'percentuais': None, 'cobertura_classificada_percentual': None,
            'metodo': 'Proporção de pixels das regiões revisadas; não é área física.',
        }
    dentro = mascara_regiao(contorno, largura, altura)
    total = int(dentro.sum())
    if total < 16:
        raise ValueError('Contorno muito pequeno para contabilizar pixels.')
    dono = np.zeros((altura, largura), dtype=np.uint8)
    indices = {'granulacao': 1, 'esfacelo': 2, 'necrose': 3, 'nao_classificado': 4}
    for regiao in regioes:
        if regiao.classe not in CLASSES_TECIDO:
            continue
        m = mascara_regiao(regiao, largura, altura) & dentro
        # Regiões diferentes não podem reivindicar os mesmos pixels.
        if np.any(m & (dono != 0)):
            raise ValueError('Regiões de tecidos sobrepostas: corrija os contornos antes de salvar.')
        dono[m] = indices[regiao.classe]
    contagens = {classe: int(np.count_nonzero(dono == codigo)) for classe, codigo in indices.items()}
    contagens['nao_classificado'] += int(np.count_nonzero(dentro & (dono == 0)))
    percentuais = {classe: round(contagens[classe] * 100 / total, 2) for classe in indices}
    cobertura = round((total - contagens['nao_classificado']) * 100 / total, 2)
    return {
        'disponivel': True,
        'motivo': None,
        'percentuais': percentuais,
        'cobertura_classificada_percentual': cobertura,
        'pixels_contorno': total,
        'metodo': 'Percentual de pixels dentro do contorno manual da lesão. Classes atribuídas/revisadas pelo profissional. Não representa cm², profundidade nem diagnóstico automático.',
    }


def gerar_visualizacao(
    caminho_origem: str, regioes: list[RegiaoManual], destino: str,
    *, aprovado: bool, provedor: str,
) -> tuple[Path, dict]:
    imagem = cv2.imread(str(caminho_origem), cv2.IMREAD_COLOR)
    if imagem is None:
        raise ValueError('Não foi possível abrir a imagem processada.')
    altura, largura = imagem.shape[:2]
    if altura * largura > 24_000_000:
        raise ValueError('Imagem grande demais para renderizar marcações.')
    estatisticas = calcular_proporcoes(regioes, largura, altura)
    estatisticas['status_validacao'] = 'aprovado' if aprovado else 'rascunho_nao_validado'
    estatisticas['metodo'] += (
        ' Versão APROVADA pelo profissional.' if aprovado
        else ' RASCUNHO: proporções exploratórias, não validadas pelo profissional.'
    )
    base = imagem.copy()
    for regiao in regioes:
        if regiao.classe == 'contorno_lesao':
            continue
        mascara = mascara_regiao(regiao, largura, altura)
        camada = np.zeros_like(imagem)
        camada[:] = CORES[regiao.classe]
        base[mascara] = cv2.addWeighted(imagem[mascara], .76, camada[mascara], .24, 0)
    for regiao in regioes:
        pontos = np.asarray([
            (round(p.x * (largura - 1)), round(p.y * (altura - 1))) for p in regiao.pontos
        ], dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(base, [pontos], True, CORES[regiao.classe],
                      max(2, largura // 350), cv2.LINE_AA)
    faixa = max(32, min(52, altura // 15))
    cv2.rectangle(base, (0, 0), (largura, faixa), (0, 0, 0), -1)
    texto = ('REVISAO PROFISSIONAL APROVADA' if aprovado else 'RASCUNHO - NAO APROVADO')
    escala = max(.3, min(.65, largura / 1100))
    cv2.putText(base, texto, (8, faixa - 9), cv2.FONT_HERSHEY_SIMPLEX, escala,
                (255, 255, 255), 1, cv2.LINE_AA)
    saida = Path(destino)
    saida.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(saida), base):
        raise ValueError('Falha ao gravar imagem revisada.')
    return saida, estatisticas
