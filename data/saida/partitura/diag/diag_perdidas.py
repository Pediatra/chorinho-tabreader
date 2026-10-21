"""Diagnóstico: por que as pautas de N013-N018 (iwaki) foram perdidas."""
import json
import cv2
import numpy as np
from tab import cache
from tab.partitura_pauta import achar_pautas

d = json.load(open("data/saida/partitura/diag/indice_rodada1.json"))
for e in d["negativos"]:
    if e["numero"] not in ("N013", "N014", "N015", "N016", "N017", "N018"):
        continue
    pasta = cache.pasta_do_video(e["chave"], cache.ModoCache())
    q = cache.ler_quadro(cache.caminho_do_quadro(pasta, f"presenca_{e['indice_quadro']:02d}", "png"))
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    m = cv2.adaptiveThreshold(cinza, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 10)
    L = max(40, round(0.04 * q.shape[1]))
    ab = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (L, 1)))
    c = np.count_nonzero(ab, axis=1)
    print(e["numero"], q.shape, "novo:", [p.caixa for p in achar_pautas(q)])
    print("  linhas>=0.05:", [(y, int(c[y])) for y in range(q.shape[0] // 2, q.shape[0]) if c[y] >= 0.05 * q.shape[1]])
    cv2.imwrite(f"data/saida/partitura/diag/{e['numero']}.png", q[q.shape[0] // 2 :, :])
