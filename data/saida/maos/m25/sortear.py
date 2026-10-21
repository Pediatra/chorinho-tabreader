"""Sorteio da 1025: treino (4 cliques) e prova (marcação completa), semente 20261025."""

import json
import os
import random
import subprocess

A = "/acervo"
NOVOS = ("gabriel cryslian", "serge kottelat", "yunus guitarist", "ギタロー ⧸ guitarous")
FORA = ("raman korshun",)
N_TREINO, N_PROVA = 9, 6
m11 = {v["arquivo"] for v in json.load(open("data/saida/maos/m11b/chaves.json"))["videos"]}
idx = json.load(open("data/saida/maos/m3b/indice.json"))
m3b = {x["arquivo"] for x in idx.get("quadros", idx)}


def dur(rel):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", os.path.join(A, rel)], capture_output=True, text=True)
    return float(r.stdout.strip())


rng = random.Random(20261025)
treino, prova = [], []
for canal in sorted(os.listdir(A)):
    p = os.path.join(A, canal)
    if not os.path.isdir(p) or canal in FORA:
        continue
    vids = sorted(f"{canal}/{v}" for v in os.listdir(p)
                  if v.lower().endswith((".mp4", ".webm", ".mkv")) and "campanitas" not in v.lower())
    novo = canal in NOVOS
    livres = [v for v in vids if v not in m11 and v not in m3b] or vids
    n = N_PROVA if novo else N_TREINO
    rng.shuffle(livres)
    escolhidos = [livres[i % len(livres)] for i in range(n)]
    for v in escolhidos:
        d = dur(v)
        item = {"arquivo": v, "t": round(rng.uniform(0.15, 0.85) * d, 2)}
        (prova if novo else treino).append(item)
json.dump(treino, open("data/saida/maos/m25/lista_treino.json", "w"), ensure_ascii=False, indent=1)
json.dump(prova, open("data/saida/maos/m25/lista_prova.json", "w"), ensure_ascii=False, indent=1)
print(len(treino), len(prova))
