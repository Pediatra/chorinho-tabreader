"""Figuras e clipes de conferência da medição de atraso (trilha A1).

Usa matplotlib: roda só na imagem derivada ``chorinho-audio:dev`` (``Dockerfile.audio``), nunca
na base. Nenhum teste importa este módulo.

Entradas: o JSON de ``tab.audio_atraso`` e o vídeo (para recalcular o espectrograma). Antes de
desenhar, RECONSTRÓI as medições com as mesmas funções de ``tab.audio_atraso`` e confere com o
JSON: qualquer diferença é erro e aparece na saída.

Trechos (regra, não gosto): 8 s começando 0,5 s antes do 1º ``t_ini`` de (tela 1, exibição 1),
(tela 7, exibição 1) e (tela 3, exibição 2). Exibição 1 é a primeira no tempo.

Uso::

    python -m tab.audio_figuras --atraso data/saida/audio/a1/atraso_mvp.json \\
        --video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" \\
        --pasta data/saida/audio/a1/figuras --clipes data/saida/audio/a1/clipes
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from tab.audio.atraso import (
    Evento,
    medir_passada,
    preparar,
)
from tab.audio.onsets import fluxo_nas_alturas, midi_da_nota

#: Duração de cada trecho, em segundos.
DURACAO_TRECHO_S = 8.0

#: Antecedência do trecho em relação ao 1º ``t_ini`` da exibição, em segundos.
ANTECEDENCIA_S = 0.5

#: Trechos escolhidos por regra: (nome, tela, índice da exibição; 0 é a 1ª no tempo).
REGRAS_TRECHO = (
    ("trecho1_tela1_exib1", 1, 0),
    ("trecho2_tela7_exib1", 7, 0),
    ("trecho3_tela3_exib2", 3, 1),
)

#: Taxa dos cliques (e dos WAV de cliques), em Hz.
TAXA_CLIQUE = 48000

#: Duração de cada clique, em segundos.
DURACAO_CLIQUE_S = 0.010

#: Frequência do clique, em Hz.
FREQ_CLIQUE_HZ = 2000.0

#: Amplitude do clique (fração do fundo de escala); audível, sem saturar.
AMPLITUDE_CLIQUE = 0.5

#: Limiar de detecção dos cliques no resíduo (fração do máximo do casamento de filtro).
LIMIAR_CLIQUE = 0.5


def _janela_quadros(tempos: np.ndarray, a: float, b: float) -> tuple[int, int]:
    """Índices ``[ini, fim)`` dos quadros com instante em ``[a, b)``.

    Args:
        tempos: instantes dos quadros.
        a: início, em segundos.
        b: fim (exclusivo), em segundos.

    Returns:
        ``(ini, fim)``.
    """
    return (
        int(np.searchsorted(tempos, a, side="left")),
        int(np.searchsorted(tempos, b, side="left")),
    )


def _curva_alturas(
    ctx, midis: list[int], a: float, b: float
) -> tuple[np.ndarray, np.ndarray]:
    """Curva ``fluxo_nas_alturas`` do evento, só nos quadros da janela ``[a, b)``.

    Args:
        ctx: ``tab.audio_atraso.Contexto`` do vídeo.
        midis: MIDI das notas do evento.
        a: início da janela.
        b: fim da janela.

    Returns:
        ``(tempos_dos_quadros, valores)`` dentro da janela.
    """
    k_a, k_b = _janela_quadros(ctx.tempos, a, b)
    ini = max(0, k_a - 1)
    fim = min(len(ctx.tempos), k_b + 1)
    curva = fluxo_nas_alturas(ctx.mag[ini:fim], ctx.freqs, midis)
    return ctx.tempos[k_a:k_b], curva[k_a - ini : k_b - ini]


def _eventos_do_json(
    eventos_json: list[dict],
) -> tuple[list[Evento], list[float], list[tuple[float, float]]]:
    """Reconstrói os eventos (e larguras) a partir das linhas do JSON.

    Args:
        eventos_json: lista ``eventos`` do JSON de ``tab.audio_atraso``.

    Returns:
        ``(eventos, t_ini, larguras)``.
    """
    eventos = [
        Evento(
            tela=int(e["tela"]),
            exibicao=int(e["exibicao"]),
            passagem=int(e["passagem"]),
            coluna=int(e["coluna"]),
            t_ini=float(e["t_ini"]),
            notas=tuple((int(c), int(s)) for c, s in e["notas"]),
        )
        for e in eventos_json
    ]
    larguras = [(float(e["w_esq"]), float(e["w_dir"])) for e in eventos_json]
    return eventos, [e.t_ini for e in eventos], larguras


def conferir_com_json(ctx, atraso: dict) -> int:
    """Reexecuta as medições e compara com o JSON; devolve o número de diferenças.

    Args:
        ctx: contexto do vídeo (``tab.audio_atraso.preparar``).
        atraso: JSON completo de ``tab.audio_atraso``.

    Returns:
        Quantidade de campos ``t_som`` (ou ``delta_ms``) diferentes entre recalculo e JSON.
    """
    k = int(atraso["transposicao"]["k"])
    mediana_s = float(atraso["mediana_delta_fluxo_passada1_s"])
    eventos, t_ini, larguras = _eventos_do_json(atraso["eventos"])
    p1 = medir_passada(eventos, larguras, t_ini, ctx, k)
    p2 = medir_passada(eventos, larguras, [t + mediana_s for t in t_ini], ctx, k)
    diferencas = 0
    for linha, r1, r2 in zip(atraso["eventos"], p1, p2, strict=True):
        for passada, recalc in (("passada1", r1), ("passada2", r2)):
            for metodo in ("fluxo", "alturas"):
                esperado = linha[passada][metodo]["t_som"]
                obtido = recalc[metodo]["t_som"]
                if (esperado is None) != (obtido is None) or (
                    esperado is not None and abs(esperado - obtido) > 1e-6
                ):
                    diferencas += 1
    return diferencas


def escolher_trechos(eventos_json: list[dict]) -> list[dict]:
    """Aplica a regra de trecho: 0,5 s antes do 1º ``t_ini`` da exibição, 8 s de duração.

    Args:
        eventos_json: lista ``eventos`` do JSON.

    Returns:
        Lista de ``{"nome", "tela", "exibicao", "inicio", "fim"}``.

    Raises:
        ValueError: se a regra não achar eventos para uma (tela, exibição).
    """
    trechos = []
    for nome, tela, exibicao in REGRAS_TRECHO:
        ts = [
            float(e["t_ini"])
            for e in eventos_json
            if e["tela"] == tela and e["exibicao"] == exibicao
        ]
        if not ts:
            raise ValueError(f"sem eventos para tela {tela} exibição {exibicao}")
        inicio = min(ts) - ANTECEDENCIA_S
        trechos.append(
            {
                "nome": nome,
                "tela": tela,
                "exibicao": exibicao,
                "inicio": inicio,
                "fim": inicio + DURACAO_TRECHO_S,
            }
        )
    return trechos


def _eventos_no_trecho(eventos_json: list[dict], trecho: dict) -> list[dict]:
    """Eventos do JSON cujo ``t_ini`` cai no trecho.

    Args:
        eventos_json: lista ``eventos`` do JSON.
        trecho: trecho de ``escolher_trechos``.

    Returns:
        Eventos em ordem de tempo.
    """
    return [e for e in eventos_json if trecho["inicio"] <= e["t_ini"] < trecho["fim"]]


def figura_trecho(ctx, trecho: dict, eventos: list[dict], pasta: Path, k: int) -> Path:
    """Figura de um trecho: espectrograma, fluxo com picos e alturas por evento.

    Args:
        ctx: contexto do vídeo.
        trecho: trecho escolhido.
        eventos: eventos do trecho (do JSON).
        pasta: onde gravar a PNG.
        k: transposição da medição (do JSON).

    Returns:
        Caminho da PNG (largura de 2400 px).
    """
    a, b = trecho["inicio"], trecho["fim"]
    i0, i1 = _janela_quadros(ctx.tempos, a, b)
    tempos = ctx.tempos[i0:i1]
    db = 20.0 * np.log10(ctx.mag[i0:i1].T + 1e-9)
    vmax = float(db.max())

    deltas = [e["passada2"]["fluxo"]["delta_ms"] for e in eventos]
    deltas = [d for d in deltas if d is not None]
    mediana = float(np.median(deltas)) if deltas else float("nan")
    telas = sorted({e["tela"] for e in eventos})

    fig, (ax1, ax2, ax3) = plt.subplots(
        3,
        1,
        figsize=(24, 16),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1.5, 1.5]},
    )
    fig.suptitle(
        f"{trecho['nome']} | {a:.3f}-{b:.3f} s do vídeo | telas {telas} | "
        f"Δ mediano (fluxo, passada 2) = {mediana:.1f} ms (n={len(deltas)})",
        fontsize=14,
    )

    malha = ax1.pcolormesh(
        tempos, ctx.freqs, db, shading="auto", cmap="magma", vmin=vmax - 80, vmax=vmax
    )
    ax1.set_yscale("log")
    ax1.set_ylim(60, 2500)
    ax1.set_ylabel("Hz (log)")
    ax1.set_title("espectrograma (dB)")
    fig.colorbar(malha, ax=ax1, pad=0.01).set_label("dB")

    ax2.plot(tempos, ctx.fluxo[i0:i1], color="C0", lw=1)
    pk = np.asarray([i for i in ctx.picos_idx if i0 <= i < i1], dtype=np.int64)
    ax2.scatter(ctx.tempos[pk], ctx.fluxo[pk], color="k", s=14, zorder=3)
    ax2.set_ylabel("fluxo")
    ax2.set_title("fluxo espectral (pontos: picos)")

    cores = plt.get_cmap("tab10")
    for n, e in enumerate(eventos):
        midis = [midi_da_nota(c, s, k) for c, s in e["notas"]]
        j_a, j_b = e["passada2"]["janela"]
        tq, valores = _curva_alturas(ctx, midis, j_a, j_b)
        ax3.plot(tq, valores, color=cores(n % 10), lw=1, label=f"col {e['coluna']}")
    ax3.set_ylabel("fluxo nas alturas")
    ax3.set_xlabel("tempo do vídeo (s)")
    ax3.set_title("fluxo nas alturas do evento (curva dentro da janela de cada evento)")

    for ax in (ax1, ax2, ax3):
        for e in eventos:
            ax.axvline(e["t_ini"], color="white" if ax is ax1 else "0.3", ls="--", lw=1)
        for e in eventos:
            if e["passada2"]["fluxo"]["t_som"] is not None:
                ax.axvline(e["passada2"]["fluxo"]["t_som"], color="red", lw=1.2)
    for e in eventos:
        ax1.text(
            e["t_ini"],
            ax1.get_ylim()[1] * 0.95,
            f"c{e['coluna']}",
            color="white",
            fontsize=8,
            rotation=90,
            va="top",
        )
    for e in eventos:
        if e["passada2"]["alturas"]["t_som"] is not None:
            ax3.axvline(
                e["passada2"]["alturas"]["t_som"], color="orange", lw=1.2, ls=":"
            )
    ax3.legend(loc="upper right", fontsize=7, ncol=8)
    ax1.set_xlim(a, b)

    saida = pasta / f"{trecho['nome']}.png"
    fig.savefig(saida, dpi=100)
    plt.close(fig)
    return saida


def figura_histograma(eventos: list[dict], pasta: Path) -> Path:
    """Histograma de Δ (passada 2) para os dois métodos, em bins de 10 ms de -300 a +300.

    Args:
        eventos: linhas do JSON.
        pasta: pasta de saída.

    Returns:
        Caminho da PNG.
    """
    fig, ax = plt.subplots(figsize=(14, 8), dpi=100)
    bins = np.arange(-300, 301, 10)
    info = []
    for metodo, cor, estilo in (("fluxo", "C0", "-"), ("alturas", "C1", "--")):
        d = [e["passada2"][metodo]["delta_ms"] for e in eventos]
        d = np.asarray([x for x in d if x is not None], dtype=np.float64)
        fora = int(np.sum((d < -300) | (d > 300)))
        ax.hist(
            d,
            bins=bins,
            histtype="step",
            color=cor,
            ls=estilo,
            lw=2,
            label=f"{metodo} (n={d.size}, fora de ±300 ms: {fora})",
        )
        med = float(np.median(d))
        ax.axvline(med, color=cor, ls=estilo, lw=1.2)
        info.append(f"{metodo}: mediana {med:.1f} ms")
    ax.set_xlabel("Δ = t_som - t_ini (ms), passada 2")
    ax.set_ylabel("eventos")
    ax.set_title(
        "Histograma de Δ, passada 2 (linhas verticais: medianas) | " + " | ".join(info)
    )
    ax.legend()
    saida = pasta / "histograma_delta.png"
    fig.savefig(saida, dpi=100)
    plt.close(fig)
    return saida


def figura_delta_no_tempo(eventos: list[dict], pasta: Path) -> Path:
    """Δ (fluxo, passada 2) contra ``t_ini``, cor por tela, com a reta de deriva.

    Args:
        eventos: linhas do JSON.
        pasta: pasta de saída.

    Returns:
        Caminho da PNG.
    """
    fig, ax = plt.subplots(figsize=(18, 8), dpi=100)
    pts = [
        (e["t_ini"], e["passada2"]["fluxo"]["delta_ms"], e["tela"])
        for e in eventos
        if e["passada2"]["fluxo"]["delta_ms"] is not None
    ]
    t = np.asarray([p[0] for p in pts])
    d = np.asarray([p[1] for p in pts])
    cmap = plt.get_cmap("tab20")
    for tela in sorted({p[2] for p in pts}):
        sel = [p for p in pts if p[2] == tela]
        ax.scatter(
            [p[0] for p in sel],
            [p[1] for p in sel],
            s=18,
            color=cmap((tela - 1) % 20),
            label=f"tela {tela}",
        )
    coef = np.polyfit(t, d, 1)
    xs = np.linspace(t.min(), t.max(), 50)
    ax.plot(
        xs,
        np.polyval(coef, xs),
        color="k",
        lw=1.5,
        label=f"deriva {coef[0] * 60:.2f} ms/min",
    )
    ax.set_xlabel("t_ini (s do vídeo)")
    ax.set_ylabel("Δ (ms), método fluxo, passada 2")
    ax.set_title("Δ contra o tempo, cor por tela")
    ax.legend(ncol=5, fontsize=8)
    saida = pasta / "delta_no_tempo.png"
    fig.savefig(saida, dpi=100)
    plt.close(fig)
    return saida


def _rajada() -> np.ndarray:
    """Forma de onda de um clique: senóide de ``FREQ_CLIQUE_HZ`` com envelope de Hann.

    Returns:
        Vetor de ``round(DURACAO_CLIQUE_S * TAXA_CLIQUE)`` amostras (float).
    """
    n = round(DURACAO_CLIQUE_S * TAXA_CLIQUE)
    t = np.arange(n) / TAXA_CLIQUE
    return AMPLITUDE_CLIQUE * np.sin(2 * np.pi * FREQ_CLIQUE_HZ * t) * np.hanning(n)


def trilha_cliques(instantes_rel: list[float], dur: float) -> np.ndarray:
    """Trilha de cliques estéreo: cada clique começa no instante dado (relativo ao clipe).

    Args:
        instantes_rel: instantes dos cliques, em segundos a partir do início do clipe.
        dur: duração do clipe, em segundos.

    Returns:
        Array ``[amostras, 2]`` float, em ``[-1, 1]``.
    """
    n = round(dur * TAXA_CLIQUE)
    trilha = np.zeros(n, dtype=np.float64)
    burst = _rajada()
    for t in instantes_rel:
        i = round(t * TAXA_CLIQUE)
        if 0 <= i < n:
            fim = min(n, i + len(burst))
            trilha[i:fim] += burst[: fim - i]
    return np.stack([trilha, trilha], axis=1)


def gravar_wav(caminho: Path, trilha: np.ndarray) -> None:
    """Grava uma trilha estéreo float em WAV PCM 16 bits.

    Args:
        caminho: arquivo de saída.
        trilha: ``[amostras, 2]`` em ``[-1, 1]``.
    """
    pcm = np.clip(np.round(trilha * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(TAXA_CLIQUE)
        w.writeframes(pcm.tobytes())


def _ffmpeg(args: list[str]) -> None:
    """Roda o ffmpeg e falha alto se ele falhar.

    Args:
        args: argumentos depois do binário.

    Raises:
        RuntimeError: se o ffmpeg devolver erro.
    """
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {proc.stderr.strip()}")


def clipe_com_cliques(video: str, inicio: float, wav: Path, saida: Path) -> None:
    """Recorta o trecho do vídeo, recodifica em H.264 e mistura o áudio original com a trilha.

    Args:
        video: vídeo de origem (somente leitura).
        inicio: início do trecho, em segundos do vídeo.
        wav: trilha de cliques (estéreo, ``TAXA_CLIQUE``).
        saida: MP4 de saída.
    """
    filtro = (
        "[0:a]aresample=48000,aformat=channel_layouts=stereo[a];"
        "[1:a]aformat=channel_layouts=stereo[c];"
        "[a][c]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[m]"
    )
    _ffmpeg(
        [
            "-ss",
            f"{inicio:.3f}",
            "-i",
            video,
            "-i",
            str(wav),
            "-t",
            f"{DURACAO_TRECHO_S:.3f}",
            "-filter_complex",
            filtro,
            "-map",
            "0:v:0",
            "-map",
            "[m]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(saida),
        ]
    )


def _decodificar(caminho: str, inicio: float, dur: float) -> np.ndarray:
    """Áudio mono de um trecho, decodificado pelo ffmpeg a ``TAXA_CLIQUE``.

    Args:
        caminho: arquivo (vídeo ou MP4).
        inicio: início, em segundos.
        dur: duração, em segundos.

    Returns:
        Amostras float em ``[-1, 1)``.
    """
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-ss",
            f"{inicio:.3f}",
            "-i",
            caminho,
            "-t",
            f"{dur:.3f}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(TAXA_CLIQUE),
            "-f",
            "s16le",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype="<i2").astype(np.float64) / 32768.0


def _atraso_entre(out: np.ndarray, ref: np.ndarray, maximo: int) -> int:
    """Deslocamento ``L`` com ``out[m] ~ ref[m - L]``, por correlação cruzada (FFT).

    Args:
        out: sinal do clipe de saída.
        ref: sinal de referência (o mesmo trecho do vídeo original).
        maximo: busca em ``[-maximo, maximo]`` amostras.

    Returns:
        ``L`` (em amostras) de maior correlação.
    """
    n = len(out) + len(ref)
    nfft = 1 << int(np.ceil(np.log2(n)))
    c = np.fft.irfft(np.fft.rfft(out, nfft) * np.conj(np.fft.rfft(ref, nfft)), nfft)
    lags = np.concatenate([np.arange(0, maximo + 1), np.arange(-maximo, 0)])
    return int(lags[np.argmax(c[lags % nfft])])


def verificar_clipe(
    video: str,
    inicio: float,
    instantes_rel: list[float],
    mp4: Path,
) -> dict:
    """Confere a posição dos cliques no MP4: subtrai a referência e casa o clique.

    O resíduo ``out - ref`` (com o atraso ``L`` da correlação) deixa só os cliques e o erro de
    codec. Cada clique é achado pelo casamento de filtro com a forma do clique. ``erro`` é a
    posição achada menos a esperada, em ms, na linha do tempo do MP4.

    Args:
        video: vídeo de origem.
        inicio: início do trecho, em segundos do vídeo.
        instantes_rel: instantes esperados dos cliques, relativos ao clipe.
        mp4: clipe gerado.

    Returns:
        ``{"lag_amostras", "lag_ms", "esperados", "achados", "erro_max_ms", "erro_medio_ms"}``.
    """
    out = _decodificar(str(mp4), 0.0, DURACAO_TRECHO_S)
    ref = _decodificar(video, inicio, DURACAO_TRECHO_S)
    n = min(len(out), len(ref))
    out, ref = out[:n], ref[:n]
    lag = _atraso_entre(out, ref, 4800)
    # resíduo indexado pelo quadro do CLIPE (out): resid[m] = out[m] - ref[m - lag]
    resid = np.zeros(n)
    if lag >= 0:
        resid[lag:] = out[lag:] - ref[: n - lag]
    else:
        resid[: n + lag] = out[: n + lag] - ref[-lag:]
    burst = _rajada()
    casamento = np.correlate(resid, burst, mode="valid")
    limiar = LIMIAR_CLIQUE * float(np.max(np.abs(casamento))) if casamento.size else 0.0
    sep = int(0.3 * TAXA_CLIQUE)
    achados: list[int] = []
    for i in np.argsort(-np.abs(casamento)):
        if np.abs(casamento[i]) < limiar:
            break
        if all(abs(int(i) - j) >= sep for j in achados):
            achados.append(int(i))
    achados.sort()
    esperados = [round(t * TAXA_CLIQUE) for t in instantes_rel]
    erros_ms: list[float] = []
    for e in esperados:
        if not achados:
            break
        mais = min(achados, key=lambda x: abs(x - e))
        erros_ms.append((mais - e) / TAXA_CLIQUE * 1000.0)
    return {
        "lag_amostras": lag,
        "lag_ms": round(lag / TAXA_CLIQUE * 1000.0, 4),
        "esperados": len(esperados),
        "achados": len(achados),
        "erro_max_ms": round(float(np.max(np.abs(erros_ms))), 4) if erros_ms else None,
        "erro_medio_ms": round(float(np.mean(erros_ms)), 4) if erros_ms else None,
    }


def gerar_clipes(
    video: str,
    trechos: list[dict],
    eventos: list[dict],
    pasta: Path,
) -> dict:
    """Clipes de conferência: dois MP4 por trecho (cliques em ``t_ini`` e em ``t_som``).

    Args:
        video: vídeo de origem.
        trechos: trechos de ``escolher_trechos``.
        eventos: linhas do JSON.
        pasta: pasta de saída dos MP4 e dos WAV de cliques.

    Returns:
        Dicionário com o resultado de ``verificar_clipe`` por arquivo.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    resultado: dict = {}
    for trecho in trechos:
        a = trecho["inicio"]
        no_trecho = _eventos_no_trecho(eventos, trecho)
        marcador = [e["t_ini"] - a for e in no_trecho]
        audio = [
            e["passada2"]["fluxo"]["t_som"] - a
            for e in no_trecho
            if e["passada2"]["fluxo"]["t_som"] is not None
        ]
        for tipo, instantes in (("marcador", marcador), ("audio", audio)):
            wav = pasta / f"{trecho['nome']}_cliques_{tipo}.wav"
            gravar_wav(wav, trilha_cliques(instantes, DURACAO_TRECHO_S))
            mp4 = pasta / f"{trecho['nome']}_clique_{tipo}.mp4"
            clipe_com_cliques(video, a, wav, mp4)
            resultado[mp4.name] = verificar_clipe(video, a, instantes, mp4)
            resultado[mp4.name]["cliques_esperados_s"] = [
                round(x, 4) for x in instantes
            ]
    return resultado


