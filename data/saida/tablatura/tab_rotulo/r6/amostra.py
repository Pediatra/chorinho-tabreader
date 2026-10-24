"""0218: mede a amostra do gerador com o G17 antes de treinar (AGENTS §7.2).

Gera 2000 sistemas pelas sementes de treino (``random.Random(semente)``, as fontes do
treino) e conta as notas "x", as colunas com 2 ou mais "x" (o X empilhado) e o tamanho
delas. Desenha 6 sistemas com coluna de X em ``r6/exemplos/``.

Uso (container): python data/saida/tablatura/tab_rotulo/r6/amostra.py
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
    tamanhos: Counter = Counter()
    notas_x = sistemas = desenhados = 0
    for semente in range(2000):
        img, info = gerar_sistema(random.Random(semente), D.FONTES_TREINO)
        xs = [n for n in info["notas"] if n["rotulo"] == "x"]
        notas_x += len(xs)
        colunas = Counter(round(n["x"]) for n in xs)
        empilhadas = [k for k in colunas.values() if k >= 2]
        tamanhos.update(empilhadas)
        sistemas += bool(empilhadas)
        if empilhadas and desenhados < 6:
            desenhados += 1
            cv2.imwrite(str(AQUI / "exemplos" / f"{semente}_coluna_x.png"), img)
    res = {
        "n": 2000,
        "notas_x": notas_x,
        "sistemas_com_coluna_x": sistemas,
        "colunas_x_por_tamanho": {str(k): v for k, v in sorted(tamanhos.items())},
    }
    (AQUI / "amostra.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
