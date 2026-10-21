"""Experimento exploratorio de sincronia (nao faz parte do produto).

Gera mp4 (AAC) e mov (PCM) com um clique de 5 ms (envelope senoidal, centro em 1.0025 s
do tempo da fonte de audio), com deslocamento -itsoffset conhecido, e mede o instante
do clique pelo centroide de energia decodificado com ffmpeg a 22050 Hz.
"""

import json
import subprocess

import numpy as np

PASTA = "/app/data/saida/audio/a0/exp2"
CENTRO = 1.0025
TAXA = 22050
GEN = (
    "aevalsrc=0.8*sin(2*PI*2000*t)*sin(PI*(t-1.0)/0.005)"
    "*between(t\\,1.0\\,1.005):s=44100:d=3"
)


def rodar(args: list[str]) -> bytes:
    return subprocess.run(args, check=True, capture_output=True).stdout


def sondar(arq: str) -> dict:
    bruto = rodar(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", arq]
    )
    d = json.loads(bruto)
    st = {s["codec_type"]: s for s in d["streams"]}
    pkt = {}
    for tipo, sel in (("a", "a:0"), ("v", "v:0")):
        p = rodar(
            [
                "ffprobe", "-v", "error", "-select_streams", sel,
                "-show_entries", "packet=pts_time", "-read_intervals", "%+#1",
                "-of", "csv=p=0", arq,
            ]
        ).decode().strip().rstrip(",")
        pkt[tipo] = p
    return {
        "start_video": float(st["video"]["start_time"]),
        "start_audio": float(st["audio"]["start_time"]),
        "start_formato": float(d["format"]["start_time"]),
        "pts1_audio": pkt["a"],
        "pts1_video": pkt["v"],
        "codec_audio": st["audio"]["codec_name"],
    }


def medir(arq: str) -> dict:
    bruto = rodar(
        [
            "ffmpeg", "-nostdin", "-v", "error", "-i", arq, "-map", "0:a:0",
            "-ac", "1", "-ar", str(TAXA), "-f", "s16le", "-",
        ]
    )
    a = np.frombuffer(bruto, dtype=np.int16).astype(float)
    pico = int(np.argmax(np.abs(a)))
    j = slice(max(pico - 300, 0), pico + 300)
    w = a[j] ** 2
    idx = np.arange(j.start, j.stop)
    centro_idx = float((idx * w).sum() / w.sum())
    return {"n": len(a), "pico_idx": pico, "centro_idx": centro_idx,
            "centro_s": centro_idx / TAXA}


def main() -> None:
    for off in (0.0, 0.5):
        for cod in ("aac", "pcm"):
            ext = "mp4" if cod == "aac" else "mov"
            ca = ["-c:a", "aac", "-b:a", "128k"] if cod == "aac" else ["-c:a", "pcm_s16le"]
            arq = f"{PASTA}/sync_{off}_{cod}.{ext}"
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-y",
                 "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
                 "-itsoffset", str(off), "-f", "lavfi", "-i", GEN,
                 "-t", "3", "-map", "0:v", "-map", "1:a",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", *ca, arq],
                check=True,
            )
            s = sondar(arq)
            m = medir(arq)
            # instante do clique na linha do tempo do video = CENTRO + off (fonte + offset)
            esperado = CENTRO + off
            # t_amostra0 implicito: o que faria o clique cair em esperado
            t0_impl = esperado - m["centro_s"]
            print(f"## off={off} {cod} ({ext})")
            print("  sondagem:", json.dumps(s))
            print("  decodificado:", json.dumps(m))
            print(f"  clique esperado (video) = {esperado:.6f}")
            print(f"  t_amostra0 implicito = {t0_impl:.6f}")
            print(f"  erro se t0=0: {(m['centro_s'] - esperado)*1000:.3f} ms")
            print(f"  erro se t0=start_audio: {((m['centro_s']+s['start_audio'])-esperado)*1000:.3f} ms")
            print(f"  erro se t0=pts1_audio: {((m['centro_s']+float(s['pts1_audio']))-esperado)*1000:.3f} ms")


if __name__ == "__main__":
    main()
