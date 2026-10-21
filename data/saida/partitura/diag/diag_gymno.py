"""Diagnóstico: Gymnopédie t=9.5, perfil de linhas perto da pauta."""
import cv2
import numpy as np
from tab import leitor
from tab.caminhos import acervo
from tab.partitura_pauta import achar_pautas

v = str(acervo() / "robert lunn/gymnopédie no.1 (erik satie) - includes sheet music⧸tab - classical guitar.mp4")
q = leitor.quadro_em(v, 9.5)
cv2.imwrite("data/saida/partitura/diag/gymno_9.5.png", q)
cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
print(q.shape, achar_pautas(q))
for k, inv in enumerate([False, True]):
    g = cv2.bitwise_not(cinza) if inv else cinza
    m = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 10)
    ab = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (77, 1)))
    c = np.count_nonzero(ab, axis=1)
    print("mascara", k, [(y, int(c[y])) for y in range(q.shape[0]) if c[y] >= 96])
