"""Pente do braço: ajuste global das cordas e dos trastes pela imagem (M3c, 1009).

A calibração pela música (rodada 1007) acerta os trastes do meio, mas comprime as
cordas e erra o nut. A correção pela imagem da 1007 procurava CADA corda e CADA
traste numa janela pequena: quando o erro passava da janela, a linha pulava para a
vizinha. Aqui o PENTE inteiro é ajustado de uma vez, com poucos parâmetros e busca
global:

- cordas: as 6 juntas igualmente espaçadas, ``v'_j = a + b (j - 1) / 5``, em três
  bandas de casas (1-4, 5-8, 9-12), cada banda com o seu ``(a, b)``. ``a`` e ``b``
  viram funções lineares de ``u`` (ajuste aos três centros de banda);
- trastes: ``u'_n = (alfa s_n + beta) / (gama s_n + 1)`` para ``n = 0..12``, com o
  nut em ``n = 0``.

Cada parâmetro é o máximo do perfil da imagem retificada pela H da música (realce
do fundo, como em :mod:`tab.maos_linhas_braco`) nas posições previstas. Faixas e
passos são constantes deste módulo, fixados antes de medir.

Diferença para a 1007: a retificação do pente usa a janela vertical
``V0_PENTE``..``V1_PENTE``, maior que a de :func:`tab.maos_medicoes_braco.retificar`,
porque a busca das cordas vai até ``v`` de -0,5 a 2,1.

Entrada: :func:`calibrar_por_pente`. O resto são funções puras (numpy e OpenCV).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

from tab.maos.braco.braco import realcar
from tab.maos.calibrar_por_notas import (
    S_TRASTES,
    aplicar_homografia,
    diferenca_entre_h,
    v_corda,
)
from tab.maos.linhas_braco import mapa_retificacao
from tab.maos.medicoes_braco import (
    JANELA_CORDA,
    JANELA_TRASTE,
    KU,
    KV,
    MARGEM_V,
    U0,
    U1,
)
from tab.maos.refinar_braco import ajustar_pontos

#: Janela vertical (em v) da retificação do pente. A busca das cordas cobre
#: a de -0,5 a 0,5 e b até 1,6, então a janela da 1007 (-0,2 a 1,2) não serve.
V0_PENTE = -0.6
V1_PENTE = 1.6

#: Último traste do pente (``n = 0`` é o nut). Os trastes 13 e 14 não entram na busca.
ULTIMO_TRASTE = 12

#: Bandas de casas para as cordas, como pares de trastes: casas 1-4, 5-8 e 9-12.
BANDAS = ((0, 4), (4, 8), (8, 12))

#: Cordas: ``a`` (posição da corda 1, em v) e ``b`` (vão 1-6, em v; nominal 1,0).
FAIXA_A = (-0.5, 0.5)
FAIXA_B = (0.6, 1.6)
PASSO_GROSSO_CORDA = 0.01

#: Trastes: ``alfa``, ``beta`` e ``gama`` de ``u' = (alfa s + beta) / (gama s + 1)``.
#: ``beta`` vai de -0,6 a +0,6 do primeiro passo de traste (``s_1 - s_0``).
FAIXA_ALFA = (0.85, 1.15)
FRACAO_BETA = 0.6
PASSO_PRIMEIRA_CASA = float(S_TRASTES[1] - S_TRASTES[0])
FAIXA_BETA = (-FRACAO_BETA * PASSO_PRIMEIRA_CASA, FRACAO_BETA * PASSO_PRIMEIRA_CASA)
FAIXA_GAMA = (-0.4, 0.4)
PASSO_GROSSO_ALFA = 0.005
PASSO_GROSSO_BETA = 0.001
PASSO_GROSSO_GAMA = 0.01

#: Busca fina: cobre +/- um passo grosso, com passo grosso / ``FATOR_FINO``.
FATOR_FINO = 10

#: Componentes que o pente ajusta. A diagnose roda um de cada vez.
COMPONENTES = ("cordas", "trastes")


def retificar_pente(mediana: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Retifica o braço pela H numa janela vertical que cobre a busca do pente.

    Mesma conta de :func:`tab.maos_medicoes_braco.retificar`, com a janela
    ``V0_PENTE``..``V1_PENTE`` em vez de ``V0``..``V1``.

    Args:
        mediana: quadro BGR da mediana.
        H: homografia que leva ``(u, v)`` para pixels.

    Returns:
        Imagem ``float32`` retificada, em tons de cinza.
    """
    cinza = cv2.cvtColor(mediana, cv2.COLOR_BGR2GRAY).astype(np.float32)
    M = mapa_retificacao(H, KU, KV, U0, V0_PENTE)
    tamanho = (round((U1 - U0) * KU), round((V1_PENTE - V0_PENTE) * KV))
    return cv2.warpPerspective(cinza, M, tamanho, flags=cv2.INTER_LINEAR)


