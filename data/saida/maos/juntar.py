"""Rascunho: junta jpgs de uma pasta em folhas 2 colunas x 4 linhas."""
import sys
from pathlib import Path
import cv2
import numpy as np
pasta, saida = Path(sys.argv[1]), Path(sys.argv[2])
arqs = sorted(pasta.glob("*.jpg"))
L = 640
for k in range(0, len(arqs), 8):
    cels = []
    for a in arqs[k:k + 8]:
        im = cv2.imread(str(a))
        im = cv2.resize(im, (L, round(im.shape[0] * L / im.shape[1])))
        c = np.zeros((480, L, 3), np.uint8)
        c[: min(480, im.shape[0])] = im[:480]
        cels.append(c)
    while len(cels) % 2:
        cels.append(np.zeros_like(cels[0]))
    linhas = [np.hstack(cels[i:i + 2]) for i in range(0, len(cels), 2)]
    cv2.imwrite(f"{saida}_{k // 8}.jpg", np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 85])
