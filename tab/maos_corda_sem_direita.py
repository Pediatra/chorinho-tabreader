"""Corda sem a mão direita: decodificador por ataque com polifonia e continuidade (M8).

Pergunta da rodada M8: sem a câmera da mão direita (pausada pela decisão 1005), quanto se
acerta da CORDA de cada nota, usando a altura (tirada da tablatura do produto, ou seja,
áudio perfeito), a posição da mão esquerda e uma regra de posição e continuidade? O gabarito
é a corda da tablatura do produto.

Modelo:

- **Ataque**: notas com o mesmo ``t_ini`` (tolerância de 0,02 s). Cada nota tem como
  candidatos as cordas em que a mesma altura existe, com casa de 0 a 19.
- **Polifonia**: num ataque, notas diferentes nunca usam a mesma corda. As combinações
  válidas são enumeradas; o ataque sem combinação válida (produto inconsistente) cai numa
  enumeração sem a restrição e é contado à parte.
- **Custo do ataque**: ``α·casa`` por nota presa, mais ``β·dist(casa, janela)`` (zero dentro
  da janela da mão esquerda). Corda solta custa zero, com a mão onde estiver. Abertura das
  presas acima de 4 casas custa ``γ``.
- **Continuidade**: ``δ·|Δ posição|`` entre ataques consecutivos, com posição = menor casa
  presa do ataque. Ataque só de cordas soltas não muda a posição: ela é carregada.
- **Viterbi** sobre a sequência de ataques do vídeo.

Degraus, na mesma tabela, por vídeo:

- **D0**: casa mais baixa, nota a nota (referência, sem polifonia nem continuidade);
- **D1**: decodificador sem câmera (``β = 0``);
- **D2**: D1 mais a janela da mão esquerda pela câmera do braço. A câmera só é usada onde
  casa com o quadro do gabarito do dono (``data/gold/maos/braco.json``); no ataque em que
  não casa, D2 cai para D1. A calibração feita pelas notas não entra;
- **D3**: câmera perfeita e sem vazar: janela = mediana das casas presas dos vizinhos (até
  1 s, sem o próprio ataque e sem cordas soltas), ± 2 casas.

Uso::

    python -m tab.maos_corda_sem_direita
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import math
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, MAOS_M3B, MAOS_M8, acervo
from .maos_braco_geometria import Geometria, ajustar, montar_geometria
from .maos_padroes_preparar import VIDEOS, notas_com_tempo

#: Afinação padrão: MIDI das cordas soltas, da 1 (mi aguda) à 6 (mi grave).
AFINACAO_MIDI = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}

#: Maior casa considerada (0 é a corda solta).
CASA_MAX = 19

#: Tolerância, em segundos, para considerar duas notas do mesmo ataque.
TOLERANCIA_ATAQUE_S = 0.02

#: Abertura máxima das casas presas de um ataque antes da penalidade ``γ``.
ABERTURA_MAX = 4

#: Pontas da mão usadas na janela (8, 12, 16 e 20: as pontas de indicador a mínimo).
PONTAS_JANELA = (8, 12, 16, 20)

#: Score mínimo de uma ponta para entrar na janela.
SCORE_MIN = 0.3

#: Número mínimo de pontas da mão esquerda sobre o braço para a mão ser escolhida.
MIN_PONTOS_NO_BRACO = 2

#: Folga, em px, da caixa do braço (região do casamento da câmera).
MARGEM_CAIXA_PX = 25

#: Busca da câmera, em px, em volta da posição do gabarito.
BUSCA_CAMERA_PX = 60

#: Limiar de correlação (NCC) para considerar a câmera igual à do quadro do gabarito.
LIMIAR_CAMERA = 0.8

#: Raio, em segundos, dos vizinhos da janela D3 e meia largura da janela, em casas.
RAIO_VIZINHOS_S = 1.0
MEIA_JANELA_D3 = 2.0

#: Grade de avaliação (γ fixo em 5). Valores da rodada, em decimal: α 0,5/1/2, β 1/3/10,
#: δ 0/0,5/2.
GRADE_ALFA = (0.5, 1.0, 2.0)
GRADE_BETA = (1.0, 3.0, 10.0)
GRADE_DELTA = (0.0, 0.5, 2.0)

#: Quatro vídeos do M8, na ordem dos ``VIDEOS`` do M5, com o quadro do gabarito do braço.
NOMES = ("retrato", "noturno", "lacrimosa", "glimpse")
QUADRO_DO_BRACO = {
    "retrato": "q02",
    "noturno": "q16",
    "lacrimosa": "q21",
    "glimpse": "q23",
}

#: Degraus e seus nomes na tabela.
DEGRAUS = ("D0", "D1", "D2", "D3")

#: Combinação de um ataque: um par ``(corda, casa)`` por nota, na ordem das notas.
Combo = tuple[tuple[int, int], ...]

#: Janela de casas ``(baixa, alta)``, ou ``None`` quando não há janela.
Janela = tuple[float, float] | None


@dataclasses.dataclass(frozen=True)
class Pesos:
    """Pesos do decodificador.

    Attributes:
        alpha: custo por casa de nota presa (preferência por casa baixa).
        beta: custo por casa de distância à janela da mão esquerda.
        gamma: custo de abertura da fôrma (presas em mais de 4 casas).
        delta: custo por casa de deslocamento da posição entre ataques.
    """

    alpha: float = 1.0
    beta: float = 3.0
    gamma: float = 5.0
    delta: float = 0.5


#: Pesos a priori: α=1, β=3, γ=5, δ=0,5 (fixados antes de medir).
PESOS_PRIORI = Pesos()


@dataclasses.dataclass(frozen=True)
class Nota:
    """Uma nota do produto com tempo: corda e casa da tablatura (gabarito).

    Attributes:
        indice: posição da nota na lista filtrada do vídeo.
        t: instante ``t_ini``, em segundos.
        corda: corda da tablatura do produto (1 a 6).
        casa: casa da tablatura do produto (0 a 19).
    """

    indice: int
    t: float
    corda: int
    casa: int


@dataclasses.dataclass(frozen=True)
class Ataque:
    """Notas que começam no mesmo instante.

    Attributes:
        t: instante do ataque (``t_ini`` da primeira nota).
        notas: notas do ataque, na ordem em que aparecem no produto.
    """

    t: float
    notas: tuple[Nota, ...]


@dataclasses.dataclass
class VideoPreparado:
    """Um vídeo pronto para decodificar e avaliar.

    Attributes:
        nome: nome curto do vídeo (``retrato``, ``noturno``...).
        notas: notas com tempo, do produto (gabarito).
        ataques: ataques em ordem de tempo.
        combos: combinações possíveis por ataque (a ordem é a das notas do ataque).
        sem_combo_valida: ataques sem combinação sem repetir corda.
        janelas_d2: janela da câmera por ataque e nota (``None`` onde não há).
        janelas_d3: janela de vizinhos por ataque e nota.
        cobertura: contagens da câmera e da janela D2.
    """

    nome: str
    notas: list[Nota]
    ataques: list[Ataque]
    combos: list[list[Combo]]
    sem_combo_valida: int
    janelas_d2: list[list[Janela]]
    janelas_d3: list[list[Janela]]
    cobertura: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class Referencia:
    """Geometria do braço do gabarito do dono, para projetar pontos de uma mão.

    Attributes:
        geo: eixo e trastes do quadro (``montar_geometria``).
        params: ajuste projetivo de piso sobre todos os trastes clicados.
        corda1: dois pontos da corda 1 no quadro do gabarito.
        corda6: dois pontos da corda 6 no quadro do gabarito.
        caixa: ``(x0, y0, x1, y1)`` da região do braço, no quadro do gabarito.
        tempo: segundo do quadro do gabarito no vídeo.
    """

    geo: Geometria
    params: np.ndarray
    corda1: np.ndarray
    corda6: np.ndarray
    caixa: tuple[int, int, int, int]
    tempo: float


# ---------------------------------------------------------------------------------
# Altura, candidatos e ataques (funções puras)
# ---------------------------------------------------------------------------------


def altura_midi(corda: int, casa: int) -> int:
    """Altura MIDI de uma nota na afinação padrão.

    Args:
        corda: corda (1 é a mais aguda, 6 a mais grave).
        casa: casa (0 é a corda solta).

    Returns:
        Número MIDI da nota.
    """
    return AFINACAO_MIDI[corda] + casa


def candidatos_da_altura(midi: int) -> list[tuple[int, int]]:
    """Cordas e casas em que a altura existe, com casa de 0 a ``CASA_MAX``.

    Args:
        midi: altura MIDI.

    Returns:
        Pares ``(corda, casa)``, da corda 1 para a 6.
    """
    saida = []
    for corda in sorted(AFINACAO_MIDI):
        casa = midi - AFINACAO_MIDI[corda]
        if 0 <= casa <= CASA_MAX:
            saida.append((corda, casa))
    return saida


def agrupar_ataques(
    notas: list[Nota], tolerancia: float = TOLERANCIA_ATAQUE_S
) -> list[Ataque]:
    """Agrupa as notas em ataques pelo instante de início.

    Uma nota entra no ataque corrente se começa até ``tolerancia`` segundos depois da
    primeira nota dele.

    Args:
        notas: notas com tempo.
        tolerancia: tolerância, em segundos.

    Returns:
        Ataques em ordem de tempo; cada um com as notas na ordem do produto.
    """
    grupos: list[list[Nota]] = []
    for nota in sorted(notas, key=lambda n: (n.t, n.indice)):
        if grupos and nota.t - grupos[-1][0].t <= tolerancia:
            grupos[-1].append(nota)
        else:
            grupos.append([nota])
    return [Ataque(t=g[0].t, notas=tuple(g)) for g in grupos]


def _encaixar(
    opcoes: list[list[tuple[int, int]]],
    i: int,
    usadas: set[int],
    atual: list[tuple[int, int]],
    saida: list[Combo],
) -> None:
    """Enumera, por recursão, as combinações sem corda repetida.

    Args:
        opcoes: candidatos de cada nota do ataque.
        i: índice da nota que está sendo escolhida.
        usadas: cordas já usadas nesta combinação.
        atual: escolhas feitas até agora (pilha).
        saida: lista onde as combinações completas são acumuladas.
    """
    if i == len(opcoes):
        saida.append(tuple(atual))
        return
    for corda, casa in opcoes[i]:
        if corda in usadas:
            continue
        usadas.add(corda)
        atual.append((corda, casa))
        _encaixar(opcoes, i + 1, usadas, atual, saida)
        atual.pop()
        usadas.discard(corda)


def combinacoes_do_ataque(ataque: Ataque) -> tuple[list[Combo], bool]:
    """Combinações possíveis de um ataque, com a polifonia imposta.

    Args:
        ataque: o ataque (notas com o gabarito de altura).

    Returns:
        ``(combinacoes, valida)``. ``valida`` é ``False`` quando não há combinação sem corda
        repetida (ataque inconsistente): nesse caso a lista é o produto sem a restrição.
    """
    opcoes = [candidatos_da_altura(altura_midi(n.corda, n.casa)) for n in ataque.notas]
    saida: list[Combo] = []
    _encaixar(opcoes, 0, set(), [], saida)
    if saida:
        return saida, True
    return list(itertools.product(*opcoes)), False


def posicao_da_combinacao(combo: Combo) -> int | None:
    """Posição de um ataque: a menor casa presa (``None`` se só há cordas soltas).

    Args:
        combo: combinação do ataque, ``(corda, casa)`` por nota.

    Returns:
        A menor casa maior que zero, ou ``None``.
    """
    presas = [casa for _, casa in combo if casa > 0]
    return min(presas) if presas else None


def distancia_a_janela(casa: float, janela: tuple[float, float]) -> float:
    """Distância de uma casa até a janela (zero dentro dela).

    Args:
        casa: casa da nota.
        janela: ``(baixa, alta)``.

    Returns:
        Quantas casas faltam para entrar na janela (0 se já está dentro).
    """
    baixa, alta = janela
    if casa < baixa:
        return baixa - casa
    if casa > alta:
        return casa - alta
    return 0.0


def custo_combinacao(combo: Combo, janelas: list[Janela], pesos: Pesos) -> float:
    """Custo de um ataque numa combinação.

    Soma ``α·casa`` e ``β·dist(casa, janela)`` sobre as notas presas. Corda solta custa zero
    (bordões e campanellas), com a mão onde estiver. Abertura acima de 4 casas custa ``γ``.

    Args:
        combo: combinação do ataque.
        janelas: janela de cada nota do ataque (``None`` quando não há).
        pesos: pesos do decodificador.

    Returns:
        O custo do ataque nessa combinação.
    """
    custo = 0.0
    casas: list[int] = []
    for (_, casa), janela in zip(combo, janelas, strict=True):
        if casa == 0:
            continue
        casas.append(casa)
        custo += pesos.alpha * casa
        if janela is not None:
            custo += pesos.beta * distancia_a_janela(casa, janela)
    if casas and max(casas) - min(casas) > ABERTURA_MAX:
        custo += pesos.gamma
    return custo


def decodificar(
    combos_por_ataque: list[list[Combo]],
    janelas_por_ataque: list[list[Janela]],
    pesos: Pesos,
) -> list[Combo]:
    """Viterbi sobre os ataques: a combinação de menor custo total.

    O estado de um ataque é ``(combinação, posição)``. A posição é a do próprio ataque
    quando ele tem nota presa, ou a carregada do ataque anterior quando só tem cordas
    soltas. A transição custa ``δ·|Δ posição|`` entre posições definidas.

    Args:
        combos_por_ataque: combinações possíveis de cada ataque, em ordem de tempo.
        janelas_por_ataque: janelas de cada nota de cada ataque.
        pesos: pesos do decodificador.

    Returns:
        Uma combinação por ataque, na mesma ordem.
    """
    if not combos_por_ataque:
        return []
    custos: dict[tuple[int, int | None], float] = {}
    retro: list[dict[tuple[int, int | None], tuple[int, int | None] | None]] = []
    for k, combos in enumerate(combos_por_ataque):
        novos: dict[tuple[int, int | None], float] = {}
        bp: dict[tuple[int, int | None], tuple[int, int | None] | None] = {}
        for i, combo in enumerate(combos):
            p_c = posicao_da_combinacao(combo)
            base = custo_combinacao(combo, janelas_por_ataque[k], pesos)
            if k == 0:
                novos[(i, p_c)] = base
                bp[(i, p_c)] = None
                continue
            for (j, p_prev), acumulado in custos.items():
                trans = 0.0
                if p_c is not None and p_prev is not None:
                    trans = pesos.delta * abs(p_c - p_prev)
                p_novo = p_c if p_c is not None else p_prev
                total = acumulado + trans + base
                chave = (i, p_novo)
                if chave not in novos or total < novos[chave]:
                    novos[chave] = total
                    bp[chave] = (j, p_prev)
        custos = novos
        retro.append(bp)
    chave: tuple[int, int | None] | None = min(custos, key=custos.__getitem__)
    escolha: list[Combo] = [()] * len(combos_por_ataque)
    for k in range(len(combos_por_ataque) - 1, -1, -1):
        assert chave is not None
        escolha[k] = combos_por_ataque[k][chave[0]]
        chave = retro[k][chave]
    return escolha


def casa_mais_baixa(ataque: Ataque) -> Combo:
    """Degrau D0: cada nota na casa mais baixa em que a altura existe.

    Não usa polifonia nem continuidade.

    Args:
        ataque: o ataque.

    Returns:
        Uma combinação ``(corda, casa)`` por nota, na ordem do ataque.
    """
    return tuple(
        min(candidatos_da_altura(altura_midi(n.corda, n.casa)), key=lambda c: c[1])
        for n in ataque.notas
    )


def janelas_de_vizinhos(
    ataques: list[Ataque],
    raio_s: float = RAIO_VIZINHOS_S,
    meia: float = MEIA_JANELA_D3,
) -> dict[int, Janela]:
    """Degrau D3: janela de cada nota pela mediana das casas presas dos vizinhos.

    Os vizinhos são as notas presas a até ``raio_s`` segundos, de outros ataques. A própria
    nota e as do mesmo ataque ficam de fora, e cordas soltas não entram na mediana. A casa
    da própria nota não influencia a janela.

    Args:
        ataques: ataques do vídeo, em ordem de tempo.
        raio_s: raio, em segundos, da busca de vizinhos.
        meia: meia largura da janela, em casas.

    Returns:
        Janela ``(mediana - meia, mediana + meia)`` por índice de nota; ``None`` quando não
        há vizinho presa.
    """
    marcados = [(k, n) for k, a in enumerate(ataques) for n in a.notas]
    saida: dict[int, Janela] = {}
    for k, nota in marcados:
        vizinhas = [
            m.casa
            for km, m in marcados
            if km != k and m.casa > 0 and abs(m.t - nota.t) <= raio_s
        ]
        if not vizinhas:
            saida[nota.indice] = None
            continue
        mediana = float(statistics.median(vizinhas))
        saida[nota.indice] = (mediana - meia, mediana + meia)
    return saida


# ---------------------------------------------------------------------------------
# Geometria do braço do gabarito e câmera (cv2 e numpy)
# ---------------------------------------------------------------------------------


def inverter_casa(params: np.ndarray, t: float) -> float:
    """Casa contínua de uma posição do eixo, pela inversa do modelo projetivo.

    O modelo é ``t = (a·s + b) / (c·s + 1)`` com ``s = 1 - 2^(-n/12)``. Invertido:
    ``s = (b - t) / (t·c - a)`` e ``n = -12·log2(1 - s)``.

    Args:
        params: ``[a, b, c]`` de ``ajustar(..., "proj")``.
        t: posição ao longo do eixo, em px a partir da âncora.

    Returns:
        A casa contínua, ou NaN fora do domínio do modelo.
    """
    a, b, c = (float(x) for x in params)
    denominador = t * c - a
    if denominador == 0.0:
        return math.nan
    s = (b - t) / denominador
    if not s < 1.0:
        return math.nan
    return -12.0 * math.log2(1.0 - s)


def projecao(
    ref: Referencia, ponto: list[float], deslocamento: tuple[float, float]
) -> tuple[float, float]:
    """Projeta um ponto do quadro no eixo do gabarito.

    Args:
        ref: geometria do braço do gabarito.
        ponto: ``[x, y]`` no quadro do vídeo.
        deslocamento: ``(dx, dy)`` da câmera; o ponto no gabarito é ``ponto - deslocamento``.

    Returns:
        ``(t, perp)``: posição ao longo do eixo e distância perpendicular, em px.
    """
    q = np.asarray(ponto, dtype=float) - np.asarray(deslocamento, dtype=float)
    rel = q - ref.geo.origem
    u = ref.geo.u
    nrm = np.array([-u[1], u[0]])
    return float(rel @ u), float(rel @ nrm)


def casa_do_ponto(
    ref: Referencia, ponto: list[float], deslocamento: tuple[float, float]
) -> float:
    """Casa contínua de um ponto do quadro, pelo eixo do gabarito.

    Args:
        ref: geometria do braço do gabarito.
        ponto: ``[x, y]`` no quadro do vídeo.
        deslocamento: ``(dx, dy)`` da câmera.

    Returns:
        A casa contínua, ou NaN fora do domínio.
    """
    t, _ = projecao(ref, ponto, deslocamento)
    return inverter_casa(ref.params, t)


def _perpendicular_da_corda(
    corda: np.ndarray, ref: Referencia, t: float
) -> float | None:
    """Distância perpendicular, no eixo, em que a corda cruza a posição ``t``.

    Args:
        corda: dois pontos da corda, no quadro do gabarito.
        ref: geometria do braço do gabarito.
        t: posição ao longo do eixo, em px.

    Returns:
        O deslocamento perpendicular da corda, ou ``None`` se a corda é paralela ao eixo.
    """
    a, b = corda
    d = b - a
    u = ref.geo.u
    du = float(d @ u)
    if abs(du) < 1e-9:
        return None
    lam = (t - float((a - ref.geo.origem) @ u)) / du
    x = a + lam * d
    nrm = np.array([-u[1], u[0]])
    return float((x - ref.geo.origem) @ nrm)


def faixa_do_braco(ref: Referencia, t: float) -> tuple[float, float] | None:
    """Faixa perpendicular do braço em ``t``: entre as cordas 1 e 6, com uma corda de folga.

    Args:
        ref: geometria do braço do gabarito.
        t: posição ao longo do eixo, em px.

    Returns:
        ``(baixa, alta)`` em px, ou ``None`` se as cordas não se definem em ``t``.
    """
    p1 = _perpendicular_da_corda(ref.corda1, ref, t)
    p6 = _perpendicular_da_corda(ref.corda6, ref, t)
    if p1 is None or p6 is None:
        return None
    folga = abs(p1 - p6) / 5.0
    return min(p1, p6) - folga, max(p1, p6) + folga


def janela_da_mao_esquerda(
    maos: list[dict[str, Any]],
    ref: Referencia,
    deslocamento: tuple[float, float],
) -> Janela:
    """Janela de casas da mão esquerda, pelas pontas 8, 12, 16 e 20.

    A mão escolhida é a de ``lado == "esquerda"`` com mais pontas (score >= 0,3) sobre a faixa
    do braço. Precisa de ao menos ``MIN_PONTOS_NO_BRACO`` pontas sobre o braço.

    Args:
        maos: mãos do instante (``lado``, ``scores`` e ``pts``, como no JSON das pontas).
        ref: geometria do braço do gabarito.
        deslocamento: ``(dx, dy)`` da câmera.

    Returns:
        ``(floor(min) - 1, ceil(max) + 1)`` das casas projetadas, ou ``None``.
    """
    melhor: dict[str, Any] | None = None
    melhor_n = 0
    for mao in maos:
        if mao.get("lado") != "esquerda":
            continue
        scores = mao.get("scores") or []
        pts = mao.get("pts") or []
        n_sobre = 0
        for i, ponto in enumerate(pts):
            if not _ponta_valida(ponto, scores, i):
                continue
            t, perp = projecao(ref, ponto, deslocamento)
            casa = inverter_casa(ref.params, t)
            faixa = faixa_do_braco(ref, t)
            if faixa is None or not math.isfinite(casa):
                continue
            if faixa[0] <= perp <= faixa[1] and -1 <= casa <= CASA_MAX + 2:
                n_sobre += 1
        if n_sobre > melhor_n:
            melhor, melhor_n = mao, n_sobre
    if melhor is None or melhor_n < MIN_PONTOS_NO_BRACO:
        return None
    casas = []
    for i in PONTAS_JANELA:
        if _ponta_valida(melhor["pts"][i], melhor["scores"], i):
            casa = casa_do_ponto(ref, melhor["pts"][i], deslocamento)
            if math.isfinite(casa):
                casas.append(casa)
    if not casas:
        return None
    return float(math.floor(min(casas)) - 1), float(math.ceil(max(casas)) + 1)


def _ponta_valida(ponto: Any, scores: list[Any], i: int) -> bool:
    """Se a ponta ``i`` existe e tem score mínimo.

    Args:
        ponto: ``[x, y]`` ou ``None``.
        scores: score de cada ponto (pode estar vazio).
        i: índice da ponta.

    Returns:
        ``True`` se o ponto tem coordenadas e score >= ``SCORE_MIN``.
    """
    if ponto is None or ponto[0] is None or ponto[1] is None:
        return False
    if i >= len(scores) or scores[i] is None:
        return False
    return float(scores[i]) >= SCORE_MIN


def casar_camera(
    quadro: np.ndarray,
    referencia: np.ndarray,
    caixa: tuple[int, int, int, int],
) -> tuple[float, tuple[float, float]]:
    """Casa a região do braço do gabarito com o quadro do vídeo (translação).

    O recorte do gabarito é procurado no quadro, dentro de ``BUSCA_CAMERA_PX`` px da posição
    de origem. O deslocamento devolvido é o da câmera: um ponto ``p`` do quadro corresponde
    a ``p - deslocamento`` no gabarito.

    Args:
        quadro: quadro do vídeo, BGR.
        referencia: quadro do gabarito, BGR (mesma resolução do vídeo).
        caixa: ``(x0, y0, x1, y1)`` da região do braço no quadro do gabarito.

    Returns:
        ``(score, (dx, dy))``: NCC do melhor casamento e o deslocamento.
    """
    x0, y0, x1, y1 = caixa
    cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
    modelo = cv2.cvtColor(referencia, cv2.COLOR_BGR2GRAY)[y0:y1, x0:x1]
    altura, largura = cinza.shape
    sx0, sy0 = max(x0 - BUSCA_CAMERA_PX, 0), max(y0 - BUSCA_CAMERA_PX, 0)
    sx1, sy1 = min(x1 + BUSCA_CAMERA_PX, largura), min(y1 + BUSCA_CAMERA_PX, altura)
    regiao = cinza[sy0:sy1, sx0:sx1]
    if modelo.shape[0] > regiao.shape[0] or modelo.shape[1] > regiao.shape[1]:
        return -1.0, (0.0, 0.0)
    resultado = cv2.matchTemplate(regiao, modelo, cv2.TM_CCOEFF_NORMED)
    _, valor, _, (lx, ly) = cv2.minMaxLoc(resultado)
    return float(valor), (float(sx0 + lx - x0), float(sy0 + ly - y0))


# ---------------------------------------------------------------------------------
# Carregamento e preparo dos vídeos
# ---------------------------------------------------------------------------------


def referencia_do_braco(id_quadro: str) -> Referencia:
    """Carrega a geometria do braço de um quadro do gabarito do dono.

    Args:
        id_quadro: id do quadro (``q02``, ``q16``, ``q21`` ou ``q23``).

    Returns:
        A referência pronta para projeção e casamento.

    Raises:
        ValueError: se o quadro não tem a geometria completa do braço.
    """
    registro = json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))["quadros"][
        id_quadro
    ]
    geo = montar_geometria(id_quadro, registro)
    if geo is None:
        raise ValueError(f"quadro {id_quadro} sem geometria completa do braço")
    pontos = [
        (geo.ancora_n, 0.0),
        *((tr.numero, tr.t) for tr in geo.trastes if tr.numero != geo.ancora_n),
    ]
    params = ajustar(pontos, "proj")
    corda1 = np.asarray(registro["corda1"], dtype=float)
    corda6 = np.asarray(registro["corda6"], dtype=float)
    todos = [*registro["corda1"], *registro["corda6"], *registro["trastes"]]
    if isinstance(registro.get("nut"), list):
        todos.append(registro["nut"])
    xs = [p[0] for p in todos]
    ys = [p[1] for p in todos]
    caixa = (
        int(min(xs)) - MARGEM_CAIXA_PX,
        int(min(ys)) - MARGEM_CAIXA_PX,
        int(max(xs)) + MARGEM_CAIXA_PX,
        int(max(ys)) + MARGEM_CAIXA_PX,
    )
    indice = json.loads((MAOS_M3B / "indice.json").read_text(encoding="utf-8"))
    tempo = next(q["t"] for q in indice["quadros"] if q["id"] == id_quadro)
    return Referencia(geo, params, corda1, corda6, caixa, float(tempo))


def quadro_bgr(video: Path, instante: float) -> np.ndarray:
    """Um quadro do vídeo no instante dado, em BGR, lido pelo ffmpeg.

    Mesmo comando de ``tab.maos_visao_dedos.quadro_bgr``, sem importar o detector de mãos
    (que precisa do rtmlib, só presente na imagem de GPU).

    Args:
        video: arquivo de vídeo do acervo.
        instante: segundo do quadro.

    Returns:
        Quadro ``uint8`` em BGR.

    Raises:
        RuntimeError: se o ffmpeg não devolve um quadro decodificável.
    """
    bruto = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{max(instante, 0.0):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    quadro = cv2.imdecode(np.frombuffer(bruto, dtype=np.uint8), cv2.IMREAD_COLOR)
    if quadro is None:
        raise RuntimeError(f"quadro não decodificado em t={instante:.3f}")
    return quadro


def carregar_notas(produto: Path) -> tuple[list[Nota], int]:
    """Notas com tempo do produto, com corda e casa válidas.

    Args:
        produto: JSON do produto (lista ``notas``).

    Returns:
        ``(notas, fora)``: as notas e quantas com tempo foram descartadas por corda ou casa
        fora do intervalo.
    """
    brutas = json.loads(produto.read_text(encoding="utf-8"))["notas"]
    notas: list[Nota] = []
    fora = 0
    for n in notas_com_tempo(brutas):
        corda, casa = int(n["corda"]), int(n["casa"])
        if corda not in AFINACAO_MIDI or not 0 <= casa <= CASA_MAX:
            fora += 1
            continue
        notas.append(Nota(len(notas), float(n["t_ini"]), corda, casa))
    return notas, fora


def carregar_pontas(caminho: Path) -> list[tuple[float, list[dict[str, Any]]]]:
    """Mãos de cada instante das pontas (``tab.maos_pontas_notas``), em ordem de tempo.

    Args:
        caminho: JSON de pontas.

    Returns:
        Lista de ``(t_ini, maos)``.
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))["instantes"]
    return sorted(
        ((float(r["t_ini"]), r["maos"]) for r in dados), key=lambda par: par[0]
    )


