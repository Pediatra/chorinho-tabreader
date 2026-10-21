"""Passo 1: tabela das exibicoes com alarme_leitura, e motivos por coluna.

Le so JSON. Nao altera nenhum arquivo de entrada.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
LOTE = RAIZ / "data/saida/audio/a4/lote1"
SAIDA = RAIZ / "data/saida/audio/a4/campanitas_alarmes"
VIDEO = "transcriptor_campanitas"


def main() -> int:
    """Gera tabela_alarmes.csv e tabela_todas_telas.csv."""
    audio = json.loads((LOTE / f"v21_{VIDEO}.audio.json").read_text())
    alin = json.loads((LOTE / f"alinhado_v21_{VIDEO}.json").read_text())
    prod = json.loads((LOTE / f"{VIDEO}.json").read_text())

    t_por_tela = {t["id"]: t for t in prod["telas"]}
    colunas_por_tela: dict[int, list[dict]] = {}
    for c in alin["colunas"]:
        colunas_por_tela.setdefault(c["tela"], []).append(c)
    notas_por_tela: dict[int, int] = Counter(n["tela"] for n in prod["notas"])

    cab = [
        "tela", "exibicao", "t0", "t1", "duracao_s", "n_colunas_produto",
        "n_colunas_sequencia", "n_abafadas", "n_notas_produto", "T_s",
        "trecho_colunas", "n_casadas", "n_abafadas_casadas", "cos_medio",
        "recusada", "motivo_exibicao", "rasgueado", "alarme_leitura",
        "n_fora_do_trecho", "n_sem_ataque_casado", "n_exibicao_recusada",
        "n_cosseno_baixo", "n_afirmadas",
    ]
    linhas = []
    for e in audio["exibicoes"]:
        tela = e["tela"]
        t = t_por_tela[tela]["exibicoes"][e["exibicao"]]
        cols = colunas_por_tela.get(tela, [])
        motivos = Counter(c["motivo"] for c in cols if c["motivo"])
        n_ab = sum(1 for c in cols if c["tipo"] == "abafada")
        linhas.append({
            "tela": tela,
            "exibicao": e["exibicao"],
            "t0": t["t0"],
            "t1": t["t1"],
            "duracao_s": round(t["t1"] - t["t0"], 3),
            "n_colunas_produto": len({c["coluna"] for c in cols if c["tipo"] == "nota"}),
            "n_colunas_sequencia": len(cols),
            "n_abafadas": n_ab,
            "n_notas_produto": notas_por_tela.get(tela, 0),
            "T_s": e["T_s"],
            "trecho_colunas": e["trecho_colunas"],
            "n_casadas": e["n_casadas"],
            "n_abafadas_casadas": e["n_abafadas_casadas"],
            "cos_medio": e["cos_medio"],
            "recusada": e["recusada"],
            "motivo_exibicao": e["motivo"],
            "rasgueado": e["rasgueado"],
            "alarme_leitura": e["alarme_leitura"],
            "n_fora_do_trecho": motivos.get("fora_do_trecho", 0),
            "n_sem_ataque_casado": motivos.get("sem_ataque_casado", 0),
            "n_exibicao_recusada": motivos.get("exibicao_recusada", 0),
            "n_cosseno_baixo": motivos.get("cosseno_baixo", 0),
            "n_afirmadas": sum(1 for c in cols if c["t_audio"] is not None),
        })

    with (SAIDA / "tabela_todas_telas.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cab)
        w.writeheader()
        w.writerows(linhas)
    alarmes = [r for r in linhas if r["alarme_leitura"]]
    with (SAIDA / "tabela_alarmes.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cab)
        w.writeheader()
        w.writerows(alarmes)

    print(f"telas={len(linhas)} alarmes={len(alarmes)}")
    for r in alarmes:
        print(
            r["tela"], r["t0"], r["t1"], r["n_colunas_produto"],
            r["n_colunas_sequencia"], r["n_casadas"], r["cos_medio"],
            r["n_abafadas"], r["n_fora_do_trecho"], r["n_sem_ataque_casado"],
            r["n_exibicao_recusada"], sep="\t",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
