"""Áudio dos vídeos, em cache, com conversão exata entre tempo do vídeo e amostra (A0).

Trilha "tempo pelo áudio": achar no áudio o instante em que cada nota soa. Esta é a fundação:
extrai o áudio de um vídeo para FLAC mono, 16 bits, na taxa de ``TAXA_PADRAO`` (22050 Hz),
guarda em cache e converte o tempo do vídeo em índice de amostra e vice-versa.

Layout do cache (``<raiz>`` = ``caminhos.cache_quadros() / "audio"``)::

    <raiz>/<sha1(chave)[:24]>.flac    áudio decodificado, FLAC mono s16
    <raiz>/<sha1(chave)[:24]>.json    meta: chave, sondagem, t_amostra0, n_amostras, taxa...

A chave é a mesma de ``tab.censo.chave_do_arquivo`` (caminho relativo ao acervo, tamanho e mtime),
então um vídeo que muda ganha arquivo novo. A gravação é atômica: o temporário fica na mesma pasta
e só é renomeado para o destino quando o ffmpeg termina sem erro.

Convenção de tempo (medida, ver ``tests/test_audio_extrair.py``): tudo é em SEGUNDOS na linha do
tempo do vídeo (o mesmo PTS que ``tab.leitor`` usa). ``t_amostra0`` é o instante, nessa linha, da
amostra de índice 0 do FLAC, e é o ``best_effort_timestamp_time`` do PRIMEIRO FRAME de áudio
decodificado (já sem o pre-skip/priming do codec).

O que foi medido (clique de 5 ms com centro em 1,0025 s do áudio; erro = instante medido menos
esperado, pelo mesmo método do teste, argmax do pico. O argmax tem viés fixo de +0,13 ms neste
clique; o resto é o erro da convenção):
  - PCM (mov), desl. 0 e 0,5 s, e vídeo deslocado 0,3 s: +0,13 ms (start_time: igual)
  - AAC (mp4), desl. 0: +0,13 ms (start_time: igual); desl. 0,5 s: -0,64 ms
  - Opus (mkv), desl. 0: +0,13 ms; desl. 0,5 s: +1,13 ms (start_time: -6,9 e -5,9 ms: errado,
    por isso o frame é usado). O mkv guarda tempo em ms, o que explica o 1 ms.
O ffmpeg não preenche silêncio antes do início do áudio.

Uso::

    python -m tab.audio_extrair VIDEO [--json SAIDA] [--taxa 22050]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from tab.comum.caminhos import acervo, cache_quadros
from tab.tablatura.censo.censo import chave_do_arquivo

#: Taxa do áudio extraído, em Hz (mono, FLAC 16 bits).
TAXA_PADRAO = 22050

#: Formato do arquivo de áudio no cache.
FORMATO_META = "flac s16"

#: Versão da convenção de tempo gravada no meta. Quem muda a convenção (ex.: o que vira
#: ``t_amostra0``) soma 1 aqui; o cache com outra versão é refeito, nunca reaproveitado.
VERSAO_CONVENCAO = 2


def raiz_audio() -> Path:
    """Raiz do cache de áudio, dentro do cache de quadros.

    Returns:
        ``caminhos.cache_quadros() / "audio"`` (o diretório pode ainda não existir).
    """
    return cache_quadros() / "audio"


def caminho_no_cache(chave: str, raiz: Path | None = None) -> Path:
    """Caminho do FLAC de um vídeo no cache de áudio.

    Args:
        chave: chave de retomada do vídeo (``relativo|tamanho|mtime``).
        raiz: diretório do cache; se ``None``, usa ``raiz_audio()``.

    Returns:
        ``<raiz>/<sha1(chave)[:24]>.flac``. O meta fica ao lado, com ``.json``.
    """
    base = raiz if raiz is not None else raiz_audio()
    digest = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]
    return base / f"{digest}.flac"


def indice_de(t_video: float, meta: dict) -> int:
    """Índice da amostra de áudio mais próxima de um instante do vídeo.

    Args:
        t_video: instante na linha do tempo do vídeo, em segundos.
        meta: meta do áudio (``t_amostra0`` e ``taxa``).

    Returns:
        ``round((t_video - t_amostra0) * taxa)``, como ``int``. Pode ser negativo se o instante
        for anterior ao início do áudio.
    """
    return round((t_video - float(meta["t_amostra0"])) * int(meta["taxa"]))


def instante_de(indice: int, meta: dict) -> float:
    """Instante, na linha do tempo do vídeo, de uma amostra do áudio.

    Args:
        indice: índice da amostra no FLAC (0 é a primeira).
        meta: meta do áudio (``t_amostra0`` e ``taxa``).

    Returns:
        ``t_amostra0 + indice / taxa``, em segundos.
    """
    return float(meta["t_amostra0"]) + int(indice) / int(meta["taxa"])


def _flutuante(valor: object) -> float | None:
    """Converte um campo do ffprobe em float, devolvendo ``None`` se ausente ou inválido.

    Args:
        valor: campo bruto (string, número ou ``None``).

    Returns:
        O valor como float, ou ``None``.
    """
    if valor is None or valor == "N/A":
        return None
    try:
        return float(valor)
    except TypeError, ValueError:
        return None


def _primeiro_pacote(caminho: str, seletor: str) -> float | None:
    """PTS do primeiro pacote de um stream (``a:0`` ou ``v:0``), numa chamada de ``ffprobe``.

    Args:
        caminho: vídeo.
        seletor: ``"a:0"`` ou ``"v:0"``.

    Returns:
        O ``pts_time`` do primeiro pacote, ou ``None`` se o ffprobe não o informar.
    """
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            seletor,
            "-show_entries",
            "packet=pts_time",
            "-read_intervals",
            "%+#1",
            "-of",
            "csv=p=0",
            caminho,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falhou em {seletor}: {proc.stderr.strip()}")
    primeira = proc.stdout.strip().splitlines()
    if not primeira:
        return None
    return _flutuante(primeira[0].strip().rstrip(","))


def _primeiro_frame_audio(caminho: str) -> float | None:
    """Instante do primeiro frame de áudio DECODIFICADO (após o pre-skip/priming do codec).

    Lê os primeiros frames (não só o primeiro pacote: no AAC o primeiro pacote não gera frame
    de saída) e devolve o ``best_effort_timestamp_time`` do primeiro que tiver instante.

    Args:
        caminho: vídeo.

    Returns:
        O instante do primeiro frame decodificado, ou ``None`` se o ffprobe não o informar.
    """
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-read_intervals",
            "%+#8",
            "-of",
            "csv=p=0",
            caminho,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falhou nos frames de áudio: {proc.stderr.strip()}")
    for linha in proc.stdout.splitlines():
        valor = _flutuante(linha.strip().rstrip(","))
        if valor is not None:
            return valor
    return None


def sondar(caminho: str) -> dict:
    """Sondagem do vídeo: primeiro stream de vídeo, primeiro de áudio e o formato.

    Usa uma chamada de ``ffprobe`` com ``-show_streams -show_format`` e uma por stream para o PTS
    do primeiro pacote (``-read_intervals`` não separa streams numa só chamada).

    Args:
        caminho: vídeo.

    Returns:
        ``{"video": {...}|None, "audio": {...}|None, "duracao_formato_s": float|None}``. Cada
        stream traz ``codec``, ``start_time``, ``duration``, ``time_base`` e
        ``pts_primeiro_pacote``; o áudio traz também ``sample_rate``, ``channels`` e
        ``pts_primeiro_frame`` (o primeiro frame decodificado, usado como ``t_amostra0``). Sem stream
        de áudio, ``"audio"`` é ``None`` (não é erro).

    Raises:
        RuntimeError: se o ffprobe falhar ao ler o arquivo.
    """
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            caminho,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falhou em {caminho}: {proc.stderr.strip()}")
    bruto = json.loads(proc.stdout or "{}")
    fluxos = bruto.get("streams") or []
    video_bruto = next((f for f in fluxos if f.get("codec_type") == "video"), None)
    audio_bruto = next((f for f in fluxos if f.get("codec_type") == "audio"), None)

    video = None
    if video_bruto is not None:
        video = {
            "codec": video_bruto.get("codec_name"),
            "start_time": _flutuante(video_bruto.get("start_time")),
            "duration": _flutuante(video_bruto.get("duration")),
            "time_base": video_bruto.get("time_base"),
            "pts_primeiro_pacote": _primeiro_pacote(caminho, "v:0"),
        }
    audio = None
    if audio_bruto is not None:
        audio = {
            "codec": audio_bruto.get("codec_name"),
            "start_time": _flutuante(audio_bruto.get("start_time")),
            "duration": _flutuante(audio_bruto.get("duration")),
            "time_base": audio_bruto.get("time_base"),
            "sample_rate": int(audio_bruto["sample_rate"])
            if audio_bruto.get("sample_rate")
            else None,
            "channels": audio_bruto.get("channels"),
            "pts_primeiro_pacote": _primeiro_pacote(caminho, "a:0"),
            "pts_primeiro_frame": _primeiro_frame_audio(caminho),
        }
    return {
        "video": video,
        "audio": audio,
        "duracao_formato_s": _flutuante((bruto.get("format") or {}).get("duration")),
    }


def _gravar_atomico(destino: Path, texto: str) -> None:
    """Grava um texto num temporário da mesma pasta e renomeia para o destino.

    Args:
        destino: arquivo final.
        texto: conteúdo a gravar (UTF-8).
    """
    temporario = destino.with_name(f".{destino.name}.tmp")
    temporario.write_text(texto, encoding="utf-8")
    os.replace(temporario, destino)


def extrair(caminho: str, destino: Path, taxa: int = TAXA_PADRAO) -> dict:
    """Extrai o primeiro stream de áudio do vídeo para FLAC mono, de forma atômica.

    Args:
        caminho: vídeo de origem (somente leitura).
        destino: arquivo FLAC final. O temporário ``.<nome>.tmp`` fica na mesma pasta.
        taxa: taxa de amostragem de saída, em Hz.

    Returns:
        ``{"comando": [...], "tempo_extracao_s": float, "tamanho_bytes": int}``.

    Raises:
        RuntimeError: se o ffmpeg falhar; o temporário é removido.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(f".{destino.name}.tmp")
    comando = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-i",
        caminho,
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(taxa),
        "-sample_fmt",
        "s16",
        "-c:a",
        "flac",
        "-f",
        "flac",
        str(temporario),
    ]
    inicio = time.monotonic()
    proc = subprocess.run(comando, capture_output=True, text=True)
    tempo = time.monotonic() - inicio
    if proc.returncode != 0:
        temporario.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg falhou ao extrair o áudio: {proc.stderr.strip()}")
    os.replace(temporario, destino)
    return {
        "comando": comando,
        "tempo_extracao_s": round(tempo, 3),
        "tamanho_bytes": destino.stat().st_size,
    }


