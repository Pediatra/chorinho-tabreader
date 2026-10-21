"""Passo 6: picos de fluxo por coluna para TODAS as 52 telas (alarmadas e aceitas).

Mesma janela do alinhador (MARGEM=3 s para o fluxo de exibicao) e mesmos picos. Diagnostico:
se alarmadas tem mais picos por coluna do que aceitas, o fluxo nao e um ataque por coluna
(rasgueado/ressonancia), e o casamento falha. Saida: picos_todas_telas.csv.
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np

from tab.audio_alinhar import alinhar, esconder_marcador
from tab.audio_produto import alarme_leitura
from tab.audio_extrair import garantir, ler
from tab.audio_onsets import espectrograma, fluxo_espectral, picos

LOTE = Path("/app/data/saida/audio/a4/lote1")
SAIDA = Path("/app/data/saida/audio/a4/campanitas_alarmes")
VIDEO = "/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4"
MARGEM = 3.0


def main() -> int:
    """Conta picos de fluxo dentro de [t0,t1] por coluna, para todas as telas."""
    produto = json.loads((LOTE / "transcriptor_campanitas.json").read_text())
    oculto = esconder_marcador(produto)
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    saida = alinhar(oculto, amostras, taxa, t_am0, metodo="onsets")
    res = {e["tela"]: e for e in saida["exibicoes"]}
    tb = {t["id"]: t["exibicoes"][0] for t in produto["telas"]}
    ncol: dict[int, int] = {}
    for c in saida["colunas"]:
        ncol[c["tela"]] = ncol.get(c["tela"], 0) + 1
    linhas = []
    for tela in sorted(tb):
        t0, t1 = tb[tela]["t0"], tb[tela]["t1"]
        mag, t_on, _ = espectrograma(amostras, taxa, t_am0, t0=t0 - MARGEM, t1=t1 + MARGEM)
        fl = fluxo_espectral(mag)
        t_pk = t_on[np.asarray(picos(fl, t_on), dtype=np.int64)]
        n_pk = int(np.sum((t_pk >= t0) & (t_pk <= t1)))
        n = ncol.get(tela, 0)
        r = res[tela]
        linhas.append({
            "tela": tela,
            "alarme_leitura": alarme_leitura(bool(r.get("recusada_exibicao")), r.get("cos_medio"), bool(r.get("rasgueado", False))),
            "recusada": r.get("recusada_exibicao"),
            "n_casadas": r.get("n_casadas", 0),
            "cos_medio": r.get("cos_medio"),
            "colunas": n,
            "picos_dentro": n_pk,
            "picos_por_coluna": round(n_pk / n, 3) if n else None,
            "dur_s": round(t1 - t0, 3),
        })
        print(tela, linhas[-1]["alarme_leitura"], n, n_pk, round(n_pk / n, 2) if n else None, sep="\t")
    with (SAIDA / "picos_todas_telas.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
