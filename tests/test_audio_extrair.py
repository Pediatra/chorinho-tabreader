"""Testes do cache de áudio (`tab/audio_extrair.py`): ida e volta, cache, sincronia e conversão.

Tudo é sintético: os vídeos são gerados com ffmpeg (lavfi) dentro de `tmp_path`. Sem GPU e sem
acervo. Os testes pulam se o ffmpeg não existir.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tab.audio_extrair import (
    caminho_no_cache,
    garantir,
    indice_de,
    instante_de,
    ler,
    sondar,
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe ausentes",
)

#: Centro do clique no áudio da fonte (tempo do stream antes do deslocamento), em segundos.
CENTRO_CLIQUE = 1.0025
#: Tolerância da sincronia, em segundos (3 ms).
TOLERANCIA_S = 0.003
#: Gerador do clique: rajada de 5 ms de senóide de 2 kHz, com envelope senoidal (centro em
#: CENTRO_CLIQUE) e silêncio no resto. O envelope é o que dá um pico estável.
GERADOR_CLIQUE = (
    "aevalsrc=0.8*sin(2*PI*2000*t)*sin(PI*(t-1.0)/0.005)"
    "*between(t\\,1.0\\,1.005):s=44100:d=3"
)


def _gerar_video(
    caminho: Path,
    *,
    gerador_audio: str | None,
    off_audio: float = 0.0,
    off_video: float = 0.0,
    codec: str = "aac",
) -> Path:
    """Gera um vídeo sintético com testsrc e, opcionalmente, um áudio.

    Args:
        caminho: arquivo de saída (.mp4, .mov ou .mkv).
        gerador_audio: expressão lavfi do áudio, ou ``None`` para vídeo sem áudio.
        off_audio: deslocamento (``-itsoffset``) aplicado à entrada do áudio, em segundos.
        off_video: deslocamento (``-itsoffset``) aplicado à entrada do vídeo, em segundos.
        codec: ``"aac"``, ``"opus"`` ou ``"pcm"`` (pcm_s16le, sem codificador).

    Returns:
        O próprio caminho.
    """
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-itsoffset",
        str(off_video),
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=25",
    ]
    if gerador_audio is not None:
        cmd += [
            "-itsoffset",
            str(off_audio),
            "-f",
            "lavfi",
            "-i",
            gerador_audio,
            "-t",
            "3",
            "-map",
            "0:v",
            "-map",
            "1:a",
        ]
    else:
        cmd += ["-t", "3", "-map", "0:v"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if gerador_audio is not None:
        if codec == "aac":
            cmd += ["-c:a", "aac", "-b:a", "128k"]
        elif codec == "opus":
            cmd += ["-c:a", "libopus", "-b:a", "96k"]
        else:
            cmd += ["-c:a", "pcm_s16le"]
    cmd.append(str(caminho))
    subprocess.run(cmd, check=True)
    return caminho


def _decodificar_direto(video: Path) -> np.ndarray:
    """Decodifica o áudio do vídeo direto pelo ffmpeg, sem o cache (mesma reamostragem).

    Args:
        video: vídeo de origem.

    Returns:
        Amostras ``int16`` mono a 22050 Hz.
    """
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(video),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "22050",
            "-f",
            "s16le",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.int16).copy()


def test_ida_e_volta_e_exata(tmp_path):
    """O FLAC decodificado por `ler` é idêntico ao decodificado direto do vídeo."""
    video = _gerar_video(
        tmp_path / "v.mp4",
        gerador_audio="aevalsrc=0.5*sin(2*PI*440*t):s=44100:d=3",
    )
    raiz = tmp_path / "cache"
    flac, meta = garantir(str(video), raiz=raiz, raiz_acervo=str(tmp_path))

    amostras, taxa = ler(flac)
    direto = _decodificar_direto(video)
    assert taxa == 22050
    assert amostras.dtype == np.int16
    assert np.array_equal(amostras, direto)
    assert meta["n_amostras"] == len(amostras)
    assert abs(meta["duracao_audio_s"] - sondar(str(video))["duracao_formato_s"]) <= 0.1
    # a escrita é atômica: nenhum temporário sobra na pasta do cache
    assert list(raiz.rglob(".*.tmp")) == []


def test_cache_hit_nao_regrava(tmp_path):
    """A segunda chamada reaproveita o FLAC e o meta sem regravá-los."""
    video = _gerar_video(
        tmp_path / "v.mp4",
        gerador_audio="aevalsrc=0.5*sin(2*PI*440*t):s=44100:d=2",
    )
    raiz = tmp_path / "cache"
    flac, meta1 = garantir(str(video), raiz=raiz, raiz_acervo=str(tmp_path))
    meta_arq = flac.with_suffix(".json")
    mtime_flac = flac.stat().st_mtime_ns
    mtime_meta = meta_arq.stat().st_mtime_ns

    flac2, meta2 = garantir(str(video), raiz=raiz, raiz_acervo=str(tmp_path))

    assert meta1["cache"] == "miss"
    assert meta2["cache"] == "hit"
    assert flac2 == flac
    assert flac.stat().st_mtime_ns == mtime_flac
    assert meta_arq.stat().st_mtime_ns == mtime_meta


@pytest.mark.parametrize(
    ("off_video", "off_audio", "codec"),
    [
        (0.0, 0.0, "aac"),
        (0.0, 0.5, "aac"),
        (0.0, 0.0, "pcm"),
        (0.0, 0.5, "pcm"),
        (0.3, 0.5, "pcm"),
        (0.0, 0.0, "opus"),
        (0.0, 0.5, "opus"),
    ],
)
def test_sincronia_do_clique(tmp_path, off_video, off_audio, codec):
    """O clique do áudio cai no instante esperado da linha do tempo do vídeo (tolerância 3 ms).

    O clique está em CENTRO_CLIQUE do stream de áudio; com o deslocamento do áudio, o esperado
    na linha do tempo do vídeo é CENTRO_CLIQUE + off_audio. O caso com vídeo deslocado testa que
    `t_amostra0` é absoluto, não relativo ao início do vídeo. O Opus é o codec do MVP do acervo.
    """
    ext = {"pcm": "mov", "opus": "mkv"}.get(codec, "mp4")
    video = _gerar_video(
        tmp_path / f"sinc_{off_video}_{off_audio}_{codec}.{ext}",
        gerador_audio=GERADOR_CLIQUE,
        off_audio=off_audio,
        off_video=off_video,
        codec=codec,
    )
    flac, meta = garantir(
        str(video), raiz=tmp_path / "cache", raiz_acervo=str(tmp_path)
    )
    amostras, _ = ler(flac)

    pico = int(np.argmax(np.abs(amostras.astype(np.int64))))
    esperado = CENTRO_CLIQUE + off_audio
    medido = instante_de(pico, meta)
    assert abs(medido - esperado) <= TOLERANCIA_S, (
        f"erro de {(medido - esperado) * 1000:.3f} ms (t0={meta['t_amostra0']})"
    )
    for i in (0, 1000, pico, len(amostras) - 1):
        assert indice_de(instante_de(i, meta), meta) == i


def test_indice_e_instante_sao_inversos():
    """Conversão tempo <-> amostra é exata no sentido amostra -> tempo -> amostra."""
    meta = {"t_amostra0": 0.5, "taxa": 22050}
    assert instante_de(22050, meta) == pytest.approx(1.5)
    assert indice_de(1.5, meta) == 22050
    assert indice_de(0.5, meta) == 0
    assert indice_de(0.5 + 0.4 / 22050, meta) == 0
    assert indice_de(0.5 - 1.0, meta) == -22050
    for i in (0, 1, 12345, 22050 * 600):
        assert indice_de(instante_de(i, meta), meta) == i


def test_caminho_no_cache_e_estavel(tmp_path):
    """O nome do FLAC é o sha1 da chave (24 hex), o mesmo do cache de quadros."""
    caminho = caminho_no_cache("chave-de-teste|123|456", tmp_path)
    assert caminho == tmp_path / "f34cbde6f49e10082c7224f0.flac"
    assert caminho_no_cache("chave-de-teste|123|456", tmp_path) == caminho
    assert caminho_no_cache("outra|123|456", tmp_path) != caminho


def test_video_sem_audio(tmp_path):
    """Vídeo sem áudio: `sondar` devolve áudio None e `garantir` falha com mensagem clara."""
    video = _gerar_video(tmp_path / "mudo.mp4", gerador_audio=None)
    assert sondar(str(video))["audio"] is None
    with pytest.raises(ValueError, match="áudio"):
        garantir(str(video), raiz=tmp_path / "cache", raiz_acervo=str(tmp_path))


def test_meta_tem_os_campos_do_contrato(tmp_path):
    """O meta gravado traz a sondagem e os campos de tempo que a trilha vai consumir."""
    video = _gerar_video(
        tmp_path / "v.mp4",
        gerador_audio="aevalsrc=0.5*sin(2*PI*440*t):s=44100:d=2",
    )
    flac, _ = garantir(str(video), raiz=tmp_path / "cache", raiz_acervo=str(tmp_path))
    meta = json.loads(flac.with_suffix(".json").read_text(encoding="utf-8"))
    for campo in (
        "chave",
        "caminho",
        "sondagem",
        "taxa",
        "canais",
        "formato",
        "t_amostra0",
        "n_amostras",
        "duracao_audio_s",
        "deslocamento_audio_video_ms",
        "tempo_extracao_s",
        "tamanho_bytes",
        "comando_ffmpeg",
    ):
        assert campo in meta
    assert meta["canais"] == 1
    assert meta["taxa"] == 22050


def test_cache_com_outra_convencao_e_refeito(tmp_path):
    """Meta gravado com outra versão da convenção de tempo não é reaproveitado."""
    video = _gerar_video(
        tmp_path / "v.mp4",
        gerador_audio="aevalsrc=0.5*sin(2*PI*440*t):s=44100:d=2",
    )
    raiz = tmp_path / "cache"
    flac, _ = garantir(str(video), raiz=raiz, raiz_acervo=str(tmp_path))
    meta_arq = flac.with_suffix(".json")
    meta = json.loads(meta_arq.read_text(encoding="utf-8"))
    meta["versao_convencao"] = 1
    meta_arq.write_text(json.dumps(meta), encoding="utf-8")

    _, meta2 = garantir(str(video), raiz=raiz, raiz_acervo=str(tmp_path))
    assert meta2["cache"] == "miss"
    assert meta2["versao_convencao"] == 2