def _sondar_flac(caminho_flac: Path) -> dict:
    """Taxa e número de amostras de um FLAC, lidos do ffprobe.

    Args:
        caminho_flac: arquivo FLAC gerado por ``extrair``.

    Returns:
        ``{"taxa": int, "n_amostras": int}``. ``n_amostras`` vem de ``duration_ts`` na
        ``time_base`` do stream, convertido para a taxa.
    """
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,duration_ts,time_base",
            "-of",
            "json",
            str(caminho_flac),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falhou no FLAC: {proc.stderr.strip()}")
    stream = json.loads(proc.stdout or "{}")["streams"][0]
    taxa = int(stream["sample_rate"])
    num, den = (int(x) for x in stream["time_base"].split("/"))
    n = round(int(stream["duration_ts"]) * num / den * taxa)
    return {"taxa": taxa, "n_amostras": n}


def ler(caminho_flac: Path) -> tuple[np.ndarray, int]:
    """Decodifica o FLAC para amostras ``int16`` mono, sem converter para float.

    Args:
        caminho_flac: FLAC gerado por ``extrair``.

    Returns:
        ``(amostras, taxa)``: ``amostras`` é ``np.ndarray`` de ``np.int16``; ``taxa`` vem do meta
        ao lado (``.json``) se existir, senão do ffprobe.

    Raises:
        RuntimeError: se o ffmpeg falhar ao decodificar.
    """
    caminho_flac = Path(caminho_flac)
    meta_arq = caminho_flac.with_suffix(".json")
    if meta_arq.is_file():
        taxa = int(json.loads(meta_arq.read_text(encoding="utf-8"))["taxa"])
    else:
        taxa = _sondar_flac(caminho_flac)["taxa"]
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(caminho_flac),
            "-f",
            "s16le",
            "-ac",
            "1",
            "-",
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falhou ao decodificar {caminho_flac}: "
            f"{proc.stderr.decode(errors='replace').strip()}"
        )
    amostras = np.frombuffer(proc.stdout, dtype=np.int16).copy()
    return amostras, taxa


