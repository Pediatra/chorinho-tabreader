"""Folhas das trocas da 0213 (vermelho = antigo, verde = novo)."""
import glob

import cv2
import numpy as np

B = "/app/data/saida/tab_rotulo/diag/painel_0213/"
for nome in ("desenho", "prova", "regressao"):
    arqs = sorted(glob.glob(B + f"{nome}_*.jpg"))
    imgs = []
    for a in arqs:
        im = cv2.resize(cv2.imread(a), (400, 195))
        cv2.putText(im, a.rsplit("_", 1)[-1][:-4], (5, 22), 0, 0.7, (0, 255, 255), 2)
        imgs.append(im)
    while len(imgs) % 5:
        imgs.append(np.full((195, 400, 3), 255, np.uint8))
    linhas = [np.hstack(imgs[i : i + 5]) for i in range(0, len(imgs), 5)]
    cv2.imwrite(B + f"folha_{nome}.jpg", np.vstack(linhas))
    print(nome, len(arqs))
