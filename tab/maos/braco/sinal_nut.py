"""Rodada 1033 (desenvolvimento): sinal de nut suspeito v2, com a borda do painel.

Pré-registro: ``docs/rodadas/1033-sinal-de-nut-suspeito-v2.md``.

O v1 (regra de borda da 1030) olha só as 4 bordas do quadro. Em vídeos com a tela dividida, o
braço sai pela borda do painel, uma linha reta que atravessa o quadro. O v2 junta essas linhas
às bordas e testa os limiares de 2 a 5 % da borda menor.

CLI: ``python -m tab.maos_braco_sinal_nut medir`` (CPU).
"""

from __future__ import annotations

import argparse
import json
import sys

import cv2
import numpy as np

from tab.comum.caminhos import MAOS_M26, MAOS_M27, MAOS_M29, MAOS_M31, MAOS_M32
from tab.maos.braco.detector import _imagem, _ler_json
from tab.maos.gabarito import gravar_atomico

#: Diferença mínima de intensidade (cinza suavizado) entre pixels vizinhos.
GRADIENTE_FORTE = 25
#: Fração mínima da largura (ou da altura) com gradiente forte para ser linha de painel.
FRACAO_LINHA = 0.80
#: Linhas a até esta fração da borda do quadro já são borda e ficam de fora.
FRACAO_PERTO_DA_BORDA = 0.02
#: Limiares testados (fração da borda menor) e o mínimo de falsos pegos.
LIMIARES = (0.02, 0.03, 0.04, 0.05)
MIN_PEGOS = 5
#: Limite de certos mandados para revisão a mais (fração dos certos não sinalizados).
LIMITE_CERTOS_A_MAIS = 0.10
#: Ciclos revisados usados na medida e o lote sem rótulo.
CICLOS = (("1026", MAOS_M26), ("1027", MAOS_M27), ("1029", MAOS_M29))
LOTE_SEM_ROTULO = ("1032", MAOS_M32)
ARQUIVO_MEDIDA = MAOS_M31 / "medida_1033.json"
#: Arquivos de um ciclo (os mesmos nomes do ``tab.maos_braco_ciclo``, que importa daqui).
ARQUIVO_INDICE = "indice.json"
ARQUIVO_PREVISTO = "previsto.json"
#: Limiar escolhido na medida da 1033 (``medida_1033.json``): 2 % da borda menor.
FRACAO_V2 = 0.02


