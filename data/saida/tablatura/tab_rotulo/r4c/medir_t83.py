"""0205 na T8.3: a faixa "não sei" (L = 0,02, técnica 0,15) fora de amostra, 3 sementes.

Lê cada tela da T8.3 com o _atqg da dobra 0 (os 8 ouros no treino; a T8.3 em nenhum treino)
e conta como ``tab.ataque_r4.medir``. Grava ``r4c/medida_t83_<versao>.json``.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4c/medir_t83.py atqg [recorte]

``recorte``: "alto" (padrão desde a 0210; grava ``medida_t83_<versao>_alto.json``) ou "painel".
"""

import json
import sys
from collections import Counter

from tab import ataque_r4 as A
from tab import caminhos, detector_tab
from tab.gpu import trava_gpu

GAB = caminhos.TAB_ROTULO / "r2" / "conferir_t83" / "ataque_t83.json"
INDICE = caminhos.SAIDA / "t83" / "ferramenta" / "indice.json"


def main() -> int:
    """Mede e grava."""
    versao = sys.argv[1]
    recorte = sys.argv[2] if len(sys.argv) > 2 else "alto"
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    gab = A.gabarito_por_tela(GAB)
    saida = {}
    for s in (1, 2, 3):
        modelo = detector_tab.carregar(A.modelo_da_dobra(versao, 0, s))
        por_l = {lim: Counter() for lim in A.LIMIARES_MEDIDOS}
        for tela, notas in sorted(gab.items()):
            r = indice[tela]
            pred, passo = A.ler_tela(
                modelo, caminhos.acervo() / r["video"], float(r["t"]), recorte
            )
            for lim in A.LIMIARES_MEDIDOS:
                por_l[lim] += A.contar(notas, A.com_limiar(pred, lim), passo)
        saida[s] = {str(k): dict(v) for k, v in por_l.items()}
        for lim in (0.02, 0.15, 0.5):
            m = A.regra(por_l[lim])
            print(f"{versao} s{s} L {lim}: sim falso {m['nao|sim']}/{m['nao|sim'] + m['nao|nao']}"
                  f" custo {m['sim|nao']}/{m['sim|nao'] + m['sim|sim']}"
                  f" casa {por_l[lim]['casa_certa']}/{por_l[lim]['casadas']}", flush=True)
    (caminhos.TAB_ROTULO / "r4c" / f"medida_t83_{versao}{'_alto' if recorte == 'alto' else ''}.json").write_text(
        json.dumps(saida, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "medida T8.3"):  # protocolo da GPU compartilhada
        codigo = main()
    raise SystemExit(codigo)
