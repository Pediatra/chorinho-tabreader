"""D1 da partitura: 1 recorte por vídeo com a semente, lido com Audiveris e homr (rodada 3161).

Para cada vídeo da lista final (``amostra_final.json``), escolhe um recorte com pauta entre os
de ``videos/<slug>/recortes/indice.json`` com ``random.Random(f"{semente}:{vídeo}")``. Não é o
"mais legível". Depois roda ``ler_pasta`` só nesse recorte. Tudo grava dentro da pasta do vídeo.

Vídeo sem nenhum recorte com pauta fica registrado como ``sem_recorte`` e não é trocado
aqui: a troca só vale para o paginar (ver a rodada 3160).

Uso (dentro do container, na raiz do projeto)::

    python -m tab.partitura_amostra_ler
"""

from __future__ import annotations

import argparse
import json
import random
import time

from .caminhos import PART_FRENTE_D
from .partitura_video import ler_pasta
from .video import _slug

SEMENTE = 0
LISTA = PART_FRENTE_D / "amostra_final.json"
ESCOLHA = PART_FRENTE_D / "escolha_recortes.json"


def _escolher(pasta_video, video: str) -> str | None:
    """Recorte com pauta escolhido pela semente para um vídeo.

    Args:
        pasta_video: pasta ``videos/<slug>`` do vídeo.
        video: ``canal/arquivo`` do vídeo (entra na semente).

    Returns:
        O ``id`` do recorte, ou None se o vídeo não tem recorte com pauta.
    """
    indice = json.loads(
        (pasta_video / "recortes" / "indice.json").read_text(encoding="utf-8")
    )
    com_pauta = sorted(e["id"] for e in indice if not e["sem_pauta"])
    if not com_pauta:
        return None
    return random.Random(f"{SEMENTE}:{video}").choice(com_pauta)


def main(argv: list[str] | None = None) -> int:
    """Escolhe um recorte por vídeo e roda ``ler_pasta`` só nele.

    Args:
        argv: sem argumentos.

    Returns:
        Zero.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    lista = json.loads(LISTA.read_text(encoding="utf-8"))["escolhidos_final"]
    videos = [v for canal in sorted(lista) for v in lista[canal]]
    registros: list[dict] = []
    for ordem, video in enumerate(videos, start=1):
        pasta = PART_FRENTE_D / "videos" / _slug(video)
        escolhido = _escolher(pasta, video)
        registro: dict = {"ordem": ordem, "video": video, "recorte": escolhido}
        if escolhido is None:
            registro["estado"] = "sem_recorte"
            registros.append(registro)
            print(f"{ordem}/{len(videos)} sem recorte: {video[:40]}", flush=True)
        else:
            inicio = time.time()
            try:
                ler_pasta(pasta, ids=[escolhido])
                registro["estado"] = "lido"
            except Exception as falha:
                registro["estado"] = f"erro: {type(falha).__name__}: {falha}"
            registro["segundos"] = round(time.time() - inicio, 1)
            registros.append(registro)
            print(
                f"{ordem}/{len(videos)} {escolhido} {registro['estado'][:60]}",
                flush=True,
            )
        ESCOLHA.write_text(
            json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    lidos = sum(1 for r in registros if r.get("estado") == "lido")
    print(f"fim: {lidos} lidos de {len(videos)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
