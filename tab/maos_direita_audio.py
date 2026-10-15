"""Tempo do som por ataque para a M7: ``t_audio`` vindo do alinhador de áudio (rodada 1012).

A rodada 1011 mediu que o gesto da mão direita vem cerca de 0,1 a 0,2 s depois do ``t_ini``
do marcador. A trilha do áudio (``tab.audio_alinhar``) diz, para cada coluna de cada
exibição, o instante em que ela soa (``t_audio``). Este módulo liga cada ataque do produto
(instante ``t_ini`` distinto) à coluna correspondente (tela, exibição, coluna) e devolve o
``t_audio``, ou None quando a coluna foi recusada pelo alinhador.

Funções puras, sem vídeo. A CLI só lê os produtos e os alinhamentos já gravados em
``MAOS_M7/audio`` e grava ``ataques_audio.json``.

Uso::

    python -m tab.maos_direita_audio
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .caminhos import MAOS_M7
from .maos_direita_tempo import NOMES
from .maos_padroes_preparar import VIDEOS

#: Pasta dos alinhamentos e dos arquivos derivados (dentro de ``MAOS_M7``).
PASTA_AUDIO = MAOS_M7 / "audio"

#: Casas de precisão para os instantes, como nos demais arquivos da M7.
CASAS_T = 3


def _log(msg: str) -> None:
    """Progresso no stderr (o stdout fica para o resumo final).

    Args:
        msg: texto da linha.
    """
    print(msg, file=sys.stderr, flush=True)


def indice_colunas_audio(
    colunas: list[dict[str, Any]],
) -> dict[tuple[int, int, int], dict[str, Any]]:
    """Índice ``(tela, exibicao, coluna) -> registro`` das colunas do alinhamento.

    Args:
        colunas: lista ``colunas`` do alinhamento (ou do ``chorinho/audio@1``).

    Returns:
        Dicionário com a chave ``(tela, exibicao, coluna)`` como inteiros.
    """
    return {(int(c["tela"]), int(c["exibicao"]), int(c["coluna"])): c for c in colunas}


def ataques_com_t_audio(
    notas: list[dict[str, Any]], colunas: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Um registro por instante ``t_ini`` distinto, com o ``t_audio`` da(s) coluna(s).

    Um ataque é um instante distinto do produto (arredondado a 3 casas). As notas sem
    ``t_ini`` ou sem ``exibicao`` são ignoradas. Se o instante cai em mais de uma coluna,
    o ``t_audio`` é a mediana das colunas que não foram recusadas. Se todas foram recusadas
    (ou não existem no alinhamento), o ``t_audio`` é None e ``motivo`` diz por quê.

    Args:
        notas: lista ``notas`` do produto (``t_ini``, ``tela``, ``exibicao``, ``coluna``).
        colunas: lista ``colunas`` do alinhamento da trilha do áudio.

    Returns:
        Lista ordenada por ``t_ini`` de ``{t_ini, t_audio, colunas, motivo}``, em que
        ``colunas`` são as chaves ``[tela, exibicao, coluna]`` do ataque e ``motivo`` é
        ``None`` quando há ``t_audio``.
    """
    indice = indice_colunas_audio(colunas)
    por_instante: dict[float, set[tuple[int, int, int]]] = {}
    for nota in notas:
        if nota.get("t_ini") is None or nota.get("exibicao") is None:
            continue
        t = round(float(nota["t_ini"]), CASAS_T)
        chave = (int(nota["tela"]), int(nota["exibicao"]), int(nota["coluna"]))
        por_instante.setdefault(t, set()).add(chave)
    saida = []
    for t in sorted(por_instante):
        chaves = sorted(por_instante[t])
        validos = []
        motivos = []
        for chave in chaves:
            reg = indice.get(chave)
            if reg is None:
                motivos.append("coluna ausente no alinhamento")
            elif reg.get("t_audio") is None:
                motivos.append(str(reg.get("motivo") or "recusada"))
            else:
                validos.append(float(reg["t_audio"]))
        t_audio = round(statistics.median(validos), CASAS_T) if validos else None
        saida.append(
            {
                "t_ini": t,
                "t_audio": t_audio,
                "colunas": [list(c) for c in chaves],
                "motivo": None
                if t_audio is not None
                else "; ".join(sorted(set(motivos))),
            }
        )
    return saida