def maos_no_instante(
    pontas: list[tuple[float, list[dict[str, Any]]]], t: float, tolerancia: float
) -> list[dict[str, Any]] | None:
    """Mãos do instante de pontas mais próximo de ``t``, dentro da tolerância.

    Args:
        pontas: saída de ``carregar_pontas``.
        t: instante do ataque.
        tolerancia: tolerância, em segundos.

    Returns:
        A lista de mãos, ou ``None`` se não há instante dentro da tolerância.
    """
    if not pontas:
        return None
    t_mais, maos = min(pontas, key=lambda par: abs(par[0] - t))
    return maos if abs(t_mais - t) <= tolerancia else None


def camera_por_instante(
    video: Path,
    ref: Referencia,
    instantes: list[float],
    cache: Path,
) -> dict[str, tuple[float, float, float]]:
    """Score e deslocamento da câmera em cada instante, com cache em JSON.

    Args:
        video: vídeo do acervo.
        ref: referência do braço (tempo e caixa do quadro do gabarito).
        instantes: instantes a conferir.
        cache: arquivo JSON de cache (criado se faltar).

    Returns:
        ``chave(t)`` -> ``(score, dx, dy)``, com ``chave = f"{t:.3f}"``.
    """
    saida: dict[str, tuple[float, float, float]] = {}
    if cache.exists():
        saida = {
            k: tuple(v)
            for k, v in json.loads(cache.read_text(encoding="utf-8")).items()
        }
    pendentes = sorted({round(t, 3) for t in instantes} - {float(k) for k in saida})
    if not pendentes:
        return saida
    referencia = quadro_bgr(video, ref.tempo)

    def conferir(t: float) -> tuple[float, tuple[float, float, float]]:
        quadro = quadro_bgr(video, t)
        score, (dx, dy) = casar_camera(quadro, referencia, ref.caixa)
        return t, (score, dx, dy)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for t, valor in pool.map(conferir, pendentes):
            saida[f"{t:.3f}"] = valor
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(saida, indent=0), encoding="utf-8")
    return saida


