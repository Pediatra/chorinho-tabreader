"""Figura M4: espectrograma 444-453 s com t_ini/t_som, RMS embaixo e diferenca de quadros."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from tab import audio_extrair, audio_onsets  # noqa: E402

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
PASTA = "/app/data/saida/audio/a1b/"
T0, T1 = 444.0, 453.0


def main():
    flac, meta = audio_extrair.garantir(VIDEO)
    amostras, taxa = audio_extrair.ler(flac)
    mag, tempos, freqs = audio_onsets.espectrograma(
        amostras, taxa, float(meta["t_amostra0"]), t0=T0, t1=T1)
    lmag = np.log1p(100.0 * mag)
    m4a = json.load(open(PASTA + "m4_audio.json"))
    m4v = json.load(open(PASTA + "m4_video.json"))
    marc = m4a["marcadores"]
    pares = [p for p in m4v["pares"] if T0 <= p["pts"] <= T1]
    fig, eixos = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1.3, 1.3]})
    ax = eixos[0]
    fmax = 4000
    kf = freqs <= fmax
    ax.imshow(lmag[:, kf].T, origin="lower", aspect="auto", cmap="magma",
              extent=[tempos[0], tempos[-1], 0, fmax])
    for m in marc:
        ax.axvline(m["t_ini"], color="cyan", ls="--", lw=1)
        ax.axvline(m["t_som"], color="lime", ls="-", lw=1)
    ax.axvline(448.5147, color="white", lw=1.5, ls=":")
    ax.set_ylabel("Hz")
    ax.set_title("retrato brasileiro 444-453 s: t_ini (ciano tracejado), t_som (verde), corte 448,515 (branco)")
    ax2 = eixos[1]
    ax2.plot(m4a["rms_t"], m4a["rms_db"], lw=0.8, color="black")
    ax2.axvline(448.5147, color="red", lw=1, ls=":")
    ax2.set_ylabel("RMS dBFS\n(10 ms)")
    ax3 = eixos[2]
    ax3.plot([p["pts"] for p in pares], [p["fora"] for p in pares], "o-", ms=3, lw=0.8,
             label="fora do painel")
    ax3.plot([p["pts"] for p in pares], [p["painel"] for p in pares], "x-", ms=3, lw=0.6,
             label="dentro do painel")
    ax3.axvline(448.5147, color="red", lw=1, ls=":")
    ax3.set_yscale("log")
    ax3.set_ylabel("dif. media\nquadro (tons)")
    ax3.set_xlabel("tempo do video (s)")
    ax3.legend(loc="upper right", fontsize=8)
    ax3.set_xlim(T0, T1)
    fig.tight_layout()
    fig.savefig(PASTA + "m4_corte_444_453.png", dpi=110)
    print("figura salva; marcadores", len(marc), "pares", len(pares))


if __name__ == "__main__":
    main()
