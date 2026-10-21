"""Diagnóstico: linhas cruas de ``tab.avaliar.avaliar`` (canal, acertos, total) por modo.

Uso (dentro de /app): python data/saida/barline_fina/diag_oficial.py {controle,variante} MODELO
"""

import sys

from tab import avaliar
from tab import tabseg


def main() -> int:
    """Aplica o modo e imprime as linhas cruas da aferição.

    Returns:
        Código de saída (0).
    """
    modo, modelo = sys.argv[1], sys.argv[2]
    if modo == "controle":
        tabseg.LARGURA_MAX_BARLINE_PASSOS = float("inf")
    print(f"modo={modo} LARGURA_MAX_BARLINE_PASSOS={tabseg.LARGURA_MAX_BARLINE_PASSOS}")
    for linha in avaliar.avaliar(modelo):
        print(linha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
