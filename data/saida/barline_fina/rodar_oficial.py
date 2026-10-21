"""Roda ``tab.avaliar.main`` (métrica oficial) com o modelo dado, no controle ou na variante.

Uso (dentro do container, a partir de /app):
    python data/saida/barline_fina/rodar_oficial.py {controle,variante} MODELO

Mesma troca de constante que ``rodar.py``: no controle, ``LARGURA_MAX_BARLINE_PASSOS`` = inf.
"""

import sys

from tab import avaliar
from tab import tabseg


def main() -> int:
    """Aplica o modo e chama ``tab.avaliar.main`` com ``--modelo`` explícito.

    Returns:
        Código de saída de ``tab.avaliar.main``.
    """
    modo, modelo = sys.argv[1], sys.argv[2]
    if modo == "controle":
        tabseg.LARGURA_MAX_BARLINE_PASSOS = float("inf")
    elif modo != "variante":
        raise SystemExit(f"modo desconhecido: {modo}")
    print(f"modo={modo} modelo={modelo} LARGURA_MAX_BARLINE_PASSOS={tabseg.LARGURA_MAX_BARLINE_PASSOS}")
    sys.argv = ["tab.avaliar", "--modelo", modelo]
    return avaliar.main()


if __name__ == "__main__":
    sys.exit(main())
