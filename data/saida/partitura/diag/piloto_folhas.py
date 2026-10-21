"""Folha de contatos dos contextos de página de cada vídeo do piloto."""
import glob
import os

import cv2
import numpy as np

base = "data/saida/partitura/sem_produto"
for pasta in sorted(glob.glob(f"{base}/*")):
    fs = sorted(glob.glob(f"{pasta}/recortes/contexto_P*.jpg"))
    if not fs:
        continue
    ims = [cv2.resize(cv2.imread(f), (480, 270)) for f in fs]
    for im, f in zip(ims, fs):
        cv2.putText(im, os.path.basename(f)[9:12], (5, 25), 0, 0.9, (0, 0, 255), 2)
    while len(ims) % 5:
        ims.append(np.zeros_like(ims[0]))
    linhas = [np.hstack(ims[i : i + 5]) for i in range(0, len(ims), 5)]
    nome = os.path.basename(pasta)[:12].replace(" ", "_")
    cv2.imwrite(f"data/saida/partitura/diag/piloto_{nome}.jpg", np.vstack(linhas))
