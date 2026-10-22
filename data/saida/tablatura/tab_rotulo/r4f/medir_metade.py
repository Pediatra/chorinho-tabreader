"""0209: a faixa (L = 0,02, técnica 0,15) na metade da T8.3 que ficou fora do treino.

O modelo ``atqm<h>`` (treinado com a metade h da T8.3) é medido nas telas da outra metade; o
``atqt`` (sem T8.3), nas mesmas telas. Soma as duas metades. Grava ``r4f/medida_metade.json``.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4f/medir_metade.py
"""

import json
from collections import Counter

from tab import ataque_r4 as A
from tab import caminhos, detector_tab

GAB = caminhos.TAB_ROTULO / "r2" / "conferir_t83" / "ataque_t83.json"
INDICE = caminhos.SAIDA / "t83" / "ferramenta" / "indice.json"
CACHE = caminhos.SAIDA / "n4" / "cache_t83"
L = 0.02


def main() -> int:
    """Mede e grava."""
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    metade = {}
    for f in CACHE.glob("*.json"):
        m = json.loads(f.read_text(encoding="utf-8"))
        metade[int(m["tela"])] = m["metade"]
    gab = A.gabarito_por_tela(GAB)
    saida = {}
    for versao in ("atqt", "atqm"):
        for s in (1, 2, 3):
            soma = Counter()
            for h in ("a", "b"):
                nome = versao if versao == "atqt" else f"atqm{h}"
                modelo = detector_tab.carregar(A.modelo_da_dobra(nome, 0, s))
                for tela, notas in sorted(gab.items()):
                    if metade.get(tela) in (None, h):
                        continue  # só as telas da outra metade
                    r = indice[tela]
                    pred, passo = A.ler_tela(modelo, caminhos.acervo() / r["video"], float(r["t"]))
                    soma += A.contar(notas, A.com_limiar(pred, L), passo)
            m = A.regra(soma)
            saida[f"{versao}_s{s}"] = dict(soma)
            print(f"{versao} s{s}: sim falso {m['nao|sim']}/{m['nao|sim'] + m['nao|nao']}"
                  f" custo {m['sim|nao']}/{m['sim|nao'] + m['sim|sim']}"
                  f" casa {soma['casa_certa']}/{soma['casadas']}", flush=True)
    (caminhos.TAB_ROTULO / "r4f" / "medida_metade.json").write_text(
        json.dumps(saida, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