def preparar_video(
    nome: str,
    entrada: dict[str, Any],
    id_quadro: str,
    pasta_cache: Path,
) -> VideoPreparado:
    """Monta um vídeo: notas, ataques, combinações, janelas D2 e D3 e a cobertura.

    Args:
        nome: nome curto do vídeo.
        entrada: entrada de ``VIDEOS`` (``arquivo``, ``produto``, ``pontas``).
        id_quadro: quadro do gabarito do braço para este vídeo.
        pasta_cache: pasta onde fica o cache da câmera.

    Returns:
        O vídeo pronto para decodificar.
    """
    video = acervo() / entrada["arquivo"]
    notas, fora = carregar_notas(entrada["produto"])
    ataques = agrupar_ataques(notas)
    combos_e_validade = [combinacoes_do_ataque(a) for a in ataques]
    combos = [c for c, _ in combos_e_validade]
    sem_valida = sum(1 for _, valida in combos_e_validade if not valida)

    ref = referencia_do_braco(id_quadro)
    pontas = carregar_pontas(entrada["pontas"])
    tem_presa = [any(n.casa > 0 for n in a.notas) for a in ataques]
    maos_por_ataque = [
        maos_no_instante(pontas, a.t, TOLERANCIA_ATAQUE_S) for a in ataques
    ]
    instantes_camera = [
        a.t
        for a, presa, maos in zip(ataques, tem_presa, maos_por_ataque, strict=True)
        if presa and maos is not None
    ]
    cam = camera_por_instante(
        video, ref, instantes_camera, pasta_cache / f"camera_{nome}.json"
    )

    janelas_d2: list[list[Janela]] = []
    scores: list[float] = []
    n_com_camera = 0
    n_com_janela = 0
    for a, presa, maos in zip(ataques, tem_presa, maos_por_ataque, strict=True):
        janela: Janela = None
        if presa and maos is not None:
            score, dx, dy = cam[f"{a.t:.3f}"]
            scores.append(score)
            if score >= LIMIAR_CAMERA:
                n_com_camera += 1
                janela = janela_da_mao_esquerda(maos, ref, (dx, dy))
                if janela is not None:
                    n_com_janela += 1
        janelas_d2.append([janela] * len(a.notas))

    n_presa = sum(tem_presa)
    cobertura: dict[str, Any] = {
        "notas_com_tempo": len(notas),
        "notas_descartadas_fora_do_dominio": fora,
        "ataques": len(ataques),
        "ataques_com_presa": n_presa,
        "ataques_com_pontas": len(instantes_camera),
        "ataques_camera_casa": n_com_camera,
        "ataques_com_janela_camera": n_com_janela,
        "fracao_com_janela_camera": n_com_janela / n_presa if n_presa else 0.0,
        "scores_camera": {
            "minimo": min(scores) if scores else None,
            "mediana": float(statistics.median(scores)) if scores else None,
            "maximo": max(scores) if scores else None,
            "acima_0_6": sum(s >= 0.6 for s in scores),
            "acima_0_7": sum(s >= 0.7 for s in scores),
            "acima_0_8": sum(s >= LIMIAR_CAMERA for s in scores),
            "acima_0_9": sum(s >= 0.9 for s in scores),
        },
        "limiar_camera": LIMIAR_CAMERA,
        "quadro_do_braco": id_quadro,
        "ataques_sem_combinacao_valida": sem_valida,
    }
    janelas_d3_por_nota = janelas_de_vizinhos(ataques)
    janelas_d3 = [[janelas_d3_por_nota[n.indice] for n in a.notas] for a in ataques]
    return VideoPreparado(
        nome=nome,
        notas=notas,
        ataques=ataques,
        combos=combos,
        sem_combo_valida=sem_valida,
        janelas_d2=janelas_d2,
        janelas_d3=janelas_d3,
        cobertura=cobertura,
    )


