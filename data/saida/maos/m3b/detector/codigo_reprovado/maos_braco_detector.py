"""Detector do braço do violão num quadro (M3b): cordas, nut e trastes.

Sem coordenadas fixas. O quadro inteiro entra na busca:

1. segmentos de reta (LSD) e a direção dominante do braço (histograma de ângulos);
2. família de cordas: segmentos longos quase paralelos a essa direção, agrupados
   pela distância ao eixo; a cadeia de 4 a 6 picos com espaçamento coerente é o
   grupo de cordas (as duas de fora são as cordas 1 e 6);
3. trastes: picos do gradiente ao longo do eixo, amostrados só dentro da faixa
   das cordas (um traste é uma borda perpendicular às cordas);
4. numeração pelo modelo projetivo 1D da regra das 12 notas (rodada 1005): RANSAC
   sobre ternas de picos com números 1 a 20; a melhor hipótese é refinada por
   mínimos quadrados. O nut é o ponto em que o modelo vale 0 (``t(0) = b``).

Uso::

    python -m tab.maos_braco_detector --conjunto dev
    python -m tab.maos_braco_detector --conjunto teste
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys

import cv2
import numpy as np

from .caminhos import MAOS_M3B
from .maos_braco_geometria import ajustar, s_do_traste

PASTA_DETECTOR = MAOS_M3B / "detector"
PASTA_QUADROS = MAOS_M3B / "quadros"
ARQUIVO_DIVISAO = PASTA_DETECTOR / "divisao.json"

#: Número de trastes considerados pelo modelo (a regra das 12 notas).
N_TRASTES = 20
#: Comprimento mínimo de um segmento de corda, em fração da diagonal do quadro.
FRACAO_COMPRIMENTO = 0.10
#: Tolerância angular da família de cordas, em graus.
TOLERANCIA_ANGULO = 4.0
#: Passo (distância entre duas cordas vizinhas), em px. O acervo tem 14 a 45 px
#: (AGENTS.md); a folga cobre a perspectiva.
ESPACO_MINIMO_CORDA = 12.0
ESPACO_MAXIMO_CORDA = 50.0
#: Razão máxima entre o maior e o menor espaçamento de uma cadeia de cordas.
RAZAO_ESPACO_MAXIMA = 2.2
#: Número mínimo de cordas numa cadeia para aceitar o grupo.
CORDAS_MINIMAS = 4
#: Fração da largura local da casa usada como tolerância de um traste.
FRACAO_TOLERANCIA = 0.25
#: Brilho abaixo do qual um pixel da faixa conta como escuro (tampo do braço).
LIMIAR_ESCURO = 110
#: Fração mínima de pixels escuros na faixa de cordas (o papel da tablatura é claro).
FRACAO_ESCURA_MINIMA = 0.25
#: Número mínimo de trastes explicados pelo modelo para aceitar o braço.
TRASTES_MINIMOS = 4
#: Limiar de pico do gradiente, em fração do percentil 99.
FRACAO_LIMIAR_PICO = 0.30
#: Distância mínima entre dois picos de traste, em px.
DISTANCIA_PICO_TRASTE = 6
#: Máximo de picos de traste usados nas ternas (controla o custo).
MAXIMO_PICOS = 24
#: Quantas direções fortes do quadro são testadas.
DIRECOES_TESTADAS = 5
#: Quantas cadeias de cordas por direção recebem a validação pelo modelo.
CADEIAS_POR_DIRECAO = 4

NUMEROS = np.arange(1, N_TRASTES + 1)
S_NUMEROS = np.array([s_do_traste(int(n)) for n in NUMEROS])
TERNAS_NUMEROS = np.array(list(itertools.combinations(NUMEROS, 3)))


def segmentos_lsd(cinza: np.ndarray) -> np.ndarray:
    """Segmentos de reta do quadro, pelo LSD do OpenCV.

    Args:
        cinza: imagem em tons de cinza.

    Returns:
        Matriz ``(n, 4)`` com ``x1, y1, x2, y2`` de cada segmento.
    """
    lsd = cv2.createLineSegmentDetector(0)
    linhas = lsd.detect(cinza)[0]
    if linhas is None:
        return np.zeros((0, 4), dtype=float)
    return linhas.reshape(-1, 4).astype(float)


def angulos_segmentos(segmentos: np.ndarray) -> np.ndarray:
    """Ângulo de cada segmento em graus, módulo 180.

    Args:
        segmentos: matriz ``(n, 4)``.

    Returns:
        Vetor de ângulos em ``[0, 180)``.
    """
    dx = segmentos[:, 2] - segmentos[:, 0]
    dy = segmentos[:, 3] - segmentos[:, 1]
    return np.degrees(np.arctan2(dy, dx)) % 180.0


def angulos_dominantes(
    angulos: np.ndarray, pesos: np.ndarray, quantos: int = 3
) -> list[float]:
    """Os ``quantos`` ângulos mais fortes, ponderados pelo comprimento.

    Args:
        angulos: ângulos dos segmentos, em graus módulo 180.
        pesos: peso de cada segmento (comprimento).
        quantos: quantos picos devolver.

    Returns:
        Ângulos (graus) dos picos, do mais forte ao mais fraco.
    """
    if len(angulos) == 0:
        return []
    histograma, _ = np.histogram(angulos, bins=180, range=(0.0, 180.0), weights=pesos)
    suave = (np.roll(histograma, 1) + histograma + np.roll(histograma, -1)) / 3.0
    escolhidos: list[float] = []
    for i in np.argsort(-suave):
        if suave[i] <= 0:
            break
        distancias = [min(abs(i - j), 180 - abs(i - j)) for j in escolhidos]
        if all(distancia > 4 for distancia in distancias):
            escolhidos.append(float(i) + 0.5)
        if len(escolhidos) == quantos:
            break
    return escolhidos


def picos_1d(sinal: np.ndarray, distancia: int, limiar: float) -> list[int]:
    """Índices dos máximos locais de um sinal, do mais forte ao mais fraco.

    Args:
        sinal: vetor 1D.
        distancia: distância mínima entre dois picos, em amostras.
        limiar: valor mínimo de um pico.

    Returns:
        Índices dos picos, ordenados pela força.
    """
    if len(sinal) < 3:
        return []
    meio = sinal[1:-1]
    locais = np.where((meio > sinal[:-2]) & (meio >= sinal[2:]) & (meio >= limiar))[0]
    locais = locais + 1
    ordem = locais[np.argsort(-sinal[locais])]
    escolhidos: list[int] = []
    for i in ordem:
        if all(abs(int(i) - j) >= distancia for j in escolhidos):
            escolhidos.append(int(i))
    return escolhidos


def suavizar(sinal: np.ndarray, sigma: float) -> np.ndarray:
    """Suavização gaussiana de um vetor 1D.

    Args:
        sinal: vetor 1D.
        sigma: desvio padrão em amostras.

    Returns:
        Vetor suavizado, do mesmo tamanho.
    """
    return (
        cv2.GaussianBlur(sinal.astype(np.float32).reshape(1, -1), (0, 0), sigma)
        .reshape(-1)
        .astype(float)
    )


def cadeias_de_cordas(
    distancias: np.ndarray, pesos: np.ndarray, extensao: float
) -> list[tuple[list[float], float]]:
    """Cadeias de 4 a 6 cordas com espaçamento coerente, da mais forte à mais fraca.

    Args:
        distancias: distância de cada segmento ao origem do quadro (ao longo da
            normal do braço).
        pesos: comprimento de cada segmento.
        extensao: maior distância possível (para limitar o histograma).

    Returns:
        Lista de ``(distâncias das cordas, peso total)``, ordenada por tamanho
        da cadeia e depois por peso. Pode ser vazia.
    """
    if len(distancias) == 0:
        return []
    bins = np.arange(-extensao, extensao + 2.0, 1.0)
    histograma, _ = np.histogram(distancias, bins=bins, weights=pesos)
    suave = suavizar(histograma, 1.5)
    centros = bins[:-1] + 0.5
    picos = picos_1d(suave, 3, 0.0)[:30]
    if len(picos) < CORDAS_MINIMAS:
        return []
    ordenados = sorted(picos, key=lambda i: centros[i])
    posicoes = centros[ordenados]
    forcas = suave[ordenados]
    candidatas: list[tuple[int, float, list[float]]] = []
    for tamanho in (6, 5, 4):
        for inicio in range(len(posicoes) - tamanho + 1):
            fatia = posicoes[inicio : inicio + tamanho]
            espacos = np.diff(fatia)
            if espacos.min() < ESPACO_MINIMO_CORDA:
                continue
            if espacos.max() > ESPACO_MAXIMO_CORDA:
                continue
            if espacos.max() / espacos.min() > RAZAO_ESPACO_MAXIMA:
                continue
            peso = float(forcas[inicio : inicio + tamanho].sum())
            candidatas.append((tamanho, peso, [float(x) for x in fatia]))
    candidatas.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return [(cordas, peso) for _, peso, cordas in candidatas]


def escore_trastes(
    cinza: np.ndarray, theta: float, d_lo: float, d_hi: float
) -> tuple[np.ndarray, np.ndarray]:
    """Força de borda perpendicular às cordas, ao longo do eixo do braço.

    Para cada posição ``u`` no eixo, média do módulo do gradiente na direção do
    eixo ao longo da faixa das cordas. Um traste é uma borda com essa direção;
    as próprias cordas quase não contribuem.

    Args:
        cinza: imagem em tons de cinza.
        theta: direção do braço, em graus.
        d_lo: distância (normal) da corda de uma borda da faixa.
        d_hi: distância (normal) da corda da outra borda.

    Returns:
        ``(us, escore)``: posições ao longo do eixo (px) e a força em cada uma.
    """
    altura, largura = cinza.shape
    rad = np.radians(theta)
    v = np.array([np.cos(rad), np.sin(rad)])
    normal = np.array([-np.sin(rad), np.cos(rad)])
    diagonal = float(np.hypot(altura, largura))
    us = np.arange(-diagonal, diagonal, 1.0)
    ws = np.linspace(d_lo, d_hi, 9)
    xs = us[:, None] * v[0] + ws[None, :] * normal[0]
    ys = us[:, None] * v[1] + ws[None, :] * normal[1]
    dentro = (xs >= 0) & (xs <= largura - 1) & (ys >= 0) & (ys <= altura - 1)
    suave = cv2.GaussianBlur(cinza.astype(np.float32), (0, 0), 1.2)
    gx = cv2.Sobel(suave, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(suave, cv2.CV_32F, 0, 1, ksize=3)
    gradiente = np.abs(gx * v[0] + gy * v[1])
    amostra = cv2.remap(
        gradiente,
        xs.astype(np.float32),
        ys.astype(np.float32),
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    escore = amostra.mean(axis=1).astype(float)
    escore[~dentro.all(axis=1)] = 0.0
    return us, escore


def ajustar_numeros(
    posicoes: np.ndarray, forcas: np.ndarray
) -> tuple[np.ndarray, int, float] | None:
    """Acha o modelo projetivo e a numeração dos trastes por RANSAC em ternas.

    Cada terna de picos recebe uma terna de números (1 a 20). A hipótese fica
    com o maior número de números explicados (um pico dentro de 1/4 da casa
    local). O modelo é refinado por mínimos quadrados nos pares explicados.

    Args:
        posicoes: posições dos picos ao longo do eixo (px).
        forcas: força de cada pico (não usada na pontuação; desempata).

    Returns:
        ``(parametros [a, b, c], numeros explicados, resíduo)`` ou ``None``.
    """
    ordem = np.argsort(posicoes)
    posicoes = posicoes[ordem][:MAXIMO_PICOS]
    m = len(posicoes)
    if m < 3:
        return None
    melhor_pontuacao = -np.inf
    melhor_params: np.ndarray | None = None
    s3 = S_NUMEROS[TERNAS_NUMEROS - 1]
    for trio in itertools.combinations(range(m), 3):
        ts = posicoes[list(trio)]
        matriz = np.zeros((len(TERNAS_NUMEROS), 3, 3))
        rhs = np.zeros((len(TERNAS_NUMEROS), 3))
        for r in range(3):
            matriz[:, r, 0] = s3[:, r]
            matriz[:, r, 1] = 1.0
            matriz[:, r, 2] = -s3[:, r] * ts[r]
            rhs[:, r] = ts[r]
        matriz += np.eye(3)[None, :, :] * 1e-9
        params = np.linalg.solve(matriz, rhs[..., None])[..., 0]
        pontuacao, _ = _pontuar(params, posicoes)
        i = int(np.argmax(pontuacao))
        if pontuacao[i] > melhor_pontuacao:
            melhor_pontuacao = float(pontuacao[i])
            melhor_params = params[i]
    if melhor_params is None or melhor_pontuacao < TRASTES_MINIMOS:
        return None
    previstos = _previstos(melhor_params)
    explicados = _explicados(previstos, posicoes)
    pares = [(int(n), float(posicoes[j])) for n, j in explicados]
    if len(pares) >= 3:
        refinado = ajustar(pares, "proj")
        if np.all(np.isfinite(refinado)):
            melhor_params = refinado
    previstos = _previstos(melhor_params)
    explicados = _explicados(previstos, posicoes)
    residuo = (
        float(np.mean([abs(posicoes[j] - previstos[n - 1]) for n, j in explicados]))
        if explicados
        else float("inf")
    )
    return melhor_params, len(explicados), residuo


def _previstos(params: np.ndarray) -> np.ndarray:
    """Posições previstas dos trastes 1 a 20 pelo modelo.

    Args:
        params: ``[a, b, c]`` do modelo projetivo.

    Returns:
        Vetor ``(20,)`` com a posição (px) de cada traste.
    """
    s = S_NUMEROS
    with np.errstate(divide="ignore", invalid="ignore"):
        return (params[0] * s + params[1]) / (params[2] * s + 1.0)


def _pontuar(params: np.ndarray, posicoes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pontuação de cada hipótese da terna, em lote.

    Args:
        params: parâmetros ``(n_hipoteses, 3)`` de ``[a, b, c]``.
        posicoes: posições ordenadas dos picos.

    Returns:
        ``(pontuação, previsões)`` por hipótese. A pontuação é o número de
        trastes explicados, ou -1 se a hipótese é inválida (não monótona).
    """
    s = S_NUMEROS[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        previstos = (params[:, 0:1] * s + params[:, 1:2]) / (params[:, 2:3] * s + 1.0)
    finito = np.all(np.isfinite(previstos), axis=1)
    diferencas = np.diff(previstos, axis=1)
    monotona = np.all(diferencas > 0, axis=1) | np.all(diferencas < 0, axis=1)
    largura = np.abs(np.gradient(np.nan_to_num(previstos), axis=1))
    tolerancia = FRACAO_TOLERANCIA * largura
    m = len(posicoes)
    idx = np.searchsorted(posicoes, np.nan_to_num(previstos))
    baixo = posicoes[np.clip(idx - 1, 0, m - 1)]
    alto = posicoes[np.clip(idx, 0, m - 1)]
    distancia = np.minimum(
        np.abs(np.nan_to_num(previstos) - baixo),
        np.abs(np.nan_to_num(previstos) - alto),
    )
    explicado = (distancia <= tolerancia) & finito[:, None]
    pontuacao = explicado.sum(axis=1).astype(float)
    pontuacao[~(finito & monotona)] = -1.0
    return pontuacao, previstos


def _explicados(previstos: np.ndarray, posicoes: np.ndarray) -> list[tuple[int, int]]:
    """Pares ``(número, índice do pico)`` explicados por um modelo.

    Args:
        previstos: posições previstas dos trastes 1 a 20.
        posicoes: posições ordenadas dos picos.

    Returns:
        Pares com o número do traste e o índice do pico mais perto, quando o
        pico está dentro da tolerância.
    """
    largura = np.abs(np.gradient(previstos))
    tolerancia = FRACAO_TOLERANCIA * largura
    pares: list[tuple[int, int]] = []
    for k, previsto in enumerate(previstos):
        if not np.isfinite(previsto):
            continue
        j = int(np.argmin(np.abs(posicoes - previsto)))
        if abs(posicoes[j] - previsto) <= tolerancia[k]:
            pares.append((k + 1, j))
    return pares


def _lado_da_corda(cinza: np.ndarray, theta: float, d: float) -> tuple[float, float]:
    """Altura (y) e brilho médio de uma corda, no meio da imagem.

    Args:
        cinza: imagem em tons de cinza.
        theta: direção do braço, em graus.
        d: distância da corda ao origem, ao longo da normal.

    Returns:
        ``(y no meio da imagem, brilho médio ao longo da corda)``.
    """
    altura, largura = cinza.shape
    rad = np.radians(theta)
    v = np.array([np.cos(rad), np.sin(rad)])
    normal = np.array([-np.sin(rad), np.cos(rad)])
    if abs(v[0]) < 1e-6:
        return float(altura / 2.0), 0.0
    u_meio = (largura / 2.0 - d * normal[0]) / v[0]
    y_meio = u_meio * v[1] + d * normal[1]
    us = np.linspace(0.2 * largura, 0.8 * largura, 40)
    us_u = (us - d * normal[0]) / v[0]
    xs = us_u * v[0] + d * normal[0]
    ys = us_u * v[1] + d * normal[1]
    dentro = (xs >= 0) & (xs <= largura - 1) & (ys >= 0) & (ys <= altura - 1)
    if not dentro.any():
        return float(y_meio), 0.0
    brilho = float(cinza[ys[dentro].astype(int), xs[dentro].astype(int)].mean())
    return float(y_meio), brilho


def contar_trastes_candidatos(
    cinza: np.ndarray, theta: float, d_lo: float, d_hi: float
) -> tuple[np.ndarray, np.ndarray]:
    """Picos de traste de uma faixa de cordas (posições e forças).

    Args:
        cinza: imagem em tons de cinza.
        theta: direção do braço, em graus.
        d_lo: distância de uma corda de fora.
        d_hi: distância da outra corda de fora.

    Returns:
        ``(posições ao longo do eixo, forças)`` dos picos de traste.
    """
    us, escore = escore_trastes(cinza, theta, d_lo, d_hi)
    if not escore.any():
        return np.zeros(0), np.zeros(0)
    limiar = FRACAO_LIMIAR_PICO * float(np.percentile(escore, 99))
    picos = picos_1d(suavizar(escore, 1.0), DISTANCIA_PICO_TRASTE, limiar)
    if not picos:
        return np.zeros(0), np.zeros(0)
    return us[picos], escore[picos]


def fracao_escura(cinza: np.ndarray, theta: float, d_lo: float, d_hi: float) -> float:
    """Fração de pixels escuros dentro da faixa de cordas.

    Args:
        cinza: imagem em tons de cinza.
        theta: direção do braço, em graus.
        d_lo: distância de uma corda de fora.
        d_hi: distância da outra corda de fora.

    Returns:
        Fração (0 a 1) de amostras da faixa com brilho abaixo de ``LIMIAR_ESCURO``.
    """
    altura, largura = cinza.shape
    rad = np.radians(theta)
    v = np.array([np.cos(rad), np.sin(rad)])
    normal = np.array([-np.sin(rad), np.cos(rad)])
    us = np.arange(-np.hypot(altura, largura), np.hypot(altura, largura), 2.0)
    ws = np.linspace(d_lo, d_hi, 5)
    xs = us[:, None] * v[0] + ws[None, :] * normal[0]
    ys = us[:, None] * v[1] + ws[None, :] * normal[1]
    dentro = (xs >= 0) & (xs <= largura - 1) & (ys >= 0) & (ys <= altura - 1)
    if not dentro.any():
        return 0.0
    valores = cinza[ys[dentro].astype(int), xs[dentro].astype(int)]
    return float((valores < LIMIAR_ESCURO).mean())


def avaliar_faixa(cinza: np.ndarray, theta: float, cordas: list[float]) -> dict | None:
    """Detecta traste e numeração numa faixa de cordas proposta.

    Args:
        cinza: imagem em tons de cinza.
        theta: direção do braço, em graus.
        cordas: distâncias (normais) das cordas da faixa, em ordem.

    Returns:
        Resultado do detector para esta faixa (``braco`` indica se o modelo
        projetivo explicou ao menos ``TRASTES_MINIMOS`` trastes).
    """
    d_lo, d_hi = cordas[0], cordas[-1]
    escura = fracao_escura(cinza, theta, d_lo, d_hi)
    if escura < FRACAO_ESCURA_MINIMA:
        return None
    posicoes, forcas = contar_trastes_candidatos(cinza, theta, d_lo, d_hi)
    ajuste = ajustar_numeros(posicoes, forcas) if len(posicoes) >= 3 else None
    rad = np.radians(theta)
    normal = np.array([-np.sin(rad), np.cos(rad)])
    v = np.array([np.cos(rad), np.sin(rad)])
    resultado: dict = {
        "braco": ajuste is not None,
        "theta_graus": float(theta),
        "cordas_d": cordas,
        "faixa": [d_lo, d_hi],
        "picos_trastes": len(posicoes),
        "fracao_escura": escura,
        "trastes_explicados": 0,
        "residuo": None,
        "nut": None,
        "trastes": [],
        "_lados": {
            "d_lo": _lado_da_corda(cinza, theta, d_lo),
            "d_hi": _lado_da_corda(cinza, theta, d_hi),
        },
    }
    if ajuste is None:
        return resultado
    params, n_explicados, residuo = ajuste
    previstos = _previstos(params)
    observados = {n for n, _ in _explicados(previstos, _posicoes_ordenadas(posicoes))}
    w_meio = (d_lo + d_hi) / 2.0
    nut_u = float(params[1])
    resultado["trastes_explicados"] = int(n_explicados)
    resultado["residuo"] = residuo
    resultado["nut"] = {
        "u": nut_u,
        "ponto": [
            float(nut_u * v[0] + w_meio * normal[0]),
            float(nut_u * v[1] + w_meio * normal[1]),
        ],
    }
    resultado["trastes"] = [
        {
            "numero": int(n),
            "u": float(previstos[n - 1]),
            "observado": bool(n in observados),
            "ponto": [
                float(previstos[n - 1] * v[0] + w_meio * normal[0]),
                float(previstos[n - 1] * v[1] + w_meio * normal[1]),
            ],
        }
        for n in range(1, N_TRASTES + 1)
        if np.isfinite(previstos[n - 1])
    ]
    return resultado


def _posicoes_ordenadas(posicoes: np.ndarray) -> np.ndarray:
    """Posições dos picos em ordem crescente, como ``ajustar_numeros`` as usa.

    Args:
        posicoes: posições dos picos.

    Returns:
        Posições ordenadas e truncadas em ``MAXIMO_PICOS``.
    """
    return np.sort(posicoes)[:MAXIMO_PICOS]


def detectar(cinza: np.ndarray) -> dict:
    """Detecta o braço no quadro: varre direções e faixas de cordas.

    Para cada direção forte do quadro, cada cadeia de cordas candidata é avaliada
    pelo modelo dos trastes. Fica a faixa com mais trastes explicados.

    Args:
        cinza: imagem em tons de cinza.

    Returns:
        Dicionário com ``braco`` (bool) e, se achado, as cordas, o nut e os
        trastes (previstos pelo modelo, com ``observado`` para os explicados).
    """
    segmentos = segmentos_lsd(cinza)
    altura, largura = cinza.shape
    comprimentos = np.hypot(
        segmentos[:, 2] - segmentos[:, 0], segmentos[:, 3] - segmentos[:, 1]
    )
    minimo = FRACAO_COMPRIMENTO * float(np.hypot(altura, largura))
    longos = comprimentos >= minimo
    segmentos = segmentos[longos]
    comprimentos = comprimentos[longos]
    extensao = float(np.hypot(altura, largura))
    melhor: dict | None = None
    testadas = 0
    for theta in angulos_dominantes(
        angulos_segmentos(segmentos), comprimentos, quantos=DIRECOES_TESTADAS
    ):
        rad = np.radians(theta)
        normal = np.array([-np.sin(rad), np.cos(rad)])
        diferenca = (angulos_segmentos(segmentos) - theta + 90.0) % 180.0 - 90.0
        mascara = np.abs(diferenca) <= TOLERANCIA_ANGULO
        if not mascara.any():
            continue
        meios = (segmentos[mascara, :2] + segmentos[mascara, 2:]) / 2.0
        distancias = meios @ normal
        cadeias = cadeias_de_cordas(distancias, comprimentos[mascara], extensao)
        for cordas, _ in cadeias[:CADEIAS_POR_DIRECAO]:
            testadas += 1
            resultado = avaliar_faixa(cinza, theta, cordas)
            if resultado is None:
                continue
            if melhor is None or _chave(resultado) > _chave(melhor):
                melhor = resultado
    if melhor is None:
        return {"braco": False, "testadas": testadas}
    melhor["testadas"] = testadas
    return melhor


def _chave(resultado: dict) -> tuple[bool, int, int]:
    """Ordem de preferência entre faixas candidatas.

    Args:
        resultado: saída de ``avaliar_faixa``.

    Returns:
        Tupla (achou braço, trastes explicados, número de cordas).
    """
    return (
        bool(resultado["braco"]),
        int(resultado["trastes_explicados"]),
        len(resultado["cordas_d"]),
    )


def carregar_divisao() -> dict:
    """Lê a divisão desenvolvimento/teste gravada antes das medições.

    Returns:
        Dicionário com ``desenvolvimento`` e ``teste`` (listas de ids de quadro).
    """
    return json.loads(ARQUIVO_DIVISAO.read_text(encoding="utf-8"))


def main() -> int:
    """Roda o detector nos quadros de um conjunto e grava JSON e imagens.

    Returns:
        Código de saída (0).
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--conjunto", choices=("dev", "teste"), required=True)
    args = parser.parse_args()
    divisao = carregar_divisao()
    ids = divisao["quadros_dev" if args.conjunto == "dev" else "quadros_teste"]
    PASTA_DETECTOR.mkdir(parents=True, exist_ok=True)
    for id_quadro in ids:
        cinza = cv2.imread(str(PASTA_QUADROS / f"{id_quadro}.png"), 0)
        resultado = detectar(cinza)
        saida = PASTA_DETECTOR / f"{id_quadro}_{args.conjunto}.json"
        saida.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(
            id_quadro,
            "braco" if resultado["braco"] else "sem braco",
            resultado.get("trastes_explicados", 0),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
