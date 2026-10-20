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

from .caminhos import MAOS_M26, MAOS_M27, MAOS_M29, MAOS_M30, MAOS_M31, MAOS_M32
from .maos_braco_detector import _imagem, _ler_json
from .maos_braco_faixa import recortar
from .maos_braco_juncao import faixa_do_quadro
from .maos_braco_vizinhos import nut_confiante
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

#: 1035: mancha compacta (altura máxima em px e largura máxima em fração do espaço).
ALTURA_MANCHA = 18
LARGURA_MANCHA = 0.60
#: 1035: fatores do limiar pelo quartil inferior, escolhidos sem rótulo.
FATORES_Q25 = (2.0, 3.0, 4.0)
#: 1035: disparos máximos (fração das decisões) no desenvolvimento sem rótulo.
LIMITE_DISPAROS_DEV = 0.02
#: 1035: vídeos de desenvolvimento (aço, guitarous, 1030 sem o v15, que tem casos).
VIDEOS_DEV_1035 = (9, 10, 11, 12, 13, 14, 16)
ARQUIVO_MEDIDA_1035 = MAOS_M31 / "medida_1035.json"


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


def pontuacoes_compactas(
    residuo: np.ndarray, xs: list[float], numeros: list[int]
) -> dict[int, float]:
    """Pontuação de cada casa cuja mancha clara é compacta (1035).

    Args:
        residuo: saída de ``residuo_claro``.
        xs: x de cada traste previsto na faixa.
        numeros: número do detector de cada traste.

    Returns:
        ``{casa: máximo do resíduo}`` só para as casas com mancha compacta.
    """
    pares = sorted(zip(numeros, xs, strict=True))
    inicio, fim = LINHAS_ESCALA
    saida: dict[int, float] = {}
    for (n_a, x_a), (n_b, x_b) in itertools.pairwise(pares):
        if n_b != n_a + 1:
            continue
        esquerda, direita = sorted((x_a, x_b))
        folga = (1.0 - CENTRO_ESPACO) / 2.0 * (direita - esquerda)
        c0 = max(0, int(esquerda + folga))
        c1 = min(residuo.shape[1], int(direita - folga) + 1)
        if c1 <= c0:
            continue
        janela = residuo[inicio:fim, c0:c1]
        maximo = float(janela.max())
        if maximo <= 0.0:
            continue
        mascara = (janela >= maximo / 2.0).astype(np.uint8)
        _, rotulos, estat, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)
        y, x = np.unravel_index(int(np.argmax(janela)), janela.shape)
        componente = rotulos[y, x]
        altura = int(estat[componente, cv2.CC_STAT_HEIGHT])
        largura = int(estat[componente, cv2.CC_STAT_WIDTH])
        if altura <= ALTURA_MANCHA and largura <= LARGURA_MANCHA * (direita - esquerda):
            saida[n_b] = maximo
    return saida


def marcadas_1035(pontuacoes: dict[int, float], fator: float) -> list[int]:
    """Casas marcadas pelo limiar max(20, fator x Q25) das pontuações compactas.

    Args:
        pontuacoes: saída de ``pontuacoes_compactas``.
        fator: F do pré-registro.

    Returns:
        As casas marcadas, em ordem.
    """
    if not pontuacoes:
        return []
    q25 = float(np.percentile(list(pontuacoes.values()), 25))
    limiar = max(MINIMO_ABSOLUTO, fator * q25)
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


def _pontuacoes_do_quadro(imagem: np.ndarray, previsto: dict) -> dict[int, float]:
    """Pontuações compactas de um quadro (vazio sem faixa).

    Args:
        imagem: quadro BGR.
        previsto: previsão do quadro.

    Returns:
        Saída de ``pontuacoes_compactas``.
    """
    montagem = faixa_do_quadro(previsto)
    if montagem is None:
        return {}
    matriz, xs = montagem
    numeros = [int(t["numero"]) for t in previsto["trastes"]]
    return pontuacoes_compactas(residuo_claro(recortar(imagem, matriz)), xs, numeros)


