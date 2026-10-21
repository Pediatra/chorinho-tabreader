"""Desenha a caixa do detector num quadro para olhar (Fase 7.1)."""
import sys

import cv2

from tab import leitor, telas
from tab.caminhos import acervo

video, t, saida = sys.argv[1], float(sys.argv[2]), sys.argv[3]
q = leitor.quadro_em(str(acervo() / video), t)
rect = telas.painel_do_quadro(q)
print("rect", rect)
img = q.copy()
if rect is not None:
    cv2.rectangle(img, (rect[0], rect[1]), (rect[2], rect[3]), (0, 0, 255), 6)
cv2.imwrite(saida, cv2.resize(img, (1110, int(1110 * img.shape[0] / img.shape[1]))))
