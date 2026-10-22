"""Quadros inteiros do South American Music em instantes das páginas, para olhar."""

import glob

import cv2
import numpy as np

from tab import leitor

V = "/acervo/guitar dell ́arte/south american music (easy), guitar tutorial with sheet and tab.mp4"
ts = [32.0, 50.0, 80.0, 100.0, 170.0, 182.0]
imgs = []
for t in ts:
    q = leitor.quadro_em(V, t)
    q = cv2.resize(q, (960, 540))
    cv2.putText(q, f"t={t}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    imgs.append(q)
linhas = [np.hstack(imgs[i : i + 2]) for i in range(0, 6, 2)]
cv2.imwrite("data/saida/fase8/olhar/south_american.jpg", np.vstack(linhas))
