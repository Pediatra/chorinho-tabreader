"""0211, INFORMATIVA: a T8.4 (já gasta) recontada com o gabarito corrigido pelo dono em 2026-10-22.

Lê a versão escolhida em ``r4g/decisao.json`` (com o ``L`` dos ouros), a dobra 0 e as 3
sementes, com o recorte alto. Conta como ``tab.ataque_r4.contar`` e grava
``r4g/medida_t84.json``. Aceite: "sim" falso ≤ 5 % e custo ≤ 10 %, sementes somadas.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4g/medir_t84.py
"""

import json
from collections import Counter

from tab import ataque_r4 as A
from tab import caminhos, detector_tab
from tab.gpu import trava_gpu

GAB = caminhos.TAB_ROTULO / "r2" / "conferir_t84" / "ataque_t84.json"
INDICE = caminhos.SAIDA / "t84" / "ferramenta" / "indice.json"
DECISAO = caminhos.TAB_ROTULO / "r4g" / "decisao.json"


def main() -> int:
    """Mede, imprime e grava."""
    decisao = json.loads(DECISAO.read_text(encoding="utf-8"))
    versao = decisao["escolhida"]
    L = decisao["versoes"][versao]["L"]
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    gab = A.gabarito_por_tela(GAB)
    saida: dict = {"versao": versao, "L": L, "sementes": {}}
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
    (caminhos.TAB_ROTULO / "r4g" / "medida_t84_informativa.json").write_text(
        json.dumps(saida, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "recontagem informativa T8.4"):  # protocolo da GPU compartilhada
        codigo = main()
    raise SystemExit(codigo)
