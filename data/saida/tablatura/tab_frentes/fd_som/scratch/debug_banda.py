import sys

import numpy as np

sys.path.insert(0, "/app")
from tab.som_casa_energia import (  # noqa: E402
    espectro_local,
    energia_faixa_db,
    frequencia_midi,
)

TAXA = 22050
midi = 52
t = np.arange(int(3.0 * TAXA)) / TAXA
f0 = frequencia_midi(midi)
s = np.zeros_like(t)
m = (t >= 1.5) & (t < 3.0)
for k, a in ((1, 1.0), (2, 0.5), (3, 0.25)):
    s[m] += 0.3 * a * np.sin(2 * np.pi * k * f0 * t[m])
rng = np.random.default_rng(1)
s = s + 1e-3 * rng.standard_normal(len(t))

tempos, freqs, mag2 = espectro_local(s, TAXA, 1.5)
print("quadros", len(tempos), "tempos[0..2]", tempos[:3], "tempos[-1]", tempos[-1])
print("bin", freqs[1] - freqs[0], "f0", f0)
e = energia_faixa_db(freqs, mag2, f0)
print("energia no f0 (dB) por quadro, amostras:")
print(np.round(e[::6], 1))
print("mediana", np.median(e), "max", e.max(), "min", e.min())
ataque = (tempos >= 1.5 - 0.03) & (tempos <= 1.5 + 0.12)
print("ataque max", e[ataque].max(), "D1 =", e[ataque].max() - np.median(e))
