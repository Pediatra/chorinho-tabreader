"""Testes sintéticos da rodada 1031 (A5): alvo sem nut e a classe de itens do treino."""

import inspect

import numpy as np
import pytest

from tab.maos_braco_a5 import mapas_alvo_sem_nut
from tab.maos_braco_detector import _Itens, _treinar

CORDA1 = [[0.0, 40.0], [1023.0, 40.0]]
CORDA6 = [[0.0, 150.0], [1023.0, 150.0]]
TRASTES_X = {1: 400.0, 2: 600.0, 3: 800.0}
X_INICIO = 300.0


def _rotulo_sem_nut() -> dict:
    """Rótulo sintético sem nut: cordas horizontais e três trastes.

    Returns:
        Dicionário no formato de ``rotulo_na_faixa``, sem traste de número 0.
    """
    return {
        "corda1": CORDA1,
        "corda6": CORDA6,
        "trastes": [[n, x, 95.0] for n, x in TRASTES_X.items()],
    }


def test_mapas_alvo_sem_nut_zera_o_canal_do_nut():
    """O canal do nut fica todo zero quando o quadro não tem nut."""
    alvo = mapas_alvo_sem_nut(_rotulo_sem_nut(), X_INICIO)
    assert alvo.shape == (4, 192, 1024)
    assert alvo.dtype == np.float32
    assert np.all(alvo[3] == 0.0)


def test_mapas_alvo_sem_nut_cordas_comecam_em_x_inicio():
    """As cordas são zero antes de x_inicio e cristas cheias depois dele."""
    alvo = mapas_alvo_sem_nut(_rotulo_sem_nut(), X_INICIO)
    for canal, y in ((0, 40), (1, 150)):
        assert np.all(alvo[canal][:, : int(X_INICIO)] == 0.0)
        assert alvo[canal][y, int(X_INICIO) :].max() == pytest.approx(1.0)


def test_mapas_alvo_sem_nut_x_inicio_negativo_comeca_em_zero():
    """Um x_inicio negativo (cordas que saem pela borda) começa em x = 0."""
    alvo = mapas_alvo_sem_nut(_rotulo_sem_nut(), -25.0)
    assert alvo[0][40, 0] == pytest.approx(1.0)


def test_mapas_alvo_sem_nut_traste_em_cada_casa():
    """O canal de trastes tem uma crista cheia em cada traste, entre as duas cordas."""
    alvo = mapas_alvo_sem_nut(_rotulo_sem_nut(), X_INICIO)
    for x in TRASTES_X.values():
        assert alvo[2][96, int(x)] == pytest.approx(1.0)
    assert alvo[2][96, 500] < 0.01


def test_mapas_alvo_sem_nut_recusa_rotulo_com_nut():
    """Rótulo com traste de número 0 (nut) é recusado, para não virar alvo errado."""
    rotulo = _rotulo_sem_nut()
    rotulo["trastes"].append([0, 100.0, 95.0])
    with pytest.raises(ValueError, match="nut"):
        mapas_alvo_sem_nut(rotulo, X_INICIO)


def test_treinar_aceita_classe_itens_com_padrao_itens():
    """``_treinar`` ganhou ``classe_itens``, com ``_Itens`` como padrão."""
    parametro = inspect.signature(_treinar).parameters["classe_itens"]
    assert parametro.default is _Itens
