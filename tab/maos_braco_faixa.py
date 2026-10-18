"""Faixa retificada do braço (M21, fase A): eixo, erro simulado e rótulos na faixa.

A faixa é um retângulo girado ao longo do eixo do braço, reamostrado em 1024 x 192 px,
com o braço na horizontal. O eixo vai do nut até a ponta das cordas no corpo, e a altura
da faixa é 3 vezes a distância entre as cordas 1 e 6 (a largura do braço).

O eixo que o detector recebe não é o do gabarito: ``perturbar`` simula o erro de um
localizador grosseiro, com sorteio uniforme e semente fixa pelo chamador. Os rótulos da
faixa são as marcas verdadeiras levadas pela mesma afim, de modo que o modelo aprende a
achar a linha real, e não o eixo sorteado.

``voltar`` leva pontos da faixa de volta ao quadro, pela inversa da afim. Este módulo usa
só numpy e OpenCV. As marcas vêm de ``tab.maos_braco_tempo`` e a regra das 12 notas de
``tab.maos_braco_regra``.
"""

from __future__ import annotations

import math
import random

import cv2
import numpy as np

from .maos_braco_regra import prever_trastes
from .maos_braco_tempo import Marcas

#: Largura e altura da faixa retificada, em px.
LARGURA_FAIXA = 1024
ALTURA_FAIXA = 192
#: Margem do retângulo antes do nut (lado do nut), como fração do comprimento. Emenda 2
#: da rodada 1021: 0,12 (era 0,05), para a perturbação nunca cortar o nut.
MARGEM_ANTES_NUT = 0.12
#: Margem do retângulo depois do extremo, como fração do comprimento (sem mudança).
MARGEM_APOS_EXTREMO = 0.05
#: Meia altura da faixa, em larguras do braço (a altura inteira é 3 larguras).
MEIA_ALTURA_EM_LARGURAS = 1.5
#: Erro simulado do eixo (pré-registro 1021): limites dos sorteios.
ERRO_PERPENDICULAR = 0.3  # fração da largura, para os dois lados
ERRO_AO_LONGO = 0.05  # fração do comprimento, para os dois lados
ERRO_ROTACAO_GRAUS = 3.0
ERRO_ESCALA = 0.10  # fração, para mais e para menos
#: Âncoras da regra das 12 notas dentro da faixa.
ANCORAS_PREVISAO = (5, 12)
#: Dimensão "sem limite" para a regra: ela só corta o que cai fora do quadro original.
SEM_LIMITE = 10**6


def _como_3x3(matriz: np.ndarray) -> np.ndarray:
    """Completa uma afim 2x3 para a forma homogênea 3x3.

    Args:
        matriz: afim ``(2, 3)`` ou homografia ``(3, 3)``.

    Returns:
        Homografia ``(3, 3)``.
    """
    if matriz.shape == (3, 3):
        return matriz
    completa = np.eye(3)
    completa[:2] = matriz
    return completa


def aplicar_matriz(matriz: np.ndarray, pontos: object) -> np.ndarray:
    """Aplica uma afim ou homografia a pontos 2D.

    Args:
        matriz: afim ``(2, 3)`` ou homografia ``(3, 3)``.
        pontos: array com a última dimensão igual a 2 (um ou mais pontos).

    Returns:
        Array com a mesma forma de ``pontos``.
    """
    m = _como_3x3(np.asarray(matriz, dtype=float))
    pts = np.asarray(pontos, dtype=float)
    n = pts.size // 2
    homog = np.concatenate([pts.reshape(n, 2), np.ones((n, 1))], axis=1)
    proj = homog @ m.T
    return (proj[:, :2] / proj[:, 2:3]).reshape(pts.shape)


def _ponto_na_perpendicular(
    corda: np.ndarray,
    origem: np.ndarray,
    u: np.ndarray,
    n: np.ndarray,
    s: float,
) -> float:
    """Coordenada transversal da corda onde ela cruza a perpendicular em ``s``.

    Args:
        corda: dois pontos ``(2, 2)`` da corda.
        origem: nut, origem do eixo.
        u: vetor unitário do eixo.
        n: normal do eixo, ``[-u[1], u[0]]``.
        s: posição ao longo do eixo, em px a partir da origem.

    Returns:
        Coordenada transversal ``p`` em px.

    Raises:
        ValueError: se a corda é perpendicular ao eixo.
    """
    a0 = corda[0]
    d = corda[1] - corda[0]
    du = float(d @ u)
    if abs(du) < 1e-9:
        raise ValueError("corda perpendicular ao eixo")
    lam = (s - float((a0 - origem) @ u)) / du
    return float((a0 - origem) @ n + lam * float(d @ n))


