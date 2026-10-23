"""0215: mede a amostra do gerador com o G16 antes de treinar (AGENTS §7.2).

Gera 2000 sistemas pelas sementes de treino (``random.Random(semente)``, as fontes do
treino), conta os sistemas e as marcas de expressão do G16 e quantas notas ficam embaixo
de uma (todas atacadas, se não têm técnica). Desenha 6 exemplos em ``r5/exemplos/``.

Uso (container): python data/saida/tablatura/tab_rotulo/r5/amostra.py
"""

import json
import random
from collections import Counter
from pathlib import Path

import cv2

from tab.tablatura.leitura import detector_tab as D
from tab.tablatura.treino.sintetico_sistema import gerar_sistema

AQUI = Path(__file__).resolve().parent


def main() -> None:
    """Conta e desenha."""
    (AQUI / "exemplos").mkdir(exist_ok=True)
    textos: Counter = Counter()
    sistemas = desenhados = 0
    for semente in range(2000):
        img, info = gerar_sistema(random.Random(semente), D.FONTES_TREINO)
        marcas = [it for it in info["estrutura"] if it["tipo"] == "expressao"]
        sistemas += bool(marcas)
        textos.update(m["texto"] for m in marcas)
        if marcas and desenhados < 6:
            desenhados += 1
            cv2.imwrite(str(AQUI / "exemplos" / f"{semente}_expressao.png"), img)
    res = {"n": 2000, "sistemas_com_expressao": sistemas, "marcas": dict(textos)}
    (AQUI / "amostra.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
