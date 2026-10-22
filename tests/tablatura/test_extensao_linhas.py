"""Extensão em x das cordas: faixa de destaque clara conta, vídeo escuro não.

Casos medidos: End of Beginning (kenneth acoustic, t=52 s), em que a faixa amarela do
compasso tocado apagava as cordas no Otsu; Gymnopédie (robert lunn, t=163 s), em que o
papel branco fica sobre vídeo escuro. As imagens abaixo reproduzem a geometria, sem
acervo.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.tablatura.leitura.tabseg import extensao_das_linhas

CORDAS = [30, 60, 90, 120, 150, 180]


def _faixa(fundo: int, x0: int, x1: int, cor_linha: int) -> np.ndarray:
    """Faixa 210 x 1200 com fundo ``fundo`` e 6 cordas de 2 px entre ``x0`` e ``x1``."""
    img = np.full((210, 1200, 3), fundo, np.uint8)
    for y in CORDAS:
        cv2.line(img, (x0, y), (x1, y), (cor_linha,) * 3, 2)
    return img


def test_faixa_amarela_de_destaque_nao_parte_a_extensao() -> None:
    img = _faixa(250, 10, 1190, 40)
    # destaque amarelo claro (cinza ~235) com cordas cinza-médio, quase sem contraste
    img[:, 300:700] = (180, 245, 250)
    for y in CORDAS:
        cv2.line(img, (300, y), (700, y), (205, 215, 215), 2)
    x0, x1 = extensao_das_linhas(img, CORDAS)
    assert x0 <= 20
    assert x1 >= 1180


def test_video_escuro_ao_lado_do_papel_nao_entra() -> None:
    img = _faixa(255, 400, 900, 30)
    # vídeo escuro dos dois lados do papel, com riscos horizontais mais escuros nas
    # alturas das cordas (o contraste local acharia "linha" ali)
    img[:, :380] = 60
    img[:, 920:] = 60
    for y in CORDAS:
        cv2.line(img, (0, y), (380, y), (20, 20, 20), 2)
        cv2.line(img, (920, y), (1199, y), (20, 20, 20), 2)
    x0, x1 = extensao_das_linhas(img, CORDAS)
    assert 380 <= x0 <= 420
    assert 880 <= x1 <= 920
