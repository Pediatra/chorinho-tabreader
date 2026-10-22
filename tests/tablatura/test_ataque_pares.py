"""Testes do pré-rótulo do ataque por par (rodada 0201)."""

import cv2
import numpy as np

from tab.tablatura.ataque.pares import mascara_de_tinta, pares_da_tela, tinta_entre


def _nota(corda: int, x: float, casa: str = "3") -> dict:
    return {"corda": corda, "x_centro_quadro": x, "casa": casa, "_corda_par": corda}


def test_pares_so_da_mesma_corda_e_perto() -> None:
    notas = [_nota(1, 100), _nota(2, 110), _nota(1, 140), _nota(1, 900)]
    assert pares_da_tela(notas, 20.0) == [(0, 2)]


def _tela_com_arco(arco: bool) -> np.ndarray:
    img = np.full((200, 400), 255, np.uint8)
    cv2.line(img, (0, 100), (399, 100), 0, 2)  # corda
    cv2.line(img, (300, 40), (300, 160), 0, 2)  # barra de compasso
    if arco:
        cv2.ellipse(img, (200, 80), (60, 15), 0, 180, 360, 0, 2)
    return img


def test_tinta_ve_o_arco_e_ignora_corda_e_barra() -> None:
    notas = [_nota(1, 140), _nota(1, 260)]
    args = (notas, 0, 1, 100.0, 40.0, (0.0, 0.0), 1.0)
    com, ext_com = tinta_entre(mascara_de_tinta(_tela_com_arco(True)), *args)
    sem, _ = tinta_entre(mascara_de_tinta(_tela_com_arco(False)), *args)
    assert com > 0.05
    assert ext_com > 0.6
    assert sem == 0.0
