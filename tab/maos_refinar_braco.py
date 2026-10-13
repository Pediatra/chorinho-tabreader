"""Refino da homografia do braço pelo erro de reprojeção (M3c, rodada 1007).

A H da rodada 1006 sai de uma DLT algébrica. Aqui ela é refinada pelo erro que
importa: a distância, em px, entre o ponto previsto (``H . (u, v)``) e a ponta
candidata mais perto. A associação é refeita a cada iteração (tipo ICP). O erro é
normalizado pela largura prevista da casa naquele ponto, e a perda é o biweight de
Tukey com constante ``C_TUKEY``: nota longe da grade não puxa a H.

Só numpy: Levenberg–Marquardt próprio (scipy não está no container).

``consenso`` roda o RANSAC com várias sementes, refina cada H e fica com a de menor
custo robusto. A estabilidade é medida entre conjuntos de sementes.
"""

from __future__ import annotations

from functools import partial
from typing import Any

import numpy as np

from .maos_calibrar_por_notas import (
    Conjunto,
    aplicar_homografia,
    grade_do_braco,
    largura_casa,
    ransac,
)

#: Constante do biweight de Tukey, em fração da largura prevista da casa.
C_TUKEY = 0.5

#: Iterações externas (associação e pesos) e de Levenberg–Marquardt.
ITERACOES_EXTERNAS = 30
ITERACOES_LM = 60

#: Passo relativo da diferença finita do Jacobiano.
PASSO_JACOBIANO = 1e-7

#: Mudança máxima, em px, da grade entre duas iterações externas, para parar.
TOLERANCIA_GRADE_PX = 1e-3


def rho_tukey(e: np.ndarray, c: float = C_TUKEY) -> np.ndarray:
    """Perda do biweight de Tukey, constante fora de ``c``.

    Args:
        e: resíduos normalizados, não negativos. ``inf`` (sem candidato) vale o
            máximo, ``c**2 / 6``.
        c: constante do Tukey.

    Returns:
        ``c**2/6 * (1 - (1 - (e/c)**2)**3)`` dentro de ``c``, ``c**2/6`` fora.
    """
    e = np.asarray(e, dtype=float)
    dentro = np.abs(e) < c
    x = np.where(dentro, e / c, 0.0)
    return np.where(dentro, c**2 / 6 * (1 - (1 - x**2) ** 3), c**2 / 6)


def peso_tukey(e: np.ndarray, c: float = C_TUKEY) -> np.ndarray:
    """Peso IRLS do biweight de Tukey: ``(1 - (e/c)**2)**2`` dentro de ``c``, 0 fora.

    Args:
        e: resíduos normalizados.
        c: constante do Tukey.

    Returns:
        Pesos em ``[0, 1]``, com a mesma forma de ``e``.
    """
    e = np.asarray(e, dtype=float)
    dentro = np.abs(e) < c
    x = np.where(dentro, e / c, 0.0)
    return np.where(dentro, (1 - x**2) ** 2, 0.0)


def _valida(H: np.ndarray, c: Conjunto) -> bool:
    """A H é finita e não manda notas para os dois lados do plano.

    Args:
        H: homografia.
        c: conjunto de notas.

    Returns:
        ``True`` se a H pode ser usada.
    """
    if not np.all(np.isfinite(H)):
        return False
    w = np.column_stack([c.uv, np.ones(len(c.uv))]) @ H[2]
    return bool(np.all(w > 0) or np.all(w < 0))


def _associar(H: np.ndarray, c: Conjunto) -> dict[str, np.ndarray]:
    """Ponta candidata mais perto de cada nota, e o erro normalizado.

    Args:
        H: homografia.
        c: conjunto de notas.

    Returns:
        ``perto`` (índice da ponta), ``dest`` (``(N, 2)`` ponta escolhida), ``largura``
        (px, ``(N,)``) e ``e`` (distância dividida pela largura; ``inf`` sem candidato).
    """
    n = len(c.indices)
    pred = aplicar_homografia(H, c.uv)
    dist = np.linalg.norm(c.cand - pred[:, None, :], axis=2)
    dist = np.where(c.mascara, dist, np.inf)
    perto = np.argmin(dist, axis=1)
    dmin = dist[np.arange(n), perto]
    largura = largura_casa(H, c.casa, c.uv[:, 1])
    with np.errstate(divide="ignore", invalid="ignore"):
        e = dmin / largura
    e = np.where(np.isfinite(e), e, np.inf)
    return {
        "perto": perto,
        "dest": c.cand[np.arange(n), perto],
        "largura": largura,
        "e": e,
    }


