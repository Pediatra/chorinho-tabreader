"""Calibra SAT_CURSOR (rodada 0152, C3, critérios revisados): cobertura na faixa do cursor."""

import json
from pathlib import Path

import cv2
import numpy as np

from tab import leitor

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152")
VIDEO = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
REC = (855, 1085)
XMAX = 1640
LIMIARES = [80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5]


def quadro(t: float) -> np.ndarray:
    """Quadro do kenneth em ``t``, faixa do recorte, até ``XMAX``."""
    return list(leitor.quadros(VIDEO, t, t + 0.1, 10.0, recorte_y=REC))[0][1][:, :XMAX].copy()


def faixa(q: np.ndarray) -> tuple[int, int]:
    """Faixa de colunas do cursor: núcleo (>= 100 px azuis) mais 2 colunas de cada lado."""
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    azul = (h >= 90) & (h <= 130) & (s >= 5)
    nucleo = np.flatnonzero(azul.sum(axis=0) >= 100)
    return int(nucleo.min()) - 2, int(nucleo.max()) + 3


def relatorio(t: float) -> dict:
    """Cobertura (i) na faixa do cursor e tinta mascarada fora da faixa (ii), por limiar."""
    q = quadro(t)
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    x0, x1 = faixa(q)
    tinta = cinza < 200
    ref = np.zeros(cinza.shape, bool)
    ref[:, x0:x1] = cinza[:, x0:x1] < 240
    fora = np.ones(cinza.shape, bool)
    fora[:, x0:x1] = False
    faixa_h = (h >= 90) & (h <= 130)
    out = {"t": t, "faixa": [x0, x1], "pixels_cursor": int(ref.sum()), "tinta": int(tinta.sum()), "limiares": {}}
    for lim in LIMIARES:
        m = faixa_h & (s >= lim)
        cob = float((m & ref).sum() / max(ref.sum(), 1))
        tinta_fora = float((m & tinta & fora).sum() / max(tinta.sum(), 1))
        out["limiares"][lim] = {"cobertura": round(cob, 4), "tinta_fora_mascarada": round(tinta_fora, 5)}
    return out


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    resultados = [relatorio(184.0), relatorio(110.0)]
    for r in resultados:
        print("t", r["t"], "faixa", r["faixa"], "pixels_cursor", r["pixels_cursor"], "tinta", r["tinta"])
        for lim, v in r["limiares"].items():
            print(f"  sat>={lim:>2}  cobertura={v['cobertura']:.4f}  tinta_fora={v['tinta_fora_mascarada']:.5f}")
    (SAIDA / "calibracao_cursor_v2.json").write_text(json.dumps(resultados, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
