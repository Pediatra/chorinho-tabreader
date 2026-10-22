"""0214: confere, sem GPU, as telas reais do treino _atqb (por dobra) e a supervisão.

Uso (container): python data/saida/tablatura/tab_rotulo/r4h/conferir_telas.py
"""

import sys
from collections import Counter

sys.path.insert(0, "/app/data/saida/tablatura/n4")

import treinar_ft as T  # noqa: E402


def main() -> None:
    """Imprime, por dobra, as telas por fonte e as notas supervisionadas."""
    for d, fora in sorted(T.DOBRAS.items()):
        antes = T.carregar_telas(fora, False, True, True, None, True)
        telas = T.carregar_telas(fora, False, True, True, None, True, True, True)
        print(d, len(antes), "->", len(telas), dict(Counter(t["slug"][:4] for t in telas)),
              T.contar_alvos(telas), flush=True)


if __name__ == "__main__":
    main()