def colunas_da_banda(banda: tuple[int, int]) -> tuple[int, int]:
    """Colunas da retificada que cobrem uma banda de casas.

    Args:
        banda: par de trastes ``(lo, hi)``; a banda vai de ``s_lo`` a ``s_hi``.

    Returns:
        ``(x0, x1)`` em colunas, ``x1`` exclusivo.
    """
    lo, hi = banda
    x0 = round((float(S_TRASTES[lo]) - U0) * KU)
    x1 = round((float(S_TRASTES[hi]) - U0) * KU)
    return x0, x1


def perfis_cordas(retificada: np.ndarray) -> list[np.ndarray]:
    """Perfil horizontal (linhas claras) de cada banda de casas.

    Args:
        retificada: imagem retificada (:func:`retificar_pente`).

    Returns:
        Um perfil 1D por banda de :data:`BANDAS`, em ``v`` (uma posição por linha).
    """
    realce = realcar(retificada, eixo=0, janela=JANELA_CORDA)
    perfis = []
    for banda in BANDAS:
        x0, x1 = colunas_da_banda(banda)
        perfis.append(realce[:, x0:x1].mean(axis=1))
    return perfis


def perfil_trastes(retificada: np.ndarray) -> np.ndarray:
    """Perfil vertical (qualquer tom) dos trastes, na faixa das cordas.

    O valor absoluto do realce, como ``"qualquer"`` em
    :func:`tab.maos_linhas_braco.pico_na_janela`: o traste pode ser claro ou escuro.

    Args:
        retificada: imagem retificada (:func:`retificar_pente`).

    Returns:
        Um perfil 1D por coluna (uma posição por coluna, em ``u``).
    """
    realce = realcar(retificada, eixo=1, janela=JANELA_TRASTE)
    y0 = round((v_corda(1) - MARGEM_V - V0_PENTE) * KV)
    y1 = round((v_corda(6) + MARGEM_V - V0_PENTE) * KV)
    y0 = max(y0, 0)
    y1 = min(y1, retificada.shape[0])
    return np.abs(realce[y0:y1].mean(axis=0))


def valor_no_perfil(perfil: np.ndarray, posicoes: np.ndarray) -> np.ndarray:
    """Valor do perfil em posições fracionárias, ``-inf`` fora do perfil.

    Args:
        perfil: perfil 1D.
        posicoes: índices fracionários, de qualquer forma.

    Returns:
        Valores interpolados linearmente, da mesma forma que ``posicoes``.
    """
    indices = np.arange(len(perfil), dtype=float)
    valores = np.interp(posicoes, indices, perfil)
    dentro = (posicoes >= 0.0) & (posicoes <= len(perfil) - 1.0)
    return np.where(dentro, valores, -np.inf)


