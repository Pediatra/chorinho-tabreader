"""Passo 3: colunas do produto por tela, ordenadas por x_centro_quadro (texto, para comparar com os PNG)."""

import json
import sys
from pathlib import Path

LOTE = Path("/var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/a4/lote1")
TELAS = [3, 38, 17, 13, 20, 34, 30]


def main() -> int:
    """Imprime a sequencia de cada tela pedida."""
    prod = json.loads((LOTE / "transcriptor_campanitas.json").read_text())
    alin = json.loads((LOTE / "alinhado_v21_transcriptor_campanitas.json").read_text())
    tipo = {(c["tela"], c["coluna"]): c["tipo"] for c in alin["colunas"]}
    for tela in TELAS:
        notas = sorted(
            (n for n in prod["notas"] if n["tela"] == tela), key=lambda n: n["x_centro_quadro"]
        )
        nao = sorted(
            (n for n in prod["nao_notas"] if n["tela"] == tela), key=lambda n: n["x_centro_quadro"]
        )
        print(f"== tela {tela}  notas={len(notas)} nao_notas={len(nao)}")
        itens = [("N", n["x_centro_quadro"], n["coluna"], f"c{n['corda']}/k{n['casa']}") for n in notas]
        itens += [("S", n["x_centro_quadro"], n["coluna"], f"{n['classe']}:{n['simbolo_cru'].get('top3', [[None]])[0][0]}") for n in nao]
        for kind, x, col, txt in sorted(itens, key=lambda i: i[1]):
            print(f"  x={x:7.1f} col={col:3d} {kind} {txt}  alin={tipo.get((tela, col), '-')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