def _contar_k(pontuacoes: list[dict[int, float]], fator: float) -> dict:
    """Decisões e disparos de um fator sobre uma lista de quadros.

    Args:
        pontuacoes: pontuações compactas por quadro.
        fator: F.

    Returns:
        ``{"decisoes", "k0", "disparos"}``.
    """
    ks = [deslocamento_pelas_marcas(marcadas_1035(p, fator)) for p in pontuacoes]
    decididos = [k for k in ks if k is not None]
    return {
        "decisoes": len(decididos),
        "k0": sum(1 for k in decididos if k == 0),
        "disparos": sum(1 for k in decididos if k != 0),
    }


def medir_1035() -> dict:
    """1035: escolhe F nos quadros densos sem rótulo e testa nos ciclos revisados.

    Returns:
        O resultado gravado em ``medida_1035.json``.
    """
    dev: list[dict[int, float]] = []
    for numero in VIDEOS_DEV_1035:
        nome = f"v{numero:02d}"
        dimensoes = _ler_json(MAOS_M31 / f"dimensoes_{nome}.json")
        caminho = MAOS_M30 / f"video_{numero:02d}.jsonl"
        with caminho.open(encoding="utf-8") as entrada:
            registros = [json.loads(linha) for linha in entrada if linha.strip()]
        for registro in registros:
            registro["dimensoes"] = dimensoes.get(registro["id"])
            if not nut_confiante(registro):
                continue
            imagem = cv2.imread(
                str(MAOS_M31 / "denso" / nome / f"{registro['id']}.jpg")
            )
            if imagem is not None:
                dev.append(_pontuacoes_do_quadro(imagem, registro["previsto"]))
    tabela = []
    for fator in FATORES_Q25:
        conta = _contar_k(dev, fator)
        conta["fator"] = fator
        conta["disparos_fracao"] = (
            conta["disparos"] / conta["decisoes"] if conta["decisoes"] else None
        )
        tabela.append(conta)
    aceitos = [
        t
        for t in tabela
        if t["decisoes"] and t["disparos_fracao"] <= LIMITE_DISPAROS_DEV
    ]
    resultado: dict = {"rodada": 1035, "quadros_dev": len(dev), "dev": tabela}
    if not aceitos:
        resultado["escolhido"] = None
        resultado["passa"] = False
        gravar_atomico(ARQUIVO_MEDIDA_1035, resultado)
        return resultado
    fator = max(aceitos, key=lambda t: (t["k0"], -t["fator"]))["fator"]
    resultado["escolhido"] = fator
    falsos: dict[str, int | None] = {}
    certos: dict[str, int | None] = {}
    for rodada, pasta in CICLOS:
        previstos = _ler_json(pasta / "previsto.json")["quadros"]
        itens = {
            item["id"]: item for item in _ler_json(pasta / "indice.json")["quadros"]
        }
        for linha in _ler_json(pasta / "medida.json")["linhas"]:
            previsto = previstos.get(linha["id"])
            if linha["sinalizado"] or not previsto or not previsto["achou"]:
                continue
            imagem = _imagem(pasta / itens[linha["id"]]["png"])
            k = deslocamento_pelas_marcas(
                marcadas_1035(_pontuacoes_do_quadro(imagem, previsto), fator)
            )
            chave = f"{rodada}:{linha['id']}"
            if linha["classe"] == "falso":
                falsos[chave] = k
            elif linha["classe"] == "certo":
                certos[chave] = k
    disparos = [c for c, k in certos.items() if k not in (None, 0)]
    resultado.update(
        {
            "falsos": falsos,
            "certos": len(certos),
            "certos_decididos": sum(1 for k in certos.values() if k is not None),
            "certos_disparados": disparos,
            "passa": falsos.get("1027:q56") not in (None, 0)
            and len(disparos) <= LIMITE_CERTOS * max(1, len(certos)),
        }
    )
    gravar_atomico(ARQUIVO_MEDIDA_1035, resultado)
    return resultado


def main() -> int:
    """Ponto de entrada: ``medir``.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="parte", required=True)
    sub.add_parser("medir", help="mede a conferência nos ciclos revisados (CPU)")
    sub.add_parser("medir-1035", help="1035: F sem rótulo e teste nos ciclos (CPU)")
    args = parser.parse_args()
    resultado = medir() if args.parte == "medir" else medir_1035()
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
