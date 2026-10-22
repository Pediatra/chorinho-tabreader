"""0214: mede a amostra do gerador com G13–G15 antes de treinar (AGENTS §7.2).

Gera 2000 sistemas pelas sementes de treino (``random.Random(semente)``, as fontes do
treino) e conta as variantes novas e as notas sem ataque. Desenha 8 exemplos com as
variantes novas em ``r4h/exemplos/`` para olhar.

Uso (container): python data/saida/tablatura/tab_rotulo/r4h/amostra.py
"""

import json
import random
from collections import Counter
from pathlib import Path

import cv2

from tab.tablatura.leitura import detector_tab as D
from tab.tablatura.treino.sintetico_sistema import gerar_sistema

AQUI = Path(__file__).resolve().parent
NOVAS = ("ligadura", "ligadura_parenteses", "ligadura_harm", "arco_solto")


def main() -> None:
    """Conta e desenha."""
    (AQUI / "exemplos").mkdir(exist_ok=True)
    sistemas: Counter = Counter()
    notas: Counter = Counter()
    vistos: Counter = Counter()
    for semente in range(2000):
        img, info = gerar_sistema(random.Random(semente), D.FONTES_TREINO)
        v = info["variantes"]
        for nome in NOVAS:
            sistemas[nome] += nome in v
        for n in info["notas"]:
            notas[n["tecnica"] or "atacada"] += 1
        alvo = [x for x in NOVAS[1:] if x in v and vistos[x] < 3]
        if alvo:
            for x in alvo:
                vistos[x] += 1
            cv2.imwrite(str(AQUI / "exemplos" / f"{semente}_{'_'.join(alvo)}.png"), img)
    res = {"sistemas_com": dict(sistemas), "notas_por_tecnica": dict(notas), "n": 2000}
    (AQUI / "amostra.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
