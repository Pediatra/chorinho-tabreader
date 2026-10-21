"""Recortes do painel da tablatura em volta de colunas nunca acesas (Parte 1). Só leitura."""

import json
import os

import cv2
import numpy as np

from tab.leitor import quadro_em

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
PRODUTO = "data/saida/conserto_v2/mvp.json"
ALINHADO = "data/saida/audio/a2/alinhado_v2_r1.json"
PASTA = "data/saida/audio/a2/v3/recortes"
ALVOS = [(2, 17), (2, 18), (4, 9), (4, 10), (8, 8), (12, 25)]


def main():
    os.makedirs(PASTA, exist_ok=True)
    p = json.load(open(PRODUTO, encoding="utf-8"))
    alin = json.load(open(ALINHADO, encoding="utf-8"))
    telas = {t["id"]: t for t in p["telas"]}
    xs = {}
    for n in p["notas"]:
        xs.setdefault((n["tela"], n["coluna"]), []).append(n["x_centro_quadro"])
    for tela, col in ALVOS:
        t = telas[tela]
        ex_ok = [e for e in alin["exibicoes"] if e["tela"] == tela and e.get("trecho_colunas") and e["trecho_colunas"][0] <= col <= e["trecho_colunas"][1]]
        ex = ex_ok[0]
        idx = ex["exibicao"]
        e_prod = t["exibicoes"][idx]
        meio = (e_prod["t0"] + e_prod["t1"]) / 2
        quadro = quadro_em(VIDEO, meio)
        if quadro is None:
            print("sem quadro", tela, col)
            continue
        x0p, y0p, x1p, y1p = t["painel"]
        xc = float(np.mean(xs[(tela, col)]))
        passo = t["passo"]
        jan = int(6 * passo)
        xa, xb = max(0, int(xc - jan)), min(quadro.shape[1], int(xc + jan))
        recorte = quadro[y0p:y1p, xa:xb].copy()
        cv2.line(recorte, (int(xc - xa), 0), (int(xc - xa), recorte.shape[0] - 1), (0, 255, 255), 1)
        ampl = cv2.resize(recorte, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        cv2.putText(ampl, f"tela {tela} col {col} (exib {idx}, t={meio:.1f}s)", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        caminho = f"{PASTA}/t{tela:02d}_c{col:02d}.png"
        cv2.imwrite(caminho, ampl)
        print("recorte", caminho, "xc", round(xc, 1), "painel", t["painel"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
