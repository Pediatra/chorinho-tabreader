"""Diagnóstico dos pixels do cursor fora da faixa de matiz (rodada 0152, C3)."""

from collections import Counter

import cv2
import numpy as np

from tab import leitor

VIDEO = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
REC = (855, 1085)


def main() -> None:
    q = list(leitor.quadros(VIDEO, 184.0, 184.1, 10.0, recorte_y=REC))[0][1][:, :1640].copy()
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    print("colunas 1160..1166: amostra de pixels BGR, HSV")
    for x in range(1160, 1167):
        col = q[:, x]
        hs = hsv[:, x]
        fora = ~((hs[:, 0] >= 90) & (hs[:, 0] <= 130) & (hs[:, 1] >= 5))
        print(f"x={x} fora_da_faixa={int(fora.sum())} de {q.shape[0]}")
        cont = Counter(tuple(int(c) for c in p) for p in col[fora][:400])
        print("   BGR mais comuns fora:", cont.most_common(5))
        cont2 = Counter(tuple(int(c) for c in p) for p in col[~fora][:400])
        print("   BGR mais comuns dentro:", cont2.most_common(3))
    print("linhas com cursor (x=1163, sat>=5 e hue azul):", int(((hsv[:, 1163, 0] >= 90) & (hsv[:, 1163, 0] <= 130) & (hsv[:, 1163, 1] >= 5)).sum()))
    fora_linhas = np.flatnonzero(~((hsv[:, 1163, 0] >= 90) & (hsv[:, 1163, 0] <= 130) & (hsv[:, 1163, 1] >= 5)))
    print("linhas fora em x=1163:", fora_linhas.tolist())
    print("HSV de x=1163 nas linhas fora (ate 12):")
    for y in fora_linhas[:12]:
        print("  y", int(y), hsv[y, 1163].tolist(), q[y, 1163].tolist())


if __name__ == "__main__":
    main()
