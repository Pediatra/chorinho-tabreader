"""Gerador sintético do braço (``tab.maos_braco_sintetico``): registro e geometria."""

from __future__ import annotations

import random

import numpy as np
import pytest

from tab.maos_braco_sintetico import (
    DIMENSOES,
    TRASTE_JUNCAO,
    TRASTES_MINIMOS_NO_QUADRO,
    gerar,
    trastes_no_plano,
)
from tab.maos_braco_tempo import marcas_do_registro


def _fundo(altura: int = 1080, largura: int = 1920) -> np.ndarray:
    """Fundo liso e cinza, do tamanho dado.

    Args:
        altura: altura em px.
        largura: largura em px.

    Returns:
        Imagem BGR uint8.
    """
    return np.full((altura, largura, 3), 90, dtype=np.uint8)


@pytest.mark.parametrize("semente", range(10))
def test_registro_valido_para_marcas_do_registro(semente: int) -> None:
    """O registro passa em ``marcas_do_registro``, com trastes contíguos a partir do 1."""
    imagem, registro = gerar(random.Random(semente), _fundo())
    marcas = marcas_do_registro(registro)
    assert marcas is not None
    jf = TRASTE_JUNCAO[registro["classe"]]
    assert registro["casa_juncao"] == jf
    assert sorted(marcas.trastes) == list(range(1, jf + 1))
    distancias = [
        float(np.linalg.norm(marcas.trastes[n] - marcas.nut)) for n in range(1, jf + 1)
    ]
    assert distancias == sorted(distancias)
    assert imagem.shape == (DIMENSOES[1], DIMENSOES[0], 3)
    assert imagem.dtype == np.uint8


@pytest.mark.parametrize("semente", range(10))
def test_trastes_dentro_do_quadro(semente: int) -> None:
    """O nut e pelo menos 8 trastes ficam dentro do quadro."""
    _, registro = gerar(random.Random(semente), _fundo())
    marcas = marcas_do_registro(registro)
    largura, altura = DIMENSOES
    pontos = np.array([marcas.trastes[n] for n in marcas.trastes])
    dentro = (
        (pontos[:, 0] >= 0)
        & (pontos[:, 0] < largura)
        & (pontos[:, 1] >= 0)
        & (pontos[:, 1] < altura)
    )
    assert int(dentro.sum()) >= TRASTES_MINIMOS_NO_QUADRO
    assert 0 <= marcas.nut[0] < largura and 0 <= marcas.nut[1] < altura


def test_razao_do_traste_5_no_plano() -> None:
    """No plano, (t5 - t0) / (t12 - t0) fica entre 0,4 e 0,6 (a regra das 12 notas)."""
    t = trastes_no_plano(12)
    assert 0.4 < (t[5] - t[0]) / (t[12] - t[0]) < 0.6


def test_as_duas_classes_aparecem() -> None:
    """As duas classes saem do sorteio (clássico e aço)."""
    classes = {
        gerar(random.Random(s), _fundo(720, 1280))[1]["classe"] for s in range(12)
    }
    assert classes == {"classico", "aco"}


def test_registro_e_deterministico_com_a_semente() -> None:
    """A mesma semente dá o mesmo registro e a mesma imagem."""
    img_a, reg_a = gerar(random.Random(7), _fundo())
    img_b, reg_b = gerar(random.Random(7), _fundo())
    assert reg_a == reg_b
    assert np.array_equal(img_a, img_b)
