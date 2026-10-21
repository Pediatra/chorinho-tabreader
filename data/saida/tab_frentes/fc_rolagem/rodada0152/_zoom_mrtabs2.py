"""Ampliação dos rótulos de compasso dos saltos mr. tabs 172,7 e 206,1 (rodada 0152, C5)."""

from pathlib import Path

import cv2

from tab import leitor

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152/mrtabs_w150")
VIDEO = "/acervo/mr. tabs/blind melon - no rain - guitar tab ｜ lesson ｜ cover ｜ tutorial ｜ lead only.mp4"
REC = (807, 1019)


def quadro(t: float):
    return list(leitor.quadros(VIDEO, t, t + 0.1, 10.0, recorte_y=REC))[0][1][:, :1920].copy()


def par(a, b, xa, xb):
    ia = max(0, xa - 130)
    ib = max(0, xb - 130)
    za = cv2.resize(a[0:70, ia : xa + 130], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    zb = cv2.resize(b[0:70, ib : xb + 130], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    return cv2.hconcat([za, zb])


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    a = quadro(172.7)
    b = quadro(173.0)
    img1 = par(a, b, 1520, 165)
    c = quadro(206.1)
    d = quadro(206.5)
    img2 = par(c, d, 1471, 125)
    cv2.imwrite(str(SAIDA / "rotulos_172.7_173.0.png"), img1)
    cv2.imwrite(str(SAIDA / "rotulos_206.1_206.5.png"), img2)
    print("gravado", img1.shape, img2.shape)


if __name__ == "__main__":
    main()
