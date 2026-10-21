"""Ampliação dos rótulos de compasso nos quadros 184,4 e 184,9 do kenneth (rodada 0152, C4)."""

from pathlib import Path

import cv2

from tab import leitor

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152/transicao_kenneth")
VIDEO = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
REC = (855, 1085)


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    for t in (184.4, 184.9):
        q = list(leitor.quadros(VIDEO, t, t + 0.1, 10.0, recorte_y=REC))[0][1][:, :1640].copy()
        tiras = [
            cv2.resize(q[0:60, 440:620], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC),
            cv2.resize(q[0:60, 1030:1210], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC),
            cv2.resize(q[0:60, 440:620], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC) * 0 + 255,
        ]
        img = cv2.hconcat([tiras[0], tiras[1]])
        cv2.imwrite(str(SAIDA / f"rotulos_{t:.1f}.png"), img)
        print("gravado", t, img.shape)


if __name__ == "__main__":
    main()