# ---------------------------------------------------------------------------------
# Decodificar e medir
# ---------------------------------------------------------------------------------


def decodar(video: VideoPreparado, degrau: str, pesos: Pesos) -> list[Combo]:
    """Decodifica o vídeo num degrau.

    Args:
        video: vídeo preparado.
        degrau: ``"D0"``, ``"D1"``, ``"D2"`` ou ``"D3"``.
        pesos: pesos (o ``beta`` é zerado em D1).

    Returns:
        Uma combinação por ataque.

    Raises:
        ValueError: se o degrau não existe.
    """
    if degrau == "D0":
        return [casa_mais_baixa(a) for a in video.ataques]
    if degrau == "D1":
        sem_janela = [[None] * len(a.notas) for a in video.ataques]
        return decodificar(
            video.combos, sem_janela, dataclasses.replace(pesos, beta=0.0)
        )
    if degrau == "D2":
        return decodificar(video.combos, video.janelas_d2, pesos)
    if degrau == "D3":
        return decodificar(video.combos, video.janelas_d3, pesos)
    raise ValueError(f"degrau desconhecido: {degrau}")


def _janela_de_degrau(video: VideoPreparado, degrau: str) -> list[list[Janela]]:
    """Janelas por ataque e nota para o degrau (D0 e D1 não têm janela).

    Args:
        video: vídeo preparado.
        degrau: ``"D0"``, ``"D1"``, ``"D2"`` ou ``"D3"``.

    Returns:
        Lista de janelas, uma por nota de cada ataque.
    """
    if degrau == "D2":
        return video.janelas_d2
    if degrau == "D3":
        return video.janelas_d3
    return [[None] * len(a.notas) for a in video.ataques]


