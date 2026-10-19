"""Rodada 1028, P3: consenso por vídeo (sinal S4). Só sinaliza, não corrige.

Dois quadros são da mesma tomada quando, do mesmo vídeo, o ponto médio das cordas 1 e 6
de um está a no máximo 0,3 da largura do braço do outro, e o eixo difere até 3 graus.
Dentro de cada tomada, os quadros não sinalizados formam a referência. Para cada quadro,
a referência mais próxima (pelo ponto médio das cordas) dá a numeração: os trastes do
quadro são medidos em casas na curva da referência. Se a numeração do quadro difere por
um deslocamento inteiro k ≠ 0, com cada traste a no máximo 0,25 casa do deslocamento,
o quadro recebe o sinal S4 e é sinalizado. Quadro sem referência na tomada fica como está.

Pré-registro: ``docs/rodadas/1028-um-braco-consenso-e-retreino.md``.
"""

from __future__ import annotations

import math

import numpy as np

from .maos_braco_regra import eixo_do_braco

#: Mesma tomada: distância entre os pontos médios das cordas, em fração da largura.
FRACAO_LARGURA_TOMADA = 0.30
#: Mesma tomada: diferença máxima do eixo, em graus.
ANGULO_TOMADA_GRAUS = 3.0
#: Deslocamento: tolerância de cada traste, em casas.
TOLERANCIA_CASAS = 0.25
#: Sinal S4 do consenso.
SINAL_S4 = "S4"


def _meio(par: list) -> np.ndarray:
    """Ponto médio de um par de pontos.

    Args:
        par: dois pontos ``[x, y]``.

    Returns:
        Ponto médio ``(2,)``.
    """
    return np.asarray(par, dtype=float).mean(axis=0)


def _eixo(quadro: dict) -> tuple[np.ndarray, np.ndarray, float]:
    """Origem, direção e largura do braço de um quadro (pelas cordas 1 e 6).

    Args:
        quadro: entrada com ``corda1`` e ``corda6`` (dois pontos cada).

    Returns:
        ``(origem, u, largura)``, com a largura medida perpendicular ao eixo.
    """
    origem, u = eixo_do_braco(quadro["corda1"], quadro["corda6"])
    normal = np.array([-u[1], u[0]])
    largura = abs(
        float(np.dot(_meio(quadro["corda6"]) - _meio(quadro["corda1"]), normal))
    )
    return origem, u, largura


def _tem_cordas(quadro: dict) -> bool:
    """Se o quadro tem as cordas 1 e 6 com dois pontos cada (braço achado).

    Args:
        quadro: entrada com ``corda1`` e ``corda6`` (podem faltar).

    Returns:
        True quando as duas cordas têm dois pontos.
    """
    return all(
        quadro.get(c) is not None and np.asarray(quadro[c]).shape == (2, 2)
        for c in ("corda1", "corda6")
    )


def mesma_tomada(a: dict, b: dict) -> bool:
    """Se dois quadros do mesmo vídeo são da mesma tomada (regra do P3).

    Args:
        a: quadro com ``arquivo``, ``corda1`` e ``corda6``.
        b: quadro com ``arquivo``, ``corda1`` e ``corda6``.

    Returns:
        True quando o vídeo é o mesmo, a distância entre os pontos médios das cordas 1 e 6
        é de até 0,3 da largura média, e o eixo difere até 3 graus.
    """
    if a["arquivo"] != b["arquivo"]:
        return False
    if not (_tem_cordas(a) and _tem_cordas(b)):
        return False
    _, ua, la = _eixo(a)
    _, ub, lb = _eixo(b)
    largura = (la + lb) / 2.0
    if largura <= 0.0:
        return False
    d1 = float(np.linalg.norm(_meio(a["corda1"]) - _meio(b["corda1"])))
    d6 = float(np.linalg.norm(_meio(a["corda6"]) - _meio(b["corda6"])))
    if max(d1, d6) > FRACAO_LARGURA_TOMADA * largura:
        return False
    cosseno = min(1.0, abs(float(np.dot(ua, ub))))
    return math.degrees(math.acos(cosseno)) <= ANGULO_TOMADA_GRAUS


def tomadas(quadros: list[dict]) -> list[list[dict]]:
    """Agrupa os quadros em tomadas (componentes da relação de mesma tomada).

    Args:
        quadros: quadros com ``id``, ``arquivo``, ``corda1`` e ``corda6``.

    Returns:
        Lista de tomadas, cada uma com os quadros dela, na ordem de entrada.
    """
    pai = list(range(len(quadros)))

    def raiz(i: int) -> int:
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    for i in range(len(quadros)):
        for j in range(i + 1, len(quadros)):
            if mesma_tomada(quadros[i], quadros[j]):
                pai[raiz(i)] = raiz(j)
    grupos: dict[int, list[dict]] = {}
    for i, quadro in enumerate(quadros):
        grupos.setdefault(raiz(i), []).append(quadro)
    return list(grupos.values())


