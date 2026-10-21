"""Recortes ampliados de células da folha censo_completar_mudancas.jpg."""

import cv2

from tab.caminhos import RAIZ

D = RAIZ / "data" / "saida" / "partitura" / "diag"


def main() -> None:
    """Grava zoom_leo.png e zoom_transc.png."""
    folha = cv2.imread(str(D / "censo_completar_mudancas.jpg"))
    for nome, (x0, y0, x1, y1) in {
        "leo": (960, 170, 1440, 280),
        "transc": (0, 1040, 480, 1150),
        "dell": (0, 170, 960, 280),
    }.items():
        corte = folha[y0:y1, x0:x1]
        cv2.imwrite(str(D / f"zoom_{nome}.png"), cv2.resize(corte, None, fx=2, fy=2))


if __name__ == "__main__":
    main()