def garantir(
    caminho_video: str,
    raiz: Path | None = None,
    raiz_acervo: str | None = None,
    taxa: int = TAXA_PADRAO,
) -> tuple[Path, dict]:
    """Garante o FLAC e o meta de um vídeo: reaproveita o cache ou extrai.

    Args:
        caminho_video: vídeo (caminho absoluto).
        raiz: raiz do cache de áudio; se ``None``, ``raiz_audio()``.
        raiz_acervo: raiz para a chave relativa; se ``None``, ``caminhos.acervo()``.
        taxa: taxa do FLAC, em Hz.

    Returns:
        ``(caminho_flac, meta)``. Em cache hit, ``meta["cache"] == "hit"`` e o arquivo não é
        regravado; senão ``"miss"``.

    Raises:
        ValueError: se o vídeo não tiver stream de áudio.
    """
    base_acervo = raiz_acervo if raiz_acervo is not None else str(acervo())
    chave = chave_do_arquivo(caminho_video, base_acervo)
    flac = caminho_no_cache(chave, raiz)
    meta_arq = flac.with_suffix(".json")

    if flac.is_file() and meta_arq.is_file():
        meta = json.loads(meta_arq.read_text(encoding="utf-8"))
        if (
            meta.get("chave") == chave
            and meta.get("taxa") == taxa
            and meta.get("versao_convencao") == VERSAO_CONVENCAO
        ):
            meta["cache"] = "hit"
            return flac, meta

    sondagem = sondar(caminho_video)
    audio = sondagem["audio"]
    if audio is None:
        raise ValueError(f"o vídeo não tem stream de áudio: {caminho_video}")

    video = sondagem["video"]
    ext = extrair(caminho_video, flac, taxa)
    info_flac = _sondar_flac(flac)
    # Convenção medida (ver docstring do módulo): o instante do primeiro frame decodificado.
    # O start_time do stream erra 6-7 ms com Opus (o pre-skip não entra nele).
    origem = "pts_primeiro_frame"
    t_amostra0 = audio["pts_primeiro_frame"]
    if t_amostra0 is None:
        origem, t_amostra0 = "start_time", audio["start_time"]
    if t_amostra0 is None:
        origem, t_amostra0 = "zero", 0.0
    inicio_video = video["start_time"] if video and video["start_time"] else 0.0
    meta = {
        "chave": chave,
        "caminho": os.path.relpath(caminho_video, base_acervo),
        "sondagem": sondagem,
        "taxa": info_flac["taxa"],
        "canais": 1,
        "formato": FORMATO_META,
        "t_amostra0": float(t_amostra0),
        "origem_t_amostra0": origem,
        "versao_convencao": VERSAO_CONVENCAO,
        "n_amostras": info_flac["n_amostras"],
        "duracao_audio_s": info_flac["n_amostras"] / info_flac["taxa"],
        "deslocamento_audio_video_ms": round(
            (float(audio["start_time"] or 0.0) - inicio_video) * 1000.0, 3
        ),
        "tempo_extracao_s": ext["tempo_extracao_s"],
        "tamanho_bytes": ext["tamanho_bytes"],
        "comando_ffmpeg": ext["comando"],
        "cache": "miss",
    }
    _gravar_atomico(meta_arq, json.dumps(meta, ensure_ascii=False, indent=2))
    return flac, meta


