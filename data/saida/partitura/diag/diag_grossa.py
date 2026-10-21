"""Diagnóstico: pauta sintética de linhas de 5 px."""
import cv2
import numpy as np
from tab import partitura_pauta as pp

img = np.full((1080, 1920, 3), 255, np.uint8)
for k in range(5):
    cv2.line(img, (200, 300 + 20 * k), (1700, 300 + 20 * k), (0, 0, 0), 5)
cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
for k, m in enumerate(pp._mascaras_de_tinta(cinza)):
    ab = pp._abrir(m, 1920)
    c = np.count_nonzero(ab, axis=1)
    print(k, [(y, int(c[y])) for y in range(280, 400) if c[y] > 0])
    print("  linhas", [(l.y, l.espessura, l.forte) for l in pp._linhas_da_abertura(ab, 1920, k == 0)])
