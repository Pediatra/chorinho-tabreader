"""Calibra SAT_CURSOR (rodada 0152, C3): cobertura do cursor e tinta mascarada por limiar."""

import json
from pathlib import Path

import cv2
import numpy as np

from tab import leitor

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152")
VIDEO = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
REC = (855, 1085)
XMAX = 1640
LIMIARES = [80, 70, 60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5]


def quadro(t: float) -> np.ndarray:
    """Quadro do kenneth em ``t``, faixa do recorte, até ``XMAX``."""
    return list(leitor.quadros(VIDEO, t, t + 0.1, 10.0, recorte_y=REC))[0][1][:, :XMAX].copy()


def colunas_cursor(q: np.ndarray) -> list[int]:
    """Colunas com pelo menos 100 px de matiz azul (90–130) e sat >= 5."""
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    azul = (h >= 90) & (h <= 130) & (s >= 5)
    return [int(x) for x in np.flatnonzero(azul.sum(axis=0) >= 100)]


def relatorio(t: float) -> dict:
    """Cobertura (i) e tinta mascarada (ii) para cada limiar, num quadro."""
    q = quadro(t)
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    tinta = cinza < 200
    cols = colunas_cursor(q)
    faixa_h = (h >= 90) & (h <= 130)
    saida = {"t": t, "colunas": cols, "tinta": int(tinta.sum()), "limiares": {}}
    for lim in LIMIARES:
        m = faixa_h & (s >= lim)
        cob = float(m[:, cols].mean()) if cols else 0.0
        tinta_m = float((m & tinta).sum() / max(tinta.sum(), 1))
        saida["limiares"][lim] = {"cobertura": round(cob, 4), "tinta_mascarada": round(tinta_m, 5)}
    return saida


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    resultados = [relatorio(184.0), relatorio(110.0)]
    for r in resultados:
        print("t", r["t"], "colunas", r["colunas"], "tinta", r["tinta"])
        for lim, v in r["limiares"].items():
            print(f"  sat>={lim:>2}  cobertura={v['cobertura']:.4f}  tinta_mascarada={v['tinta_mascarada']:.5f}")
    (SAIDA / "calibracao_cursor.json").write_text(json.dumps(resultados, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