def pontuar(video: VideoPreparado, escolha: list[Combo], degrau: str) -> dict[str, int]:
    """Contagens de acerto e de erro de um degrau sobre um vídeo.

    Erros de nota presa são separados pela janela usada: sem janela, com a janela errada
    (a casa real fica fora dela) ou com a janela certa (a erro está dentro da região).

    Args:
        video: vídeo preparado.
        escolha: combinação escolhida por ataque.
        degrau: degrau medido (define a janela do erro).

    Returns:
        Contagens por nome (``n``, ``acertos``, ``amb_n``, ``amb_acertos``...).
    """
    janelas = _janela_de_degrau(video, degrau)
    cont = {
        "n": 0,
        "acertos": 0,
        "amb_n": 0,
        "amb_acertos": 0,
        "pres_n": 0,
        "pres_acertos": 0,
        "sol_n": 0,
        "sol_acertos": 0,
        "erros": 0,
        "erro_janela_errada": 0,
        "erro_janela_certa": 0,
        "erro_sem_janela": 0,
        "erro_solta": 0,
    }
    for a, combo, janela_a in zip(video.ataques, escolha, janelas, strict=True):
        for nota, (corda_pred, _), janela in zip(a.notas, combo, janela_a, strict=True):
            acertou = corda_pred == nota.corda
            cont["n"] += 1
            cont["acertos"] += acertou
            if len(candidatos_da_altura(altura_midi(nota.corda, nota.casa))) > 1:
                cont["amb_n"] += 1
                cont["amb_acertos"] += acertou
            if nota.casa > 0:
                cont["pres_n"] += 1
                cont["pres_acertos"] += acertou
            else:
                cont["sol_n"] += 1
                cont["sol_acertos"] += acertou
            if acertou:
                continue
            cont["erros"] += 1
            if nota.casa == 0:
                cont["erro_solta"] += 1
            elif janela is None:
                cont["erro_sem_janela"] += 1
            elif janela[0] <= nota.casa <= janela[1]:
                cont["erro_janela_certa"] += 1
            else:
                cont["erro_janela_errada"] += 1
    return cont


