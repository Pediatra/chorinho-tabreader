"""Folhas para o dono achar capo nos gabaritos antigos (decisão 1010). Só leitura."""
import json
import cv2
import numpy as np
from pathlib import Path

CONJ = [
    ("m25t", "data/gold/maos/braco_m25_treino.json", "data/saida/maos/m25/treino"),
    ("m25p", "data/gold/maos/braco_m25_prova.json", "data/saida/maos/m25/prova"),
    ("m26", "data/gold/maos/braco_m26.json", "data/saida/maos/m26"),
    ("m27", "data/gold/maos/braco_m27.json", "data/saida/maos/m27"),
    ("m29", "data/gold/maos/braco_m29.json", "data/saida/maos/m29"),
]
W, H = 320, 180
cel = []
lista = []
for nome, ouro, pasta in CONJ:
    g = json.load(open(ouro))["quadros"]
    ix = {i["id"]: i for i in json.load(open(Path(pasta) / "indice.json"))["quadros"]}
    for k in sorted(g):
        r = g[k]
        if r.get("braco") == "nao" or not r.get("corda1") or not r.get("corda6"):
            continue
        im = cv2.imread(str(Path(pasta) / ix[k]["png"]))
        e = ix[k]["largura"] / im.shape[1]
        pts = np.array(r["corda1"] + r["corda6"], float) / e
        x0, y0 = pts.min(0); x1, y1 = pts.max(0)
        px, py = 0.08 * (x1 - x0) + 10, 0.25 * (y1 - y0) + 10
        x0, y0 = int(max(0, x0 - px)), int(max(0, y0 - py))
        x1, y1 = int(min(im.shape[1], x1 + px)), int(min(im.shape[0], y1 + py))
        c = im[y0:y1, x0:x1]
        f = min(W / c.shape[1], H / c.shape[0])
        c = cv2.resize(c, (max(1, int(c.shape[1] * f)), max(1, int(c.shape[0] * f))))
        tela = np.full((H, W, 3), 40, np.uint8)
        tela[: c.shape[0], : c.shape[1]] = c
        rot = f"{nome}:{k}"
        cv2.putText(tela, rot, (4, 18), 0, 0.55, (0, 0, 0), 4)
        cv2.putText(tela, rot, (4, 18), 0, 0.55, (0, 255, 255), 1)
        cel.append(tela)
        lista.append({"chave": rot, "arquivo": ix[k]["arquivo"]})
COLS, LINHAS = 6, 10
por = COLS * LINHAS
for n in range(0, len(cel), por):
    bloco = cel[n : n + por]
    bloco += [np.zeros((H, W, 3), np.uint8)] * (por - len(bloco))
    img = np.vstack([np.hstack(bloco[i : i + COLS]) for i in range(0, por, COLS)])
    cv2.imwrite(f"data/saida/maos/capo_auditoria/folha_{n // por + 1}.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(lista, open("data/saida/maos/capo_auditoria/lista.json", "w"), ensure_ascii=False, indent=1)
print(len(cel), "quadros,", (len(cel) + por - 1) // por, "folhas")
