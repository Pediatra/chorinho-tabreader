"""Experimento: qual timestamp dá o instante real da amostra 0 decodificada (Opus/AAC/PCM)."""

import subprocess
import tempfile
from pathlib import Path

import numpy as np

from tests.test_audio_extrair import CENTRO_CLIQUE, GERADOR_CLIQUE, _gerar_video

TAXA = 22050


def out(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def primeiro_frame(arq):
    txt = out(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_frames",
               "-read_intervals", "%+#1", "-show_entries", "frame=pts_time,best_effort_timestamp_time,nb_samples",
               "-of", "csv=p=0", arq])
    return txt.splitlines()[0] if txt else "?"


def pri_pacote(arq):
    return out(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                "packet=pts_time", "-read_intervals", "%+#1", "-of", "csv=p=0", arq]).rstrip(",")


with tempfile.TemporaryDirectory() as d:
    base = Path(d)
    for cod, ext in (("aac", "mp4"), ("pcm", "mov"), ("opus", "mkv"), ("opus", "mp4")):
        for off in (0.0, 0.5):
            arq = _gerar_video(base / f"{cod}_{off}.{ext}", gerador_audio=GERADOR_CLIQUE,
                               off_audio=off, codec=cod)
            pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(arq), "-map", "0:a:0",
                                  "-ac", "1", "-ar", str(TAXA), "-f", "s16le", "-"],
                                 check=True, capture_output=True).stdout
            a = np.frombuffer(pcm, dtype=np.int16).astype(np.int64)
            pico = int(np.argmax(np.abs(a)))
            j = slice(max(pico - 300, 0), pico + 300)
            w = a[j] ** 2
            cen = float((np.arange(j.start, j.stop) * w).sum() / w.sum()) / TAXA
            t0_real = CENTRO_CLIQUE + off - cen
            st = out(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                      "stream=start_time", "-of", "csv=p=0", str(arq)])
            print(f"{cod:5s} {ext} off={off}: t0_real={t0_real:+.5f} start_time={st} "
                  f"pkt1={pri_pacote(str(arq))} frame1(pts,best_effort,nb)={primeiro_frame(str(arq))}")
