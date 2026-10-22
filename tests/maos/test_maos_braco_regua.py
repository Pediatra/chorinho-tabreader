"""Testes da régua de casas (``tab.maos_braco_regua``, rodada 1040). Sem acervo."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from tab.maos.braco.regua import (
    abertura,
    ajustar,
    casas_do_quadro,
    melhor_deslocamento,
)
from tab.maos.braco.tempo import Marcas

#: Violão ideal: escala de 600 px, cordas de 40 px no nut a 50 px no traste 12.
ESCALA = 600.0


def _posicao(n: int) -> float:
    return ESCALA * (1.0 - 2.0 ** (-n / 12.0))


def _marcas(nut_x: float = 0.0) -> Marcas:
    p12 = _posicao(12)
    return Marcas(
        nut=np.array([nut_x, 100.0]),
        trastes={n: np.array([nut_x + _posicao(n), 100.0]) for n in range(1, 8)},
        corda1=np.array([[nut_x, 80.0], [nut_x + p12, 75.0]]),
        corda6=np.array([[nut_x, 120.0], [nut_x + p12, 125.0]]),
    )


def test_abertura_no_nut_e_no_traste_12():
    marcas = _marcas()
    u = np.array([1.0, 0.0])
    assert abertura(marcas, np.array([0.0, 100.0]), u) == pytest.approx(40.0)
    assert abertura(marcas, np.array([_posicao(12), 100.0]), u) == pytest.approx(50.0)


def test_razao_cai_com_a_casa_e_a_reta_acha_o_deslocamento_zero():
    casas = casas_do_quadro(_marcas())
    assert [n for n, _ in casas] == list(range(1, 8))
    razoes = [r for _, r in casas]
    assert all(b < a for a, b in itertools.pairwise(razoes))
    alfa, beta = ajustar(casas)
    assert 0.06 < beta < 0.09
    s, margem = melhor_deslocamento(casas[2:5], alfa, beta)
    assert s == 0
    assert margem > 0
    deslocadas = [(n - 1, r) for n, r in casas[2:5]]
    assert melhor_deslocamento(deslocadas, alfa, beta)[0] == 1


def test_sem_nut_nao_ha_casas():
    marcas = _marcas()
    sem = Marcas(
        nut=None, trastes=marcas.trastes, corda1=marcas.corda1, corda6=marcas.corda6
    )
    assert casas_do_quadro(sem) == []
