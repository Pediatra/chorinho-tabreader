"""Mede o DESTAQUE DE COR por algarismo — o segundo observador do estado do marcador.

Por que existe: o `rastrear` procura a **faixa vertical** e por isso chama de `ausente` vídeos que TÊM
marcador — o `kimny's guitar` tem um algarismo **verde** entre pretos, e o `mr. tabs` tem um **destaque
azul**. A formulação do dono continua valendo (o marcador é um ESTADO: "qual nota está acesa"), mas o
estado tem **duas fontes**, e esta é a segunda.

O sinal não precisa de rótulo para ser medido: se **um** algarismo é colorido e os outros são cinzas, ele
é um **outlier** de coloração. Este módulo mede a coloração de cada token e mostra o ranking — e é a
**separação** que decide se a fonte é utilizável (um outlier claro) ou ruído (todos parecidos).

Uso:

    python -m tab.destaque --video "<caminho>" --frac 0.65
"""

import argparse
import sys

import cv2
import numpy as np

from .inventario import ler_quadro
from .painel import escolher


def coloracao(rec: np.ndarray) -> float:
    """Mede a coloração de um recorte (0 = cinza, alto = colorido).

    Usa ``max(canais) - min(canais)`` por pixel, que é **invariante ao brilho** — um algarismo claro e um
    escuro, ambos cinzas, dão o mesmo zero; um verde dá alto.

    Args:
        rec: recorte em BGR.

    Returns:
        Média da diferença entre o canal mais alto e o mais baixo.
    """
    if rec.ndim == 2 or rec.size == 0:
        return 0.0
    b, g, r = (
        rec[:, :, 0].astype(np.int16),
        rec[:, :, 1].astype(np.int16),
        rec[:, :, 2].astype(np.int16),
    )
    return float(
        np.clip(
            np.maximum(np.maximum(b, g), r) - np.minimum(np.minimum(b, g), r), 0, None
        ).mean()
    )


def main() -> int:
    """Mostra o ranking de coloração dos algarismos de um quadro."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--frac", type=float, default=0.65)
    args = ap.parse_args()

    quadro, via = ler_quadro(args.video, args.frac)
    if quadro is None:
        print("quadro ilegível", file=sys.stderr)
        return 2
    cand = escolher(quadro)
    if cand is None:
        print("sem painel", file=sys.stderr)
        return 3
    cor = quadro if quadro.ndim == 3 else cv2.cvtColor(quadro, cv2.COLOR_GRAY2BGR)
    passo = cand.grade.passo
    y_roi0 = cand.y0
    itens = []
    for t in cand.grade.glifos:
        cx = (t.x0 + t.x1) // 2
        cy = (t.y0 + t.y1) // 2
        rec = cor[y_roi0 + t.y0 : y_roi0 + t.y1, t.x0 : t.x1]
        itens.append(
            (coloracao(rec), cx, cy, (t.x1 - t.x0) / passo, (t.y1 - t.y0) / passo)
        )
    itens.sort(reverse=True)
    print(f"painel={cand.nome} passo={passo:.1f} tokens={len(itens)} via={via}")
    print("top 5 por COLORAÇÃO (0 = cinza):")
    for c, cx, cy, w, h in itens[:5]:
        print(f"   coloração={c:6.1f} x={cx:5d} y={cy:5d} {w:.2f}x{h:.2f} passos")
    mediana = float(np.median([x[0] for x in itens])) if itens else 0.0
    print(
        f"mediana da coloração: {mediana:.1f} | máximo: {itens[0][0]:.1f}"
        if itens
        else ""
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
