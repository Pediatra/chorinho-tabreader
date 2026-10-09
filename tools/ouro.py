"""Monta amostras para GABARITO VERIFICADO a partir do acervo real.

Para cada (vídeo, instante): extrai o quadro, acha a grade da tablatura, recorta a
região da TAB ampliada (para leitura humana) e grava a segmentação automática
(corda, x, caixa de cada glifo). O rótulo (a casa) é preenchido à mão depois.

Uso:
    python tools/ouro.py --saida /tmp/ouro --n 6
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tabseg import segmentar  # noqa: E402
from inventario import ler_quadro, FAIXAS  # noqa: E402

RAIZ = "/run/media/gabriel/3014CD4714CD1130/chorinho"


def melhor_faixa(frame: np.ndarray):
    melhor = None
    for nome, y0, y1 in FAIXAS:
        y1 = min(y1, frame.shape[0])
        if y1 - y0 < 60:
            continue
        roi = frame[y0:y1, :]
        try:
            g = segmentar(roi)
        except Exception:
            continue
        if len(g.linhas_y) != 6 or not g.glifos:
            continue
        score = (g.glifos_centrados, len(g.glifos))
        if melhor is None or score > melhor[0]:
            melhor = (score, nome, y0, roi, g)
    return melhor


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=RAIZ)
    ap.add_argument("--saida", default="/tmp/ouro")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--por-canal", type=int, default=1)
    ap.add_argument("--instante", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    os.makedirs(args.saida, exist_ok=True)
    rng = random.Random(args.seed)

    canais = [d for d in sorted(glob.glob(os.path.join(args.raiz, "*")))
              if os.path.isdir(d) and os.path.basename(d) != "derived"]
    feitos = 0
    indice = []
    for canal in canais:
        if feitos >= args.n:
            break
        vids = sorted(glob.glob(os.path.join(canal, "**", "*.mp4"), recursive=True))
        if not vids:
            continue
        sucessos_canal = 0
        for v in rng.sample(vids, min(len(vids), 12)):
            if feitos >= args.n or sucessos_canal >= args.por_canal:
                break
            frame, via = ler_quadro(v, args.instante)
            if frame is None:
                continue
            m = melhor_faixa(frame)
            if m is None:
                continue
            score, faixa, y0, roi, g = m
            nome = f"{feitos:02d}_{os.path.basename(canal)[:14].strip()}"
            pasta = os.path.join(args.saida, nome)
            os.makedirs(pasta, exist_ok=True)
            # recorte da TAB, 2x, para leitura humana
            l0 = max(0, g.linhas_y[0] - int(1.2 * g.passo))
            l1 = min(roi.shape[0], g.linhas_y[-1] + int(1.2 * g.passo))
            crop = roi[l0:l1, :]
            crop2 = cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            cv2.imwrite(os.path.join(pasta, "crop2x.png"), crop2)
            glifos = []
            for gl in g.glifos:
                glifos.append({"corda": int(gl.corda), "x0": int(gl.x0), "x1": int(gl.x1),
                               "y0": int(gl.y0 - l0), "y1": int(gl.y1 - l0),
                               "coluna": int(gl.coluna), "casa": None})
            auto = {"video": os.path.relpath(v, args.raiz), "instante_frac": args.instante,
                    "via": via, "faixa": faixa, "y0_roi": l0, "passo": round(g.passo, 2),
                    "linhas_y": g.linhas_y, "glifos": glifos}
            with open(os.path.join(pasta, "auto.json"), "w") as fh:
                json.dump(auto, fh, ensure_ascii=False, indent=1)
            indice.append({"amostra": nome, "video": auto["video"], "faixa": faixa,
                           "passo": auto["passo"], "n_glifos": len(glifos)})
            print(f"{nome}: {auto['video'][:56]} | faixa={faixa} passo={auto['passo']} "
                  f"glifos={len(glifos)}", flush=True)
            feitos += 1
            sucessos_canal += 1
    with open(os.path.join(args.saida, "indice.json"), "w") as fh:
        json.dump(indice, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
