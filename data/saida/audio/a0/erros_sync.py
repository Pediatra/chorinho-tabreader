"""Erro medido da sincronia com o modulo real (mesmo metodo do teste: argmax + instante_de)."""

import tempfile
from pathlib import Path

import numpy as np

from tab.audio_extrair import garantir, instante_de, ler
from tests.test_audio_extrair import CENTRO_CLIQUE, GERADOR_CLIQUE, _gerar_video

with tempfile.TemporaryDirectory() as d:
    base = Path(d)
    for off_v, off_a, cod in [
        (0.0, 0.0, "aac"), (0.0, 0.5, "aac"), (0.0, 0.0, "pcm"), (0.0, 0.5, "pcm"), (0.3, 0.5, "pcm"), (0.0, 0.0, "opus"), (0.0, 0.5, "opus"),
    ]:
        ext = {"pcm": "mov", "opus": "mkv"}.get(cod, "mp4")
        v = _gerar_video(base / f"s_{off_v}_{off_a}_{cod}.{ext}", gerador_audio=GERADOR_CLIQUE,
                         off_audio=off_a, off_video=off_v, codec=cod)
        flac, meta = garantir(str(v), raiz=base / "cache", raiz_acervo=str(base))
        a, _ = ler(flac)
        pico = int(np.argmax(np.abs(a.astype(np.int64))))
        esp = CENTRO_CLIQUE + off_a
        med = instante_de(pico, meta)
        print(f"video_off={off_v} audio_off={off_a} {cod}: t0={meta['t_amostra0']:.6f} "
              f"pico={pico} medido={med:.6f} esperado={esp:.6f} erro={(med-esp)*1000:+.3f} ms")
