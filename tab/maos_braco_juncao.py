"""Rodada 1031, método J: numeração com o nut fora pela junção do braço com o corpo.

Pré-registro: ``docs/rodadas/1031-nut-fora-por-vizinhos-e-juncao.md``. A ideia é do dono:
a casa 12 fica na divisão do braço com o corpo no violão de nylon, e a 14 no de aço.

A junção é achada por uma regra sobre a imagem, sem treino. O quadro é retificado na faixa
do braço (``tab.maos_braco_faixa``), e de cada lado da escala lê-se uma banda por fora das
cordas, onde fica o que está ao lado do braço: a roupa, a mão ou o fundo antes do corpo, e
o tampo ou a ilharga depois. A cor média de cada coluna das duas bandas dá um sinal ao
longo do braço, e a junção é o ponto de mudança desse sinal: o corte em dois segmentos com
a menor soma de quadrados. O contraste do corte (distância entre as médias dos dois lados,
em desvios dentro dos segmentos) diz se a junção foi achada.

O número da junção é aprendido no próprio vídeo, nos quadros com o nut visível com
confiança (a regra do método V): o traste mais perto da junção recebe o número do detector.
A moda vale se for 12 ou 14 e se ao menos 70 % dos quadros concordarem. Um vídeo que nunca
mostra o nut usa a contagem de trastes (≤ 18 dá 12; ≥ 21 dá 14; 19 ou 20 não decide).
"""

from __future__ import annotations

import collections
from collections.abc import Callable

import cv2
import numpy as np

from .maos_braco_faixa import aplicar_matriz, matriz_da_faixa, recortar
from .maos_braco_vizinhos import nut_confiante

#: Bandas por fora da escala, em linhas da faixa de 192 px (eixo em y = 96, uma largura
#: entre corda1 e corda6 vale 64 px): de 0,6 a 0,9 largura do eixo, de cada lado, logo por
#: fora da escala (mais longe, a curva do bojo põe a mudança 1 traste depois).
BANDA_CIMA = (38, 58)
BANDA_BAIXO = (134, 154)
#: Suavização do sinal ao longo do braço (colunas).
JANELA_SUAVE = 9
#: Menor segmento aceito de cada lado do corte (colunas da faixa).
SEGMENTO_MINIMO = 24
#: Primeiro traste (número do detector) da janela de busca: antes dele, mão e capo dominam.
TRASTE_INICIO_BUSCA = 5
#: Contraste mínimo do corte para a junção contar como achada.
CONTRASTE_MINIMO = 3.0
#: Números de junção aceitos (nylon e aço) e concordância mínima no vídeo.
NUMEROS_JUNCAO = (12, 14)
CONCORDANCIA_MINIMA = 0.70
#: Contagem de trastes sem nut: até este número, junção 12; a partir do outro, 14.
CONTAGEM_NYLON = 18
CONTAGEM_ACO = 21


def faixa_do_quadro(previsto: dict) -> tuple[np.ndarray, list[float]] | None:
    """Afim da faixa do braço e a posição x de cada traste na faixa.

    A origem é o meio das pontas de corda1 e corda6 do lado do nut previsto (ou a
    primeira ponta, sem nut); a largura é a maior distância entre as cordas nas pontas.

    Args:
        previsto: previsão de um quadro (``corda1``, ``corda6``, ``nut``, ``trastes``).

    Returns:
        ``(matriz, xs)`` com ``xs`` na ordem de ``trastes``, ou None sem braço.
    """
    if not previsto.get("achou") or not previsto.get("trastes"):
        return None
    c1 = np.asarray(previsto["corda1"], dtype=float)
    c6 = np.asarray(previsto["corda6"], dtype=float)
    perto = (c1[0] + c6[0]) / 2.0
    longe = (c1[1] + c6[1]) / 2.0
    if previsto.get("nut") is not None:
        nut = np.asarray(previsto["nut"], dtype=float)
        if np.linalg.norm(longe - nut) < np.linalg.norm(perto - nut):
            perto, longe = longe, perto
    comprimento = float(np.linalg.norm(longe - perto))
    largura = max(
        float(np.linalg.norm(c1[0] - c6[0])), float(np.linalg.norm(c1[1] - c6[1]))
    )
    if comprimento == 0.0 or largura == 0.0:
        return None
    u = (longe - perto) / comprimento
    matriz = matriz_da_faixa((perto, u, comprimento, largura))
    pontos = [t["ponto"] for t in previsto["trastes"]]
    xs = [float(x) for x in aplicar_matriz(matriz, pontos)[:, 0]]
    return matriz, xs


