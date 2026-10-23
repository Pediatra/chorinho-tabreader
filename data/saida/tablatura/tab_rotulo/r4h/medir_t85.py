"""0214: a prova lacrada T8.5, uma vez só (pré-registro em docs/rodadas/0214-r4h-ligaduras.md).

Mede a versão pedida (``atqb``, que decide; ``atqa``, só informada e depois) com o ``L``
dos ouros de ``r4h/decisao.json``, a dobra 0, as 3 sementes e o recorte alto. Conta como
``tab.ataque_r4.contar`` e grava ``r4h/medida_t85_<versao>.json``. Aceite: "sim" falso
≤ 5 % e custo ≤ 10 %, sementes somadas. Recusa medir de novo uma versão já medida.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tablatura/tab_rotulo/r4h/medir_t85.py atqb
"""

import json
import sys
from collections import Counter

from tab import ataque_r4 as A
from tab import caminhos, detector_tab
from tab.gpu import trava_gpu

GAB = caminhos.TAB_ROTULO / "r2" / "conferir_t85" / "ataque_t85.json"
INDICE = caminhos.SAIDA / "tablatura" / "t85" / "ferramenta" / "indice.json"
DECISAO = caminhos.TAB_ROTULO / "r4h" / "decisao.json"


def main(versao: str) -> int:
    """Mede, imprime e grava."""
    destino = caminhos.TAB_ROTULO / "r4h" / f"medida_t85_{versao}.json"
    # Emenda de 2026-10-23, antes de medir: o dono vai revisar o modo ataque da T8.5 com o
    # seletor corrigido. A medida espera ``r4h/t85_liberada.json``, gravado depois disso.
    if not (caminhos.TAB_ROTULO / "r4h" / "t85_liberada.json").exists():
        raise SystemExit("a T8.5 espera a revisão do dono (falta r4h/t85_liberada.json)")
    if destino.exists():
        raise SystemExit(f"{destino.name} já existe: a T8.5 se mede uma vez só")
    decisao = json.loads(DECISAO.read_text(encoding="utf-8"))
    if versao == "atqb" and not decisao["atqb_passa_nos_ouros"]:
        raise SystemExit("o atqb não passou nos ouros: a T8.5 não se gasta")
    if versao == "atqa" and not (caminhos.TAB_ROTULO / "r4h" / "medida_t85_atqb.json").exists():
        raise SystemExit("o atqa só se mede depois do atqb")
    L = decisao["versoes"][versao]["L"]
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    gab = A.gabarito_por_tela(GAB)
    saida: dict = {"versao": versao, "L": L, "telas": sorted(gab), "sementes": {}}
    soma: Counter = Counter()
    for s in (1, 2, 3):
        modelo = detector_tab.carregar(A.modelo_da_dobra(versao, 0, s))
        por_l = {lim: Counter() for lim in A.LIMIARES_MEDIDOS}
        for tela, notas in sorted(gab.items()):
            r = indice[tela]
            pred, passo = A.ler_tela(modelo, caminhos.acervo() / r["video"], float(r["t"]))
            for lim in A.LIMIARES_MEDIDOS:
                por_l[lim] += A.contar(notas, A.com_limiar(pred, lim), passo)
        m = A.regra(por_l[L])
        soma += m
        saida["sementes"][s] = {str(k): dict(v) for k, v in por_l.items()}
        print(
            f"{versao} s{s} L {L}: sim falso {m['nao|sim']}/{m['nao|sim'] + m['nao|nao']}"
            f" custo {m['sim|nao']}/{m['sim|nao'] + m['sim|sim']}"
            f" casa {por_l[L]['casa_certa']}/{por_l[L]['casadas']}"
            f" não lidas {m['nao|nao_lida'] + m['sim|nao_lida']}",
            flush=True,
        )
    sf = (soma["nao|sim"], soma["nao|sim"] + soma["nao|nao"])
    custo = (soma["sim|nao"], soma["sim|nao"] + soma["sim|sim"])
    passa = sf[0] / sf[1] <= 0.05 and custo[0] / custo[1] <= 0.10
    saida.update({"sim_falso_soma": sf, "custo_soma": custo, "passa": passa})
    print(
        f"soma: sim falso {sf[0]}/{sf[1]} ({sf[0] / sf[1]:.1%}) custo {custo[0]}/{custo[1]}"
        f" ({custo[0] / custo[1]:.1%}) -> {'PASSA' if passa else 'REPROVA'}",
        flush=True,
    )
    destino.write_text(json.dumps(saida, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "medida T8.5"):  # protocolo da GPU compartilhada
        codigo = main(sys.argv[1])
    raise SystemExit(codigo)
