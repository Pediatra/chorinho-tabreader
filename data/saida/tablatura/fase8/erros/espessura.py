"""Espessura das linhas de corda e da linha intrusa, em quadros dos 8 ouros."""
import json, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, "/app")
from tab import painel as P
from tab.tabseg import mascaras_candidatas

def espessura(m, y):
    perfil = m.mean(axis=1)
    alvo = 0.5 * perfil[y]
    a = y
    while a > 0 and perfil[a - 1] >= alvo: a -= 1
    b = y
    while b < len(perfil) - 1 and perfil[b + 1] >= alvo: b += 1
    return b - a + 1

import glob
for f in sorted(glob.glob("/app/data/gold/ouro_video/*.json")):
    o = json.load(open(f))
    if "retrato_brasileiro.json" in f: continue
    for t in [t for t in o["telas"] if t.get("conferida") or "v2" not in f][:3]:
        subprocess.run(["ffmpeg","-loglevel","error","-y","-ss",str(t["quadro_ref_s"]),"-i","/acervo/"+o["video"],"-frames:v","1","/tmp/f.png"],check=True)
        img = cv2.imread("/tmp/f.png")
        c = P.escolher_ou_mascara(img)
        if c is None: print(f.split("/")[-1][:15], t["id"], "sem painel"); continue
        m = mascaras_candidatas(img)[0][1].astype(np.float32)
        ys = [c.y0 + y for y in c.grade.linhas_y]
        print(f.split("/")[-1][:15], t["id"], "passo", round(c.passo,1), "esp", [espessura(m, y) for y in ys])