def pontuar_cordas(perfil: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Soma do perfil nas 6 cordas, para cada par ``(a, b)``.

    Args:
        perfil: perfil horizontal de uma banda (:func:`perfis_cordas`).
        a: ``(n,)`` posições da corda 1, em v.
        b: ``(n,)`` vãos 1-6, em v.

    Returns:
        ``(n,)`` escores; ``-inf`` se alguma corda cai fora da retificada.
    """
    fracao = np.arange(6) / 5.0
    v = a[:, None] + b[:, None] * fracao[None, :]
    return valor_no_perfil(perfil, (v - V0_PENTE) * KV).sum(axis=1)


def pontuar_trastes(
    perfil: np.ndarray, alfa: np.ndarray, beta: np.ndarray, gama: np.ndarray
) -> np.ndarray:
    """Soma do perfil nos trastes ``n = 0..12``, para cada ``(alfa, beta, gama)``.

    Args:
        perfil: perfil vertical (:func:`perfil_trastes`).
        alfa: ``(n,)``.
        beta: ``(n,)``.
        gama: ``(n,)``.

    Returns:
        ``(n,)`` escores; ``-inf`` se algum traste cai fora da retificada.
    """
    s = S_TRASTES[: ULTIMO_TRASTE + 1]
    u = (alfa[:, None] * s[None, :] + beta[:, None]) / (
        gama[:, None] * s[None, :] + 1.0
    )
    return valor_no_perfil(perfil, (u - U0) * KU).sum(axis=1)


def _eixo(faixa: tuple[float, float], passo: float) -> np.ndarray:
    """Malha grossa de uma faixa, com o passo pedido (extremos incluídos).

    Args:
        faixa: ``(minimo, maximo)``.
        passo: passo da malha.

    Returns:
        Os valores da malha, em ordem crescente.
    """
    n = round((faixa[1] - faixa[0]) / passo)
    return np.linspace(faixa[0], faixa[1], n + 1)


def _eixo_fino(centro: float, passo: float, faixa: tuple[float, float]) -> np.ndarray:
    """Malha fina em volta de ``centro``: +/- ``passo``, passo ``passo / FATOR_FINO``.

    Args:
        centro: melhor valor da busca grossa.
        passo: passo da malha grossa (define a meia largura).
        faixa: faixa de busca, que a malha fina não ultrapassa.

    Returns:
        Os valores da malha fina, em ordem crescente.
    """
    ini = max(centro - passo, faixa[0])
    fim = min(centro + passo, faixa[1])
    n = round((fim - ini) / (passo / FATOR_FINO))
    return np.linspace(ini, fim, n + 1)


def _maximo_da_malha(
    pontuar: Callable[..., np.ndarray], eixos: list[np.ndarray]
) -> tuple[np.ndarray, float]:
    """Parâmetros de maior escore numa malha cartesiana.

    Args:
        pontuar: função que recebe um vetor por parâmetro e devolve o escore de cada
            combinação.
        eixos: uma malha por parâmetro.

    Returns:
        ``(parametros, escore)`` da melhor combinação.

    Raises:
        ValueError: se nenhuma combinação cai dentro da retificada.
    """
    planos = [m.ravel() for m in np.meshgrid(*eixos, indexing="ij")]
    escores = pontuar(*planos)
    i = int(np.argmax(escores))
    if not np.isfinite(escores[i]):
        raise ValueError("nenhuma posição do pente cai dentro da retificada")
    return np.array([p[i] for p in planos]), float(escores[i])


def ajustar_banda_cordas(perfil: np.ndarray) -> dict[str, float]:
    """Melhor ``(a, b)`` de uma banda: busca grossa, depois fina.

    Args:
        perfil: perfil horizontal da banda (:func:`perfis_cordas`).

    Returns:
        ``a``, ``b``, ``score`` (soma do perfil nas 6 cordas) e ``score_musica``
        (o mesmo, em ``(a, b) = (0, 1)``, que é a H da música).
    """

    def pontuar(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return pontuar_cordas(perfil, a, b)

    (a0, b0), _ = _maximo_da_malha(
        pontuar,
        [_eixo(FAIXA_A, PASSO_GROSSO_CORDA), _eixo(FAIXA_B, PASSO_GROSSO_CORDA)],
    )
    (a, b), score = _maximo_da_malha(
        pontuar,
        [
            _eixo_fino(a0, PASSO_GROSSO_CORDA, FAIXA_A),
            _eixo_fino(b0, PASSO_GROSSO_CORDA, FAIXA_B),
        ],
    )
    musica = float(pontuar(np.array([0.0]), np.array([1.0]))[0])
    return {
        "a": float(a),
        "b": float(b),
        "score": score,
        "score_musica": musica,
    }


def ajustar_cordas(
    retificada: np.ndarray,
) -> tuple[tuple[float, float, float, float], dict[str, Any]]:
    """Cordas do pente: ``(a, b)`` por banda e a reta de cada um em função de ``u``.

    Args:
        retificada: imagem retificada (:func:`retificar_pente`).

    Returns:
        ``((a0, a1, b0, b1), resumo)``: ``a(u) = a0 + a1 u`` e ``b(u) = b0 + b1 u``,
        ajustados aos centros das bandas; ``resumo`` traz cada banda e os escores
        somados.
    """
    bandas = [ajustar_banda_cordas(perfil) for perfil in perfis_cordas(retificada)]
    centros = [(float(S_TRASTES[lo]) + float(S_TRASTES[hi])) / 2.0 for lo, hi in BANDAS]
    inclinacao_a, a0 = np.polyfit(centros, [b["a"] for b in bandas], 1)
    inclinacao_b, b0 = np.polyfit(centros, [b["b"] for b in bandas], 1)
    ajuste = (float(a0), float(inclinacao_a), float(b0), float(inclinacao_b))
    resumo = {
        "bandas": [
            {"casas": f"{lo + 1}-{hi}", "centro_u": round(c, 5), **b}
            for (lo, hi), c, b in zip(BANDAS, centros, bandas, strict=True)
        ],
        "linear": {"a0": ajuste[0], "a1": ajuste[1], "b0": ajuste[2], "b1": ajuste[3]},
        "score": sum(b["score"] for b in bandas),
        "score_musica": sum(b["score_musica"] for b in bandas),
    }
    return ajuste, resumo


def ajustar_trastes(
    retificada: np.ndarray,
) -> tuple[tuple[float, float, float], dict[str, float]]:
    """Trastes do pente: ``(alfa, beta, gama)`` pelo máximo do perfil vertical.

    Args:
        retificada: imagem retificada (:func:`retificar_pente`).

    Returns:
        ``((alfa, beta, gama), resumo)``. ``resumo`` traz ``score`` e
        ``score_musica`` (em ``(1, 0, 0)``, a H da música).
    """
    perfil = perfil_trastes(retificada)

    def pontuar(al: np.ndarray, be: np.ndarray, ga: np.ndarray) -> np.ndarray:
        return pontuar_trastes(perfil, al, be, ga)

    (al0, be0, ga0), _ = _maximo_da_malha(
        pontuar,
        [
            _eixo(FAIXA_ALFA, PASSO_GROSSO_ALFA),
            _eixo(FAIXA_BETA, PASSO_GROSSO_BETA),
            _eixo(FAIXA_GAMA, PASSO_GROSSO_GAMA),
        ],
    )
    (alfa, beta, gama), score = _maximo_da_malha(
        pontuar,
        [
            _eixo_fino(al0, PASSO_GROSSO_ALFA, FAIXA_ALFA),
            _eixo_fino(be0, PASSO_GROSSO_BETA, FAIXA_BETA),
            _eixo_fino(ga0, PASSO_GROSSO_GAMA, FAIXA_GAMA),
        ],
    )
    musica = float(pontuar(np.array([1.0]), np.array([0.0]), np.array([0.0]))[0])
    resumo = {
        "alfa": float(alfa),
        "beta": float(beta),
        "gama": float(gama),
        "score": score,
        "score_musica": musica,
    }
    return (float(alfa), float(beta), float(gama)), resumo


def pares_do_pente(
    H: np.ndarray,
    cordas: tuple[float, float, float, float] | None = None,
    trastes: tuple[float, float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Pares origem (u, v nominais) -> destino em px, para o ajuste da H.

    Para cada traste ``n = 0..12`` e corda ``j = 1..6``: a origem é
    ``(s_n, v_j)``; o destino é ``H(u'_n, v'_j(u'_n))``, com ``u'_n`` dado pelos
    trastes (ou ``s_n`` se não há trastes do pente) e ``v'_j`` pela reta das cordas
    (ou ``v_j`` se não há cordas do pente).

    Args:
        H: homografia da música, que leva ``(u, v)`` para pixels.
        cordas: ``(a0, a1, b0, b1)`` de :func:`ajustar_cordas`, ou ``None``.
        trastes: ``(alfa, beta, gama)`` de :func:`ajustar_trastes`, ou ``None``.

    Returns:
        ``origem`` e ``destino`` em ``(N, 2)``, com ``N = 13 * 6``.
    """
    s = S_TRASTES[: ULTIMO_TRASTE + 1]
    if trastes is None:
        u = s.copy()
    else:
        alfa, beta, gama = trastes
        u = (alfa * s + beta) / (gama * s + 1.0)
    if cordas is None:
        a = np.zeros_like(u)
        b = np.ones_like(u)
    else:
        a0, a1, b0, b1 = cordas
        a = a0 + a1 * u
        b = b0 + b1 * u
    origem = []
    destino_uv = []
    for n in range(len(s)):
        for j in range(1, 7):
            origem.append((float(s[n]), v_corda(j)))
            destino_uv.append((float(u[n]), float(a[n] + b[n] * (j - 1) / 5.0)))
    destino = aplicar_homografia(H, np.asarray(destino_uv))
    return np.asarray(origem), destino


def calibrar_por_pente(
    H: np.ndarray,
    mediana: np.ndarray,
    componentes: tuple[str, ...] = COMPONENTES,
) -> tuple[np.ndarray, dict[str, Any]]:
    """H do pente: ajusta cordas e trastes pela imagem, a partir da H da música.

    Args:
        H: homografia calibrada pela música (ponto de partida).
        mediana: quadro BGR da mediana do braço.
        componentes: o que ajustar: ``"cordas"``, ``"trastes"`` ou os dois. O que não
            está na lista fica como a música.

    Returns:
        ``(H_novo, resumo)``. ``resumo`` traz ``cordas`` e ``trastes`` (parâmetros,
        escores e escores da música), ``mudanca_H_vs_musica`` (px sobre a grade) e
        ``residuo_ajuste_px`` (quanto a H nova deixa de passar pelos pares).

    Raises:
        ValueError: se ``componentes`` tem um nome desconhecido.
    """
    desconhecidos = set(componentes) - set(COMPONENTES)
    if desconhecidos:
        raise ValueError(f"componentes desconhecidos: {sorted(desconhecidos)}")
    retificada = retificar_pente(mediana, H)
    resumo: dict[str, Any] = {
        "componentes": list(componentes),
        "janela_v": [V0_PENTE, V1_PENTE],
    }
    cordas = None
    trastes = None
    if "cordas" in componentes:
        cordas, resumo["cordas"] = ajustar_cordas(retificada)
    if "trastes" in componentes:
        trastes, resumo["trastes"] = ajustar_trastes(retificada)
    origem, destino = pares_do_pente(H, cordas, trastes)
    H_novo = ajustar_pontos(H, origem, destino)
    residuo = np.linalg.norm(aplicar_homografia(H_novo, origem) - destino, axis=1)
    resumo["residuo_ajuste_px"] = {
        "mediana": round(float(np.median(residuo)), 4),
        "maximo": round(float(np.max(residuo)), 4),
    }
    resumo["mudanca_H_vs_musica"] = diferenca_entre_h(H, H_novo)
    return H_novo, resumo