def sinal_das_bandas(faixa: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cor média (Lab) por coluna nas duas bandas por fora da escala.

    Args:
        faixa: faixa BGR de 192 x 1024.

    Returns:
        ``(sinal, valido)``: sinal ``(1024, 6)`` suavizado, e a máscara das colunas
        inteiras dentro do quadro (sem a borda preta da reamostragem).
    """
    lab = cv2.cvtColor(faixa, cv2.COLOR_BGR2LAB).astype(float)
    preto = faixa.sum(axis=2) == 0
    partes = []
    validos = []
    for inicio, fim in (BANDA_CIMA, BANDA_BAIXO):
        partes.append(lab[inicio:fim].mean(axis=0))
        validos.append(~preto[inicio:fim].any(axis=0))
    sinal = np.concatenate(partes, axis=1)
    nucleo = np.ones(JANELA_SUAVE) / JANELA_SUAVE
    suave = np.stack(
        [np.convolve(sinal[:, c], nucleo, mode="same") for c in range(sinal.shape[1])],
        axis=1,
    )
    return suave, validos[0] & validos[1]


def ponto_de_mudanca(
    sinal: np.ndarray, inicio: int, fim: int
) -> tuple[int, float] | None:
    """Corte de ``sinal[inicio:fim]`` em dois segmentos com a menor soma de quadrados.

    Args:
        sinal: ``(n, d)``.
        inicio: primeira coluna da janela.
        fim: coluna depois da última.

    Returns:
        ``(coluna do corte, contraste)``, ou None se a janela é curta. O contraste é a
        distância entre as médias dos segmentos dividida pelo desvio dentro deles.
    """
    trecho = sinal[inicio:fim]
    n = len(trecho)
    if n < 2 * SEGMENTO_MINIMO:
        return None
    soma = np.cumsum(trecho, axis=0)
    soma2 = np.cumsum(trecho**2, axis=0)
    total, total2 = soma[-1], soma2[-1]
    melhor: tuple[float, int] | None = None
    for k in range(SEGMENTO_MINIMO, n - SEGMENTO_MINIMO + 1):
        esq, esq2 = soma[k - 1], soma2[k - 1]
        dir_, dir2 = total - esq, total2 - esq2
        custo = float((esq2 - esq**2 / k).sum() + (dir2 - dir_**2 / (n - k)).sum())
        if melhor is None or custo < melhor[0]:
            melhor = (custo, k)
    assert melhor is not None
    custo, k = melhor
    media_esq = trecho[:k].mean(axis=0)
    media_dir = trecho[k:].mean(axis=0)
    desvio = float(np.sqrt(max(custo, 0.0) / (n * trecho.shape[1]))) + 1e-6
    contraste = float(np.linalg.norm(media_dir - media_esq)) / desvio
    return inicio + k, contraste


def achar_juncao(imagem: np.ndarray, previsto: dict) -> dict | None:
    """Acha a junção no quadro e o traste do detector mais perto dela.

    Args:
        imagem: quadro BGR na resolução nativa.
        previsto: previsão do quadro.

    Returns:
        ``{"x", "contraste", "indice", "numero"}`` (posição na faixa, contraste do corte,
        índice e número do detector do traste mais perto), ou None sem janela de busca.
    """
    montagem = faixa_do_quadro(previsto)
    if montagem is None:
        return None
    matriz, xs = montagem
    numeros = [int(t["numero"]) for t in previsto["trastes"]]
    faixa = recortar(imagem, matriz)
    sinal, valido = sinal_das_bandas(faixa)
    a_partir = [x for x, n in zip(xs, numeros, strict=True) if n >= TRASTE_INICIO_BUSCA]
    if not a_partir:
        return None
    inicio = max(0, int(min(a_partir)))
    fim = min(len(sinal), int(max(xs)) + 1)
    colunas = np.flatnonzero(valido[inicio:fim])
    if len(colunas) == 0:
        return None
    fim = inicio + int(colunas[-1]) + 1
    inicio = inicio + int(colunas[0])
    corte = ponto_de_mudanca(sinal, inicio, fim)
    if corte is None:
        return None
    x, contraste = corte
    indice = int(np.argmin([abs(xt - x) for xt in xs]))
    return {
        "x": int(x),
        "contraste": round(contraste, 3),
        "indice": indice,
        "numero": numeros[indice],
    }


def numero_do_video(juncoes_com_nut: list[int], contagens: list[int]) -> dict:
    """Número da junção de um vídeo: moda nos quadros com nut, ou a contagem de trastes.

    Args:
        juncoes_com_nut: número do detector do traste da junção, um por quadro com o nut
            visível com confiança e junção achada.
        contagens: número de trastes por quadro (só usado sem nenhum quadro com nut).

    Returns:
        ``{"numero": 12 | 14 | None, "fonte", "detalhe"}``.
    """
    if juncoes_com_nut:
        contagem = collections.Counter(juncoes_com_nut)
        moda, vezes = contagem.most_common(1)[0]
        fracao = vezes / len(juncoes_com_nut)
        valido = moda in NUMEROS_JUNCAO and fracao >= CONCORDANCIA_MINIMA
        return {
            "numero": moda if valido else None,
            "fonte": "nut",
            "detalhe": {
                "moda": moda,
                "fracao": round(fracao, 3),
                "n": len(juncoes_com_nut),
                "contagem": dict(contagem),
            },
        }
    if not contagens:
        return {"numero": None, "fonte": "nenhuma", "detalhe": {}}
    trastes = collections.Counter(contagens).most_common(1)[0][0]
    if trastes <= CONTAGEM_NYLON:
        numero = 12
    elif trastes >= CONTAGEM_ACO:
        numero = 14
    else:
        numero = None
    return {"numero": numero, "fonte": "contagem", "detalhe": {"trastes": trastes}}


def metodo_j(
    registros: list[dict], ler_imagem: Callable[[str], np.ndarray | None]
) -> tuple[dict[str, dict], dict]:
    """Método J num vídeo: aprende o número da junção e numera os quadros sem nut.

    Args:
        registros: quadros densos do vídeo (formato de ``tab.maos_braco_vizinhos``).
        ler_imagem: devolve a imagem BGR de um id (ou None, sem imagem).

    Returns:
        ``(saida, video)``: ``saida[id] = {"k", "motivo", "juncao"}`` para cada quadro com
        braço, e ``video`` com o número aprendido.
    """
    juncoes: dict[str, dict | None] = {}
    for registro in registros:
        if not registro["previsto"].get("achou"):
            continue
        imagem = ler_imagem(registro["id"])
        juncoes[registro["id"]] = (
            None if imagem is None else achar_juncao(imagem, registro["previsto"])
        )
    com_nut = [
        juncoes[r["id"]]["numero"]
        for r in registros
        if r["id"] in juncoes
        and nut_confiante(r)
        and juncoes[r["id"]] is not None
        and juncoes[r["id"]]["contraste"] >= CONTRASTE_MINIMO
    ]
    contagens = [len(r["previsto"]["trastes"]) for r in registros if r["id"] in juncoes]
    video = numero_do_video(com_nut, contagens)
    saida: dict[str, dict] = {}
    for registro in registros:
        id_q = registro["id"]
        if id_q not in juncoes:
            continue
        juncao = juncoes[id_q]
        if nut_confiante(registro):
            saida[id_q] = {"k": 0, "motivo": "nut visível", "juncao": juncao}
        elif video["numero"] is None:
            saida[id_q] = {"k": None, "motivo": "vídeo sem número", "juncao": juncao}
        elif juncao is None or juncao["contraste"] < CONTRASTE_MINIMO:
            saida[id_q] = {"k": None, "motivo": "junção não achada", "juncao": juncao}
        else:
            saida[id_q] = {
                "k": int(video["numero"]) - int(juncao["numero"]),
                "motivo": "junção",
                "juncao": juncao,
            }
    return saida, video
