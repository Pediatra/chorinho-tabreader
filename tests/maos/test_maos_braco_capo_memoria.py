"""Testes da rodada 1048 (``tab.maos.braco.capo_memoria``), sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np

from tab.maos.braco.capo_memoria import levar
from tab.maos.braco.tempo import Marcas


def _textura(semente: int) -> np.ndarray:
    """Quadro de teste com textura aleatória (muitos pontos ORB).

    Args:
        semente: semente do ruído.

    Returns:
        Imagem BGR 480 x 640.
    """
    rng = np.random.default_rng(semente)
    pequeno = rng.integers(0, 255, (60, 80), dtype=np.uint8)
    grande = np.kron(pequeno, np.ones((8, 8), dtype=np.uint8))
    return np.dstack([grande] * 3)


def _marcas(dx: float) -> Marcas:
    """Braço horizontal de teste, deslocado de dx px.

    Args:
        dx: deslocamento horizontal.

    Returns:
        As marcas.
    """
    return Marcas(
        nut=np.array([100.0 + dx, 240.0]),
        trastes={n: np.array([100.0 + dx + 40.0 * n, 240.0]) for n in range(1, 10)},
        corda1=np.array([[100.0 + dx, 200.0], [600.0 + dx, 200.0]]),
        corda6=np.array([[100.0 + dx, 280.0], [600.0 + dx, 280.0]]),
    )


def test_levar_segue_o_deslocamento():
    chave = _textura(1)
    alvo = np.roll(chave, 12, axis=1)
    ponto = levar(chave, _marcas(0), [200.0, 240.0], alvo, _marcas(12), 10)
    assert ponto is not None
    assert abs(ponto[0] - 212.0) < 2.0 and abs(ponto[1] - 240.0) < 2.0


def test_levar_recusa_imagens_sem_relacao():
    chave, alvo = _textura(1), _textura(2)
    assert levar(chave, _marcas(0), [200.0, 240.0], alvo, _marcas(0), 10) is None
