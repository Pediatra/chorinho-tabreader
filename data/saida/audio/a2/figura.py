"""Espectrograma com t_audio (alinhador) e t_som da régua, para duas exibições. Diagnóstico."""

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from tab.audio_extrair import garantir, ler  # noqa: E402
from tab.audio_onsets import espectrograma  # noqa: E402

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
ALINHADO = "data/saida/audio/a2/alinhado_onsets_r1.json"
REGUA = "data/saida/audio/a1/atraso_mvp.json"
SAIDA = "data/saida/audio/a2/figuras/{tela}_{exib}_onsets.png"
ALVOS = [(4, 0), (13, 0)]
JANELA_S = 12.0


def main():
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    alin = json.load(open(ALINHADO, encoding="utf-8"))
    regua = json.load(open(REGUA, encoding="utf-8"))
    exib = {(e["tela"], e["exibicao"]): e for e in alin["exibicoes"]}
    for tela, ex in ALVOS:
        info = exib[(tela, ex)]
        a, b = info["janela"]
        t_ini = a + 0.5
        t_fim = min(b - 0.5, t_ini + JANELA_S)
        mag, tempos, freqs = espectrograma(amostras, taxa, t_am0, t0=t_ini, t1=t_fim)
        db = 20 * np.log10(mag.T + 1e-9)
        fig, ax = plt.subplots(figsize=(12, 5))
        mascara = (freqs >= 60) & (freqs <= 1500)
        ax.imshow(
            db[mascara],
            origin="lower",
            aspect="auto",
            extent=[tempos[0], tempos[-1], freqs[mascara][0], freqs[mascara][-1]],
            cmap="magma",
            vmin=np.percentile(db, 60),
            vmax=np.percentile(db, 99.9),
        )
        cols = [c for c in alin["colunas"] if c["tela"] == tela and c["exibicao"] == ex]
        for c in cols:
            t = c["t_audio"]
            if t is not None and t_ini <= t <= t_fim:
                ax.axvline(t, color="cyan", lw=1.2)
                ax.text(t, 1450, str(c["coluna"]), color="cyan", fontsize=8, ha="center")
        reg = {
            (e["coluna"]): e["passada2"]["fluxo"]["t_som"]
            for e in regua["eventos"]
            if e["tela"] == tela and e["exibicao"] == ex
        }
        for col, t in reg.items():
            if t is not None and t_ini <= t <= t_fim:
                ax.axvline(t, color="lime", lw=1.0, ls="--")
        ax.set_title(
            f"tela {tela}, exibição {ex}: ciano = t_audio do alinhador, "
            f"verde tracejado = t_som da régua (janela de {t_fim - t_ini:.1f} s)"
        )
        ax.set_xlabel("tempo do vídeo (s)")
        ax.set_ylabel("Hz")
        fig.tight_layout()
        caminho = SAIDA.format(tela=tela, exib=ex)
        fig.savefig(caminho, dpi=110)
        plt.close(fig)
        print("figura:", caminho, "colunas na janela:", sum(1 for c in cols if c["t_audio"] is not None and t_ini <= c["t_audio"] <= t_fim))
    return 0


if __name__ == "__main__":
    sys.exit(main())