def diferencas_ms(ataques: list[dict[str, Any]]) -> list[float]:
    """Diferença ``t_audio - t_ini`` em milissegundos, só para os ataques com ``t_audio``.

    Args:
        ataques: saída de ``ataques_com_t_audio``.

    Returns:
        Lista de diferenças em ms (positivo quer dizer que o som vem depois do marcador).
    """
    return [
        (a["t_audio"] - a["t_ini"]) * 1000.0
        for a in ataques
        if a["t_audio"] is not None
    ]


def resumo_diferencas(valores_ms: list[float]) -> dict[str, float | int | None]:
    """Mediana, p10 e p90 das diferenças ``t_audio - t_ini``, em ms.

    Args:
        valores_ms: diferenças em ms (de ``diferencas_ms``).

    Returns:
        ``{n, mediana_ms, p10_ms, p90_ms}``; os valores são None se a lista estiver vazia.
    """
    if not valores_ms:
        return {"n": 0, "mediana_ms": None, "p10_ms": None, "p90_ms": None}
    arr = np.asarray(valores_ms, dtype=float)
    return {
        "n": len(arr),
        "mediana_ms": round(float(np.median(arr)), 1),
        "p10_ms": round(float(np.percentile(arr, 10)), 1),
        "p90_ms": round(float(np.percentile(arr, 90)), 1),
    }


def t_audio_por_instante(ataques: list[dict[str, Any]]) -> dict[float, float]:
    """Mapa ``t_ini -> t_audio`` só com os ataques que têm ``t_audio``.

    Args:
        ataques: saída de ``ataques_com_t_audio``.

    Returns:
        Dicionário com a chave ``t_ini`` (3 casas) e o valor ``t_audio``.
    """
    return {a["t_ini"]: a["t_audio"] for a in ataques if a["t_audio"] is not None}


def instantes_audio(ataques: list[dict[str, Any]]) -> list[float]:
    """Lista ordenada dos ``t_audio`` dos ataques que têm um.

    Args:
        ataques: saída de ``ataques_com_t_audio``.

    Returns:
        Instantes em segundos, em ordem crescente, sem repetição.
    """
    return sorted({a["t_audio"] for a in ataques if a["t_audio"] is not None})


def _carregar(caminho: Path) -> dict[str, Any]:
    """Lê um JSON do disco.

    Args:
        caminho: arquivo JSON.

    Returns:
        O conteúdo decodificado.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def main() -> None:
    """Grava ``ataques_audio.json`` em ``PASTA_AUDIO`` e imprime o resumo por vídeo."""
    saida: dict[str, Any] = {"convencao": "t_audio - t_ini > 0: som depois do marcador"}
    videos = []
    for indice, video in enumerate(VIDEOS):
        nome = NOMES[indice]
        produto = _carregar(Path(video["produto"]))
        alinhado = _carregar(PASTA_AUDIO / f"alinhado_{nome}.json")
        ataques = ataques_com_t_audio(produto["notas"], alinhado["colunas"])
        resumo = resumo_diferencas(diferencas_ms(ataques))
        n_total = len(ataques)
        _log(f"{nome}: {n_total} ataques, t_audio em {resumo['n']}")
        videos.append(
            {
                "nome": nome,
                "produto": str(video["produto"]),
                "n_ataques": n_total,
                "n_com_t_audio": resumo["n"],
                "diferenca_ms": resumo,
                "ataques": ataques,
            }
        )
    saida["videos"] = videos
    PASTA_AUDIO.mkdir(parents=True, exist_ok=True)
    (PASTA_AUDIO / "ataques_audio.json").write_text(
        json.dumps(saida, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    for v in videos:
        d = v["diferenca_ms"]
        print(
            f"{v['nome']}: ataques={v['n_ataques']} com_t_audio={v['n_com_t_audio']} "
            f"mediana={d['mediana_ms']} p10={d['p10_ms']} p90={d['p90_ms']} ms"
        )


if __name__ == "__main__":
    main()