def somar(contagens: list[dict[str, int]]) -> dict[str, int]:
    """Soma contagens de vários vídeos.

    Args:
        contagens: uma por vídeo.

    Returns:
        A soma por chave.
    """
    saida: dict[str, int] = {}
    for c in contagens:
        for chave, valor in c.items():
            saida[chave] = saida.get(chave, 0) + valor
    return saida


def taxas(cont: dict[str, int]) -> dict[str, float]:
    """Taxas de acerto a partir das contagens (0 quando o denominador é zero).

    Args:
        cont: contagens de ``pontuar``.

    Returns:
        ``acc``, ``acc_amb``, ``acc_presa``, ``acc_solta``.
    """

    def razao(acertos: int, total: int) -> float:
        return acertos / total if total else 0.0

    return {
        "acc": razao(cont["acertos"], cont["n"]),
        "acc_amb": razao(cont["amb_acertos"], cont["amb_n"]),
        "acc_presa": razao(cont["pres_acertos"], cont["pres_n"]),
        "acc_solta": razao(cont["sol_acertos"], cont["sol_n"]),
    }


def grade_de_pesos(degrau: str) -> list[Pesos]:
    """Pesos da grade de um degrau. γ fica em 5; D1 não usa β.

    Args:
        degrau: ``"D1"``, ``"D2"`` ou ``"D3"``.

    Returns:
        Lista de pesos, na ordem da grade.
    """
    if degrau == "D1":
        return [
            Pesos(alpha=a, beta=0.0, gamma=5.0, delta=d)
            for a in GRADE_ALFA
            for d in GRADE_DELTA
        ]
    return [
        Pesos(alpha=a, beta=b, gamma=5.0, delta=d)
        for a in GRADE_ALFA
        for b in GRADE_BETA
        for d in GRADE_DELTA
    ]