def _largura_em(
    corda1: np.ndarray,
    corda6: np.ndarray,
    origem: np.ndarray,
    u: np.ndarray,
    s: float,
) -> float:
    """Distância entre as cordas 1 e 6 na perpendicular ao eixo em ``s``.

    Args:
        corda1: pontos da corda 1.
        corda6: pontos da corda 6.
        origem: nut.
        u: vetor unitário do eixo.
        s: posição ao longo do eixo, em px.

    Returns:
        Largura em px.
    """
    n = np.array([-u[1], u[0]])
    p1 = _ponto_na_perpendicular(corda1, origem, u, n, s)
    p6 = _ponto_na_perpendicular(corda6, origem, u, n, s)
    return abs(p1 - p6)


def eixo_da_faixa(marcas: Marcas) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Eixo da faixa: do nut até a ponta das cordas no corpo.

    O extremo é o ponto médio das pontas de corda1 e corda6 mais longe do nut. A
    largura é a maior distância entre as retas de corda1 e corda6, medida no nut e no
    extremo.

    Args:
        marcas: marcas do quadro (precisa do nut).

    Returns:
        ``(origem, direcao, comprimento, largura)``: origem é o nut, direção é o
        vetor unitário até o extremo, comprimento e largura estão em px.

    Raises:
        ValueError: sem nut, ou com cordas degeneradas.
    """
    if marcas.nut is None:
        raise ValueError("a faixa precisa do nut")
    origem = np.asarray(marcas.nut, dtype=float)
    c1 = np.asarray(marcas.corda1, dtype=float)
    c6 = np.asarray(marcas.corda6, dtype=float)
    ponta1 = c1[int(np.argmax(np.linalg.norm(c1 - origem, axis=1)))]
    ponta6 = c6[int(np.argmax(np.linalg.norm(c6 - origem, axis=1)))]
    vetor = (ponta1 + ponta6) / 2.0 - origem
    comprimento = float(np.linalg.norm(vetor))
    if comprimento == 0.0:
        raise ValueError("extremo do braço coincide com o nut")
    u = vetor / comprimento
    largura = max(
        _largura_em(c1, c6, origem, u, 0.0),
        _largura_em(c1, c6, origem, u, comprimento),
    )
    return origem, u, comprimento, largura


def sortear_perturbacao(rng: random.Random) -> dict[str, float]:
    """Sorteia um erro simulado do eixo, dentro dos limites do pré-registro.

    Args:
        rng: gerador do chamador (semente fixa).

    Returns:
        ``perpendicular`` (fração da largura), ``ao_longo`` (fração do comprimento),
        ``rotacao_graus`` e ``escala`` (fração, para mais e para menos).
    """
    return {
        "perpendicular": rng.uniform(-ERRO_PERPENDICULAR, ERRO_PERPENDICULAR),
        "ao_longo": rng.uniform(-ERRO_AO_LONGO, ERRO_AO_LONGO),
        "rotacao_graus": rng.uniform(-ERRO_ROTACAO_GRAUS, ERRO_ROTACAO_GRAUS),
        "escala": rng.uniform(-ERRO_ESCALA, ERRO_ESCALA),
    }


def aplicar_perturbacao(
    eixo: tuple[np.ndarray, np.ndarray, float, float], perturbacao: dict[str, float]
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Aplica um erro simulado a um eixo.

    A rotação é em torno do centro do eixo; depois vêm os deslocamentos (transversal e
    ao longo) e, por fim, a escala de comprimento e largura juntos, com a origem fixa.

    Args:
        eixo: ``(origem, direcao, comprimento, largura)`` de ``eixo_da_faixa``.
        perturbacao: dicionário de ``sortear_perturbacao``.

    Returns:
        O eixo com o erro, no mesmo formato.
    """
    origem, u, comprimento, largura = eixo
    centro = origem + u * (comprimento / 2.0)
    teta = math.radians(perturbacao["rotacao_graus"])
    rot = np.array(
        [[math.cos(teta), -math.sin(teta)], [math.sin(teta), math.cos(teta)]]
    )
    origem_r = centro + rot @ (origem - centro)
    u_r = rot @ u
    n_r = np.array([-u_r[1], u_r[0]])
    origem_p = (
        origem_r
        + n_r * (perturbacao["perpendicular"] * largura)
        + u_r * (perturbacao["ao_longo"] * comprimento)
    )
    fator = 1.0 + perturbacao["escala"]
    return origem_p, u_r, comprimento * fator, largura * fator


