"""Estimativas geométricas derivadas EXCLUSIVAMENTE de medidas informadas.

Não equivalem à área real da ferida, segmentação ou planimetria validada.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _medida_positiva(valor: object) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    texto = str(valor).strip().replace(',', '.')
    if not texto or ' ' in texto:
        return None
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return None
    if not numero.is_finite() or not (Decimal('0') < numero <= Decimal('300')):
        return None
    return numero


def calcular_estimativas(comprimento: object, largura: object) -> dict:
    """Retorna resultados em cm² arredondados, sem inferir geometria real."""
    c, l = _medida_positiva(comprimento), _medida_positiva(largura)
    if c is None or l is None:
        return {
            'area_retangulo_delimitador_cm2': None,
            'area_elipse_aproximada_cm2': None,
            'area_real_segmentada_cm2': None,
            'metodo': 'Não calculado: comprimento/largura ausentes ou inválidos.',
            'observacao': 'São necessárias duas medidas positivas, em centímetros, informadas pelo profissional.',
        }
    area_retangular = c * l
    area_elipse = area_retangular * Decimal('3.14159265358979323846') / Decimal(4)
    def arredondar(v: Decimal) -> float:
        return float(v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return {
        'area_retangulo_delimitador_cm2': arredondar(area_retangular),
        'area_elipse_aproximada_cm2': arredondar(area_elipse),
        'area_real_segmentada_cm2': None,
        'metodo': 'Retângulo: comprimento × largura; elipse: π × comprimento × largura / 4.',
        'observacao': (
            'Estimativas geométricas calculadas com medidas fornecidas pelo profissional. '
            'Não representam a área real da lesão; a aproximação elíptica pressupõe formato aproximadamente elíptico.'
        ),
    }
