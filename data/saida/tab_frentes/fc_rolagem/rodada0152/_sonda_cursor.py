"""Sonda da máscara do cursor (rodada 0152, C3): só pixels, sem deslocamento."""

from pathlib import Path

import cv2
import numpy as np

from tab import leitor

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152")
VIDEO = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
REC = (855, 1085)
XMAX = 1640


def quadro(t: float) -> np.ndarray:
    """Quadro do kenneth em ``t``, faixa do recorte, até ``XMAX``."""
    return list(leitor.quadros(VIDEO, t, t + 0.1, 10.0, recorte_y=REC))[0][1][:, :XMAX].copy()


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    q = quadro(184.0)
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    h, s, v = (hsv[..., i].astype(int) for i in range(3))
    azul = (h >= 90) & (h <= 130)
    print("shape", q.shape)
    print("colunas x 1130..1200: n_azul_sat>=5 | sat_media | val_mediana")
    for x in range(1130, 1200):
        m = azul[:, x] & (s[:, x] >= 5)
        if m.sum() >= 5:
            print(x, int(m.sum()), round(float(s[:, x][m].mean()), 1), int(np.median(v[:, x][m])))
    print("sat max por coluna azul (x 1100..1220, n>=5):")
    cand = [x for x in range(1100, 1220) if (azul[:, x] & (s[:, x] >= 5)).sum() >= 5]
    print(cand)
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    tinta = cinza < 200
    print("tinta (cinza<200) no quadro:", int(tinta.sum()))
    crop = q[:, 1100:1220]
    zoom = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(SAIDA / "sonda_cursor_184_zoom.png"), zoom)
    cv2.imwrite(str(SAIDA / "sonda_cursor_184_quadro.png"), q)


if __name__ == "__main__":
    main()