def perturbar(
    eixo: tuple[np.ndarray, np.ndarray, float, float], rng: random.Random
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Sorteia e aplica um erro simulado ao eixo.

    Args:
        eixo: ``(origem, direcao, comprimento, largura)`` do gabarito.
        rng: gerador do chamador (semente fixa).

    Returns:
        O eixo com o erro sorteado.
    """
    return aplicar_perturbacao(eixo, sortear_perturbacao(rng))


def matriz_da_faixa(eixo: tuple[np.ndarray, np.ndarray, float, float]) -> np.ndarray:
    """Afim que leva o eixo à faixa de 1024 x 192 px.

    O retângulo de origem é ``[origem - 0,12 L, extremo + 0,05 L] x [-1,5 w, +1,5 w]``,
    e vai para ``[0, 1024] x [0, 192]``. Com isso o nut cai perto de x = 0,12/1,17 de
    1024 (cerca de 105 px) e o eixo, em y = 96.

    Args:
        eixo: ``(origem, direcao, comprimento, largura)``.

    Returns:
        Afim ``(2, 3)`` float64, do quadro original para a faixa.
    """
    origem, u, comprimento, largura = eixo
    n = np.array([-u[1], u[0]])
    kx = LARGURA_FAIXA / ((MARGEM_ANTES_NUT + 1.0 + MARGEM_APOS_EXTREMO) * comprimento)
    ky = ALTURA_FAIXA / (2.0 * MEIA_ALTURA_EM_LARGURAS * largura)
    linha_x = kx * u
    cx = kx * (MARGEM_ANTES_NUT * comprimento - float(origem @ u))
    linha_y = ky * n
    cy = ky * (MEIA_ALTURA_EM_LARGURAS * largura - float(origem @ n))
    return np.array(
        [[linha_x[0], linha_x[1], cx], [linha_y[0], linha_y[1], cy]], dtype=float
    )


def recortar(imagem: np.ndarray, matriz: np.ndarray) -> np.ndarray:
    """Reamostra o quadro na faixa retificada.

    Args:
        imagem: quadro BGR (ou cinza) do original.
        matriz: afim de ``matriz_da_faixa``.

    Returns:
        Faixa de 192 x 1024 px, com borda constante 0 fora do quadro.
    """
    return cv2.warpAffine(
        imagem,
        matriz,
        (LARGURA_FAIXA, ALTURA_FAIXA),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def voltar(pontos_faixa: object, matriz: np.ndarray) -> np.ndarray:
    """Leva pontos da faixa de volta ao quadro original (inversa da afim).

    Args:
        pontos_faixa: pontos ``(..., 2)`` na faixa.
        matriz: afim de ``matriz_da_faixa``.

    Returns:
        Pontos no quadro original, com a mesma forma de ``pontos_faixa``.
    """
    inversa = np.linalg.inv(_como_3x3(np.asarray(matriz, dtype=float)))
    return aplicar_matriz(inversa, pontos_faixa)


def _previstos_na_faixa(marcas: Marcas, matriz: np.ndarray) -> list | None:
    """Trastes previstos pela regra das 12 notas, levados à faixa.

    A regra roda sobre as marcas originais (com as âncoras 5 e 12). Se ela não se
    aplica, a resposta é ``None``.

    Args:
        marcas: marcas originais do quadro.
        matriz: afim de ``matriz_da_faixa``.

    Returns:
        Lista ``[numero, x, y]`` na faixa, ou ``None``.
    """
    if marcas.nut is None or any(n not in marcas.trastes for n in ANCORAS_PREVISAO):
        return None
    ancoras = {n: marcas.trastes[n].tolist() for n in ANCORAS_PREVISAO}
    try:
        previstos = prever_trastes(
            marcas.nut.tolist(),
            marcas.corda1.tolist(),
            marcas.corda6.tolist(),
            ancoras,
            (SEM_LIMITE, SEM_LIMITE),
        )
    except ValueError:
        return None
    return [
        [numero, *aplicar_matriz(matriz, np.asarray(ponto)).tolist()]
        for numero, ponto in sorted(previstos.items())
    ]


def rotulo_na_faixa(marcas: Marcas, matriz: np.ndarray) -> dict:
    """Rótulos do quadro na faixa: cordas, trastes e a previsão da regra.

    Args:
        marcas: marcas do dono no quadro (ou transformadas, no caso do rastreador).
        matriz: afim de ``matriz_da_faixa``.

    Returns:
        Dicionário com ``corda1`` e ``corda6`` (2 pontos cada), ``trastes`` (lista de
        ``[numero, x, y]``, com o nut como 0) e ``trastes_previstos`` (mesma forma, ou
        ``None`` quando a regra não se aplica).
    """
    trastes = [
        [numero, *aplicar_matriz(matriz, ponto).tolist()]
        for numero, ponto in sorted(marcas.trastes.items())
    ]
    if marcas.nut is not None:
        trastes.insert(0, [0, *aplicar_matriz(matriz, marcas.nut).tolist()])
    return {
        "corda1": aplicar_matriz(matriz, marcas.corda1).tolist(),
        "corda6": aplicar_matriz(matriz, marcas.corda6).tolist(),
        "trastes": trastes,
        "trastes_previstos": _previstos_na_faixa(marcas, matriz),
    }