def _curva_da_referencia(
    ref: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """Tabela ``(n, t)`` da referência, no eixo dela (nut = 0, trastes com número).

    O eixo é orientado para que ``t`` cresça com o número (do nut para fora).

    Args:
        ref: quadro de referência, com ``nut`` (ou None), ``corda1``, ``corda6`` e
            ``trastes`` (``[{numero, ponto}]``).

    Returns:
        ``(numeros, t, origem, u)`` com ``t`` crescente, ou None se não há 2 pontos ou a
        tabela não cresce.
    """
    origem, u, _ = _eixo(ref)
    pares: list[tuple[int, np.ndarray]] = []
    if isinstance(ref.get("nut"), list):
        pares.append((0, np.asarray(ref["nut"], dtype=float)))
    for item in ref.get("trastes") or []:
        pares.append((int(item["numero"]), np.asarray(item["ponto"], dtype=float)))
    if len(pares) < 2:
        return None
    pares.sort(key=lambda p: p[0])
    numeros = np.array([n for n, _ in pares], dtype=float)
    t = np.array([float(np.dot(p - origem, u)) for _, p in pares])
    if t[-1] < t[0]:
        t = -t
        u = -u
    if np.any(np.diff(t) <= 0.0):
        return None
    return numeros, t, origem, u


def deslocamento(quadro: dict, ref: dict) -> int | None:
    """Deslocamento inteiro k da numeração do quadro contra a referência, ou None.

    Os trastes do quadro são levados à curva da referência (em casas, por
    interpolação). Se todos ficam a até 0,25 casa de ``numero + k`` para o mesmo k
    inteiro, o deslocamento é k. Com menos de 2 trastes comparáveis, não há decisão.

    Args:
        quadro: quadro com ``trastes`` (``[{numero, ponto}]``) e ``corda1``, ``corda6``.
        ref: quadro de referência (não sinalizado, com braço).

    Returns:
        k (inteiro, pode ser 0), ou None sem decisão.
    """
    curva = _curva_da_referencia(ref)
    if curva is None:
        return None
    numeros_ref, t_ref, origem, u = curva
    pares: list[tuple[float, float]] = []
    for item in quadro.get("trastes") or []:
        t = float(np.dot(np.asarray(item["ponto"], dtype=float) - origem, u))
        if not (t_ref[0] <= t <= t_ref[-1]):
            continue
        casas = float(np.interp(t, t_ref, numeros_ref))
        pares.append((float(item["numero"]), casas))
    if len(pares) < 2:
        return None
    diferencas = [casas - numero for numero, casas in pares]
    k = round(float(np.median(diferencas)))
    if all(abs(d - k) <= TOLERANCIA_CASAS for d in diferencas):
        return int(k)
    return None


def consenso(quadros: list[dict]) -> dict[str, dict]:
    """Sinal S4 de cada quadro: deslocamento k ≠ 0 contra a referência mais próxima.

    Args:
        quadros: quadros de um lote, com ``id``, ``arquivo``, ``achou``, ``sinalizado``,
            ``nut``, ``corda1``, ``corda6`` e ``trastes`` (``[{numero, ponto}]``).

    Returns:
        ``{id: {"tomada": índice, "referencia": id ou None, "k": int ou None,
        "S4": bool}}`` para todos os quadros com braço.
    """
    saida: dict[str, dict] = {}
    for indice, grupo in enumerate(tomadas(quadros)):
        com_braco = [q for q in grupo if q["achou"] and _tem_cordas(q)]
        referencias = [q for q in com_braco if not q["sinalizado"]]
        for quadro in com_braco:
            candidatas = [r for r in referencias if r["id"] != quadro["id"]]
            entrada = {"tomada": indice, "referencia": None, "k": None, "S4": False}
            if candidatas:
                meio = _meio_geral(quadro)
                ref = min(
                    candidatas,
                    key=lambda r: float(np.linalg.norm(_meio_geral(r) - meio)),
                )
                k = deslocamento(quadro, ref)
                entrada.update(referencia=ref["id"], k=k, S4=bool(k not in (None, 0)))
            saida[quadro["id"]] = entrada
    return saida


def _meio_geral(quadro: dict) -> np.ndarray:
    """Centro do quadro: média dos pontos médios das cordas 1 e 6.

    Args:
        quadro: quadro com ``corda1`` e ``corda6``.

    Returns:
        Ponto ``(2,)``.
    """
    return (_meio(quadro["corda1"]) + _meio(quadro["corda6"])) / 2.0
