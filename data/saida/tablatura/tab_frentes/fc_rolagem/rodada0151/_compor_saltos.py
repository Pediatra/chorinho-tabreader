"""Composições antes/depois de cada salto (rodada 0151), para a leitura à mão.

Uso: python _compor_saltos.py VIDEO SALTOS_JSON OUTDIR Y0 Y1 XMAX
A grade de quadros é a mesma do módulo (mesmo t0, dur e qps do saltos.json). Para cada
salto, grava uma imagem com o quadro de antes em cima e o de depois embaixo, em escala
0,75. Cada barra candidata (limiar de 200) leva um rótulo com o x do quadro cheio.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from tab import leitor
from tab import rolagem_saltos as rs


def _quadro(bgr: np.ndarray, xmax: int, t: float) -> np.ndarray:
    """Quadro mascarado, com as barras rotuladas pelo x e o instante impresso."""
    q = bgr[:, :xmax].copy()
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    cinza[rs.mascara(bgr)[:, :xmax]] = 255
    cor = cv2.cvtColor(cinza, cv2.COLOR_GRAY2BGR)
    for x in rs.barras(cinza):
        xi = int(round(x))
        cv2.line(cor, (xi, 0), (xi, 10), (0, 0, 255), 2)
        cv2.putText(cor, str(xi), (xi + 2, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 255), 1)
    cv2.putText(cor, f"t={t:.2f}", (4, cor.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 0, 0), 1)
    return cv2.resize(cor, None, fx=0.75, fy=0.75, interpolation=cv2.INTER_AREA)


def main() -> int:
    """Grava uma composição por salto."""
    video, sj, outdir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    y0, y1, xmax = int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
    rel = json.loads(sj.read_text(encoding="utf-8"))
    outdir.mkdir(parents=True, exist_ok=True)
    quadros = list(
        leitor.quadros(video, rel["t0"], rel["t0"] + rel["dur"], rel["qps"],
                       recorte_y=(y0, y1))
    )
    tempos = np.array([t for t, _ in quadros])
    for k, s in enumerate(rel["saltos"]):
        partes = []
        for t_alvo in (s["t_antes"], s["t_depois"]):
            idx = int(np.argmin(np.abs(tempos - t_alvo)))
            partes.append(_quadro(quadros[idx][1], xmax, quadros[idx][0]))
        sep = np.zeros((6, partes[0].shape[1], 3), np.uint8)
        img = np.vstack([partes[0], sep, partes[1]])
        cv2.imwrite(str(outdir / f"salto{k:02d}_{s['t_antes']:.2f}.png"), img)
    print(f"composicoes: {len(rel['saltos'])} em {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
