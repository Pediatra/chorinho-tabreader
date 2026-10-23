"""0215: o _atqs passa nos ouros? (pré-registro em docs/rodadas/0215-expressao-e-t85.md).

Para ``_atqr`` e ``_atqs`` (recorte alto): o limiar da técnica (``escolher_limiar``) e o L
da faixa "não sei" (``escolher_nao_sei``) escolhidos nos ouros, com as 3 sementes somadas;
no L, por semente, o "sim" falso, o custo e a casa dos ouros, com a regra do slide. O
``_atqs`` passa nos ouros se o custo fica ≤ 10 % em todas as sementes, se a pior semente de
casa não fica mais de 2 abaixo da pior do ``_atqr`` e se o "sim" falso somado não passa o do
``_atqr`` mais 3, nos ouros revisados pelo dono. Não lê a T8.6.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tablatura/tab_rotulo/r5/decidir.py
"""

import json

from tab import ataque_r4 as A
from tab import caminhos

VERSOES = ("atqr", "atqs")
FOLGA_CASA = 2
CUSTO_MAXIMO = 0.10
FOLGA_SIM_FALSO = 3


def main() -> int:
    """Imprime a tabela e grava ``r5/decisao.json``."""
    linhas = {}
    for v in VERSOES:
        medidas = [
            json.loads(
                (caminhos.TAB_ROTULO / "r4a" / f"medida_{v}_s{s}_alto.json").read_text(
                    encoding="utf-8"
                )
            )
            for s in (1, 2, 3)
        ]
        tec, L = A.escolher_limiar(medidas), A.escolher_nao_sei(medidas)
        sf, custo, casa, t82 = [], [], [], []
        for m in medidas:
            o = m["ouros"]["por_limiar"][str(L)]
            r = A.regra(o)
            sf.append((r["nao|sim"], r["nao|sim"] + r["nao|nao"]))
            custo.append((r["sim|nao"], r["sim|nao"] + r["sim|sim"]))
            casa.append(o["casa_certa"])
            r82 = A.regra(m["t82"]["por_limiar"][str(L)])
            t82.append((r82["nao|sim"], r82["nao|sim"] + r82["nao|nao"]))
        linhas[v] = {
            "limiar_tecnica": tec,
            "L": L,
            "sim_falso": sf,
            "sim_falso_soma": sum(n for n, _ in sf),
            "custo": custo,
            "casa": casa,
            "t82_sim_falso": t82,
            "custo_ok": all(n / d <= CUSTO_MAXIMO for n, d in custo),
        }
        print(
            f"{v}: técnica {tec} L {L} | sim falso "
            + " · ".join(f"{n}/{d}" for n, d in sf)
            + " | custo "
            + " · ".join(f"{n}/{d}" for n, d in custo)
            + f" | casa {min(casa)}–{max(casa)} | T8.2 "
            + " · ".join(f"{n}/{d}" for n, d in t82),
            flush=True,
        )
    b = linhas["atqs"]
    passa = (
        b["custo_ok"]
        and min(b["casa"]) >= min(linhas["atqr"]["casa"]) - FOLGA_CASA
        and b["sim_falso_soma"] <= linhas["atqr"]["sim_falso_soma"] + FOLGA_SIM_FALSO
    )
    print("atqs passa nos ouros:", passa, flush=True)
    (caminhos.TAB_ROTULO / "r5" / "decisao.json").write_text(
        json.dumps({"versoes": linhas, "atqs_passa_nos_ouros": passa}, indent=1) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