def main() -> int:
    """Ponto de entrada: figuras, histograma, deriva, clipes e conferência do alinhamento.

    Returns:
        Código de saída (0 se deu certo).
    """
    matplotlib.use("Agg")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--atraso", required=True, help="JSON de tab.audio_atraso")
    parser.add_argument(
        "--video", required=True, help="vídeo de origem (somente leitura)"
    )
    parser.add_argument("--pasta", required=True, help="pasta das figuras")
    parser.add_argument("--clipes", required=True, help="pasta dos clipes")
    args = parser.parse_args()

    with open(args.atraso, encoding="utf-8") as f:
        atraso = json.load(f)
    ctx, _meta = preparar(os.path.abspath(args.video))

    diferencas = conferir_com_json(ctx, atraso)
    print(
        f"conferência com o JSON (t_som dos dois métodos, duas passadas): {diferencas} diferenças"
    )
    if diferencas:
        print("ERRO: a reconstrução não bate com o JSON", file=sys.stderr)
        return 1

    eventos = atraso["eventos"]
    k = int(atraso["transposicao"]["k"])
    pasta = Path(args.pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    trechos = escolher_trechos(eventos)
    for trecho in trechos:
        no_trecho = _eventos_no_trecho(eventos, trecho)
        caminho = figura_trecho(ctx, trecho, no_trecho, pasta, k)
        print(
            f"{trecho['nome']}: {trecho['inicio']:.3f}-{trecho['fim']:.3f} s, "
            f"{len(no_trecho)} eventos -> {caminho}"
        )
    print(f"histograma: {figura_histograma(eventos, pasta)}")
    print(f"deriva: {figura_delta_no_tempo(eventos, pasta)}")

    alinhamento = gerar_clipes(
        os.path.abspath(args.video), trechos, eventos, Path(args.clipes)
    )
    caminho_al = Path(args.clipes) / "alinhamento.json"
    caminho_al.write_text(
        json.dumps(alinhamento, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for nome, r in alinhamento.items():
        print(
            f"{nome}: lag {r['lag_ms']} ms | achados {r['achados']} de {r['esperados']} | "
            f"erro médio {r['erro_medio_ms']} ms, máximo {r['erro_max_ms']} ms"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
