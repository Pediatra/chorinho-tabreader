"""Sonda descartavel: quadros e painel de um video (C1)."""

import sys

import cv2

from tab import leitor, painel
from tab.telas import painel_do_quadro


def main() -> int:
    """Grava 3 quadros e imprime o painel de cada um."""
    video = sys.argv[1]
    saida = sys.argv[2]
    d = leitor.info(video)
    dur = float(d["duracao_s"] or 0.0)
    print("info", d)
    for frac in (0.2, 0.4, 0.6):
        t = dur * frac
        q = leitor.quadro_em(video, t)
        if q is None:
            print(f"t={t:.1f} sem quadro")
            continue
        cv2.imwrite(f"{saida}/quadro_{int(frac * 100):03d}.png", q)
        r = painel_do_quadro(q)
        c = painel.escolher_ou_mascara(q)
        print(
            f"t={t:.1f} shape={q.shape} painel_do_quadro={r} "
            f"cand={None if c is None else (c.nome, c.y0, c.y1, c.x0, c.roi.shape, round(c.passo, 1), len(c.grade.linhas_y), len(c.grade.glifos))}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
