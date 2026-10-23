"""Testes da rodada 1045 (``tab.maos.braco.capo_rede``), sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np

from tab.maos.braco.capo_rede import (
    achado,
    alvo_do_capo,
    limiar_dos_sem_capo,
    marcas_da_cabeca,
    perfil_entre_cordas,
)
from tab.maos.braco.tempo import Marcas

CORDAS = ([[0.0, 60.0], [1023.0, 60.0]], [[0.0, 130.0], [1023.0, 130.0]])


def test_alvo_do_capo_crista_entre_as_cordas():
    alvo = alvo_do_capo(CORDAS, 300.0)
    assert alvo.shape == (1, 192, 1024)
    assert alvo[0, 95, 300] > 0.99
    assert alvo[0, 95, 320] < 0.01
    assert alvo[0, 20, 300] < 0.01
    assert alvo_do_capo(CORDAS, None).max() == 0.0


def test_perfil_acha_o_pico_do_capo():
    perfil = perfil_entre_cordas(alvo_do_capo(CORDAS, 500.0)[0], CORDAS)
    assert int(np.argmax(perfil)) == 500


def test_limiar_dos_sem_capo_deixa_um_passar():
    assert abs(limiar_dos_sem_capo([0.9, 0.5, 0.1]) - 0.5) < 1e-5
    assert limiar_dos_sem_capo([0.3]) == 0.0


def test_marcas_da_cabeca_vai_para_a_ponta_das_cordas():
    marcas = Marcas(
        nut=np.array([300.0, 50.0]),
        trastes={1: np.array([350.0, 50.0])},
        corda1=np.array([[100.0, 40.0], [900.0, 40.0]]),
        corda6=np.array([[100.0, 60.0], [900.0, 60.0]]),
    )
    assert marcas_da_cabeca(marcas).nut.tolist() == [100.0, 50.0]


def test_achado_meia_casa():
    registro = {
        "braco": "sim",
        "nut": [300.0, 50.0],
        "capo": [280.0, 50.0],
        "trastes": [[350.0, 50.0], [397.0, 50.0]],
        "corda1": [[100.0, 40.0], [900.0, 40.0]],
        "corda6": [[100.0, 60.0], [900.0, 60.0]],
    }
    perto = {"nota": 0.9, "ponto": [295.0, 50.0]}
    longe = {"nota": 0.9, "ponto": [330.0, 50.0]}
    assert achado(perto, registro, 0.5) is True
    assert achado(longe, registro, 0.5) is False
    assert achado(perto, registro, 0.95) is False
