"""Junta os exemplos do G16 numa imagem só, para olhar (0215)."""

import glob
from pathlib import Path

import cv2
import numpy as np

AQUI = Path(__file__).resolve().parent


def main() -> None:
    """Empilha os exemplos, com 2× de aumento."""
    ims = [cv2.imread(f) for f in sorted(glob.glob(str(AQUI / "exemplos" / "*.png")))]
    ims = [
        cv2.resize(i, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST) for i in ims
    ]
    w = max(i.shape[1] for i in ims)
    ims = [
        cv2.copyMakeBorder(i, 0, 8, 0, w - i.shape[1], cv2.BORDER_CONSTANT, value=255)
        for i in ims
    ]
    cv2.imwrite(str(AQUI / "exemplos_g16.png"), np.vstack(ims))


if __name__ == "__main__":
    main()
