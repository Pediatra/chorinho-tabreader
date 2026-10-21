"""Diagnóstico: linhas achadas perto das pautas falsas (P004, P013, P020)."""
import json
import cv2
import numpy as np
from tab import cache
from tab.partitura_pauta import _linhas_da_mascara, _mascaras_de_tinta, achar_pautas

d = json.load(open("data/saida/partitura/p0/folhas/indice.json"))
for e in d["positivos"]:
    if e["numero"] not in ("P004", "P013", "P020"):
        continue
    pasta = cache.pasta_do_video(e["chave"], cache.ModoCache())
    q = cache.ler_quadro(cache.caminho_do_quadro(pasta, f"presenca_{e['indice_quadro']:02d}", "png"))
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    print(e["numero"], q.shape, [p.caixa for p in achar_pautas(q)])
    for k, m in enumerate(_mascaras_de_tinta(cinza)):
        ls = [l for l in _linhas_da_mascara(m, q.shape[1]) if 700 < l.y < 1080]
        print("  mascara", k, [(l.y, l.x0, l.x1, "F" if l.forte else "f") for l in ls])
        # perfil cru das linhas de pixel, sem descartar espessura
        nuc = cv2.getStructuringElement(cv2.MORPH_RECT, (77, 1))
        ab = cv2.morphologyEx(m, cv2.MORPH_OPEN, nuc)
        c = np.count_nonzero(ab, axis=1)
        print("  perfil>=0.05:", [(y, int(c[y])) for y in range(700, q.shape[0]) if c[y] >= 0.05 * q.shape[1]])
    x0, y0, x1, y1 = e["pautas"][0]
    cv2.imwrite(f"data/saida/partitura/diag/{e['numero']}.png", q[max(0, y0 - 80):min(q.shape[0], y1 + 80), :])
