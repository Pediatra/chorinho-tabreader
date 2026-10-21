"""Passo 2: gemeas por sequencia (corda, casa) entre telas.

Sequencia de cada tela: colunas em ordem, cada uma como (corda, casa) das notas;
coluna abafada (so nao_notas com X) entra como 'X'. Compara com SequenceMatcher.
"""

import csv
import difflib
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
LOTE = RAIZ / "data/saida/audio/a4/lote1"
SAIDA = RAIZ / "data/saida/audio/a4/campanitas_alarmes"
ALARMES = {3, 4, 5, 7, 8, 12, 13, 15, 16, 17, 38, 39, 40, 43, 47, 48, 49}


def sequencias(prod: dict, alin: dict) -> dict[int, list[str]]:
    """Sequencia por tela: uma entrada por coluna da sequencia do alinhador.

    Coluna com nota vira ``corda/casa`` (uniao se houver mais de uma nota); coluna
    abafada (rasgueado, so X) vira ``X``.
    """
    notas: dict[tuple[int, int], set[str]] = defaultdict(set)
    for n in prod["notas"]:
        notas[(n["tela"], n["coluna"])].add(f"{n['corda']}/{n['casa']}")
    por_tela: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for c in alin["colunas"]:
        chave = (c["tela"], c["coluna"])
        if c["tipo"] == "abafada":
            valor = "X"
        else:
            valor = "+".join(sorted(notas.get(chave, {"?"})))
        por_tela[c["tela"]].append((c["coluna"], valor))
    return {t: [v for _, v in sorted(cs)] for t, cs in por_tela.items()}


def main() -> int:
    """Calcula razao de similaridade entre telas e grava gemeas.csv."""
    prod = json.loads((LOTE / "transcriptor_campanitas.json").read_text())
    audio = json.loads((LOTE / "v21_transcriptor_campanitas.audio.json").read_text())
    alin = json.loads((LOTE / "alinhado_v21_transcriptor_campanitas.json").read_text())
    seq = sequencias(prod, alin)
    info = {}
    for e in audio["exibicoes"]:
        t = prod["telas"][e["tela"] - 1]
        info[e["tela"]] = {
            "t0": t["exibicoes"][0]["t0"],
            "t1": t["exibicoes"][0]["t1"],
            "T_s": e["T_s"],
            "alarme": e["alarme_leitura"],
            "recusada": e["recusada"],
            "cos": e["cos_medio"],
        }
    linhas = []
    for a in sorted(ALARMES):
        melhores = []
        for b in seq:
            if b == a:
                continue
            r = difflib.SequenceMatcher(None, seq[a], seq[b], autojunk=False).ratio()
            melhores.append((r, b))
        melhores.sort(reverse=True)
        for r, b in melhores[:3]:
            linhas.append({
                "alarme": a,
                "gemea": b,
                "similaridade": round(r, 3),
                "gemea_alarme": b in ALARMES,
                "n_alarme": len(seq[a]),
                "n_gemea": len(seq[b]),
                "t0_alarme": info[a]["t0"], "t1_alarme": info[a]["t1"],
                "t0_gemea": info[b]["t0"], "t1_gemea": info[b]["t1"],
                "T_alarme": info[a]["T_s"], "T_gemea": info[b]["T_s"],
                "gemea_alarme_flag": info[b]["alarme"],
                "gemea_recusada": info[b]["recusada"],
                "cos_gemea": info[b]["cos"],
            })
    with (SAIDA / "gemeas.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    for r in linhas:
        print(r["alarme"], r["gemea"], r["similaridade"], "ACEITA" if not r["gemea_recusada"] else ("recusada" + (" ALARME" if r["gemea_alarme_flag"] else "")),
              r["n_alarme"], r["n_gemea"], r["t0_alarme"], r["t0_gemea"], r["t1_alarme"], r["t1_gemea"],
              sep="\t")
    return 0


if __name__ == "__main__":
    sys.exit(main())
