"""Custo da extração de áudio em 20 vídeos do acervo (medição autorizada pelo dono).

Para cada caminho de ``lista20.txt`` (relativo ao acervo), UM POR VEZ e em ordem, chama
``tab.audio_extrair.garantir``, mede o tempo de parede da chamada e grava uma linha JSONL.
Um vídeo que falha não interrompe os outros. Depois grava um resumo em texto com a checagem
de buraco/deriva (diferença entre o áudio extraído e o stream de áudio do vídeo).

Uso, no container, a partir de /app (o script acha o repositório sozinho)::

    python data/saida/audio/a0/custo20.py
    python data/saida/audio/a0/custo20.py --saida custo20_passada2.jsonl \
        --resumo custo20_passada2_resumo.txt

Só lê o acervo (``/acervo``) e escreve no cache (``/cache/audio``) e nesta pasta.
"""

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

PASTA = Path(__file__).resolve().parent
RAIZ_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ_REPO))

from tab.audio_extrair import garantir, sondar  # noqa: E402

RAIZ_ACERVO = Path("/acervo")
#: Número de vídeos do acervo usado na projeção (estimativa, não medida).
N_PROJECAO = 2998
#: Limites da checagem de buraco/deriva, em milissegundos.
LIMITE_DIF_MS = 100.0
LIMITE_DIF_VIDEO_MS = 500.0


def _duracao_audio_fonte(sondagem: dict) -> tuple[float | None, str | None]:
    """Duração do stream de áudio, ou a do formato se o stream não trouxer.

    Args:
        sondagem: sondagem do vídeo (``tab.audio_extrair.sondar``).

    Returns:
        ``(segundos, fonte)``, com fonte ``"stream"`` ou ``"formato"``; ``(None, None)`` se
        nenhuma das duas existir.
    """
    audio = sondagem.get("audio") or {}
    if audio.get("duration"):
        return audio["duration"], "stream"
    formato = sondagem.get("duracao_formato_s")
    if formato:
        return formato, "formato"
    return None, None


def _preencher_sondagem(linha: dict, sondagem: dict) -> None:
    """Copia para a linha os campos de codec, tempo e duração da sondagem do vídeo.

    Args:
        linha: registro JSONL em construção (alterado no lugar).
        sondagem: sondagem do vídeo.
    """
    video = sondagem.get("video") or {}
    audio = sondagem.get("audio") or {}
    linha["codec_video"] = video.get("codec")
    linha["codec_audio"] = audio.get("codec")
    linha["sample_rate_audio"] = audio.get("sample_rate")
    linha["canais_audio"] = audio.get("channels")
    linha["start_time_video"] = video.get("start_time")
    linha["start_time_audio"] = audio.get("start_time")
    linha["pts1_video"] = video.get("pts_primeiro_pacote")
    linha["pts1_audio"] = audio.get("pts_primeiro_pacote")
    linha["pts1_frame_audio"] = audio.get("pts_primeiro_frame")
    linha["duracao_stream_audio_s"] = audio.get("duration")
    linha["duracao_stream_video_s"] = video.get("duration")
    linha["duracao_formato_s"] = sondagem.get("duracao_formato_s")


def medir(rel: str) -> dict:
    """Mede a extração de um vídeo do acervo e devolve o registro JSONL.

    Args:
        rel: caminho do vídeo relativo ao acervo (como em ``lista20.txt``).

    Returns:
        Dicionário com os campos do custo, a checagem de deriva e ``erro`` (``None`` se deu certo).
    """
    caminho = str(RAIZ_ACERVO / rel)
    linha: dict = {"caminho": rel, "canal": rel.split("/", 1)[0], "erro": None}
    inicio = time.monotonic()
    try:
        linha["tamanho_video_bytes"] = os.stat(caminho).st_size
        flac, meta = garantir(caminho)
        linha["tempo_parede_s"] = round(time.monotonic() - inicio, 3)
        sondagem = meta["sondagem"]
        _preencher_sondagem(linha, sondagem)
        linha["cache"] = meta["cache"]
        linha["t_amostra0"] = meta["t_amostra0"]
        linha["origem_t_amostra0"] = meta["origem_t_amostra0"]
        linha["deslocamento_audio_video_ms"] = meta["deslocamento_audio_video_ms"]
        linha["taxa_extraida"] = meta["taxa"]
        linha["n_amostras"] = meta["n_amostras"]
        linha["duracao_audio_extraido_s"] = meta["duracao_audio_s"]
        linha["tempo_extracao_s"] = meta["tempo_extracao_s"]
        linha["tamanho_flac_bytes"] = os.stat(flac).st_size
        linha["flac"] = str(flac)
    except Exception as exc:  # um vídeo que falha não para o lote
        linha["tempo_parede_s"] = round(time.monotonic() - inicio, 3)
        linha["erro"] = f"{type(exc).__name__}: {exc}"
        try:
            _preencher_sondagem(linha, sondar(caminho))
        except Exception as exc2:  # sondagem também falhou: registra e segue
            linha["erro_sondagem"] = f"{type(exc2).__name__}: {exc2}"
        return linha

    # Checagem de buraco/deriva (o ffmpeg não preenche lacunas no meio do áudio).
    dur_audio, fonte_audio = _duracao_audio_fonte(sondagem)
    linha["duracao_stream_audio_fonte"] = fonte_audio
    if dur_audio is not None:
        linha["dif_ms"] = round(
            (linha["duracao_audio_extraido_s"] - dur_audio) * 1000.0, 3
        )
    video = sondagem.get("video") or {}
    if video.get("duration") and video.get("start_time") is not None:
        fim_video = video["start_time"] + video["duration"]
        fonte_video = "stream"
    else:
        fim_video = sondagem.get("duracao_formato_s")
        fonte_video = "formato"
    linha["fim_video_fonte"] = fonte_video
    if fim_video is not None:
        linha["fim_video_s"] = fim_video
        linha["dif_video_ms"] = round(
            (
                linha["duracao_audio_extraido_s"]
                + linha["t_amostra0"]
                - fim_video
            )
            * 1000.0,
            3,
        )
    return linha


