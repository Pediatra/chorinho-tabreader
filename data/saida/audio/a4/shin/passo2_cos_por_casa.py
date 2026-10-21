"""Passo 2: cosseno por coluna afirmada, em exibições aceitas, por faixa de casa.

Colunas afirmadas = registros com t_audio nao nulo. Dois cortes:
(a) toda nota da coluna com casa <= 7 x alguma nota com casa > 7;
(b) por casa: colunas que contêm uma nota naquela casa (uma coluna pode entrar em
    mais de um balde, por ter mais de uma nota).
"""

import csv
import json
import statistics as st
import sys

BASE = "/var/home/gabriel/Projects/chorinho-dataset/data/saida/audio"
PRODUTO = f"{BASE}/a2/produtos/shin_izumi_room_335.json"
ALINH = f"{BASE}/a2/produtos/alinhado_shin_izumi_room_335.json"
SAIDA = f"{BASE}/a4/shin"


def main() -> int:
    with open(PRODUTO, encoding="utf-8") as f:
        prod = json.load(f)
    with open(ALINH, encoding="utf-8") as f:
        alin = json.load(f)

    recusada = {
        (int(e["tela"]), int(e["exibicao"])): bool(e["recusada_exibicao"])
        for e in alin["exibicoes"]
    }
    notas_col: dict[tuple[int, int], list[int]] = {}
    for n in prod["notas"]:
        chave = (int(n["tela"]), int(n["coluna"]))
        notas_col.setdefault(chave, []).append(int(n["casa"]))

    afirmadas = []
    for c in alin["colunas"]:
        if c["t_audio"] is None or c["cos"] is None:
            continue
        tela, ex = int(c["tela"]), int(c["exibicao"])
        if recusada[(tela, ex)]:
            continue
        casas = notas_col.get((tela, int(c["coluna"])), [])
        afirmadas.append(
            {
                "tela": tela,
                "coluna": int(c["coluna"]),
                "cos": float(c["cos"]),
                "casas": casas,
                "max_casa": max(casas) if casas else None,
            }
        )

    resultado = {"n_afirmadas_em_aceitas": len(afirmadas)}

    sem_alta = [a["cos"] for a in afirmadas if a["casas"] and a["max_casa"] <= 7]
    com_alta = [a["cos"] for a in afirmadas if a["casas"] and a["max_casa"] > 7]
    resultado["corte_a"] = {
        "todas_casas_le7": {
            "n": len(sem_alta),
            "mediana_cos": round(st.median(sem_alta), 4) if sem_alta else None,
        },
        "alguma_casa_gt7": {
            "n": len(com_alta),
            "mediana_cos": round(st.median(com_alta), 4) if com_alta else None,
        },
        "sem_nota_no_produto": sum(1 for a in afirmadas if not a["casas"]),
    }

    por_casa = []
    for k in range(0, 25):
        vals = [a["cos"] for a in afirmadas if k in a["casas"]]
        if not vals:
            continue
        por_casa.append(
            {
                "casa": k,
                "n_colunas": len(vals),
                "mediana_cos": round(st.median(vals), 4),
                "media_cos": round(st.mean(vals), 4),
            }
        )
    resultado["corte_b_por_casa"] = por_casa

    with open(f"{SAIDA}/cos_por_casa.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    with open(f"{SAIDA}/cos_por_casa.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(por_casa[0].keys()))
        w.writeheader()
        w.writerows(por_casa)
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
