"""Folhas com o painel.png de cada tela da T8.6 (cordas em verde, casas lidas em vermelho).

Para conferir, antes de servir, se o painel de cada tela pegou a tablatura e as 6 cordas.

Uso (container): python data/saida/tablatura/t86/folha_paineis.py
"""

import json
from pathlib import Path

import cv2
import numpy as np

T86 = Path("/app/data/saida/tablatura/t86")
LARGURA = 1000
POR_FOLHA = 8


def main() -> int:
    """Grava ``folha_paineis_<n>.jpg``."""
    indice = json.loads(
        (T86 / "ferramenta" / "indice.json").read_text(encoding="utf-8")
    )
    blocos = []
    for r in indice:
        img = cv2.imread(str(Path("/app") / r["pasta"] / "painel.png"))
        s = LARGURA / img.shape[1]
        img = cv2.resize(img, None, fx=s, fy=s)
        faixa = np.full((28, LARGURA, 3), 255, np.uint8)
        cv2.putText(
            faixa, f"id {r['id']}", (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2
        )
        blocos.append(np.vstack([faixa, img]))
    for k in range(0, len(blocos), POR_FOLHA):
        folha = np.vstack(blocos[k : k + POR_FOLHA])
        cv2.imwrite(str(T86 / f"folha_paineis_{k // POR_FOLHA + 1}.jpg"), folha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
