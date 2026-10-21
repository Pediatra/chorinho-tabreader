"""Diagnóstico: por que o destaque móvel quebra a página (canon 345-380, beam 60-90)."""

import sys

import cv2
import numpy as np

from tab.caminhos import acervo
from tab.partitura_video import MARGEM_ASSINATURA_ENTRELINHAS, _cinza, _tinta, assinatura, diferenca
from tab.partitura_pauta import achar_pautas
from tab.leitor import quadro_em

CASOS = {
    "canon": ("pablo romé/canon de pachelbel para guitarra 🤩 niveles 1-4.mp4", 345, 381),
    "beam": ("robert lunn/a beam of light on a yellow flower - full tutorial with tab - classical guitar - robert lunn.mp4", 60, 90),
}


def dil(a, r):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(a.astype(np.uint8), k) > 0


def tolerante(a, b, r=1):
    na, nb = max(1, a.sum()), max(1, b.sum())
    return max((a & ~dil(b, r)).sum() / na, (b & ~dil(a, r)).sum() / nb)


def main():
    nome = sys.argv[1]
    video, t0, t1 = CASOS[nome]
    cam = str(acervo() / video)
    prim = None
    for t in range(t0, t1):
        q = quadro_em(cam, float(t))
        ps = achar_pautas(q)
        a = assinatura(q, ps)
        desc = [(round(p.ys[0]), round(p.entrelinha, 1)) for p in ps]
        if a is None:
            print(t, "sem assinatura", desc)
            continue
        if prim is None:
            prim = a
            cv2.imwrite(f"data/saida/partitura/diag/destaque_{nome}_{t}.png", a.astype(np.uint8) * 255)
        print(t, desc, f"tinta {a.sum():4d} xor {diferenca(prim, a):.3f} tol1 {tolerante(prim, a, 1):.3f} tol2 {tolerante(prim, a, 2):.3f}")
        if t in (t0 + 10, t0 + 20):
            cv2.imwrite(f"data/saida/partitura/diag/destaque_{nome}_{t}.png", a.astype(np.uint8) * 255)
            cv2.imwrite(f"data/saida/partitura/diag/destaque_{nome}_{t}_q.jpg", q)


if __name__ == "__main__":
    main()