def _mediana(valores: list[float]) -> float | None:
    """Mediana de uma lista, ou ``None`` se vazia.

    Args:
        valores: números.

    Returns:
        A mediana ou ``None``.
    """
    return statistics.median(valores) if valores else None


def resumir(linhas: list[dict], n_lista: int, tempo_passada_s: float) -> str:
    """Monta o resumo em texto a partir dos registros do lote.

    Args:
        linhas: registros JSONL do lote, na ordem da lista.
        n_lista: número de caminhos na lista.
        tempo_passada_s: tempo de parede do lote inteiro, em segundos.

    Returns:
        Texto do resumo, pronto para gravar.
    """
    ok = [x for x in linhas if not x.get("erro")]
    falhas = [x for x in linhas if x.get("erro")]
    out: list[str] = []
    add = out.append

    add(f"Vídeos extraídos: {len(ok)} de {n_lista} (falhas: {len(falhas)})")
    for x in falhas:
        add(f"  FALHA {x['caminho']}: {x['erro']}")
    add(f"Cache hits: {sum(1 for x in ok if x.get('cache') == 'hit')} de {len(ok)}")
    add(f"Tempo de parede do lote inteiro: {tempo_passada_s:.2f} s")
    add("")

    add("Codec de vídeo: " + ", ".join(
        f"{k}={v}" for k, v in Counter(x.get("codec_video") or "sem" for x in linhas).most_common()
    ))
    add("Codec de áudio: " + ", ".join(
        f"{k}={v}" for k, v in Counter(x.get("codec_audio") or "sem" for x in linhas).most_common()
    ))
    add("Sample rate do áudio original: " + ", ".join(
        f"{k}={v}" for k, v in Counter(x.get("sample_rate_audio") or "sem" for x in linhas).most_common()
    ))
    add("Canais do áudio original: " + ", ".join(
        f"{k}={v}" for k, v in Counter(x.get("canais_audio") or "sem" for x in linhas).most_common()
    ))
    add("")

    desl = [x["deslocamento_audio_video_ms"] for x in ok]
    zeros = [v for v in desl if v == 0]
    nao_zeros = sorted(v for v in desl if v != 0)
    add(f"Deslocamento áudio-vídeo: exatamente 0 em {len(zeros)} de {len(ok)}; "
        f"diferente de 0 em {len(nao_zeros)}")
    add("  valores ≠ 0 (ms): " + (", ".join(f"{v:.3f}" for v in nao_zeros) or "nenhum"))
    add("Origem de t_amostra0: " + ", ".join(
        f"{k}={v}" for k, v in Counter(x.get("origem_t_amostra0") for x in ok).most_common()
    ))
    add("")

    tempos = [(x["tempo_parede_s"], x["caminho"]) for x in linhas if "tempo_parede_s" in x]
    tv = [t for t, _ in tempos]
    add(f"Tempo de parede por vídeo: total {sum(tv):.2f} s, mediana {_mediana(tv):.3f} s, "
        f"máximo {max(tv):.3f} s ({max(tempos)[1]})")
    add(f"  tempo_extracao_s (do meta, na 1ª passada) mediana: "
        f"{_mediana([x['tempo_extracao_s'] for x in ok]) or 0:.3f} s")
    mb_video_ok = [x["tamanho_video_bytes"] / 1e6 for x in ok]
    seg_ok = [x["tempo_parede_s"] for x in ok]
    # cache hit leva ~0 s: MB/s só faz sentido para tempo > 0 (a divisão por zero quebrou a 2ª passada)
    pares = [(m, s) for m, s in zip(mb_video_ok, seg_ok) if s > 0]
    if pares:
        taxas = [m / s for m, s in pares]
        add(f"MB/s lidos (vídeo / tempo de parede, só tempo > 0): total "
            f"{sum(m for m, _ in pares) / sum(s for _, s in pares):.2f} MB/s; "
            f"por vídeo: mediana {_mediana(taxas):.2f}, mín {min(taxas):.2f}, "
            f"máx {max(taxas):.2f} MB/s")
    add("")

    if ok:
        mb_video_media = sum(mb_video_ok) / len(ok)
        flac_mb = [x["tamanho_flac_bytes"] / 1e6 for x in ok]
        horas = [x["duracao_audio_extraido_s"] / 3600 for x in ok]
        add(f"Tamanho médio do vídeo (amostra): {mb_video_media:.1f} MB")
        add(f"Tamanho do FLAC: total {sum(flac_mb):.2f} MB para {sum(horas):.2f} h de áudio; "
            f"por hora de áudio: {sum(flac_mb) / sum(horas):.1f} MB/h")
        add(f"Tamanho médio do FLAC (amostra): {sum(flac_mb) / len(ok):.2f} MB")
        mb_s_med = _mediana(
            [x["tempo_parede_s"] / m for x, m in zip(ok, mb_video_ok) if m and x["tempo_parede_s"] > 0]
        )
        if mb_s_med is not None:
            tempo_proj_h = mb_s_med * mb_video_media * N_PROJECAO / 3600
            add(f"ESTIMATIVA para {N_PROJECAO} vídeos (tamanho médio da amostra x {N_PROJECAO}; "
                f"não é medida):")
            add(f"  tamanho do acervo: ~{mb_video_media * N_PROJECAO / 1000:.0f} GB "
                f"(referência do AGENTS.md: 255 GB / 3.899 vídeos = 65 MB médios)")
            add(f"  tempo de parede (mediana s/MB x MB totais): ~{tempo_proj_h:.1f} h, "
                f"sem paralelismo")
        add(f"ESTIMATIVA do cache de áudio para {N_PROJECAO} vídeos: "
            f"~{sum(flac_mb) / len(ok) * N_PROJECAO / 1000:.1f} GB (FLAC médio da amostra)")
    add("")

    fontes_audio = Counter(x.get("duracao_stream_audio_fonte") for x in ok)
    fontes_video = Counter(x.get("fim_video_fonte") for x in ok)
    add(f"Duração do stream de áudio veio de: {dict(fontes_audio)} "
        f"(\"formato\" = stream sem duração no ffprobe)")
    add(f"Fim do vídeo calculado com: {dict(fontes_video)}")
    add("")

    suspeitos = [
        x for x in ok
        if abs(x.get("dif_ms") or 0.0) > LIMITE_DIF_MS
        or abs(x.get("dif_video_ms") or 0.0) > LIMITE_DIF_VIDEO_MS
    ]
    add(f"Vídeos com |dif_ms| > {LIMITE_DIF_MS:.0f} ou |dif_video_ms| > "
        f"{LIMITE_DIF_VIDEO_MS:.0f}: {len(suspeitos)}")
    for x in suspeitos:
        add(f"  {x['caminho']}: dif_ms={x.get('dif_ms')} dif_video_ms={x.get('dif_video_ms')} "
            f"(áudio {x.get('duracao_stream_audio_fonte')}, fim {x.get('fim_video_fonte')})")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Roda o lote: um vídeo por vez, grava o JSONL e o resumo.

    Args:
        argv: argumentos da linha de comando (``None`` usa ``sys.argv``).

    Returns:
        Código de saída (0). Falhas de vídeos individuais vão para o registro, não para o código.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lista", default=str(PASTA / "lista20.txt"))
    ap.add_argument("--saida", default="custo20.jsonl", help="JSONL, dentro de a0/")
    ap.add_argument("--resumo", default="custo20_resumo.txt", help="resumo, dentro de a0/")
    ap.add_argument(
        "--so-resumo",
        action="store_true",
        help="não extrai: refaz o resumo a partir do JSONL já gravado em --saida",
    )
    args = ap.parse_args(argv)
    if args.so_resumo:
        registros = [
            json.loads(ln)
            for ln in (PASTA / args.saida).read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        texto = resumir(registros, len(registros), sum(x.get("tempo_parede_s", 0) for x in registros))
        (PASTA / args.resumo).write_text(texto, encoding="utf-8")
        print(texto)
        return 0

    lista = [
        ln.rstrip("\n")
        for ln in Path(args.lista).read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    saida = PASTA / args.saida
    resumo_arq = PASTA / args.resumo
    linhas: list[dict] = []
    inicio = time.monotonic()
    with saida.open("w", encoding="utf-8") as f:
        for i, rel in enumerate(lista, 1):
            x = medir(rel)
            linhas.append(x)
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
            f.flush()
            status = "ERRO " + x["erro"] if x.get("erro") else x.get("cache", "?")
            print(f"[{i:2d}/{len(lista)}] {x['tempo_parede_s']:7.3f} s  {status}  {rel}",
                  flush=True)
    tempo_total = time.monotonic() - inicio
    texto = resumir(linhas, len(lista), tempo_total)
    resumo_arq.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
