"""Painel escuro: a extensão mede só o tracejado claro, sem bolinhas nem diagrama.

Quadro sintético, sem acervo: à esquerda, bolinhas laranja com letra branca (as letras
das cordas); no meio, seis linhas claras tracejadas; à direita, um "diagrama" de acorde
(grade de linhas horizontais e verticais, nas mesmas alturas das cordas, o pior caso).
A extensão tem de cobrir só o tracejado.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.tablatura.leitura import tabseg

ALTURA = 240
LARGURA = 1920
CORDAS = [30, 66, 102, 138, 174, 210]
X_BOLINHAS = (20, 70)  # x das bolinhas, à esquerda
X_TRACEJADO = (110, 1500)  # trecho do tracejado claro
X_DIAGRAMA = (1650, 1900)  # grade do diagrama, à direita


def _quadro_escuro() -> np.ndarray:
    """Quadro BGR com bolinhas, tracejado claro e diagrama em grade.

    Returns:
        Quadro sintético 240x1920 em BGR.
    """
    quadro = np.full((ALTURA, LARGURA, 3), 26, np.uint8)  # fundo quase preto
    for y in CORDAS:  # bolinha laranja com letra branca em cada corda
        cv2.circle(quadro, (X_BOLINHAS[0] + 12, y), 12, (0, 140, 255), -1)
        cv2.putText(
            quadro,
            "e",
            (X_BOLINHAS[0] + 6, y + 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
    for y in CORDAS:  # tracejado claro: 12 px acesos, 22 apagados (buracos de 22 px)
        for x in range(X_TRACEJADO[0], X_TRACEJADO[1], 34):
            quadro[y - 1 : y + 2, x : x + 12] = 150
    # diagrama de acorde: grade cinza-clara, cordas e trastes
    x0, x1 = X_DIAGRAMA
    for y in CORDAS:
        quadro[y - 1 : y + 2, x0:x1] = 150
    for x in range(x0, x1 + 1, 50):
        quadro[CORDAS[0] : CORDAS[-1] + 1, x - 1 : x + 2] = 150
    return quadro


def test_extensao_cobre_so_o_tracejado() -> None:
    """A extensão começa depois das bolinhas e para no fim do tracejado."""
    quadro = _quadro_escuro()
    x0, x1 = tabseg.extensao_das_linhas_claras(quadro, CORDAS)
    assert X_BOLINHAS[1] <= x0 <= X_TRACEJADO[0] + 40
    assert X_TRACEJADO[1] - 20 <= x1 <= X_TRACEJADO[1] + 20


def test_buraco_do_tracejado_nao_quebra_o_trecho() -> None:
    """Buracos de 22 px no tracejado não separam o trecho."""
    quadro = _quadro_escuro()
    x0, x1 = tabseg.extensao_das_linhas_claras(quadro, CORDAS)
    assert x1 - x0 > 1000
    assert x1 < X_DIAGRAMA[0]