def custo_robusto(H: np.ndarray, c: Conjunto) -> float:
    """Soma do biweight de Tukey dos erros normalizados (menor é melhor).

    Args:
        H: homografia a avaliar.
        c: conjunto de notas.

    Returns:
        O custo; ``inf`` se a H não é válida.
    """
    if not _valida(H, c):
        return float("inf")
    return float(np.sum(rho_tukey(_associar(H, c)["e"])))


def _params(H: np.ndarray) -> np.ndarray:
    """Os 8 parâmetros livres de uma H com ``H[2, 2] = 1``.

    Args:
        H: homografia.

    Returns:
        Vetor ``(8,)`` com as entradas de H em ordem, sem a última.
    """
    return (H / H[2, 2]).ravel()[:8].copy()


def _matriz(p: np.ndarray) -> np.ndarray:
    """Monta a H 3 x 3 a partir dos 8 parâmetros livres.

    Args:
        p: vetor ``(8,)``.

    Returns:
        Homografia com ``H[2, 2] = 1``.
    """
    return np.append(p, 1.0).reshape(3, 3)


def _residuos(
    p: np.ndarray, uv: np.ndarray, destino: np.ndarray, fator: np.ndarray
) -> np.ndarray:
    """Resíduos ponderados ``fator * (H(p) . uv - destino)``, achatados.

    Args:
        p: parâmetros livres da H.
        uv: ``(N, 2)`` coordenadas do braço.
        destino: ``(N, 2)`` pontas associadas, em px.
        fator: ``(N,)`` peso de cada nota (raiz do peso de Tukey dividido pela largura).

    Returns:
        ``(2N,)`` resíduos.
    """
    pred = aplicar_homografia(_matriz(p), uv)
    return ((pred - destino) * fator[:, None]).ravel()


def _jacobiano(fun: Any, p: np.ndarray, r0: np.ndarray) -> np.ndarray:
    """Jacobiano por diferenças finitas diretas.

    Args:
        fun: função ``p -> resíduos``.
        p: ponto de avaliação.
        r0: resíduos em ``p`` (já calculados).

    Returns:
        ``(M, 8)`` matriz Jacobiana.
    """
    colunas = []
    for j in range(len(p)):
        passo = PASSO_JACOBIANO * max(abs(p[j]), 1e-4)
        q = p.copy()
        q[j] += passo
        colunas.append((fun(q) - r0) / passo)
    return np.column_stack(colunas)


def _levenberg_marquardt(
    p0: np.ndarray, fun: Any, iteracoes: int = ITERACOES_LM
) -> np.ndarray:
    """Mínimos quadrados não lineares por Levenberg–Marquardt, com escala de Marquardt.

    Args:
        p0: chute inicial, ``(8,)``.
        fun: função ``p -> resíduos``.
        iteracoes: iterações máximas.

    Returns:
        Os parâmetros de menor custo encontrados.
    """
    p = p0.copy()
    r = fun(p)
    custo = float(r @ r)
    lam = 1e-3
    for _ in range(iteracoes):
        jac = _jacobiano(fun, p, r)
        a = jac.T @ jac
        g = jac.T @ r
        diagonal = np.maximum(np.diag(a), 1e-30)
        aceitou = False
        while lam < 1e12:
            try:
                delta = np.linalg.solve(a + lam * np.diag(diagonal), -g)
            except np.linalg.LinAlgError:
                lam *= 10.0
                continue
            p_novo = p + delta
            r_novo = fun(p_novo)
            custo_novo = float(r_novo @ r_novo)
            if np.isfinite(custo_novo) and custo_novo < custo:
                aceitou = True
                break
            lam *= 10.0
        if not aceitou:
            break
        melhora = custo - custo_novo
        p, r, custo = p_novo, r_novo, custo_novo
        lam = max(lam / 10.0, 1e-12)
        if melhora <= 1e-12 * max(custo, 1e-30):
            break
    return p


def refinar_reprojecao(
    H0: np.ndarray, c: Conjunto, iteracoes: int = ITERACOES_EXTERNAS
) -> np.ndarray:
    """Refina a H pelo erro de reprojeção, com reassociação e pesos de Tukey.

    A cada iteração externa: associa cada nota à ponta candidata mais perto, calcula o
    erro normalizado pela largura da casa, dá peso de Tukey e resolve os mínimos
    quadrados ponderados (Levenberg–Marquardt) para a nova H.

    Args:
        H0: homografia inicial (por exemplo, a do RANSAC).
        c: conjunto de notas com as pontas candidatas.
        iteracoes: iterações externas máximas.

    Returns:
        A homografia refinada, com ``H[2, 2] = 1``.

    Raises:
        ValueError: se a H inicial não é válida para o conjunto.
    """
    H = H0 / H0[2, 2]
    if not _valida(H, c):
        raise ValueError("homografia inicial inválida para o conjunto")
    for _ in range(iteracoes):
        a = _associar(H, c)
        peso = peso_tukey(a["e"])
        usar = np.flatnonzero(peso > 0)
        if len(usar) < 4:
            break
        fator = np.sqrt(peso[usar]) / a["largura"][usar]
        fun = partial(_residuos, uv=c.uv[usar], destino=a["dest"][usar], fator=fator)
        H_novo = _matriz(_levenberg_marquardt(_params(H), fun))
        if not _valida(H_novo, c):
            break
        mudanca = float(
            np.max(np.linalg.norm(grade_do_braco(H_novo) - grade_do_braco(H), axis=1))
        )
        H = H_novo
        if mudanca < TOLERANCIA_GRADE_PX:
            break
    return H


