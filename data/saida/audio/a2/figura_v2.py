"""Espectrograma com t_audio (alinhador) e t_som da régua. Uso: figura_v2.py ALINHADO PREFIXO T,E ...

Diagnóstico visual. Ciano = t_audio do alinhador; verde tracejado = t_som da régua (fluxo).
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from tab.audio_extrair import garantir, ler  # noqa: E402
from tab.audio_onsets import espectrograma  # noqa: E402

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
REGUA = "data/saida/audio/a1/atraso_mvp.json"
JANELA_S = 12.0


def main(argv):
    alinhado_path, prefixo = argv[1], argv[2]
    alvos = [tuple(int(x) for x in a.split(",")) for a in argv[3:]]
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    alin = json.load(open(alinhado_path, encoding="utf-8"))
    regua = json.load(open(REGUA, encoding="utf-8"))
    exib = {(e["tela"], e["exibicao"]): e for e in alin["exibicoes"]}
    for tela, ex in alvos:
        info = exib[(tela, ex)]
        a, b = info["janela"]
        t_ini = float(os.environ.get("T_INI", a + 0.5))
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
            e["coluna"]: e["passada2"]["fluxo"]["t_som"]
            for e in regua["eventos"]
            if e["tela"] == tela and e["exibicao"] == ex
        }
        for _, t in reg.items():
            if t is not None and t_ini <= t <= t_fim:
                ax.axvline(t, color="lime", lw=1.0, ls="--")
        ax.set_title(
            f"tela {tela}, exibição {ex} (v2): ciano = t_audio, verde tracejado = "
            f"t_som da régua; janela de {t_fim - t_ini:.1f} s"
        )
        ax.set_xlabel("tempo do vídeo (s)")
        ax.set_ylabel("Hz")
        fig.tight_layout()
        caminho = f"{prefixo}_{tela}_{ex}" + os.environ.get("SUFIXO", "") + ".png"
        fig.savefig(caminho, dpi=110)
        plt.close(fig)
        print("figura:", caminho, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