def chave_pesos(pesos: Pesos) -> str:
    """Nome curto de um conjunto de pesos.

    Args:
        pesos: pesos.

    Returns:
        ``"a=..,b=..,d=.."``.
    """
    return f"a={pesos.alpha},b={pesos.beta},d={pesos.delta}"


def leave_one_out(
    videos: list[VideoPreparado],
    tabela: dict[str, dict[str, dict[str, dict[str, int]]]],
    degrau: str,
) -> dict[str, dict[str, Any]]:
    """Para cada vídeo: escolhe os pesos nos outros três e mede no de fora.

    A escolha maximiza a acurácia de corda agregada dos três de treino (empate: primeiro da
    grade). ``tabela`` é ``chave_pesos -> nome do vídeo -> contagens``.

    Args:
        videos: os quatro vídeos.
        tabela: contagens de cada configuração da grade, por vídeo.
        degrau: ``"D1"``, ``"D2"`` ou ``"D3"``.

    Returns:
        Por vídeo de fora: pesos escolhidos, acurácia de treino e de teste.
    """
    saida: dict[str, dict[str, Any]] = {}
    for alvo in videos:
        treino = [v.nome for v in videos if v.nome != alvo.nome]
        melhor_chave: str | None = None
        melhor_acc = -1.0
        for pesos in grade_de_pesos(degrau):
            chave = chave_pesos(pesos)
            agregado = somar([tabela[chave][nome] for nome in treino])
            acc = agregado["acertos"] / agregado["n"]
            if acc > melhor_acc:
                melhor_acc, melhor_chave = acc, chave
        assert melhor_chave is not None
        teste = tabela[melhor_chave][alvo.nome]
        saida[alvo.nome] = {
            "pesos": melhor_chave,
            "acc_treino": melhor_acc,
            "acc_teste": teste["acertos"] / teste["n"],
            "contagens_teste": teste,
        }
    return saida


