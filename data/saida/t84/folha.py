"""Folha com as 30 telas da T8.4 (para olhar antes de pedir ao dono)."""
import json

import cv2
import numpy as np

B = "/app/data/saida/t84/ferramenta/"
pre = json.load(open(B + "pre.json"))
linhas = []
for t in pre["telas"]:
    im = cv2.imread(B + t["arquivo"])
    s = 900 / im.shape[1]
    im = cv2.resize(im, None, fx=s, fy=s)
    im = im[: min(im.shape[0], 260)]
    pad = np.full((300, 900, 3), 255, np.uint8)
    pad[40 : 40 + im.shape[0]] = im
    cv2.putText(pad, f"tela {t['id']}  notas {len(t['notas'])}", (5, 28), 0, 0.9, (0, 0, 255), 2)
    linhas.append(pad)
for k in range(0, len(linhas), 10):
    cv2.imwrite(B + f"../folha_{k // 10 + 1}.png", np.vstack(linhas[k : k + 10]))
