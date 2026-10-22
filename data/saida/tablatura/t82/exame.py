"""T8.2: extrai 8 quadros por vídeo na janela de tablatura do censo (só saída em t82/exame)."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from tab import caminhos, leitor

RAIZ = Path("/app")
SAIDA = RAIZ / "data" / "saida" / "t82" / "exame"
CENSO = RAIZ / "data" / "saida" / "censo" / "censo_cache.jsonl"
VIDEOS = [
    "cifra club/meu lugar - arlindo cruz (completa) ｜ como tocar no violão.mp4",
    "cifra club/wicked game - chris isaak (versão única) ｜ como tocar no violão.mp4",
]


def janela(rec: dict) -> tuple[float, float]:
    """Janela de tablatura do censo: menor e maior instante com tab=true.

    Args:
        rec: registro do censo.

    Returns:
        Par (início, fim) em segundos.
    """
    tabs = [i["t"] for i in rec["instantes"] if i.get("tab")]
    return min(tabs), max(tabs)


def main() -> None:
    """Grava 8 quadros por vídeo e um índice JSON."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    recs = {}
    with CENSO.open(encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            recs[r["arquivo"]] = r
    indice = []
    for video in VIDEOS:
        rec = recs[video]
        a, b = janela(rec)
        slug = "c01_" + ("meu" if "meu lugar" in video else "wicked")
        for k, t in enumerate(np.linspace(a, b, 8), start=1):
            t = round(float(t), 2)
            quadro = leitor.quadro_em(str(caminhos.acervo() / video), t)
            nome = f"{slug}_q{k}_t{t:.0f}.png"
            if quadro is not None:
                cv2.imwrite(str(SAIDA / nome), quadro)
            indice.append({"video": video, "k": k, "t": t, "arquivo": nome,
                           "ok": quadro is not None})
            print(nome, quadro is not None, flush=True)
    (SAIDA / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
