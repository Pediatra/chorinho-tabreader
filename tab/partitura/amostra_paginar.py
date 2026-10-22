"""D1 da partitura: paginar os 40 vídeos sorteados, um por vez (rodada 3160).

Lê ``amostra.json`` (já commitado antes desta etapa) e roda ``paginar`` em cada vídeo,
na ordem do sorteio, com um vídeo por vez (o HD externo é lido quadro a quadro). Registra
tempo, número de páginas e erro de cada vídeo em ``paginar_log.json``, na pasta da frente.
Um erro num vídeo não para a rodada: ele fica registrado e a fila segue.

Os recortes de cada vídeo vão para ``videos/<slug>/`` dentro da pasta da frente.

Uso (dentro do container, na raiz do projeto)::

    python -m tab.partitura_amostra_paginar
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np

from tab.comum.caminhos import PART_FRENTE_D
from tab.partitura import video as _pv
from tab.partitura.video import paginar
from tab.tablatura.produto.video import _slug


def _forca_de_linha_segura(
    cinza: np.ndarray, y: float, entrelinha: float, x0: int, x1: int
) -> float:
    """Cópia de ``partitura_video._forca_de_linha`` com um único ajuste.

    Ajuste: se a faixa de linhas fica fora do quadro (a 6ª linha abaixo da pauta cai abaixo
    da borda da imagem), a força é 0. O original levantava ``ValueError`` (zero-size array),
    o que parava o paginar do vídeo. Quando a faixa não é vazia, o resultado é igual ao do
    original.

    Args:
        cinza: quadro em tons de cinza.
        y: linha candidata, em px.
        entrelinha: entrelinha da pauta, em px.
        x0: início horizontal (inclusive).
        x1: fim horizontal (exclusivo).

    Returns:
        A força da linha, entre 0 e 1.
    """
    altura = cinza.shape[0]
    largura = x1 - x0
    if largura <= 0:
        return 0.0
    yc = round(y)
    meia = round(entrelinha / 2)
    ya = min(max(yc - meia, 0), altura - 1)
    yb = min(max(yc + meia, 0), altura - 1)
    faixa = cinza[max(yc - 2, 0) : min(yc + 3, altura), x0:x1].astype(np.int32)
    if faixa.shape[0] == 0:
        return 0.0
    ref = (cinza[ya, x0:x1].astype(np.int32) + cinza[yb, x0:x1].astype(np.int32)) / 2
    presente = faixa.min(axis=0) <= ref - _pv.CRISTA_DELTA_EXT
    return float(np.count_nonzero(presente)) / largura


# Troca em tempo de execução: o paginar chama _forca_de_linha pelo nome do módulo.
_pv._forca_de_linha = _forca_de_linha_segura

AMOSTRA = PART_FRENTE_D / "amostra.json"
LOG = PART_FRENTE_D / "paginar_log.json"


def _videos_na_ordem(amostra: dict) -> list[str]:
    """Os vídeos escolhidos, canal por canal, na ordem alfabética dos canais.

    Args:
        amostra: documento de ``amostra.json``.

    Returns:
        Lista de ``canal/arquivo`` sem repetição.
    """
    return [
        v
        for canal in sorted(amostra["escolhidos"])
        for v in amostra["escolhidos"][canal]
    ]


def _gravar_log(registros: list[dict]) -> None:
    """Grava o log inteiro, a cada vídeo, para não perder o andamento se a rodada cair.

    Args:
        registros: uma entrada por vídeo já paginado.
    """
    LOG.parent.mkdir(parents=True, exist_ok=True)
    tmp = LOG.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(LOG)


def _rodar(video: str, origem: str) -> dict:
    """Pagina um vídeo e devolve o registro dele (erro e contagem de páginas com pauta).

    Args:
        video: ``canal/arquivo`` do vídeo.
        origem: ``sorteio`` ou ``reserva de <vídeo trocado>``.

    Returns:
        Registro com ``video``, ``origem``, ``paginas``, ``paginas_com_pauta``, ``erro``.
    """
    pasta = PART_FRENTE_D / "videos" / _slug(video)
    inicio = time.time()
    erro = None
    paginas: list[dict] = []
    try:
        paginas = paginar(video, pasta)
    except Exception as falha:
        erro = f"{type(falha).__name__}: {falha}"
    return {
        "video": video,
        "origem": origem,
        "pasta": str(pasta),
        "segundos": round(time.time() - inicio, 1),
        "paginas": len(paginas),
        "paginas_com_pauta": sum(1 for p in paginas if p.get("pautas", 0) > 0),
        "erro": erro,
    }


def main(argv: list[str] | None = None) -> int:
    """Pagina a amostra em duas passadas e grava o log.

    Primeira passada: os 40 sorteados, um por vez. Se mais de 25 % deles não têm página com
    pauta, a rodada para e o log diz isso. Segunda passada: cada sem pauta sai e entra a
    próxima reserva do mesmo canal, com o motivo no log. Reserva sem pauta também é trocada,
    enquanto houver reserva.

    Args:
        argv: sem argumentos.

    Returns:
        Zero se a rodada terminou; um se parou pela regra de 25 %.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    amostra = json.loads(AMOSTRA.read_text(encoding="utf-8"))
    registros: list[dict] = []
    for canal in sorted(amostra["escolhidos"]):
        for video in amostra["escolhidos"][canal]:
            registros.append(_rodar(video, "sorteio"))
            _gravar_log(registros)
            print(
                f"sorteio {len(registros)}: {video[:40]} paginas {registros[-1]['paginas']}",
                flush=True,
            )
    sem_pagina = [r for r in registros if r["paginas_com_pauta"] == 0]
    parar = len(sem_pagina) > 0.25 * len(registros)
    if parar:
        print(
            f"PARADA: {len(sem_pagina)} de {len(registros)} sem página com pauta (>25%)",
            flush=True,
        )
        _gravar_log(
            [
                *registros,
                {"parada": True, "sem_pauta_primeira_passada": len(sem_pagina)},
            ]
        )
        return 1
    reservas = {c: list(amostra["reservas"][c]) for c in amostra["reservas"]}
    for r in sem_pagina:
        canal = r["video"].split("/", 1)[0]
        trocado = r["video"]
        while reservas.get(canal):
            proxima = reservas[canal].pop(0)
            novo = _rodar(proxima, f"reserva de {trocado}")
            registros.append(novo)
            _gravar_log(registros)
            print(f"reserva: {proxima[:40]} paginas {novo['paginas']}", flush=True)
            if novo["paginas_com_pauta"] > 0:
                break
    print(
        f"fim: {len(registros)} registros; sem página com pauta: "
        f"{sum(1 for r in registros if r['paginas_com_pauta'] == 0)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
