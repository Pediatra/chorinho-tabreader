"""Passo 4: janela. Fluxo espectral e picos em [t0-3, t1+3] para telas alarmadas e uma gemea aceita.

Reexecuta tab.audio_alinhar.alinhar (metodo onsets, o mesmo da v2.1) para obter trecho_tempo
e os t_audio de cada tela. Usa tab.audio_onsets para espectrograma, fluxo e picos.
Saidas: figuras/*.png, janela_densidade.csv, janela_resumo.json.
"""

import csv
import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from tab.audio_alinhar import alinhar, esconder_marcador  # noqa: E402
from tab.audio_extrair import garantir, ler  # noqa: E402
from tab.audio_onsets import espectrograma, fluxo_espectral, picos  # noqa: E402

LOTE = Path("/app/data/saida/audio/a4/lote1")
SAIDA = Path("/app/data/saida/audio/a4/campanitas_alarmes")
VIDEO = "/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4"
ALARMADAS = [3, 38, 17, 13]
GEMEAS = {3: 20, 38: 20, 17: 34, 13: 30}
MARGEM = 3.0


def densidade(t_pk: np.ndarray, a: float, b: float) -> float:
    """Picos por segundo no intervalo [a, b)."""
    if b <= a:
        return 0.0
    return float(np.sum((t_pk >= a) & (t_pk < b)) / (b - a))


def main() -> int:
    """Gera figuras e tabela de densidade para as telas escolhidas."""
    (SAIDA / "figuras").mkdir(exist_ok=True)
    produto = json.loads((LOTE / "transcriptor_campanitas.json").read_text())
    oculto = esconder_marcador(produto)
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    saida = alinhar(oculto, amostras, taxa, t_am0, metodo="onsets")
    res = {e["tela"]: e for e in saida["exibicoes"]}
    tb = {t["id"]: t["exibicoes"][0] for t in produto["telas"]}
    colunas = {}
    for c in saida["colunas"]:
        colunas.setdefault(c["tela"], []).append(c)

    linhas = []
    resumo = {}
    alvos = ALARMADAS + sorted(set(GEMEAS.values()))
    for tela in alvos:
        t0, t1 = tb[tela]["t0"], tb[tela]["t1"]
        a, b = t0 - MARGEM, t1 + MARGEM
        mag, t_on, _ = espectrograma(amostras, taxa, t_am0, t0=a, t1=b)
        fl = fluxo_espectral(mag)
        idx = np.asarray(picos(fl, t_on), dtype=np.int64)
        t_pk = t_on[idx]
        f_pk = fl[idx]
        dur = t1 - t0
        inside = (t_pk >= t0) & (t_pk <= t1)
        forte = f_pk >= np.quantile(fl, 0.75)
        ncol = len(colunas[tela])
        ncol_nota = sum(1 for c in colunas[tela] if c["tipo"] == "nota")
        e = res[tela]
        d_in = densidade(t_pk, t0, t1)
        d_antes = densidade(t_pk, a, t0)
        d_depois = densidade(t_pk, t1, b)
        linha = {
            "tela": tela,
            "papel": "alarme" if tela in ALARMADAS else "gemea_aceita",
            "t0": t0, "t1": t1, "duracao_s": round(dur, 3),
            "colunas_sequencia": ncol, "colunas_nota": ncol_nota,
            "picos_dentro": int(inside.sum()),
            "picos_forte_dentro": int((inside & forte).sum()),
            "densidade_dentro_pps": round(d_in, 2),
            "densidade_antes_pps": round(d_antes, 2),
            "densidade_depois_pps": round(d_depois, 2),
            "colunas_por_s": round(ncol / dur, 2),
            "mediana_intervalo_dentro_s": round(float(np.median(np.diff(t_pk[inside]))), 3)
            if inside.sum() > 2 else None,
            "T_usado_s": e.get("T_usado_s"),
            "trecho_tempo": e.get("trecho_tempo"),
            "trecho_colunas": e.get("trecho_colunas"),
            "n_casadas": e.get("n_casadas"),
            "cos_medio": e.get("cos_medio"),
            "recusada": e.get("recusada_exibicao"),
        }
        linhas.append(linha)
        resumo[tela] = linha
        print(tela, linha["papel"], linha["picos_dentro"], linha["densidade_dentro_pps"],
              linha["densidade_antes_pps"], linha["densidade_depois_pps"], linha["cos_medio"],
              linha["trecho_tempo"], sep="\t")

        fig, ax = plt.subplots(figsize=(13, 4))
        ax.plot(t_on, fl, color="0.3", lw=0.9, label="fluxo espectral")
        ax.plot(t_pk, f_pk, "o", ms=3, color="tab:blue", label="picos (todos)")
        ax.plot(t_pk[inside], f_pk[inside], "o", ms=5, mfc="none", mec="tab:red",
                label="picos dentro de [t0,t1]")
        ax.axvspan(t0, t1, color="0.9", zorder=0, label="exibicao [t0,t1]")
        ax.axvline(t0, color="tab:green", ls="--", label="t0")
        ax.axvline(t1, color="tab:green", ls=":", label="t1")
        tr = e.get("trecho_tempo")
        if tr and tr[0] is not None:
            ax.axvline(tr[0], color="tab:orange", lw=1.5, label="trecho: 1o casado")
            ax.axvline(tr[1], color="tab:orange", lw=1.5, ls="-.", label="trecho: ultimo casado")
        ax.set_xlim(a, b)
        ax.set_xlabel("tempo do video (s)")
        ax.set_ylabel("fluxo espectral")
        ax.set_title(
            f"tela {tela} ({linha['papel']}) cos={linha['cos_medio']} casadas={linha['n_casadas']} "
            f"| dentro {d_in:.1f}/s, antes {d_antes:.1f}/s, depois {d_depois:.1f}/s"
        )
        ax.legend(fontsize=7, loc="upper right", ncol=2)
        fig.tight_layout()
        fig.savefig(SAIDA / "figuras" / f"janela_tela{tela}.png", dpi=110)
        plt.close(fig)

    with (SAIDA / "janela_densidade.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    (SAIDA / "janela_resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
