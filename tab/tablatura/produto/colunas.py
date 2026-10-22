"""Colunas: notas com o mesmo x (um acorde) formam UMA coluna.

Um acorde é desenhado com as notas empilhadas no mesmo x. Se o estado do marcador for lido nota a nota,
a célula de uma delas fica vazia (a fronteira entre vizinhos cai no próprio x) e só uma recebe onset.
Agrupando antes, o acorde vira uma unidade do estado: todas as suas notas recebem o mesmo onset.

Tudo aqui está no espaço do QUADRO (``x_quadro``), o mesmo do marcador.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass
class Coluna:
    """Um grupo de notas com o mesmo x (uma coluna da tablatura).

    Attributes:
        x_quadro: x da coluna no quadro, a mediana dos x das notas do grupo.
        indices: índices (na lista de entrada) das notas do grupo.
    """

    x_quadro: float
    indices: list[int]


def agrupar_colunas(
    xs_quadro: list[float], passo: float, tol: float = 0.35
) -> list[Coluna]:
    """Agrupa notas em colunas por varredura em x ordenado.

    Uma nota entra na coluna corrente quando a distância dela ao x da coluna (a mediana
    dos x já agrupados) é menor que ``tol * passo``. Senão, abre uma coluna nova.

    Args:
        xs_quadro: x de cada nota, no espaço do quadro.
        passo: distância vertical entre cordas, em px (``r["passo"]``).
        tol: fração do passo que define "mesmo x".

    Returns:
        Colunas ordenadas por x. Cada nota aparece em exatamente uma coluna.

    Raises:
        ValueError: se ``passo`` não for positivo.
    """
    if passo <= 0:
        raise ValueError(f"passo deve ser positivo, veio {passo}")
    limite = tol * passo
    ordem = sorted(range(len(xs_quadro)), key=lambda i: xs_quadro[i])
    colunas: list[Coluna] = []
    membros: list[int] = []
    for i in ordem:
        if membros:
            x_corrente = statistics.median(xs_quadro[j] for j in membros)
            if xs_quadro[i] - x_corrente < limite:
                membros.append(i)
                continue
            colunas.append(_fechar(xs_quadro, membros))
        membros = [i]
    if membros:
        colunas.append(_fechar(xs_quadro, membros))
    return colunas


def _fechar(xs_quadro: list[float], membros: list[int]) -> Coluna:
    """Monta a coluna a partir dos índices já agrupados.

    Args:
        xs_quadro: x de todas as notas.
        membros: índices das notas da coluna.

    Returns:
        A ``Coluna`` com a mediana dos x dos membros.
    """
    return Coluna(
        x_quadro=float(statistics.median(xs_quadro[j] for j in membros)),
        indices=list(membros),
    )
