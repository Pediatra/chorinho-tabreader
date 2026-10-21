"""Folhas das miniaturas do cifra club: painel na metade de cima e sem painel."""
import json

import cv2
import numpy as np

B = "/app/data/saida/tab_rotulo/diag/painel_cifra/"
L = [json.loads(linha) for linha in open(B + "medida.jsonl")]
grupos = {
    "cima": [r for r in L if r.get("painel") and r["painel"]["centro_frac"] < 0.5],
    "sem": [r for r in L if not r.get("erro") and r.get("painel") is None],
    "baixo": [r for r in L if r.get("painel") and r["painel"]["centro_frac"] >= 0.5],
}
for nome, rs in grupos.items():
    imgs = []
    for r in rs:
        im = cv2.imread(B + f"{r['k']:03d}.jpg")
        cv2.putText(im, str(r["k"]), (5, 25), 0, 0.8, (0, 0, 255), 2)
        imgs.append(cv2.resize(im, (320, 156)))
    while len(imgs) % 6:
        imgs.append(np.full((156, 320, 3), 255, np.uint8))
    linhas = [np.hstack(imgs[i : i + 6]) for i in range(0, len(imgs), 6)]
    for p in range(0, len(linhas), 7):
        cv2.imwrite(B + f"folha_{nome}_{p // 7 + 1}.jpg", np.vstack(linhas[p : p + 7]))
    print(nome, len(rs))
