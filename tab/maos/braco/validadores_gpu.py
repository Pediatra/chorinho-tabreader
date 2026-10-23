"""Rodada 1044, parte GPU: as 22 hipóteses (11 pares × original/espelho) por quadro.

O espelho é o quadro virado na horizontal: a cadeia roda nele e a previsão volta pelo mesmo
espelho (x → largura − 1 − x). Se a corda 1 voltar do lado da corda 6 da hipótese de
referência, as duas são trocadas, para a numeração das cordas seguir a da referência.

CLI: ``python -m tab.maos.braco.validadores_gpu hipoteses --rodada N`` grava um
``previsto.json`` por hipótese em ``data/saida/maos/m44/hipoteses/<N>/``.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from tab.comum.arquivos import gravar_atomico
from tab.maos.braco.ciclo import RODADAS, aplicar_sinal_nut_v2, prever_quadros
from tab.maos.braco.validadores import (
    MODOS,
    PARES,
    PASTA_HIPOTESES,
    REFERENCIA,
    nome_da_hipotese,
)


def espelhar_pasta(pasta: Path, indice: dict, destino: Path) -> dict:
    """Grava os quadros espelhados e devolve o índice que aponta para eles.

    Args:
        pasta: pasta da rodada (``pasta / item["png"]``).
        indice: ``indice.json`` da rodada.
        destino: pasta dos quadros espelhados.

    Returns:
        Uma cópia do índice com ``png`` relativo a ``destino``.
    """
    novo = copy.deepcopy(indice)
    (destino / "quadros").mkdir(parents=True, exist_ok=True)
    for item in novo["quadros"]:
        imagem = cv2.imread(str(pasta / item["png"]))
        relativo = f"quadros/{item['id']}.png"
        cv2.imwrite(str(destino / relativo), cv2.flip(imagem, 1))
        item["png"] = relativo
    return novo


def _virar(ponto: list[float], largura: int) -> list[float]:
    """Um ponto pelo espelho horizontal.

    Args:
        ponto: ``[x, y]``.
        largura: largura do quadro.

    Returns:
        ``[largura - 1 - x, y]``.
    """
    return [float(largura - 1 - ponto[0]), float(ponto[1])]


def desespelhar(previsto: dict, largura: int) -> dict:
    """Leva uma previsão feita no quadro espelhado de volta ao quadro original.

    Args:
        previsto: entrada de ``previsto.json``.
        largura: largura do quadro.

    Returns:
        Uma cópia com ``nut``, cordas e trastes no quadro original.
    """
    novo = copy.deepcopy(previsto)
    if not novo.get("achou"):
        return novo
    novo["nut"] = _virar(novo["nut"], largura)
    for nome in ("corda1", "corda6"):
        novo[nome] = [_virar(p, largura) for p in novo[nome]]
    for traste in novo.get("trastes") or []:
        traste["ponto"] = _virar(traste["ponto"], largura)
    return novo


def alinhar_cordas(previsto: dict, referencia: dict) -> dict:
    """Troca as cordas 1 e 6 se a corda 1 está do lado da corda 6 da referência.

    Args:
        previsto: entrada de ``previsto.json`` (já no quadro original).
        referencia: a mesma entrada da hipótese de referência.

    Returns:
        A previsão, com as cordas trocadas se preciso.
    """
    if not (previsto.get("achou") and referencia.get("achou")):
        return previsto
    meio1 = np.mean(np.asarray(previsto["corda1"], dtype=float), axis=0)
    ref1 = np.mean(np.asarray(referencia["corda1"], dtype=float), axis=0)
    ref6 = np.mean(np.asarray(referencia["corda6"], dtype=float), axis=0)
    if np.linalg.norm(meio1 - ref6) < np.linalg.norm(meio1 - ref1):
        previsto = dict(previsto, corda1=previsto["corda6"], corda6=previsto["corda1"])
    return previsto


def hipoteses(numero: str) -> None:
    """Roda as 22 hipóteses numa rodada e grava cada uma.

    Args:
        numero: rodada do ciclo.
    """
    rodada = RODADAS[numero]
    indice = json.loads((rodada.pasta / "indice.json").read_text(encoding="utf-8"))
    saida = PASTA_HIPOTESES / numero
    espelho = saida / "espelho"
    indice_espelho = espelhar_pasta(rodada.pasta, indice, espelho)
    larguras = {item["id"]: item["largura"] for item in indice["quadros"]}
    ordem = [item["id"] for item in indice["quadros"]]
    entradas = {
        "original": (rodada.pasta, indice),
        "espelho": (espelho, indice_espelho),
    }
    docs = {}
    for modo in MODOS:
        pasta, indice_modo = entradas[modo]
        for par in PARES:
            previstos = prever_quadros(pasta, indice_modo, *par)
            aplicar_sinal_nut_v2(previstos, pasta, indice_modo)
            if modo == "espelho":
                previstos = {
                    id_q: desespelhar(p, larguras[id_q])
                    for id_q, p in previstos.items()
                }
            docs[nome_da_hipotese(par, modo)] = previstos
    referencia = docs[nome_da_hipotese(*REFERENCIA)]
    for nome, previstos in docs.items():
        alinhados = {
            id_q: alinhar_cordas(previstos[id_q], referencia[id_q]) for id_q in ordem
        }
        gravar_atomico(saida / f"{nome}.json", {"ordem": ordem, "quadros": alinhados})


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p_hip = sub.add_parser("hipoteses", help="as 22 hipóteses (GPU)")
    p_hip.add_argument("--rodada", required=True)
    args = parser.parse_args()
    hipoteses(args.rodada)
    return 0


if __name__ == "__main__":
    sys.exit(main())
