"""Rascunho M0: desenha as detecções do censo de mãos para OLHAR (1 quadro por vídeo).

Uso: python data/saida/maos/folha.py <censo.jsonl> <prefixo_saida> [n_videos] [semente]
Mão L = verde, R = magenta, mão dentro da TAB = cinza, rosto = ciano, TAB = amarelo.
Grava também <prefixo>.json com o manifesto (vídeo, quadro, o que o censo afirmou).
"""

import hashlib
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "/app")
from tab.maos_tabela import resumo_do_quadro  # noqa: E402

CACHE = Path("/cache/png")
COR = {"L": (0, 220, 0), "R": (255, 0, 255)}


def pasta(chave: str) -> Path:
    return CACHE / hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]


def main() -> None:
    entrada, prefixo = Path(sys.argv[1]), sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    rng = random.Random(int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    regs = [json.loads(linha) for linha in entrada.read_text().splitlines()]
    regs.sort(key=lambda r: r["chave"])
    if n < len(regs):
        regs = rng.sample(regs, n)
    regs.sort(key=lambda r: (r["canal"], r["chave"]))
    cels, manifesto = [], []
    for k, r in enumerate(regs, 1):
        q = rng.choice(r["quadros"])
        img = cv2.imread(str(pasta(r.get("chave_real", r["chave"])) / f"presenca_{q['i']:02d}.png"))
        esp = max(2, img.shape[1] // 400)
        if q["rect"]:
            x0, y0, x1, y1 = q["rect"]
            cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 255), esp)
        for f in q["rostos"]:
            x0, y0, x1, y1 = f["caixa"]
            cv2.rectangle(img, (x0, y0), (x1, y1), (255, 255, 0), esp)
        for m in q["maos"]:
            cor = (128, 128, 128) if m["na_tab"] else COR[m["lado"]]
            for p in m["pts"]:
                cv2.circle(img, tuple(p), esp * 2, cor, -1)
            x0, y0, x1, y1 = m["caixa"]
            cv2.rectangle(img, (x0, y0), (x1, y1), cor, esp)
            cv2.putText(img, m["lado"], (x0, max(30, y0 - 8)), 0, esp * 0.8, cor, esp)
        h, w = img.shape[:2]
        img = cv2.resize(img, (640, round(h * 640 / w)))
        if img.shape[0] > 480:
            img = cv2.resize(img, (round(img.shape[1] * 480 / img.shape[0]), 480))
        cel = np.zeros((480, 640, 3), np.uint8)
        cel[: img.shape[0], : img.shape[1]] = img
        rq = resumo_do_quadro(q)
        afirma = f"E={int(rq['esquerda'])} D={int(rq['direita'])} {rq['vista']}"
        rot = f"{k:02d} {r['canal'][:14]} | {afirma}"
        cv2.putText(cel, rot, (5, 470), 0, 0.6, (0, 0, 0), 4)
        cv2.putText(cel, rot, (5, 470), 0, 0.6, (255, 255, 255), 1)
        cels.append(cel)
        manifesto.append({"n": k, "canal": r["canal"], "arquivo": r["arquivo"],
                          "quadro": q["i"], "t": q["t"], "afirma": rq})
    for f in range(0, len(cels), 10):
        bloco = cels[f:f + 10]
        while len(bloco) % 2:
            bloco.append(np.zeros_like(bloco[0]))
        linhas = [np.hstack(bloco[i:i + 2]) for i in range(0, len(bloco), 2)]
        cv2.imwrite(f"{prefixo}_{f // 10 + 1}.jpg", np.vstack(linhas),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
    Path(f"{prefixo}.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
