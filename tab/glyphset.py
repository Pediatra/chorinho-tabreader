"""Inventário de glifos de tablatura: extrai, filtra lixo e agrupa por forma.

Pergunta que este script responde: os algarismos de tablatura, entre canais
diferentes e tamanhos diferentes, formam um alfabeto pequeno e reaproveitável?
Se sim, um classificador minúsculo (ou banco de templates) resolve, e um VLM de
bilhões de parâmetros é desperdício.

Uso:
    python -m tab.glyphset --saida data/saida/insp/glifos --montagem data/saida/insp/clus.png
"""

from __future__ import annotations

import argparse
import glob
import json
import os

import cv2
import numpy as np

from .caminhos import SAIDA
from .tabseg import segmentar

NORM_W, NORM_H = 16, 24  # alvo de normalização (mantém proporção, depois padding)


def normalizar(crop: np.ndarray) -> np.ndarray | None:
    """Recorta a tinta, escala por altura e centraliza — invariante de escala/posição."""
    if crop.size == 0:
        return None
    if crop.ndim == 3:
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    tinta = crop < 128 if crop.mean() > 127 else crop > 127
    if tinta.sum() < 6:
        return None
    ys, xs = np.where(tinta)
    c = tinta[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    h, w = c.shape
    escala = (NORM_H - 2) / h
    nw = max(1, min(NORM_W - 2, round(w * escala)))
    r = cv2.resize(
        c.astype(np.uint8) * 255, (nw, NORM_H - 2), interpolation=cv2.INTER_AREA
    )
    out = np.zeros((NORM_H, NORM_W), np.uint8)
    x0 = (NORM_W - nw) // 2
    out[1 : NORM_H - 1, x0 : x0 + nw] = r
    return out


def aparencia_vetor(g: np.ndarray) -> np.ndarray:
    v = g.astype(np.float32).ravel()
    n = np.linalg.norm(v)
    return v / n if n else v


def montar(
    itens: list[tuple[np.ndarray, str]], cols: int = 20, escala: int = 3
) -> np.ndarray:
    h, w = NORM_H * escala, NORM_W * escala
    linhas = []
    for i in range(0, len(itens), cols):
        fatia = itens[i : i + cols]
        linha = np.full((h + 14, (w + 8) * cols), 255, np.uint8)
        for j, (img, rotulo) in enumerate(fatia):
            big = cv2.resize(255 - img, (w, h), interpolation=cv2.INTER_NEAREST)
            x = j * (w + 8) + 4
            linha[0:h, x : x + w] = big
            cv2.putText(
                linha, rotulo[:3], (x, h + 12), cv2.FONT_HERSHEY_PLAIN, 0.8, 0, 1
            )
        linhas.append(linha)
    return np.vstack(linhas) if linhas else np.zeros((1, 1), np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--padrao", default="parts/*/*/linha_*_tablatura.png")
    ap.add_argument("--saida", default=str(SAIDA / "insp" / "glifos"))
    ap.add_argument("--montagem", default=str(SAIDA / "insp" / "clusters.png"))
    ap.add_argument(
        "--montagem-glifos", default=str(SAIDA / "insp" / "amostra_glifos.png")
    )
    ap.add_argument(
        "--limiar", type=float, default=0.10, help="distância de cosseno p/ agrupar"
    )
    ap.add_argument("--max-por-clipe", type=int, default=400)
    args = ap.parse_args()
    os.makedirs(args.saida, exist_ok=True)

    arquivos = sorted(glob.glob(args.padrao))
    amostras: list[dict] = []
    lixo = 0
    for p in arquivos:
        clip = os.path.basename(os.path.dirname(p))
        img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        g = segmentar(img)
        if len(g.linhas_y) != 6:
            continue
        passo = float(np.median(np.diff(g.linhas_y)))
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        n = 0
        for gl in g.glifos:
            if n >= args.max_por_clipe:
                break
            h = gl.y1 - gl.y0
            w = gl.x1 - gl.x0
            # lixo: fragmento de corda (chato e largo) ou bolinha de ruído
            if h < 0.35 * passo and w > 0.45 * passo:
                lixo += 1
                continue
            if h < 0.25 * passo or w < 0.10 * passo:
                lixo += 1
                continue
            crop = gray[max(0, gl.y0 - 1) : gl.y1 + 1, max(0, gl.x0 - 1) : gl.x1 + 1]
            norm = normalizar(crop)
            if norm is None:
                lixo += 1
                continue
            amostras.append(
                {
                    "clip": clip,
                    "corda": gl.corda,
                    "coluna": gl.coluna,
                    "passo": passo,
                    "x": gl.x0,
                    "norm": norm,
                }
            )
            n += 1

    print(
        f"linhas de tablatura: {len(arquivos)}  glifos válidos: {len(amostras)}  descartados: {lixo}"
    )

    # agrupamento guloso por similaridade de cosseno (alfabeto deve ser minúsculo)
    vetores = np.stack([aparencia_vetor(a["norm"]) for a in amostras])
    clusters: list[dict] = []
    for i, v in enumerate(vetores):
        if not clusters:
            clusters.append({"soma": v.copy(), "n": 1, "ids": [i]})
            continue
        sims = np.array(
            [float(v @ (c["soma"] / np.linalg.norm(c["soma"]))) for c in clusters]
        )
        k = int(np.argmax(sims))
        if sims[k] >= 1.0 - args.limiar:
            c = clusters[k]
            c["soma"] += v
            c["n"] += 1
            c["ids"].append(i)
        else:
            clusters.append({"soma": v.copy(), "n": 1, "ids": [i]})
    clusters.sort(key=lambda c: -c["n"])
    print(f"clusters de forma: {len(clusters)} (limiar de distância {args.limiar})")

    # pureza: um cluster deve vir de UM canal (o mesmo algarismo muda de forma entre canais)
    for c in clusters:
        canais = {}
        for i in c["ids"]:
            canais[amostras[i]["clip"]] = canais.get(amostras[i]["clip"], 0) + 1
        c["canais"] = canais

    medoides = []
    for c in clusters:
        melhor, melhor_d = None, -1
        media = c["soma"] / np.linalg.norm(c["soma"])
        for i in c["ids"][: min(len(c["ids"]), 60)]:
            d = float(vetores[i] @ media)
            if d > melhor_d:
                melhor, melhor_d = i, d
        medoides.append((amostras[melhor]["norm"], str(c["n"])))
    cv2.imwrite(args.montagem, montar(medoides[: min(len(medoides), 120)]))

    amostra_vis = [(a["norm"], a["clip"][:3]) for a in amostras[:400]]
    cv2.imwrite(args.montagem_glifos, montar(amostra_vis, cols=25))

    with open(os.path.join(args.saida, "clusters.json"), "w") as fh:
        json.dump(
            [
                {"n": c["n"], "canais": c["canais"], "ids": c["ids"][:200]}
                for c in clusters
            ],
            fh,
            indent=1,
        )
    multi = sum(1 for c in clusters if len(c["canais"]) > 1)
    print(f"clusters presentes em mais de um canal: {multi}/{len(clusters)}")
    print(
        "top-12 clusters (tamanho, nº de canais):",
        [(c["n"], len(c["canais"])) for c in clusters[:12]],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
