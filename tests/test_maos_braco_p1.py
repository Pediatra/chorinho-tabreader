"""Testes unitários do P1 da rodada 1028 (previsão sem o nut)."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_braco_regra import eixo_do_braco, prever_trastes_sem_nut, s_do_traste

CORDA1 = [[100.0, 500.0], [1500.0, 300.0]]
CORDA6 = [[100.0, 600.0], [1500.0, 400.0]]
DIMENSOES = (1920, 1080)


def _curva(a: float, b: float, c: float, numeros: list[int]) -> dict[int, list[float]]:
    """Pontos de um modelo projetivo conhecido, sobre o eixo dos cordas de teste.

    Args:
        a: parâmetro a.
        b: parâmetro b (posição do nut no eixo).
        c: parâmetro c.
        numeros: trastes a gerar.

    Returns:
        ``{numero: [x, y]}`` no eixo.
    """
    origem, u = eixo_do_braco(CORDA1, CORDA6)
    pontos = {}
    for n in numeros:
        s = s_do_traste(n)
        t = (a * s + b) / (c * s + 1.0)
        ponto = origem + u * t
        pontos[n] = [float(ponto[0]), float(ponto[1])]
    return pontos


def test_sem_nut_recupera_curva_com_3_ancoras():
    """Com 3 âncoras e sem nut, os outros trastes saem na curva verdadeira."""
    verdade = _curva(a=900.0, b=40.0, c=0.35, numeros=list(range(0, 20)))
    ancoras = {n: verdade[n] for n in (3, 7, 12)}
    previsao = prever_trastes_sem_nut(CORDA1, CORDA6, ancoras, DIMENSOES)
    for n in range(1, 13):
        if n in previsao and n in verdade:
            erro = np.hypot(
                previsao[n][0] - verdade[n][0], previsao[n][1] - verdade[n][1]
            )
            assert erro < 0.5, n


def test_sem_nut_com_2_ancoras_recusa_com_mensagem_clara():
    """Com 2 âncoras e sem nut a ferramenta recusa e diz por quê."""
    verdade = _curva(a=900.0, b=40.0, c=0.35, numeros=[5, 12])
    with pytest.raises(ValueError, match="3 âncoras"):
        prever_trastes_sem_nut(CORDA1, CORDA6, verdade, DIMENSOES)
