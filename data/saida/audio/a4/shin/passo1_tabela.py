"""Passo 1: tabela por exibição (42 linhas) e comparação recusadas x aceitas.

Lê o produto (A2) e o alinhamento (A2). Não toca no pipeline; só stdlib.
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

    # Notas por tela (a partir do produto).
    notas_por_tela: dict[int, list[dict]] = {}
    for n in prod["notas"]:
        notas_por_tela.setdefault(int(n["tela"]), []).append(n)

    # Duração e exibições do produto por tela.
    exib_prod: dict[tuple[int, int], dict] = {}
    for tela in prod["telas"]:
        for i, ex in enumerate(tela["exibicoes"]):
            exib_prod[(int(tela["id"]), i)] = ex

    linhas = []
    for ex in alin["exibicoes"]:
        tela = int(ex["tela"])
        idx = int(ex["exibicao"])
        pex = exib_prod[(tela, idx)]
        dur = float(pex["t1"]) - float(pex["t0"])
        notas = notas_por_tela.get(tela, [])
        n_notas = len(notas)
        n_gt7 = sum(1 for n in notas if int(n["casa"]) > 7)
        conf = [float(n["confianca"]) for n in notas if n.get("confianca") is not None]
        n_cand = int(ex["n_candidatos"])
        linhas.append(
            {
                "tela": tela,
                "exibicao": idx,
                "recusada": bool(ex["recusada_exibicao"]),
                "motivo": ex.get("motivo_exibicao") or "",
                "n_colunas": int(ex["n_colunas"]),
                "n_casadas": int(ex.get("n_casadas") or 0),
                "cos_medio": ex.get("cos_medio"),
                "T_usado_s": ex.get("T_usado_s"),
                "dur_s": round(dur, 3),
                "n_candidatos": n_cand,
                "cand_por_s": round(n_cand / dur, 3) if dur > 0 else None,
                "n_notas_tela": n_notas,
                "frac_casa_gt7": round(n_gt7 / n_notas, 4) if n_notas else None,
                "conf_media_produto": round(st.mean(conf), 4) if conf else None,
            }
        )

    campos = list(linhas[0].keys())
    with open(f"{SAIDA}/tabela_exibicoes.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    with open(f"{SAIDA}/tabela_exibicoes.json", "w", encoding="utf-8") as f:
        json.dump(linhas, f, ensure_ascii=False, indent=1)

    # Comparação recusadas x aceitas (medianas).
    campos_cmp = [
        "n_colunas",
        "n_casadas",
        "cos_medio",
        "T_usado_s",
        "dur_s",
        "cand_por_s",
        "frac_casa_gt7",
        "conf_media_produto",
    ]
    comp = {}
    for grupo, nome in ((True, "recusadas"), (False, "aceitas")):
        sub = [r for r in linhas if r["recusada"] == grupo]
        comp[nome] = {"n": len(sub)}
        for c in campos_cmp:
            vals = [r[c] for r in sub if r[c] is not None]
            comp[nome][c] = round(st.median(vals), 4) if vals else None
    print(json.dumps(comp, ensure_ascii=False, indent=1))
    with open(f"{SAIDA}/comparacao_medianas.json", "w", encoding="utf-8") as f:
        json.dump(comp, f, ensure_ascii=False, indent=1)

    print(f"exibicoes={len(linhas)} recusadas={sum(r['recusada'] for r in linhas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
