"""Faixa retificada do braço (``tab.maos_braco_faixa``): ida e volta, erro e braços."""

from __future__ import annotations

import math
import random

import numpy as np
import pytest

from tab.maos.braco.faixa import (
    ALTURA_FAIXA,
    LARGURA_FAIXA,
    aplicar_matriz,
    aplicar_perturbacao,
    eixo_da_faixa,
    matriz_da_faixa,
    perturbar,
    recortar,
    rotulo_na_faixa,
    sortear_perturbacao,
    voltar,
)
from tab.maos.braco.regra import s_do_traste
from tab.maos.braco.tempo import Marcas

#: Comprimento do braço de teste, em px.
COMPRIMENTO = 800.0
#: Largura do braço de teste (distância entre as cordas 1 e 6), em px.
LARGURA = 43.0


def _braco(angulo: float, origem: tuple[float, float] = (100.0, 96.0)) -> Marcas:
    """Braço sintético: nut na origem, cordas paralelas e trastes da regra das 12 notas.

    Args:
        angulo: rotação do braço, em radianos (0 é horizontal).
        origem: posição do nut, em px.

    Returns:
        Marcas com nut, trastes 1 a 12 e as cordas 1 e 6.
    """
    o = np.asarray(origem, dtype=float)
    u = np.array([math.cos(angulo), math.sin(angulo)])
    n = np.array([-u[1], u[0]])

    def ponto(s: float, p: float) -> np.ndarray:
        return o + s * u + p * n

    trastes = {
        numero: ponto(COMPRIMENTO * s_do_traste(numero), 0.0) for numero in range(1, 13)
    }
    return Marcas(
        nut=o,
        trastes=trastes,
        corda1=np.array([ponto(0.0, -LARGURA / 2), ponto(COMPRIMENTO, -LARGURA / 2)]),
        corda6=np.array([ponto(0.0, LARGURA / 2), ponto(COMPRIMENTO, LARGURA / 2)]),
    )


def test_ida_e_volta_com_e_sem_erro() -> None:
    """Pontos levados à faixa e de volta voltam ao lugar (erro abaixo de 1e-6)."""
    rng = random.Random(1)
    pontos = np.array([[rng.uniform(0, 1920), rng.uniform(0, 1080)] for _ in range(50)])
    eixo = eixo_da_faixa(_braco(0.3))
    for eixo_usado in (eixo, perturbar(eixo, random.Random(2))):
        matriz = matriz_da_faixa(eixo_usado)
        volta = voltar(aplicar_matriz(matriz, pontos), matriz)
        assert np.max(np.abs(volta - pontos)) < 1e-6


def test_braco_horizontal_cai_nos_lugares_da_faixa() -> None:
    """Nut em x = 1024 * 0,12 / 1,17; extremo em 1024 * 1,12 / 1,17; cordas em y = 64, 128."""
    marcas = _braco(0.0)
    matriz = matriz_da_faixa(eixo_da_faixa(marcas))
    nut = aplicar_matriz(matriz, marcas.nut)
    assert nut[0] == pytest.approx(LARGURA_FAIXA * 0.12 / 1.17, abs=1e-6)
    assert nut[1] == pytest.approx(ALTURA_FAIXA / 2, abs=1e-6)
    cordas = aplicar_matriz(matriz, marcas.corda1)
    assert cordas[:, 1] == pytest.approx([64.0, 64.0], abs=1e-6)
    cordas6 = aplicar_matriz(matriz, marcas.corda6)
    assert cordas6[:, 1] == pytest.approx([128.0, 128.0], abs=1e-6)
    extremo = aplicar_matriz(matriz, marcas.corda1[1])
    assert extremo[0] == pytest.approx(LARGURA_FAIXA * 1.12 / 1.17, abs=1e-6)


def test_braco_diagonal_e_o_mesmo_da_horizontal() -> None:
    """Um braço girado e transladado rende a mesma faixa e os mesmos rótulos."""
    horizontal = _braco(0.0)
    angulo = math.radians(30.0)
    diagonal = _braco(angulo, origem=(400.0, 300.0))
    rotulo_h = rotulo_na_faixa(horizontal, matriz_da_faixa(eixo_da_faixa(horizontal)))
    rotulo_d = rotulo_na_faixa(diagonal, matriz_da_faixa(eixo_da_faixa(diagonal)))
    assert np.allclose(rotulo_h["corda1"], rotulo_d["corda1"], atol=1e-6)
    assert np.allclose(rotulo_h["corda6"], rotulo_d["corda6"], atol=1e-6)
    assert np.allclose(
        [p[1:] for p in rotulo_h["trastes"]],
        [p[1:] for p in rotulo_d["trastes"]],
        atol=1e-6,
    )


def test_largura_e_medida_no_nut_e_no_extremo() -> None:
    """A largura do eixo é a distância entre as cordas, com o braço reto."""
    _, _, comprimento, largura = eixo_da_faixa(_braco(0.0))
    assert comprimento == pytest.approx(COMPRIMENTO, abs=1e-6)
    assert largura == pytest.approx(LARGURA, abs=1e-6)


def test_sorteio_fica_dentro_dos_limites() -> None:
    """Todo erro sorteado respeita os limites do pré-registro 1021."""
    rng = random.Random(20261021)
    for _ in range(500):
        p = sortear_perturbacao(rng)
        assert abs(p["perpendicular"]) <= 0.3
        assert abs(p["ao_longo"]) <= 0.05
        assert abs(p["rotacao_graus"]) <= 3.0
        assert abs(p["escala"]) <= 0.10


def test_erro_zero_nao_muda_o_eixo() -> None:
    """Com erro nulo, o eixo sai igual."""
    eixo = eixo_da_faixa(_braco(0.2))
    zero = {"perpendicular": 0.0, "ao_longo": 0.0, "rotacao_graus": 0.0, "escala": 0.0}
    origem, u, comprimento, largura = aplicar_perturbacao(eixo, zero)
    assert np.allclose(origem, eixo[0], atol=1e-9)
    assert np.allclose(u, eixo[1], atol=1e-9)
    assert comprimento == pytest.approx(eixo[2], abs=1e-9)
    assert largura == pytest.approx(eixo[3], abs=1e-9)


def test_trastes_previstos_batem_com_os_do_gabarito() -> None:
    """Com o braço exato, a regra das 12 notas acerta os trastes a menos de 0,2 px."""
    marcas = _braco(0.1)
    rotulo = rotulo_na_faixa(marcas, matriz_da_faixa(eixo_da_faixa(marcas)))
    previstos = {int(p[0]): p[1:] for p in rotulo["trastes_previstos"]}
    reais = {int(p[0]): p[1:] for p in rotulo["trastes"] if p[0] > 0}
    for numero in range(1, 13):
        assert np.allclose(previstos[numero], reais[numero], atol=0.2)


def test_recortar_tem_o_tamanho_da_faixa() -> None:
    """A faixa sai com 192 x 1024 px, com borda 0 onde não há quadro."""
    imagem = np.full((1080, 1920, 3), 200, dtype=np.uint8)
    faixa = recortar(imagem, matriz_da_faixa(eixo_da_faixa(_braco(0.0))))
    assert faixa.shape == (ALTURA_FAIXA, LARGURA_FAIXA, 3)
