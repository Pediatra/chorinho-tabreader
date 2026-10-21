"""0211: a decisão do produto entre _atqt, _atqe e _atqa (recorte alto), só pelos ouros.

Para cada versão: o limiar da técnica (``escolher_limiar``) e o L da faixa "não sei"
(``escolher_nao_sei``) escolhidos nos ouros com as 3 sementes somadas; no L, por semente,
o "sim" falso (``nao|sim``), o custo (``sim|nao``) e a casa dos ouros, com a regra do slide.
Fica a de menor "sim" falso somado, com custo ≤ 10 % e casa ≥ 2660 (pior _atqt antigo) em
todas as sementes. Não lê a T8.4.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4g/decidir.py
"""

import json

from tab import ataque_r4 as A
from tab import caminhos

VERSOES = ("atqt", "atqe", "atqa")
CASA_MINIMA = 2660
CUSTO_MAXIMO = 0.10


def main() -> int:
    """Imprime a tabela e grava ``r4g/decisao.json``."""
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
        ok = all(n / d <= CUSTO_MAXIMO for n, d in custo) and min(casa) >= CASA_MINIMA
        linhas[v] = {
            "limiar_tecnica": tec,
            "L": L,
            "sim_falso": sf,
            "sim_falso_soma": sum(n for n, _ in sf),
            "custo": custo,
            "casa": casa,
            "t82_sim_falso": t82,
            "passa_custo_e_casa": ok,
        }
        print(
            f"{v}: técnica {tec} L {L} | sim falso "
            + " · ".join(f"{n}/{d}" for n, d in sf)
            + " | custo "
            + " · ".join(f"{n}/{d}" for n, d in custo)
            + f" | casa {min(casa)}–{max(casa)} | T8.2 "
            + " · ".join(f"{n}/{d}" for n, d in t82)
            + f" | custo e casa ok: {ok}",
            flush=True,
        )
    validas = [v for v in VERSOES if linhas[v]["passa_custo_e_casa"]]
    escolhida = min(validas, key=lambda v: (linhas[v]["sim_falso_soma"], VERSOES.index(v)))
    print("escolhida:", escolhida, flush=True)
    (caminhos.TAB_ROTULO / "r4g" / "decisao.json").write_text(
        json.dumps({"versoes": linhas, "escolhida": escolhida}, indent=1) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
