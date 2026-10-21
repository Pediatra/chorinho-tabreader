"""Depuração do limiar de tinta (rodada 0151): barras por limiar de cinza, quadro de 63,0 s."""

import numpy as np
import cv2

from tab import leitor
from tab import rolagem_saltos as rs

V = "/acervo/mr. tabs/blind melon - no rain - guitar tab ｜ lesson ｜ cover ｜ tutorial ｜ lead only.mp4"

qs = list(leitor.quadros(V, 63.0, 63.2, 10, recorte_y=(807, 1019)))
t, q = qs[0]
cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
print("percentis de cinza (sem mascara):", np.percentile(cinza, [1, 5, 10, 25, 50]).tolist())
m = rs.mascara(q)
g = rs.cinza_mascarado(q, 0, q.shape[1], m)
for lim in (100, 150, 200, 230):
    rs.ESCURO = lim
    xs = rs.barras(g)
    print("limite", lim, "barras", len(xs), [round(x) for x in xs[:12]])
