"""Passo 5: janela das 17 alarmadas (sem figuras). Densidade, silencio e picos por coluna.

Mesmo calculo do passo 4 (MARGEM=3 s), para todas as telas com alarme_leitura.
Silencio = fracao de quadros de 50 ms dentro de [t0,t1] com fluxo abaixo de 15% do P90 do fluxo na janela.
Saida: janela_17_alarmes.csv.
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np

from tab.audio_alinhar import alinhar, esconder_marcador
from tab.audio_extrair import garantir, ler
from tab.audio_onsets import espectrograma, fluxo_espectral, picos

LOTE = Path("/app/data/saida/audio/a4/lote1")
SAIDA = Path("/app/data/saida/audio/a4/campanitas_alarmes")
VIDEO = "/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4"
ALARMES = [3, 4, 5, 7, 8, 12, 13, 15, 16, 17, 38, 39, 40, 43, 47, 48, 49]
MARGEM = 3.0


def main() -> int:
    """Calcula metricas de janela para as 17 alarmadas e grava o CSV."""
    produto = json.loads((LOTE / "transcriptor_campanitas.json").read_text())
    oculto = esconder_marcador(produto)
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    saida = alinhar(oculto, amostras, taxa, t_am0, metodo="onsets")
    res = {e["tela"]: e for e in saida["exibicoes"]}
    tb = {t["id"]: t["exibicoes"][0] for t in produto["telas"]}
    ncol = {}
    for c in saida["colunas"]:
        ncol[c["tela"]] = ncol.get(c["tela"], 0) + 1
    linhas = []
    for tela in ALARMES:
        t0, t1 = tb[tela]["t0"], tb[tela]["t1"]
        a, b = t0 - MARGEM, t1 + MARGEM
        mag, t_on, _ = espectrograma(amostras, taxa, t_am0, t0=a, t1=b)
        fl = fluxo_espectral(mag)
        t_pk = t_on[np.asarray(picos(fl, t_on), dtype=np.int64)]
        dur = t1 - t0
        dentro = (t_pk >= t0) & (t_pk <= t1)
        p90 = np.quantile(fl, 0.9)
        mask = (t_on >= t0) & (t_on <= t1)
        frac_sil = float(np.mean(fl[mask] < 0.15 * p90)) if mask.any() else None
        n_pk = int(dentro.sum())
        linhas.append({
            "tela": tela,
            "t0": t0, "t1": t1, "dur_s": round(dur, 2),
            "colunas": ncol.get(tela),
            "picos_dentro": n_pk,
            "picos_por_coluna": round(n_pk / ncol[tela], 2) if ncol.get(tela) else None,
            "dens_dentro_pps": round(n_pk / dur, 2),
            "dens_antes_pps": round(float(np.sum((t_pk >= a) & (t_pk < t0)) / MARGEM), 2),
            "dens_depois_pps": round(float(np.sum((t_pk > t1) & (t_pk <= b)) / MARGEM), 2),
            "fracao_silencio_dentro": round(frac_sil, 3) if frac_sil is not None else None,
            "n_casadas": res[tela]["n_casadas"],
            "cos_medio": res[tela]["cos_medio"],
            "trecho_colunas": res[tela]["trecho_colunas"],
        })
        print(tela, linhas[-1]["dens_dentro_pps"], linhas[-1]["picos_por_coluna"],
              linhas[-1]["fracao_silencio_dentro"], linhas[-1]["trecho_colunas"], sep="\t")
    with (SAIDA / "janela_17_alarmes.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
