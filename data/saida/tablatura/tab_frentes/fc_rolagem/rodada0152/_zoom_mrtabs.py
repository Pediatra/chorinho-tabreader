"""Ampliação dos rótulos do salto mr. tabs 161,5 → 161,8 s (rodada 0152, C5): compasso 102."""

from pathlib import Path

import cv2

from tab import leitor

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152/mrtabs_w150")
VIDEO = "/acervo/mr. tabs/blind melon - no rain - guitar tab ｜ lesson ｜ cover ｜ tutorial ｜ lead only.mp4"
REC = (807, 1019)


def quadro(t: float):
    return list(leitor.quadros(VIDEO, t, t + 0.1, 10.0, recorte_y=REC))[0][1][:, :1920].copy()


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    a = quadro(161.5)
    b = quadro(161.8)
    za = cv2.resize(a[0:70, 1380:1640], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    zb = cv2.resize(b[0:70, 60:320], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    zc = cv2.resize(a[0:70, 640:900], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    zd = cv2.resize(b[0:70, 860:1120], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    sep = 255 * (zc[:, :6] * 0 + 1)
    img = cv2.vconcat([cv2.hconcat([za, sep[:, :1] * 0 + 255 + zb[:, :0].sum() * 0][0:1] if False else [za]).copy() if False else za,
                       zb, zc, zd])
    cv2.imwrite(str(SAIDA / "rotulos_161.5_161.8.png"), img)
    print("gravado", img.shape)


if __name__ == "__main__":
    main()
