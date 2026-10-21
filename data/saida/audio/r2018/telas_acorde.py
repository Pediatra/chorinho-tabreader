"""Rodada 2018 (candidatas): quadro da tela com as colunas de 5-6 notas marcadas."""

import collections
import json
import subprocess
import sys

import cv2
import numpy as np

prod, tela_id, saida = sys.argv[1], int(sys.argv[2]), sys.argv[3]
d = json.load(open(prod))
video = d["video"]["arquivo"] if isinstance(d["video"], dict) else d["video"]
caminho = video if video.startswith("/") else "/acervo/" + video
tela = next(t for t in d["telas"] if t["id"] == tela_id)
ex = tela["exibicoes"][0]
t = ex["t0"] + 0.3 * (ex["t1"] - ex["t0"])
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", caminho,
                "-frames:v", "1", "/tmp/q.png"], check=True)
im = cv2.imread("/tmp/q.png")
x0, y0, x1, y1 = tela["painel"]
m = 20
y0, y1 = max(0, y0 - m), min(im.shape[0], y1 + m)
cols = collections.defaultdict(list)
for n in d["notas"]:
    if n["tela"] == tela_id:
        cols[n["coluna"]].append(n)
rec = im[y0:y1, :].copy()
h, w = rec.shape[:2]
faixa = 6 * 26 + 30
out = np.full((h + faixa, w, 3), 255, np.uint8)
out[:h] = rec
for c, ns in cols.items():
    x = int(np.mean([n["x_centro_quadro"] for n in ns]))
    cheio = len({n["corda"] for n in ns}) >= 5
    cor = (0, 0, 230) if cheio else (150, 150, 150)
    if cheio:
        cv2.rectangle(out, (x - 18, 2), (x + 18, h - 2), cor, 2)
    for n in ns:
        cv2.putText(out, str(n["casa"]), (x - 8, h + 26 + (n["corda"] - 1) * 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2 if cheio else 1)
cv2.putText(out, f"leitura do produto  t={t:.1f}s  tela {tela_id}", (5, h + 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
cv2.imwrite(saida, out)
print(saida, t, sum(1 for ns in cols.values() if len({n['corda'] for n in ns}) >= 5))
