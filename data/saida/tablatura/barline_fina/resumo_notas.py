"""Conta notas por corda e o total de um JSON de ``tab.transcrever`` (formato v1).

Uso: python data/saida/barline_fina/resumo_notas.py SAIDA_JSON
"""

import json
import sys
from collections import Counter


def main() -> int:
    """Imprime as notas por corda (1 a 6), o total e as notas com tempo.

    Returns:
        Código de saída (0).
    """
    with open(sys.argv[1], encoding="utf-8") as f:
        dados = json.load(f)
    notas = dados.get("notas", [])
    por_corda = Counter(n.get("corda") for n in notas)
    partes = " ".join(f"corda{c}={por_corda.get(c, 0)}" for c in range(1, 7))
    com_tempo = sum(1 for n in notas if n.get("t_ini") is not None)
    print(f"notas por corda: {partes} | outras={sum(v for k, v in por_corda.items() if k not in range(1, 7))}")
    print(f"total notas={len(notas)} com_tempo={com_tempo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
