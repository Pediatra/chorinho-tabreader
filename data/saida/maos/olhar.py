"""Rascunho (M0): folha de contato por canal, a partir do cache de quadros, para OLHAR.

Por canal ativo: até 6 vídeos sorteados (semente fixa), 3 quadros de presença cada
(0,05 / 0,50 / 0,95 da duração). Saída: data/saida/maos/olhar/<canal>.jpg.
"""

import hashlib
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

CENSO = Path("data/saida/censo/censo_cache.jsonl")
CACHE = Path("/cache/png")
SAIDA = Path("data/saida/maos/olhar")
FORA = {"violaodecria", "tv cifras"}
QUADROS = (0, 5, 11)
LARG = 360


def pasta(chave: str) -> Path:
    return CACHE / hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    por_canal: dict[str, list[dict]] = {}
    for linha in CENSO.read_text().splitlines():
        r = json.loads(linha)
        if r["canal"] in FORA:
            continue
        por_canal.setdefault(r["canal"], []).append(r)
    rng = random.Random(20261012)
    n_vid = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    for canal, regs in sorted(por_canal.items()):
        regs = sorted(regs, key=lambda r: r["chave"])
        amostra = rng.sample(regs, min(n_vid, len(regs)))
        linhas = []
        for r in amostra:
            celulas = []
            for i in QUADROS:
                img = cv2.imread(str(pasta(r["chave"]) / f"presenca_{i:02d}.png"))
                if img is None:
                    img = np.zeros((200, LARG, 3), np.uint8)
                h, w = img.shape[:2]
                img = cv2.resize(img, (LARG, max(1, round(h * LARG / w))))
                alt = 360
                if img.shape[0] > alt:
                    img = cv2.resize(img, (round(LARG * alt / img.shape[0]), alt))
                cel = np.zeros((alt, LARG, 3), np.uint8)
                cel[: img.shape[0], : img.shape[1]] = img
                celulas.append(cel)
            linha = np.hstack(celulas)
            nome = Path(r["arquivo"]).stem[:60]
            cv2.putText(linha, nome, (5, 20), 0, 0.5, (0, 0, 0), 3)
            cv2.putText(linha, nome, (5, 20), 0, 0.5, (0, 255, 255), 1)
            linhas.append(linha)
        folha = np.vstack(linhas)
        cv2.imwrite(str(SAIDA / f"{canal.replace('/', '_')}.jpg"), folha,
                    [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(canal, len(regs), "->", len(amostra))


if __name__ == "__main__":
    main()