def ajustar_pontos(
    H0: np.ndarray, origem: np.ndarray, destino: np.ndarray
) -> np.ndarray:
    """Ajuste de H, por mínimos quadrados, a pares fixos ``origem -> destino`` em px.

    Usado para corrigir a H pelos cruzamentos achados na imagem: a associação é dada
    e não muda, sem pesos.

    Args:
        H0: homografia inicial.
        origem: ``(N, 2)`` coordenadas do braço (numeração da música).
        destino: ``(N, 2)`` pixels onde os cruzamentos estão na imagem.

    Returns:
        A homografia ajustada, com ``H[2, 2] = 1``.

    Raises:
        ValueError: se há menos de 4 pares.
    """
    origem = np.asarray(origem, dtype=float)
    destino = np.asarray(destino, dtype=float)
    if len(origem) < 4 or len(origem) != len(destino):
        raise ValueError("o ajuste precisa de pelo menos 4 pares")
    fun = partial(_residuos, uv=origem, destino=destino, fator=np.ones(len(origem)))
    return _matriz(_levenberg_marquardt(_params(H0 / H0[2, 2]), fun))


def consenso(
    c: Conjunto, sementes: tuple[int, ...] | list[int], **ransac_kwargs: Any
) -> dict[str, Any]:
    """RANSAC com cada semente, refino por reprojeção, e a H de menor custo robusto.

    Uma semente cuja H inicial é inválida para o conjunto não derruba as outras: ela
    entra nos candidatos com ``valida`` False (sem H nem custo) e fica de fora da
    escolha.

    Args:
        c: conjunto de notas.
        sementes: sementes do RANSAC.
        **ransac_kwargs: repassado a :func:`tab.maos_calibrar_por_notas.ransac`
            (por exemplo ``iteracoes``).

    Returns:
        ``H`` (a escolhida), ``semente`` (a que a deu), ``custo``, ``invalidas``
        (quantas sementes deram H inválida) e ``candidatos``: uma entrada por semente.
        Válidas têm ``valida`` True, ``semente``, ``inliers_ransac``, ``custo_ransac``,
        ``inliers`` e ``custo`` após o refino, e ``H``. Inválidas têm ``valida`` False,
        ``semente`` e ``motivo``.

    Raises:
        ValueError: se nenhuma semente deu homografia válida.
    """
    candidatos: list[dict[str, Any]] = []
    for semente in sementes:
        r = ransac(c, semente, **ransac_kwargs)
        try:
            H_ref = refinar_reprojecao(r["H"], c)
        except ValueError as erro:
            candidatos.append(
                {"semente": semente, "valida": False, "motivo": str(erro)}
            )
            continue
        candidatos.append(
            {
                "semente": semente,
                "valida": True,
                "inliers_ransac": r["inliers"],
                "custo_ransac": custo_robusto(r["H"], c),
                "inliers": int(_contar_inliers(H_ref, c)),
                "custo": custo_robusto(H_ref, c),
                "H": H_ref,
            }
        )
    validas = [d for d in candidatos if d["valida"]]
    if not validas:
        raise ValueError(
            f"nenhuma das sementes {list(sementes)} deu homografia válida "
            f"para o conjunto de {len(c.indices)} notas"
        )
    escolhida = min(validas, key=lambda d: d["custo"])
    return {
        "H": escolhida["H"],
        "semente": escolhida["semente"],
        "custo": escolhida["custo"],
        "invalidas": len(candidatos) - len(validas),
        "candidatos": candidatos,
    }


def _contar_inliers(H: np.ndarray, c: Conjunto) -> int:
    """Quantas notas têm a ponta mais perto dentro da tolerância da casa (0,5 casa).

    Args:
        H: homografia.
        c: conjunto de notas.

    Returns:
        Número de inliers; 0 se a H não é válida.
    """
    if not _valida(H, c):
        return 0
    e = _associar(H, c)["e"]
    return int(np.sum(e < 0.5))