def linhas_de_painel(imagem: np.ndarray) -> tuple[list[int], list[int]]:
    """Linhas horizontais (y) e verticais (x) que atravessam o quadro: bordas de painel.

    Args:
        imagem: quadro BGR.

    Returns:
        ``(ys, xs)``: as linhas com gradiente forte em ≥ 80 % da largura (ou da altura),
        fora dos 2 % junto à borda do quadro.
    """
    cinza = cv2.GaussianBlur(cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    cinza = cinza.astype(np.int16)
    altura, largura = cinza.shape
    dy = np.abs(np.diff(cinza, axis=0)) >= GRADIENTE_FORTE
    dx = np.abs(np.diff(cinza, axis=1)) >= GRADIENTE_FORTE
    margem_y = FRACAO_PERTO_DA_BORDA * altura
    margem_x = FRACAO_PERTO_DA_BORDA * largura
    ys = [
        int(y)
        for y in np.flatnonzero(dy.mean(axis=1) >= FRACAO_LINHA)
        if margem_y < y < altura - margem_y
    ]
    xs = [
        int(x)
        for x in np.flatnonzero(dx.mean(axis=0) >= FRACAO_LINHA)
        if margem_x < x < largura - margem_x
    ]
    return ys, xs


def distancia_da_ponta(
    previsto: dict, dimensoes: tuple[int, int], paineis: tuple[list[int], list[int]]
) -> float | None:
    """Menor distância da ponta das cordas (lado do nut) a uma borda ou linha de painel.

    Args:
        previsto: previsão do quadro (``nut``, ``corda1``, ``corda6``).
        dimensoes: ``(largura, altura)``.
        paineis: ``(ys, xs)`` de ``linhas_de_painel``.

    Returns:
        A distância em px, ou None sem nut (sem nut já é suspeito).
    """
    nut = previsto.get("nut")
    if nut is None:
        return None
    largura, altura = dimensoes
    ys, xs = paineis
    alvo = np.asarray(nut, dtype=float)
    menor = float("inf")
    for corda in (previsto["corda1"], previsto["corda6"]):
        pontas = np.asarray(corda, dtype=float)
        x, y = pontas[int(np.argmin(np.linalg.norm(pontas - alvo, axis=1)))]
        candidatos = [x, y, largura - x, altura - y]
        candidatos += [abs(y - yl) for yl in ys] + [abs(x - xl) for xl in xs]
        menor = min(menor, min(candidatos))
    return float(menor)


def suspeito(
    distancia: float | None, dimensoes: tuple[int, int], fracao: float
) -> bool:
    """Nut suspeito pelo v2 com o limiar ``fracao``.

    Args:
        distancia: saída de ``distancia_da_ponta`` (None quando não há nut).
        dimensoes: ``(largura, altura)``.
        fracao: limiar, em fração da borda menor.

    Returns:
        True sem nut, ou com a ponta a até ``fracao`` da borda menor de uma borda.
    """
    return distancia is None or distancia <= fracao * min(dimensoes)


def _quadros(pasta) -> list[tuple[str, dict, tuple[int, int], float | None]]:
    """Os quadros com braço de um ciclo: id, previsão, dimensões e distância v2.

    Args:
        pasta: pasta do ciclo (``indice.json``, ``previsto.json``, ``quadros/``).

    Returns:
        Uma tupla por quadro com braço achado.
    """
    previstos = _ler_json(pasta / ARQUIVO_PREVISTO)["quadros"]
    saida = []
    for item in _ler_json(pasta / ARQUIVO_INDICE)["quadros"]:
        previsto = previstos[item["id"]]
        if not previsto["achou"]:
            continue
        dimensoes = (int(item["largura"]), int(item["altura"]))
        paineis = linhas_de_painel(_imagem(pasta / item["png"]))
        saida.append(
            (
                item["id"],
                previsto,
                dimensoes,
                distancia_da_ponta(previsto, dimensoes, paineis),
            )
        )
    return saida


def medir() -> dict:
    """Mede o v2 nos ciclos revisados e conta os disparos no lote da 1032.

    Returns:
        O resultado gravado em ``medida_1033.json``, com o limiar escolhido.
    """
    falsos: list[tuple] = []
    certos: list[tuple] = []
    for rodada, pasta in CICLOS:
        linhas = {
            linha["id"]: linha for linha in _ler_json(pasta / "medida.json")["linhas"]
        }
        for id_q, _previsto, dimensoes, distancia in _quadros(pasta):
            linha = linhas.get(id_q)
            if linha is None or linha["sinalizado"]:
                continue
            chave = f"{rodada}:{id_q}"
            if linha["classe"] == "falso":
                falsos.append((chave, dimensoes, distancia))
            elif linha["classe"] == "certo":
                certos.append((chave, dimensoes, distancia))
    lote = [
        (f"{LOTE_SEM_ROTULO[0]}:{id_q}", dimensoes, distancia)
        for id_q, previsto, dimensoes, distancia in _quadros(LOTE_SEM_ROTULO[1])
        if not previsto["sinalizado"]
    ]
    tabela = []
    for fracao in LIMIARES:
        pegos = [c for c, d, dist in falsos if suspeito(dist, d, fracao)]
        a_mais = [c for c, d, dist in certos if suspeito(dist, d, fracao)]
        no_lote = [c for c, d, dist in lote if suspeito(dist, d, fracao)]
        tabela.append(
            {
                "fracao": fracao,
                "falsos_pegos": pegos,
                "certos_a_mais": a_mais,
                "certos_a_mais_fracao": len(a_mais) / len(certos) if certos else None,
                "disparos_1032": no_lote,
            }
        )
    bons = [t for t in tabela if len(t["falsos_pegos"]) >= MIN_PEGOS]
    if bons:
        escolhido = bons[0]
    else:
        escolhido = max(tabela, key=lambda t: (len(t["falsos_pegos"]), -t["fracao"]))
    passa = (
        len(escolhido["falsos_pegos"]) >= MIN_PEGOS
        and escolhido["certos_a_mais_fracao"] is not None
        and escolhido["certos_a_mais_fracao"] <= LIMITE_CERTOS_A_MAIS
    )
    resultado = {
        "rodada": 1033,
        "falsos": [c for c, *_ in falsos],
        "certos_nao_sinalizados": len(certos),
        "quadros_1032": len(lote),
        "tabela": tabela,
        "escolhido": escolhido["fracao"],
        "passa": passa,
    }
    gravar_atomico(ARQUIVO_MEDIDA, resultado)
    return resultado


def main() -> int:
    """Ponto de entrada: ``medir``.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="parte", required=True)
    sub.add_parser("medir", help="mede o v2 nos ciclos revisados (CPU)")
    parser.parse_args()
    resultado = medir()
    resumo = {
        "falsos": resultado["falsos"],
        "certos_nao_sinalizados": resultado["certos_nao_sinalizados"],
        "escolhido": resultado["escolhido"],
        "passa": resultado["passa"],
        "tabela": [
            {
                "fracao": t["fracao"],
                "pegos": t["falsos_pegos"],
                "certos_a_mais": len(t["certos_a_mais"]),
                "disparos_1032": len(t["disparos_1032"]),
            }
            for t in resultado["tabela"]
        ],
    }
    print(json.dumps(resumo, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
