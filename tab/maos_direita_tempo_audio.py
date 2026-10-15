"""Média sincronizada da energia de movimento contra o ``t_audio`` (M7, item 1c).

Refaz a medição de ``tab.maos_direita_tempo`` com o instante do som (``t_audio`` da trilha
do áudio, ``tab.maos_direita_audio``) no lugar do ``t_ini`` do marcador. Usa os mesmos
trechos de 20 s de ``tempo.json`` e os mesmos recortes, quadros e janelas de ±0,5 s.

Como o atraso de ~0,14 s já está descontado no ``t_audio``, a convenção é: pico perto de 0 s
quer dizer que o gesto acompanha o som. Não se soma nenhum deslocamento.

Grava ``tempo_audio.json`` e ``tempo_audio.png`` em ``MAOS_M7``.

Uso::

    python -m tab.maos_direita_tempo_audio
"""

from __future__ import annotations

import json
import sys
from typing import Any

import numpy as np

from .caminhos import MAOS_M7, acervo
from .maos_direita_audio import PASTA_AUDIO, instantes_audio
from .maos_direita_tempo import (
    JANELA_S,
    N_EMBARALHAR,
    NOMES,
    RECORTES,
    SEMENTE,
    TRECHO_S,
    desenhar_grafico,
    ler_video,
    medir_trecho,
    pico_da_curva,
)
from .maos_padroes_preparar import VIDEOS

#: Título e eixo do gráfico desta medição (ASCII).
TITULO = "media sincronizada ao t_audio (som), painel inteiro, por video"
EIXO_X = (
    "atraso do movimento em relacao ao t_audio (s): pico perto de 0 = acompanha o som"
)


def _log(msg: str) -> None:
    """Progresso no stderr (o stdout fica para o resumo final).

    Args:
        msg: texto da linha.
    """
    print(msg, file=sys.stderr, flush=True)


def instantes_no_trecho(instantes: list[float], inicio: float) -> list[float]:
    """Instantes que caem no trecho ``[inicio, inicio + TRECHO_S)``.

    Args:
        instantes: instantes em segundos.
        inicio: início do trecho, em segundos.

    Returns:
        Os instantes do trecho, na ordem recebida.
    """
    return [t for t in instantes if inicio <= t < inicio + TRECHO_S]


def pico_media(curva: list[float], lags_s: list[float]) -> dict[str, float]:
    """Atraso e valor do máximo de uma média sincronizada.

    Args:
        curva: média sincronizada, do mesmo tamanho de ``lags_s``.
        lags_s: atrasos, em segundos.

    Returns:
        ``{atraso_s, valor}``, com o atraso arredondado a 3 casas.
    """
    atraso, valor = pico_da_curva(np.asarray(curva, dtype=float), np.asarray(lags_s))
    return {"atraso_s": round(atraso, 3), "valor": round(valor, 4)}


def main() -> None:
    """Mede os quatro vídeos com ``t_audio``, grava o JSON e o PNG e imprime os picos."""
    tempo_t_ini = json.loads((MAOS_M7 / "tempo.json").read_text(encoding="utf-8"))
    saida: dict[str, Any] = {
        "semente": SEMENTE,
        "trecho_s": TRECHO_S,
        "janela_s": JANELA_S,
        "embaralhamentos": N_EMBARALHAR,
        "fonte_dos_instantes": "t_audio (tab.maos_direita_audio), sem deslocamento",
        "convencao": "atraso > 0: movimento depois do t_audio",
        "videos": [],
    }
    curvas_grafico: dict[str, np.ndarray] = {}
    lags_s = np.array([])
    for indice, video in enumerate(VIDEOS):
        nome = NOMES[indice]
        caminho = acervo() / video["arquivo"]
        ataques = json.loads((PASTA_AUDIO / "ataques_audio.json").read_text())
        ataques = ataques["videos"][indice]["ataques"]
        instantes = instantes_audio(ataques)
        largura, altura, fps = ler_video(caminho)
        referencia = next(v for v in tempo_t_ini["videos"] if v["nome"] == nome)
        _log(f"{nome}: {len(instantes)} instantes com t_audio")
        trechos = []
        janelas_video: dict[str, list[np.ndarray]] = {r: [] for r in RECORTES}
        for trecho_ref in referencia["trechos"]:
            inicio = float(trecho_ref["inicio_s"])
            no_trecho = instantes_no_trecho(instantes, inicio)
            medido = medir_trecho(caminho, inicio, no_trecho, largura, altura, fps)
            for r in RECORTES:
                janelas_video[r].append(medido["janelas"][r])
            del medido["janelas"]
            trechos.append(medido)
            _log(f"  trecho {inicio:.1f}s: {len(no_trecho)} instantes")
        lags_s = np.arange(-round(JANELA_S * fps), round(JANELA_S * fps) + 1) / fps
        media = {}
        for r in RECORTES:
            todas = np.vstack(janelas_video[r])
            curva = [round(float(v), 4) for v in todas.mean(axis=0)]
            media[r] = {
                "n_eventos": len(todas),
                "curva": curva,
                "pico": pico_media(curva, [round(float(v), 4) for v in lags_s]),
            }
        curvas_grafico[nome] = np.array(media["painel"]["curva"])
        saida["videos"].append(
            {
                "nome": nome,
                "arquivo": video["arquivo"],
                "largura": largura,
                "altura": altura,
                "fps": round(fps, 4),
                "n_instantes": len(instantes),
                "trechos": trechos,
                "media_sincronizada": media,
            }
        )
    saida["lags_s"] = [round(float(v), 4) for v in lags_s]
    MAOS_M7.mkdir(parents=True, exist_ok=True)
    (MAOS_M7 / "tempo_audio.json").write_text(json.dumps(saida, indent=2))
    desenhar_grafico(
        curvas_grafico,
        lags_s,
        MAOS_M7 / "tempo_audio.png",
        titulo=TITULO,
        eixo_x=EIXO_X,
    )
    for video in saida["videos"]:
        for r in RECORTES:
            m = video["media_sincronizada"][r]
            print(
                f"{video['nome']} {r}: eventos={m['n_eventos']} "
                f"pico {m['pico']['valor']:+.4f} em {m['pico']['atraso_s']:+.3f}s"
            )


if __name__ == "__main__":
    main()
