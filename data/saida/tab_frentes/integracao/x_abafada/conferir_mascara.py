"""Confere a máscara de X do treinar_ft: perda igual sem máscara e desenho sobre o recorte."""

import random
import sys

import cv2
import numpy as np
import torch

sys.path.insert(0, "/app/data/saida/n4")
sys.path.insert(0, "/app")
import treinar_ft as T  # noqa: E402
from tab import detector_tab as D  # noqa: E402

telas = T.carregar_telas((), True)
print("telas", len(telas), "regioes_x", sum(len(t["regioes_x"]) for t in telas))
lg = torch.randn(4, 6, 128)
al = torch.rand(4, 6, 128) * 0.9
al[0, 1, 5] = 1.0
a = float(D.perda_centro(lg, al))
b = float(T.perda_centro_ignorando(lg, al, torch.zeros_like(al)))
print("perda igual sem mascara:", abs(a - b) < 1e-6, a, b)
rng = random.Random(0)
eob = [t for t in telas if t["regioes_x"]]
folha = []
for t in eob[:6]:
    r = T.amostra_real(t, rng)
    img = cv2.cvtColor(np.clip(r[0], 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    if img.max() <= 1:
        img = cv2.cvtColor((r[0] * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    ign = r[5]
    for k in range(6):
        for j in np.flatnonzero(ign[k]):
            x = int(j * D.STRIDE + D.DESLOC)
            y = int(img.shape[0] * (k + 1) / 7)
            cv2.circle(img, (x, y), 2, (0, 0, 255), -1)
        for j in np.flatnonzero(r[1][k] == 1.0):
            x = int(j * D.STRIDE + D.DESLOC)
            y = int(img.shape[0] * (k + 1) / 7)
            cv2.circle(img, (x, y), 4, (0, 200, 0), 1)
    folha.append(img)
    print(t["slug"][:20], t["tela"], "bins ignorados", int(ign.sum()))
cv2.imwrite("/app/data/saida/tab_frentes/integracao/x_abafada/mascara.png", np.vstack(folha))
