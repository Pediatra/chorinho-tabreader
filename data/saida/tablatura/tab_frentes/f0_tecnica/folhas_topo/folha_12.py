import json

import cv2
import numpy as np

F = "/app/data/saida/tab_frentes/f0_tecnica"
rel = json.load(open(F + "/topo.json"))
cort = [l for l in rel["linhas"] if l["classe"] == "cortada"]
cells = []
for l in cort[:12]:
    img = cv2.imread(F + "/" + l["recorte"])
    e = min(4.0, 420 / img.shape[1])
    p = cv2.resize(img, None, fx=e, fy=e)[:260]
    c = np.full((p.shape[0] + 40, 430, 3), 255, np.uint8)
    c[: p.shape[0], 5 : 5 + p.shape[1]] = p
    cv2.putText(c, f"{l['fonte']} t{l['tela']} r{l['indice']} {l['tecnica_dono']}", (5, p.shape[0] + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(c, f"acima {l['acima']} dentro {l['dentro']}", (5, p.shape[0] + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cells.append(c)
rows = []
for i in range(0, len(cells), 2):
    a = cells[i]
    b = cells[i + 1] if i + 1 < len(cells) else np.full_like(a, 255)
    h = max(a.shape[0], b.shape[0])
    a = np.pad(a, ((0, h - a.shape[0]), (0, 0), (0, 0)), constant_values=255)
    b = np.pad(b, ((0, h - b.shape[0]), (0, 0), (0, 0)), constant_values=255)
    rows.append(np.hstack([a, b]))
out = np.vstack(rows)
cv2.imwrite(F + "/folhas_topo/folha_cortadas_12.png", out)
print(out.shape)