def main() -> int:
    """Ponto de entrada da CLI: extrai (ou reaproveita) o áudio de um vídeo e resume.

    Returns:
        Código de saída (0 se deu certo).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video", help="vídeo de origem (somente leitura)")
    parser.add_argument("--json", dest="saida", help="grava o meta neste arquivo")
    parser.add_argument("--taxa", type=int, default=TAXA_PADRAO, help="Hz")
    args = parser.parse_args()

    flac, meta = garantir(os.path.abspath(args.video), taxa=args.taxa)
    audio = meta["sondagem"]["audio"]
    video = meta["sondagem"]["video"]
    print(f"flac: {flac}")
    print(f"cache: {meta['cache']}")
    print(
        f"video start={video['start_time']} pts1={video['pts_primeiro_pacote']} | "
        f"audio start={audio['start_time']} pts1={audio['pts_primeiro_pacote']} "
        f"codec={audio['codec']} taxa_original={audio['sample_rate']}"
    )
    print(
        f"t_amostra0={meta['t_amostra0']:.6f}s ({meta['origem_t_amostra0']}) deslocamento="
        f"{meta['deslocamento_audio_video_ms']:.3f} ms"
    )
    print(
        f"duracao audio={meta['duracao_audio_s']:.3f}s "
        f"formato={meta['sondagem']['duracao_formato_s']}s "
        f"n_amostras={meta['n_amostras']} taxa={meta['taxa']}"
    )
    print(
        f"tempo_extracao={meta['tempo_extracao_s']}s "
        f"tamanho={meta['tamanho_bytes'] / 1e6:.2f} MB"
    )
    if args.saida:
        Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
        _gravar_atomico(
            Path(args.saida), json.dumps(meta, ensure_ascii=False, indent=2)
        )
        print(f"meta gravado em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
