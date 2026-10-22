"""Folhas (4 x 3) com os recortes das regiões soltas, na ordem dos nomes."""
from pathlib import Path

import cv2
import numpy as np

P = Path("/app/data/saida/tablatura/t84/passe_ataque/regioes_soltas")
ims = []
for f in sorted(P.glob("t*.jpg"), key=lambda f: (int(f.stem.split("-")[0][1:]), int(f.stem.split("r")[-1]))):
    im = cv2.imread(str(f)); s = 420 / im.shape[1]
    im = cv2.resize(im, (420, int(im.shape[0] * s)))
    can = np.full((330, 420, 3), 255, np.uint8); h = min(330, im.shape[0]); can[:h] = im[:h]
    cv2.rectangle(can, (0, 0), (419, 329), (0, 0, 0), 1); ims.append(can)
for k in range(0, len(ims), 12):
    g = ims[k:k + 12] + [np.full((330, 420, 3), 255, np.uint8)] * (12 - len(ims[k:k + 12]))
    folha = np.vstack([np.hstack(g[i:i + 4]) for i in range(0, 12, 4)])
    cv2.imwrite(str(P.parent / f"folha_soltas_{k // 12 + 1}.jpg"), folha)
print(len(ims))
