"""Protótipo: tinta = mais escura que o fundo local (top-hat no V). Compara com a regra HSV."""

import sys

import cv2
import numpy as np

from tab.caminhos import acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import achar_pautas
from tab.partitura_recortes import _tinta_escura
from tab.partitura_video import (
    ALTURA_ASSINATURA, FRACAO_TINTA, LARGURA_ASSINATURA, MARGEM_ASSINATURA_ENTRELINHAS,
    _cinza, assinatura, diferenca,
)

CASOS = {
    "canon": ("pablo romé/canon de pachelbel para guitarra 🤩 niveles 1-4.mp4", 345, 381),
    "beam": ("robert lunn/a beam of light on a yellow flower - full tutorial with tab - classical guitar - robert lunn.mp4", 114, 163),
    "beam2": ("robert lunn/a beam of light on a yellow flower - full tutorial with tab - classical guitar - robert lunn.mp4", 182, 242),
}
DELTA = int(sys.argv[2]) if len(sys.argv) > 2 else 60


def assin_tophat(q, ps):
    if not ps:
        return None
    cinza = _cinza(q)
    v = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)[:, :, 2]
    e = float(np.median([p.entrelinha for p in ps]))
    lado = 2 * round(e) + 1
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (lado, lado))
    if _tinta_escura(cinza):
        th = cv2.morphologyEx(v, cv2.MORPH_BLACKHAT, k)
    else:
        th = cv2.morphologyEx(v, cv2.MORPH_TOPHAT, k)
    tinta = th > DELTA
    p0 = min(ps, key=lambda p: p.ys[0]); p1 = max(ps, key=lambda p: p.ys[4])
    y0 = max(0, int(p0.ys[0] - MARGEM_ASSINATURA_ENTRELINHAS * p0.entrelinha))
    y1 = min(v.shape[0], int(p1.ys[4] + MARGEM_ASSINATURA_ENTRELINHAS * p1.entrelinha) + 1)
    f = cv2.resize(tinta[y0:y1].astype(np.float32), (LARGURA_ASSINATURA, ALTURA_ASSINATURA), interpolation=cv2.INTER_AREA)
    return f >= FRACAO_TINTA


def main():
    nome = sys.argv[1]
    video, t0, t1 = CASOS[nome]
    cam = str(acervo() / video)
    ant_h = ant_t = None
    for t in range(t0, t1):
        q = quadro_em(cam, float(t))
        ps = achar_pautas(q)
        h, th = assinatura(q, ps), assin_tophat(q, ps)
        if h is None:
            print(t, "sem pauta")
            continue
        dh = diferenca(ant_h, h) if ant_h is not None else 0
        dt = diferenca(ant_t, th) if ant_t is not None else 0
        print(f"{t} hsv {dh:.3f} tophat {dt:.3f} tinta {th.sum()}")
        if t in (t0 + 5, t0 + 15):
            cv2.imwrite(f"data/saida/partitura/diag/tophat_{nome}_{t}.png", th.astype(np.uint8) * 255)
        ant_h, ant_t = h, th


if __name__ == "__main__":
    main()
