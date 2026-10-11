"""Tablatura ESCURA (cifra club): cordas claras sobre fundo escuro.

Medido nos 15 quadros rotulados do `cifra club` (fundo cinza mediano 26, cordas 13,7 a 21,5
mais claras que o fundo acima): o caminho do HEAD não as achava (5 de 15). O caminho escuro
só entra quando o do HEAD não acha nada, e só para fundo escuro com cordas mais claras.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab import painel, telas


def _tab_escura() -> np.ndarray:
    """Quadro 1920x1080: fundo escuro liso, 6 cordas cinza-claras e algarismos brancos."""
    img = np.full((1080, 1920, 3), 26, np.uint8)
    for i in range(6):
        y = 790 + i * 52
        cv2.line(img, (60, y), (1500, y), (70, 70, 70), 2)
        for x in range(180, 1400, 130):
            cv2.putText(
                img,
                str((x // 130) % 9),
                (x, y + 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                (235, 235, 235),
                3,
            )
    return img


def _tab_clara() -> np.ndarray:
    """Quadro com papel branco e tablatura escura: painel claro, o caminho do HEAD o acha."""
    img = np.full((1080, 1920, 3), 245, np.uint8)
    for i in range(6):
        y = 790 + i * 52
        cv2.line(img, (60, y), (1500, y), (30, 30, 30), 2)
        for x in range(180, 1400, 130):
            cv2.putText(
                img,
                str((x // 130) % 9),
                (x, y + 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.1,
                (20, 20, 20),
                3,
            )
    return img


def test_tab_escura_e_achada_pelo_caminho_escuro():
    quadro = _tab_escura()
    achados = painel.candidatos_claros_escuros(quadro)
    assert achados, "a TAB escura deve virar candidato no caminho escuro"
    rect = telas.painel_do_quadro(quadro)
    assert rect is not None
    _, y0, _, y1 = rect
    assert y0 <= 790 and y1 >= 790 + 5 * 52


def test_painel_claro_nao_entra_no_caminho_escuro():
    quadro = _tab_clara()
    assert painel.candidatos_claros_escuros(quadro) == []
    assert telas.painel_do_quadro(quadro) == telas._painel_do_quadro_claro(quadro)


def test_fundo_claro_sem_tab_fica_sem_caixa():
    quadro = np.full((1080, 1920, 3), 245, np.uint8)
    assert telas.painel_do_quadro(quadro) is None


def test_fundo_escuro_sem_cordas_fica_sem_caixa():
    quadro = np.full((1080, 1920, 3), 26, np.uint8)
    assert telas.painel_do_quadro(quadro) is None
