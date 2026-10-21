"""Casa do capotraste por vídeo, tirada das observações do dono nos gabaritos do braço.

Decisão 1010: com capo, o nut do braço é o capo, e a casa do capo vai na observação do
quadro ("capotraste casa N"). Este módulo junta essas casas por vídeo, sem interpretar além
do número escrito. Serve de verdade para quem estima a casa do capo de outro jeito (por
exemplo, a trilha áudio, pela altura que soa contra a casa da tablatura).

CLI: ``python -m tab.maos_braco_capo`` grava ``data/saida/maos/capo_por_video.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from .caminhos import (
    GABARITO_BRACO,
    GABARITO_BRACO_M11B,
    GABARITO_BRACO_M25_PROVA,
    GABARITO_BRACO_M25_TREINO,
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    GABARITO_BRACO_M29,
    GABARITO_BRACO_M32,
    GABARITO_BRACO_M36,
    MAOS_M3B,
    MAOS_M11B,
    MAOS_M25,
    MAOS_M26,
    MAOS_M27,
    MAOS_M29,
    MAOS_M32,
    MAOS_M36,
    SAIDA,
)
from .maos_gabarito import gravar_atomico

#: Gabaritos do braço e a pasta do ``indice.json`` de cada um (nome curto, ouro, pasta).
GABARITOS = (
    ("m3b", GABARITO_BRACO, MAOS_M3B),
    ("m11b", GABARITO_BRACO_M11B, MAOS_M11B),
    ("m25_treino", GABARITO_BRACO_M25_TREINO, MAOS_M25 / "treino"),
    ("m25_prova", GABARITO_BRACO_M25_PROVA, MAOS_M25 / "prova"),
    ("m26", GABARITO_BRACO_M26, MAOS_M26),
    ("m27", GABARITO_BRACO_M27, MAOS_M27),
    ("m29", GABARITO_BRACO_M29, MAOS_M29),
    ("m32", GABARITO_BRACO_M32, MAOS_M32),
    ("m36", GABARITO_BRACO_M36, MAOS_M36),
)
ARQUIVO_SAIDA = SAIDA / "maos" / "capo_por_video.json"

#: "capotraste casa 3", "capotraste na casa 2", "capostraste casa 1", "capotraste 6 casa",
#: "capotraste 2 casa". O número que vem depois de "capo..." (com "na"/"casa" opcionais),
#: ou o que vem antes de "casa".
PADRAO_CASA = re.compile(
    r"capo\w*\s*(?:na\s+)?(?:casa\s+)?(\d+)|(\d+)\s*ª?\s*casa", re.IGNORECASE
)


def casa_da_observacao(obs: str | None) -> int | None:
    """A casa do capo escrita na observação (o último número que casa com o padrão).

    Args:
        obs: observação do quadro.

    Returns:
        A casa, ou None se a observação não diz.
    """
    achados = [a or b for a, b in PADRAO_CASA.findall(obs or "")]
    return int(achados[-1]) if achados else None


def juntar(registros: list[tuple[str, str, dict]]) -> list[dict]:
    """Agrupa por vídeo os quadros com capo marcado (tecla ``k``) e a casa escrita.

    Args:
        registros: ``(chave do quadro, arquivo do vídeo, registro do gabarito)``.

    Returns:
        Um item por vídeo, em ordem de arquivo: ``arquivo``, ``casa`` (a única casa
        escrita, ou None se não há casa ou há mais de uma), ``casas`` (casa -> chaves,
        com ``"?"`` para quadro sem casa escrita) e ``conflito``.
    """
    por_video: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for chave, arquivo, registro in registros:
        if not registro.get("capo"):
            continue
        casa = casa_da_observacao(registro.get("obs"))
        por_video[arquivo]["?" if casa is None else str(casa)].append(chave)
    saida = []
    for arquivo in sorted(por_video):
        casas = {c: sorted(ids) for c, ids in sorted(por_video[arquivo].items())}
        numeros = [c for c in casas if c != "?"]
        saida.append(
            {
                "arquivo": arquivo,
                "casa": int(numeros[0]) if len(numeros) == 1 else None,
                "casas": casas,
                "conflito": len(numeros) > 1,
            }
        )
    return saida


def sem_capo(registros: list[tuple[str, str, dict]]) -> list[str]:
    """Vídeos com braço visto pelo dono em algum quadro e nenhum quadro com capo marcado.

    É o controle negativo: a casa do capo esperada é 0 (nos quadros vistos).

    Args:
        registros: ``(chave do quadro, arquivo do vídeo, registro do gabarito)``.

    Returns:
        Os arquivos, em ordem.
    """
    com_braco: set[str] = set()
    com_capo: set[str] = set()
    for _chave, arquivo, registro in registros:
        if registro.get("capo"):
            com_capo.add(arquivo)
        if registro.get("braco") != "nao" and registro.get("corda1"):
            com_braco.add(arquivo)
    return sorted(com_braco - com_capo)


def _registros() -> list[tuple[str, str, dict]]:
    """Os quadros de todos os gabaritos do braço, com o arquivo do vídeo de cada um.

    Returns:
        ``(nome:id, arquivo, registro)`` por quadro.
    """
    saida = []
    for nome, ouro, pasta in GABARITOS:
        quadros = json.loads(Path(ouro).read_text(encoding="utf-8"))["quadros"]
        indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
        arquivo = {item["id"]: item["arquivo"] for item in indice["quadros"]}
        for id_q, registro in quadros.items():
            saida.append((f"{nome}:{id_q}", arquivo[id_q], registro))
    return saida


def main() -> int:
    """Ponto de entrada: grava ``capo_por_video.json`` e imprime o resumo.

    Returns:
        0 ao terminar.
    """
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    registros = _registros()
    videos = juntar(registros)
    controle = sem_capo(registros)
    gravar_atomico(
        ARQUIVO_SAIDA,
        {
            "fonte": "observações do dono nos gabaritos do braço (decisão 1010)",
            "videos": videos,
            "sem_capo": controle,
        },
    )
    for video in videos:
        print(f"{video['casa']!s:>4} {video['casas']} {video['arquivo'][:70]}")
    conflitos = sum(1 for v in videos if v["conflito"])
    print(f"{len(videos)} vídeos com capo; {conflitos} com casas diferentes")
    print(f"{len(controle)} vídeos sem capo nos quadros vistos (controle)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
