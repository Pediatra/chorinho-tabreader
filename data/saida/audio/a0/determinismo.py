"""Determinismo: extrai de novo para /tmp (dentro do container) e compara amostras."""

import sys
from pathlib import Path

import numpy as np

from tab.audio_extrair import extrair, ler, garantir

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
FLAC_CACHE, _ = garantir(VIDEO)
destino = Path("/tmp/x.flac")
ext = extrair(VIDEO, destino)
a, ta = ler(FLAC_CACHE)
b, tb = ler(destino)
print("cache:", FLAC_CACHE)
print("tamanho cache:", FLAC_CACHE.stat().st_size, "tamanho /tmp:", destino.stat().st_size)
print("taxas:", ta, tb, "n:", len(a), len(b))
print("tempo nova extracao (s):", ext["tempo_extracao_s"])
print("identicas (array_equal):", bool(np.array_equal(a, b)))
sys.exit(0 if np.array_equal(a, b) else 1)
