"""Conferência no olho da máscara (rodada 0151): máscara em vermelho sobre um quadro por vídeo."""

from pathlib import Path

import cv2
import numpy as np

from tab import leitor
from tab import rolagem_saltos as rs

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0151/mascara")
CASOS = [
    ("mrtabs", "/acervo/mr. tabs/blind melon - no rain - guitar tab ｜ lesson ｜ cover ｜ tutorial ｜ lead only.mp4", 63.0, (807, 1019), 1920),
    ("kenneth", "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4", 184.0, (855, 1085), 1640),
    ("leonardo", "/acervo/leonardo ramos/aire de zamba 🎸 jorge martínez zárate ｜｜ tutorial para guitarra clásica + tabs.mp4", 24.4, (796, 1036), 1920),
]


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    for nome, video, t, rec, xmax in CASOS:
        q = list(leitor.quadros(video, t, t + 0.1, 10.0, recorte_y=rec))[0][1][:, :xmax].copy()
        m = rs.mascara(q)
        ov = q.copy()
        ov[m] = (0, 0, 255)
        img = np.vstack([q, ov])
        cv2.imwrite(str(SAIDA / f"{nome}_t{t:.1f}.png"), img)
        print(nome, "mascarado", round(float(m.mean()), 3), img.shape)


if __name__ == "__main__":
    main()
