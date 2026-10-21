"""Fração de pixels amarelos (cursor de reprodução) por recorte vs. sucesso do Audiveris."""
import json

import cv2

from tab.caminhos import SAIDA

PASTA_SP = SAIDA / "partitura" / "sem_produto"
tot = {}
for pasta in sorted(PASTA_SP.iterdir()):
    execf = pasta / "omr/audiveris/x2_margem/execucao.json"
    if not execf.exists():
        continue
    for r in json.loads(execf.read_text(encoding="utf-8")):
        img = cv2.imread(str(pasta / "omr/audiveris/x2_margem" / r["id"] / "entrada.png"))
        if img is None:
            continue
        b, g, rr = [c.astype(int) for c in cv2.split(img)]
        amarelo = ((rr - b) > 40) & ((g - b) > 40)
        frac = float(amarelo.mean())
        faixa = "com" if frac > 0.05 else "sem"
        k = (faixa, r["ok"])
        tot[k] = tot.get(k, 0) + 1
        if not r["ok"]:
            print(f"FALHA {pasta.name[:20]} {r['id']} amarelo {frac:.2f}")
for k, v in sorted(tot.items()):
    print("faixa", k[0], "ok" if k[1] else "falha", v)