def main() -> None:
    """Roda os degraus nos quatro vídeos e grava o relatório em ``MAOS_M8``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--saida", type=Path, default=MAOS_M8 / "corda_sem_direita.json"
    )
    args = parser.parse_args()

    videos = [
        preparar_video(nome, entrada, QUADRO_DO_BRACO[nome], MAOS_M8)
        for nome, entrada in zip(NOMES, VIDEOS, strict=True)
    ]

    priori: dict[str, dict[str, Any]] = {}
    for v in videos:
        priori[v.nome] = {
            d: pontuar(v, decodar(v, d, PESOS_PRIORI), d) for d in DEGRAUS
        }

    agregado_priori = {d: somar([priori[v.nome][d] for v in videos]) for d in DEGRAUS}

    tabela_loo: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
    loo: dict[str, dict[str, Any]] = {}
    for degrau in ("D1", "D2", "D3"):
        tabela_loo[degrau] = {}
        for pesos in grade_de_pesos(degrau):
            chave = chave_pesos(pesos)
            tabela_loo[degrau][chave] = {
                v.nome: pontuar(v, decodar(v, degrau, pesos), degrau) for v in videos
            }
        loo[degrau] = leave_one_out(videos, tabela_loo[degrau], degrau)

    relatorio = {
        "formato": 1,
        "pesos_priori": dataclasses.asdict(PESOS_PRIORI),
        "grade": {
            "alpha": list(GRADE_ALFA),
            "beta": list(GRADE_BETA),
            "delta": list(GRADE_DELTA),
            "gamma": 5.0,
        },
        "videos": {
            v.nome: {
                "cobertura": v.cobertura,
                "priori": {
                    d: {**priori[v.nome][d], **taxas(priori[v.nome][d])}
                    for d in DEGRAUS
                },
            }
            for v in videos
        },
        "agregado_priori": {
            d: {**agregado_priori[d], **taxas(agregado_priori[d])} for d in DEGRAUS
        },
        "leave_one_out": loo,
        "grade_contagens": {
            degrau: {
                chave: {nome: taxas(c) | c for nome, c in por_video.items()}
                for chave, por_video in tabela_loo[degrau].items()
            }
            for degrau in tabela_loo
        },
    }
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for v in videos:
        print(f"== {v.nome} (quadro {v.cobertura['quadro_do_braco']})")
        for d in DEGRAUS:
            t = taxas(priori[v.nome][d])
            print(
                f"  {d}: acc {t['acc']:.3f}  amb {t['acc_amb']:.3f}  "
                f"presa {t['acc_presa']:.3f}  solta {t['acc_solta']:.3f}  "
                f"erros {priori[v.nome][d]['erros']}"
            )
        print(
            f"  cobertura janela camera: "
            f"{v.cobertura['ataques_com_janela_camera']}/"
            f"{v.cobertura['ataques_com_presa']}"
        )
    print("== agregado (pesos a priori)")
    for d in DEGRAUS:
        t = taxas(agregado_priori[d])
        print(
            f"  {d}: acc {t['acc']:.3f}  amb {t['acc_amb']:.3f}  erros {agregado_priori[d]['erros']}"
        )
    print("== deixando um vídeo de fora")
    for degrau, por_video in loo.items():
        for nome, r in por_video.items():
            print(f"  {degrau} {nome}: pesos {r['pesos']} teste {r['acc_teste']:.3f}")
    print(f"saída em {args.saida}")


if __name__ == "__main__":
    main()
