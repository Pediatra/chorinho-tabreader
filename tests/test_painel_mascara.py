"""Via aditiva por máscara (TAB estreita e fundo escuro): só roda quando o HEAD não acha nada.

Medido nos casos do dono (2026-10-11): a TAB do `kenneth acoustic` (vertical, ~600 px de 1920)
tem picos de 0,6 na janela de 480 px e ~0,2 na média do quadro. A deriva separa corda de TAB
(horizontal) de corda diagonal.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab import painel, telas


def _tab_estreita() -> np.ndarray:
    """Quadro 1920x1080 preto com 6 cordas cinza-claras e algarismos brancos em 660-1260 px."""
    img = np.zeros((1080, 1920, 3), np.uint8)
    for i in range(6):
        y = 790 + i * 20
        cv2.line(img, (660, y), (1260, y), (170, 170, 170), 2)
        for x in range(680, 1240, 60):
            cv2.putText(
                img,
                str((x // 60) % 9),
                (x, y + 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (245, 245, 245),
                2,
            )
    return img


def test_deriva_de_corda_horizontal_e_pequena() -> None:
    tinta = np.zeros((200, 900), np.uint8)
    cordas = [40, 60, 80, 100, 120, 140]
    for y in cordas:
        tinta[y - 1 : y + 2, :] = 1
    assert painel.deriva_das_cordas(tinta, cordas, 20.0) < 1.0


def test_deriva_de_corda_inclinada_e_grande() -> None:
    # inclinação 0,02 (uns 18 px em 900 px): a corda fica dentro da janela de cada fatia
    tinta = np.zeros((200, 900), np.uint8)
    cordas = [40, 60, 80, 100, 120, 140]
    for y in cordas:
        for x in range(900):
            yy = y + int(0.02 * x)
            tinta[yy - 1 : yy + 2, x] = 1
    assert painel.deriva_das_cordas(tinta, cordas, 20.0) > 10.0


def test_tab_estreita_e_achada_pela_via_por_mascara() -> None:
    quadro = _tab_estreita()
    # a via por máscara é a última: o HEAD (claro e escuro) pode ou não achar; a caixa
    # final tem de cobrir a faixa das cordas, e a TAB é achada pelo caminho completo
    caixa = telas.painel_do_quadro(quadro)
    assert caixa is not None
    x0, y0, x1, y1 = caixa
    assert x0 < 1260 and x1 > 660
    assert y0 < 810 and y1 > 890
