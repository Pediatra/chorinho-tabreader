import sys
sys.path.insert(0, "/app")
import numpy as np
from tests.test_audio_onsets import _dedilhado, NOTAS_DEDILHADO, T_AMOSTRA0, TAXA
from tab.audio_onsets import espectrograma, fluxo_espectral, picos, fluxo_nas_alturas, mascara_alturas

amostras = _dedilhado(NOTAS_DEDILHADO, 9.0)
mag, tempos, freqs = espectrograma(amostras, TAXA, T_AMOSTRA0)
fl = fluxo_espectral(mag)
pk = np.asarray(picos(fl, tempos))
print("picos", len(pk), "notas", len(NOTAS_DEDILHADO))
for t_on, m in NOTAS_DEDILHADO:
    alvo = T_AMOSTRA0 + t_on
    j = np.flatnonzero(np.abs(tempos[pk]-alvo) <= 0.15)
    best = pk[j[np.argmin(np.abs(tempos[pk[j]]-alvo))]]
    print(f"nota {m} alvo {alvo:.4f} pico {tempos[best]:.4f} erro_ms {1000*(tempos[best]-alvo):+.2f} quadro_k {best} fluxo {fl[best]:.2f} mediana {np.median(fl):.2f} max {fl.max():.1f}")
# leakage: magnitude nearest bins at onset frame of note 64, for alturas
amostras2 = _dedilhado([(1.0, 64)], 2.5)
mag2, t2, f2 = espectrograma(amostras2, TAXA, 0.0)
k = int(np.argmin(np.abs(t2 - 1.0 - 0.02)))
print("bins 29..34 Hz:", np.round(f2[29:35],1).tolist())
print("mag no quadro de 1,02 s:", np.round(mag2[k, 29:35],2).tolist())
c = fluxo_nas_alturas(mag2, f2, [64]); v = fluxo_nas_alturas(mag2, f2, [65])
print("mascara 64 bins:", np.flatnonzero(mascara_alturas(f2,[64])).tolist(), "mascara 65 bins:", np.flatnonzero(mascara_alturas(f2,[65])).tolist())
print("max c64", c.max(), "max c65", v.max(), "razao", v.max()/c.max())
