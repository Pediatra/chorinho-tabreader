"""Portão das cordas contínuas: a TAB tem 6 linhas horizontais, o braço do violão não.

Medido (data/saida/painel_braco): nas 134 caixas de TAB do gabarito de presença o número de
linhas horizontais contínuas é de 6 a 13; no braço visto na diagonal (`guitar dell'arte`,
`south american music`) é 0 ou 1.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.tablatura.leitura import painel
from tab.tablatura.produto import telas


def _tab(largura: int = 800, passo: int = 20) -> np.ndarray:
    """Recorte claro com 6 cordas horizontais e algarismos que interrompem as linhas."""
    img = np.full((8 * passo, largura, 3), 250, np.uint8)
    for i in range(6):
        y = round((1.5 + i) * passo)
        cv2.line(img, (0, y), (largura, y), (0, 0, 0), 1)
        for x in range(40, largura - 40, 70):
            cv2.rectangle(img, (x, y - 7), (x + 9, y + 7), (250, 250, 250), -1)
            cv2.putText(
                img, "3", (x, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1
            )
    return img


def _braco(largura: int = 800, passo: int = 20) -> np.ndarray:
    """Recorte claro com 6 cordas inclinadas (braço visto na diagonal) e trastes."""
    img = np.full((8 * passo, largura, 3), 250, np.uint8)
    for i in range(6):
        y = round((1.5 + i) * passo)
        cv2.line(img, (0, y - 60), (largura, y + 60), (0, 0, 0), 1)
    for x in range(0, largura, 55):
        cv2.line(img, (x, 0), (x + 20, 8 * passo), (0, 0, 0), 2)
    return img


def test_tab_tem_as_seis_cordas_continuas() -> None:
    assert painel.cordas_continuas(_tab(), 20.0) == 6


def test_braco_diagonal_fica_abaixo_do_minimo() -> None:
    assert painel.cordas_continuas(_braco(), 20.0) < painel.MIN_CORDAS_CONTINUAS


def test_recorte_vazio_nao_tem_cordas() -> None:
    assert painel.cordas_continuas(np.zeros((0, 0, 3), np.uint8), 20.0) == 0


def test_minimo_fica_entre_o_braco_e_a_tab_medidos() -> None:
    # 0-1 no braço diagonal, 6 a 13 na TAB (134 caixas do gabarito)
    assert 1 < painel.MIN_CORDAS_CONTINUAS <= 6


def test_painel_claro_continua_achando_a_tab_horizontal() -> None:
    quadro = np.full((1080, 1920, 3), 20, np.uint8)
    quadro[900:1060, :] = _tab(1920, 20)
    caixa = telas.painel_do_quadro(quadro)
    assert caixa is not None
    assert caixa[1] > 800


def test_escolher_acha_a_tab_horizontal_embaixo() -> None:
    quadro = np.full((1080, 1920, 3), 20, np.uint8)
    quadro[900:1060, :] = _tab(1920, 20)
    cand = painel.escolher(quadro)
    assert cand is not None
    assert cand.y0 + min(cand.grade.linhas_y) > 800
    assert painel.e_tablatura(cand)


def test_escolher_ou_mascara_nao_muda_quando_escolher_acha() -> None:
    quadro = np.full((1080, 1920, 3), 20, np.uint8)
    quadro[900:1060, :] = _tab(1920, 20)
    a = painel.escolher(quadro)
    b = painel.escolher_ou_mascara(quadro)
    assert a is not None and b is not None
    assert (a.x0, a.y0, a.y1) == (b.x0, b.y0, b.y1)
