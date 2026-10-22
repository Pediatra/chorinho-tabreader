import sys

import cv2

from tab.estado import SATURACAO_MARCADOR, LARGURA_MINIMA_MARCADOR
from tab.marcador import detectar_cursor

PASTA = "/app/data/saida/produto"
for nome in ["quadro_tela1_t239.png", "quadro_tela1_t241.png", "quadro_tela1_t250.png"]:
    bgr = cv2.imread(f"{PASTA}/{nome}")
    quadro = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)[297:446, :]
    det = detectar_cursor(quadro, sat_min=SATURACAO_MARCADOR)
    print(nome, "deteccao", det, "largura_min", LARGURA_MINIMA_MARCADOR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat_col = (hsv[297:446, :, 1] >= SATURACAO_MARCADOR).sum(axis=0)
    faixas = [x for x in range(1100, 1260) if sat_col[x] > 40]
    print("   colunas com saturacao alta entre 1100-1260:", faixas[:3], "...", faixas[-3:] if faixas else "")
