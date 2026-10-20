"""Rodada 1034 (desenvolvimento): conferência da numeração pelas marcações do braço.

Pré-registro: ``docs/rodadas/1034-conferencia-pelas-marcacoes.md``.

As marcações do violão de aço (casas 3, 5, 7, 9, 12, 15 e 17) são uma âncora absoluta: o salto
de 3 entre a 9 e a 12 fixa a numeração. Na faixa do braço, as cordas e os trastes saem por
aberturas morfológicas (uma linha horizontal e uma vertical), e o que sobra de claro no meio
de cada espaço entre trastes é a marcação. O deslocamento k que leva os espaços marcados ao
padrão, sem nenhum erro, diz se a numeração do detector está deslocada.

CLI: ``python -m tab.maos_braco_marcacoes medir`` (CPU).
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys

import cv2
import numpy as np

from .caminhos import MAOS_M26, MAOS_M27, MAOS_M29, MAOS_M31, MAOS_M32
from .maos_braco_detector import _imagem, _ler_json
from .maos_braco_faixa import recortar
from .maos_braco_juncao import faixa_do_quadro
from .maos_gabarito import gravar_atomico

#: Casas com marcação no padrão do violão de aço.
PADRAO = frozenset({3, 5, 7, 9, 12, 15, 17})
#: Deslocamentos testados.
DESLOCAMENTOS = (-2, -1, 0, 1, 2)
#: Mínimo de marcações para decidir.
MIN_MARCAS = 3
#: Linhas da faixa dentro da escala (entre corda1 e corda6, com folga).
LINHAS_ESCALA = (70, 122)
#: Comprimento das linhas das aberturas que tiram cordas (horizontal) e trastes (vertical).
COMPRIMENTO_ABERTURA = 25
#: Fração central de cada espaço entre trastes usada na pontuação.
CENTRO_ESPACO = 0.60
#: Um espaço é marcado com pontuação ≥ RAZAO_MEDIANA x mediana e ≥ MINIMO_ABSOLUTO.
RAZAO_MEDIANA = 4.0
MINIMO_ABSOLUTO = 20.0
#: Limite de disparos nos certos para propor a regra (pré-registro).
LIMITE_CERTOS = 0.03
CICLOS = (("1026", MAOS_M26), ("1027", MAOS_M27), ("1029", MAOS_M29))
LOTE_SEM_ROTULO = ("1032", MAOS_M32)
ARQUIVO_MEDIDA = MAOS_M31 / "medida_1034.json"


def residuo_claro(faixa: np.ndarray) -> np.ndarray:
    """O que sobra de claro na faixa depois de tirar as cordas e os trastes.

    Args:
        faixa: faixa BGR de 192 x 1024.

    Returns:
        Resíduo float32 (cinza menos o maior das duas aberturas), ≥ 0.
    """
    cinza = cv2.cvtColor(faixa, cv2.COLOR_BGR2GRAY)
    horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (COMPRIMENTO_ABERTURA, 1))
    vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, COMPRIMENTO_ABERTURA))
    cordas = cv2.morphologyEx(cinza, cv2.MORPH_OPEN, horizontal)
    trastes = cv2.morphologyEx(cinza, cv2.MORPH_OPEN, vertical)
    fundo = np.maximum(cordas, trastes).astype(np.float32)
    return np.clip(cinza.astype(np.float32) - fundo, 0.0, None)


def espacos_marcados(
    residuo: np.ndarray, xs: list[float], numeros: list[int]
) -> list[int]:
    """Números das casas (espaço entre os trastes n-1 e n) que têm marcação.

    Args:
        residuo: saída de ``residuo_claro``.
        xs: x de cada traste previsto na faixa.
        numeros: número do detector de cada traste.

    Returns:
        As casas marcadas, em ordem.
    """
    pares = sorted(zip(numeros, xs, strict=True))
    pontuacoes: dict[int, float] = {}
    inicio, fim = LINHAS_ESCALA
    for (n_a, x_a), (n_b, x_b) in itertools.pairwise(pares):
        if n_b != n_a + 1:
            continue
        esquerda, direita = sorted((x_a, x_b))
        folga = (1.0 - CENTRO_ESPACO) / 2.0 * (direita - esquerda)
        c0 = max(0, int(esquerda + folga))
        c1 = min(residuo.shape[1], int(direita - folga) + 1)
        if c1 <= c0:
            continue
        pontuacoes[n_b] = float(residuo[inicio:fim, c0:c1].max())
    if not pontuacoes:
        return []
    mediana = float(np.median(list(pontuacoes.values())))
    limiar = max(MINIMO_ABSOLUTO, RAZAO_MEDIANA * mediana)
    return sorted(n for n, p in pontuacoes.items() if p >= limiar)


def deslocamento_pelas_marcas(marcadas: list[int]) -> int | None:
    """O k que leva as casas marcadas ao padrão, sem erro, ou None sem decisão.

    Args:
        marcadas: casas com marcação (numeração do detector).

    Returns:
        O k (número verdadeiro = número do detector + k), ou None.
    """
    if len(marcadas) < MIN_MARCAS:
        return None
    validos = []
    for k in DESLOCAMENTOS:
        verdadeiras = {n + k for n in marcadas}
        if not verdadeiras <= PADRAO:
            continue
        if 12 not in verdadeiras:
            continue
        validos.append((len(verdadeiras), -abs(k), k))
    if not validos:
        return None
    melhores = [v for v in validos if v[0] == max(v[0] for v in validos)]
    if len(melhores) > 1:
        return None
    return melhores[0][2]


def conferir(imagem: np.ndarray, previsto: dict) -> dict:
    """Confere a numeração de um quadro pelas marcações.

    Args:
        imagem: quadro BGR.
        previsto: previsão do quadro.

    Returns:
        ``{"marcadas", "k"}`` (k None sem decisão).
    """
    montagem = faixa_do_quadro(previsto)
    if montagem is None:
        return {"marcadas": [], "k": None}
    matriz, xs = montagem
    numeros = [int(t["numero"]) for t in previsto["trastes"]]
    marcadas = espacos_marcados(residuo_claro(recortar(imagem, matriz)), xs, numeros)
    return {"marcadas": marcadas, "k": deslocamento_pelas_marcas(marcadas)}


def _conferir_ciclo(pasta) -> dict[str, dict]:
    """Conferência de cada quadro com braço de um ciclo.

    Args:
        pasta: pasta do ciclo.

    Returns:
        ``{id: saída de conferir}``.
    """
    previstos = _ler_json(pasta / "previsto.json")["quadros"]
    saida = {}
    for item in _ler_json(pasta / "indice.json")["quadros"]:
        previsto = previstos[item["id"]]
        if previsto["achou"]:
            saida[item["id"]] = conferir(_imagem(pasta / item["png"]), previsto)
    return saida


def medir() -> dict:
    """Mede a conferência nos ciclos revisados e conta os disparos na 1032.

    Returns:
        O resultado gravado em ``medida_1034.json``.
    """
    falsos: dict[str, dict] = {}
    certos: dict[str, dict] = {}
    for rodada, pasta in CICLOS:
        conferencias = _conferir_ciclo(pasta)
        for linha in _ler_json(pasta / "medida.json")["linhas"]:
            if linha["sinalizado"] or linha["id"] not in conferencias:
                continue
            chave = f"{rodada}:{linha['id']}"
            if linha["classe"] == "falso":
                falsos[chave] = conferencias[linha["id"]]
            elif linha["classe"] == "certo":
                certos[chave] = conferencias[linha["id"]]
    lote = _conferir_ciclo(LOTE_SEM_ROTULO[1])
    disparos_certos = [c for c, v in certos.items() if v["k"] not in (None, 0)]
    resultado = {
        "rodada": 1034,
        "falsos": falsos,
        "falsos_pegos": [c for c, v in falsos.items() if v["k"] not in (None, 0)],
        "certos": len(certos),
        "certos_decididos": sum(1 for v in certos.values() if v["k"] is not None),
        "certos_disparados": disparos_certos,
        "lote_1032": {
            "quadros": len(lote),
            "decididos": sum(1 for v in lote.values() if v["k"] is not None),
            "disparos": [i for i, v in lote.items() if v["k"] not in (None, 0)],
        },
    }
    resultado["passa"] = "1027:q56" in resultado["falsos_pegos"] and (
        len(disparos_certos) <= LIMITE_CERTOS * max(1, len(certos))
    )
    gravar_atomico(ARQUIVO_MEDIDA, resultado)
    return resultado


def main() -> int:
    """Ponto de entrada: ``medir``.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="parte", required=True)
    sub.add_parser("medir", help="mede a conferência nos ciclos revisados (CPU)")
    parser.parse_args()
    print(json.dumps(medir(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
