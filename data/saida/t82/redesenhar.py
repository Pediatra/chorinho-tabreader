"""Redesenha painel.png de cada tela com a casa na altura da sua corda.

O desenho do gerar.py punha todas as casas na primeira corda, sem mostrar a corda.
Aqui cada casa lida vai em vermelho logo acima e à direita da nota, na corda dela.
Lê só tela.json e quadro.png; não roda a rede de novo.
"""

import json
import sys
from pathlib import Path

import cv2

FONTE = cv2.FONT_HERSHEY_SIMPLEX
ESCALA = 2.0


def main() -> None:
    """Redesenha todas as telas de data/saida/t82/telas."""
    raiz = Path(sys.argv[1])
    for pasta in sorted((raiz / "telas").iterdir()):
        tela = json.loads((pasta / "tela.json").read_text(encoding="utf-8"))
        p = tela.get("painel")
        if not p or not tela.get("linhas_y"):
            continue
        q = cv2.imread(str(pasta / "quadro.png"))
        m = int(tela["passo"])
        y0, y1 = max(0, p["y0"] - m), min(q.shape[0], p["y1"] + m)
        x0, x1 = p["x0"], p["x1"]
        img = cv2.resize(q[y0:y1, x0:x1], None, fx=ESCALA, fy=ESCALA,
                         interpolation=cv2.INTER_CUBIC)
        linhas = tela["linhas_y"]
        for n in tela["notas"]:
            x = (n["x_centro_quadro"] - x0) * ESCALA
            y = (linhas[n["corda"] - 1] - y0) * ESCALA
            cv2.circle(img, (int(x), int(y)), 3, (0, 160, 0), -1)
            cv2.putText(img, str(n["casa"]), (int(x + 4), int(y - 0.35 * m * ESCALA)),
                        FONTE, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.imwrite(str(pasta / "painel.png"), img)


if __name__ == "__main__":
    main()
