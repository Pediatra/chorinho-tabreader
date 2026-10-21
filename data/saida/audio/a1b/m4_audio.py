"""M4(b): RMS (janelas de 10 ms), fluxo espectral e descontinuidades de 444 a 453 s."""
import json
import statistics as st

import numpy as np

from tab import audio_extrair, audio_onsets

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
SAIDA = "/app/data/saida/audio/a1b/"
ATRASO = "/app/data/saida/audio/a1/atraso_mvp.json"
T0, T1 = 444.0, 453.0


def main():
    flac, meta = audio_extrair.garantir(VIDEO)
    amostras, taxa = audio_extrair.ler(flac)
    t_am0 = float(meta["t_amostra0"])
    print(f"taxa={taxa} t_amostra0={t_am0} cache={meta.get('cache')} n_amostras={len(amostras)}")
    i0 = audio_extrair.indice_de(T0, meta)
    i1 = audio_extrair.indice_de(T1, meta)
    x = amostras[max(0, i0):i1].astype(np.float64) / 32768.0
    t_base = float(T0)
    # RMS em janelas NAO sobrepostas de 10 ms
    w = int(round(0.010 * taxa))
    n = len(x) // w
    blocos = x[: n * w].reshape(n, w)
    rms = np.sqrt((blocos ** 2).mean(axis=1))
    t_rms = t_base + (np.arange(n) * w + w / 2) / taxa
    db = 20 * np.log10(np.maximum(rms, 1e-7))
    print(f"janelas RMS 10 ms: {n}; RMS dBFS min={db.min():.1f} max={db.max():.1f} "
          f"mediana={np.median(db):.1f}")
    # Fluxo espectral (mesmo pre-processamento do projeto)
    mag, tempos, freqs = audio_onsets.espectrograma(amostras, taxa, t_am0, t0=T0, t1=T1)
    fluxo = audio_onsets.fluxo_espectral(mag)
    print(f"quadros STFT: {len(tempos)} passo={1000*(tempos[1]-tempos[0]):.3f} ms")
    idx_p = audio_onsets.picos(fluxo, tempos)
    top = sorted(idx_p, key=lambda k: -fluxo[k])[:10]
    print("fluxo: top 10 picos (t, valor):")
    for k in sorted(top):
        print(f"  t={tempos[k]:.4f} fluxo={fluxo[k]:.2f}")
    # Descontinuidades no RMS: razao RMS(50 ms depois)/RMS(50 ms antes), e silencios
    m50 = 5  # 5 janelas de 10 ms = 50 ms
    eventos = []
    for k in range(m50, n - m50):
        antes = np.sqrt((rms[k - m50:k] ** 2).mean())
        depois = np.sqrt((rms[k:k + m50] ** 2).mean())
        if antes > 0 and depois > 0:
            r = depois / antes
            if r > 3 or r < 1 / 3:
                eventos.append((float(t_rms[k]), float(r)))
    # agrupa degraus proximos (< 30 ms)
    grupos = []
    for t, r in eventos:
        if grupos and t - grupos[-1][-1][0] < 0.03:
            grupos[-1].append((t, r))
        else:
            grupos.append([(t, r)])
    print(f"degraus de nivel (razao >3x ou <1/3 em 50 ms): {len(grupos)} grupos")
    degraus = []
    for g in grupos:
        t_med = g[len(g) // 2][0]
        r_med = g[len(g) // 2][1]
        degraus.append(dict(t=t_med, razao=r_med, n_janelas=len(g)))
    for d in sorted(degraus, key=lambda d: -abs(np.log(d["razao"])))[:12]:
        print(f"  t={d['t']:.3f} razao={d['razao']:.2f} janelas={d['n_janelas']}")
    # Silencios: janela de 10 ms abaixo de 0,05 x mediana movel de +-0,25 s
    meia = int(0.25 / 0.010)
    silencios = []
    for k in range(n):
        lo, hi = max(0, k - meia), min(n, k + meia + 1)
        med = np.median(rms[lo:hi])
        if med > 0 and rms[k] < 0.05 * med and rms[k] > 0:
            silencios.append(float(t_rms[k]))
    print(f"janelas de 10 ms abaixo de 5% da mediana movel: {len(silencios)}")
    if silencios:
        print("  primeiras:", [round(s, 3) for s in silencios[:12]])
    # Nivel de fundo: percentil 10 do RMS em janelas de 0,5 s (passo 0,25 s)
    fundo = []
    for ini in np.arange(T0, T1 - 0.5, 0.25):
        a = int(round((ini - T0) / 0.010))
        b = a + 50
        fundo.append((float(ini + 0.25), float(np.percentile(db[a:b], 10))))
    print("nivel de fundo (P10 dBFS, janela 0,5 s, passo 0,25 s):")
    for t, v in fundo:
        print(f"  ate {t:.2f} s: P10={v:.1f} dBFS")
    # Marcadores do atraso (t_ini e t_som) no trecho
    ev = json.load(open(ATRASO))["eventos"]
    marc = []
    for e in ev:
        if T0 <= e["t_ini"] <= T1:
            marc.append(dict(t_ini=e["t_ini"], t_som=e["passada2"]["fluxo"]["t_som"],
                             tela=e["tela"], exib=e["exibicao"], col=e["coluna"]))
    marc.sort(key=lambda d: d["t_ini"])
    print(f"marcadores no trecho: {len(marc)}")
    saida = dict(
        taxa=taxa, t_amostra0=t_am0, n_janelas_rms=n,
        rms_t=[float(v) for v in t_rms], rms_db=[float(v) for v in db],
        flux_t=[float(v) for v in tempos], flux=[float(v) for v in fluxo],
        picos_fluxo=[dict(t=float(tempos[k]), valor=float(fluxo[k])) for k in idx_p],
        degraus=degraus, silencios=silencios, fundo=fundo, marcadores=marc,
    )
    with open(SAIDA + "m4_audio.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
