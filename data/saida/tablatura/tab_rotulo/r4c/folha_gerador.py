"""R4c: folha do gerador, 6 sistemas de cada variante nova (traço, slide curto, arco raso), com o rótulo marcado.

Nota com técnica sem ataque: sublinhado vermelho e o nome da técnica. Uso (container):
env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4c/folha_gerador.py
"""

import random

import cv2
import numpy as np

from tab import caminhos, sintetico_sistema as G
from tab.detector_tab import FONTES_TREINO

SEM = {"h", "p", "/", "\\", "lig", "orn", "enfeite"}
VARIANTES = ["traco", "slide_curto", "arco_raso"]
fontes = FONTES_TREINO
achados = {v: [] for v in VARIANTES}
semente = 0
while any(len(v) < 6 for v in achados.values()) and semente < 5000:
    img, info = G.gerar_sistema(random.Random(semente), fontes)
    var = set(info["variantes"])
    for v in VARIANTES:
        if v in var and len(achados[v]) < 6:
            achados[v].append((semente, img, info))
            break
    semente += 1
paineis = []
for v in VARIANTES:
    for semente, img, info in achados[v]:
        im = img.copy()
        for n in info["notas"]:
            if n["tecnica"] in SEM:
                x0, y0, x1, y1 = n["caixa"]
                cv2.line(im, (x0, y1 + 2), (x1, y1 + 2), (0, 0, 255), 2)
                cv2.putText(im, n["tecnica"], (x0, y1 + 14), cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, (0, 0, 255), 1)
        h = 220
        im = cv2.resize(im, (int(im.shape[1] * h / im.shape[0]), h))
        im = im[:, :900] if im.shape[1] > 900 else np.pad(
            im, ((0, 0), (0, 900 - im.shape[1]), (0, 0)), constant_values=255)
        faixa = np.full((20, 900, 3), 230, np.uint8)
        cv2.putText(faixa, f"{v}  semente {semente}", (4, 15), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (0, 0, 0), 1)
        paineis.append(np.vstack([faixa, im]))
saida = caminhos.TAB_ROTULO / "r4c"
for k in range(0, len(paineis), 6):
    bloco = paineis[k:k + 6]
    while len(bloco) % 2:
        bloco.append(np.full_like(bloco[0], 255))
    grade = np.vstack([np.hstack(bloco[r:r + 2]) for r in range(0, len(bloco), 2)])
    cv2.imwrite(str(saida / f"folha_gerador_{k // 6 + 1}.png"), grade)
print({v: [s for s, _, _ in a] for v, a in achados.items()})
