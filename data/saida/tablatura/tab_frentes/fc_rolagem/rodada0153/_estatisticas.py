"""Estatística da 0153 (stdlib): aceite congelado por vídeo, sobre os saltos definidos.

Lê rodada0153/<janela>/metodo.json e imprime, por grupo (mr. tabs, kenneth):
n com referência, definidos, indefinidos por motivo, mediana e máximo do erro do
método, e erro do consenso antigo e de dx_a para comparação.
"""

import json
import statistics
from collections import Counter
from pathlib import Path

R0153 = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0153")
GRUPOS = {
    "mrtabs": ["mrtabs_w150", "mrtabs_w180", "mrtabs_w210"],
    "kenneth": ["kenneth_w62", "kenneth_w92", "kenneth_w122"],
}


def main() -> int:
    """Imprime o resumo por grupo e grava resumo.json."""
    resumo = {}
    for grupo, janelas in GRUPOS.items():
        linhas = []
        for j in janelas:
            linhas += json.loads((R0153 / j / "metodo.json").read_text(encoding="utf-8"))
        defin = [x for x in linhas if x["dx_metodo"] is not None]
        indef = Counter(x["motivo"] for x in linhas if x["dx_metodo"] is None)
        erros = [x["erro_metodo"] for x in defin]
        cons = [x["erro_consenso"] for x in linhas if x["erro_consenso"] is not None]
        ea = [x["erro_a"] for x in linhas]
        med = statistics.median(erros) if erros else None
        mx = max(erros) if erros else None
        passa = bool(erros) and med <= 1.0 and mx <= 5.0
        r = {
            "n_referencia": len(linhas),
            "n_definidos": len(defin),
            "indefinidos": dict(indef),
            "erro_metodo_mediana": med,
            "erro_metodo_max": mx,
            "erro_metodo_max_salto": (
                max(defin, key=lambda x: x["erro_metodo"])["t_antes"] if defin else None
            ),
            "n_consenso_valido": len(cons),
            "erro_consenso_mediana": statistics.median(cons) if cons else None,
            "erro_consenso_max": max(cons) if cons else None,
            "erro_a_mediana": statistics.median(ea) if ea else None,
            "erro_a_max": max(ea) if ea else None,
            "aceite_passa": passa,
            "saltos": linhas,
        }
        resumo[grupo] = r
        print(
            f"{grupo}: ref={r['n_referencia']} definidos={r['n_definidos']} "
            f"indef={r['indefinidos']}"
        )
        print(
            f"  metodo: mediana={med} max={mx} (salto {r['erro_metodo_max_salto']})"
        )
        print(
            f"  consenso 0152 (n={len(cons)}): mediana={r['erro_consenso_mediana']}"
            f" max={r['erro_consenso_max']}"
        )
        print(f"  dx_a: mediana={r['erro_a_mediana']} max={r['erro_a_max']}")
        print(f"  aceite passa: {passa}")
    (R0153 / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    main()
