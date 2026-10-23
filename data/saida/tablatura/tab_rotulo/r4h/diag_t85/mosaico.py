"""Mosaicos dos recortes de erro do diagnóstico da T8.5 (0214)."""

import glob
import sys

import cv2
import numpy as np


def main() -> int:
    """Grava um mosaico por padrão de nome."""
    base = sys.argv[1]
    for nome, pat in (("t3", "custo_t3_*.png"), ("outras", "custo_t1[07]_*.png")):
        fs = sorted(glob.glob(f"{base}/recortes/{pat}"))[:12]
        ims = [cv2.imread(f) for f in fs]
        h = max(i.shape[0] for i in ims)
        w = max(i.shape[1] for i in ims)
        ims = [
            cv2.copyMakeBorder(
                i,
                0,
                h - i.shape[0] + 6,
                0,
                w - i.shape[1] + 6,
                cv2.BORDER_CONSTANT,
                value=(255, 255, 255),
            )
            for i in ims
        ]
        branco = np.full_like(ims[0], 255)
        linhas = [
            np.hstack(ims[k : k + 4] + [branco] * (4 - len(ims[k : k + 4])))
            for k in range(0, len(ims), 4)
        ]
        cv2.imwrite(f"{base}/mosaico_{nome}.png", np.vstack(linhas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
