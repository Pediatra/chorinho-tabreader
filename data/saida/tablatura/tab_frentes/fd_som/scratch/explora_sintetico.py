import sys

import numpy as np

sys.path.insert(0, "/app")
from tab.som_casa_energia import frequencia_midi, pontuar  # noqa: E402

TAXA = 22050


def sinal(midi, inicio, duracao, total, ruido, amp=0.3, parciais=((1, 1.0), (2, 0.5), (3, 0.25))):
    t = np.arange(int(total * TAXA)) / TAXA
    f0 = frequencia_midi(midi)
    s = np.zeros_like(t)
    m = (t >= inicio) & (t < inicio + duracao)
    for k, a in parciais:
        s[m] += amp * a * np.sin(2 * np.pi * k * f0 * t[m])
    rng = np.random.default_rng(1)
    return s + ruido * rng.standard_normal(len(t))


for ruido in (1e-3, 0.01, 0.05):
    for midi in (40, 52):
        x = sinal(midi, 1.5, 2.0, 3.0, ruido)
        vals = {m: pontuar(x, TAXA, 1.5, m)["score"] for m in (midi - 2, midi - 1, midi, midi + 1, midi + 2, midi + 12)}
        print("ruido", ruido, "nota", midi, {k: (None if v is None else round(v, 1)) for k, v in vals.items()})
