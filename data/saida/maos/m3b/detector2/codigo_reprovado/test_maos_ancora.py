"""Funções puras da âncora da mão (M3b): disco, direção, varredura, trastes, numeração."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_ancora_geometria import (
    achar_cordas,
    achar_trastes,
    amostrar,
    base_do_braco,
    media_de_orientacoes,
    numerar_trastes,
    perfil_longitudinal,
    pontas,
    raio_do_disco,
    tamanho_da_mao,
    tensor_da_orientacao,
    x_da_casa,
)


def _mao(largura: float, altura: float) -> np.ndarray:
    """21 pontos espalhados numa caixa ``largura`` x ``altura`` (canto em 0,0)."""
    pts = np.zeros((21, 2))
    pts[:, 0] = np.linspace(0, largura, 21)
    pts[:, 1] = np.linspace(0, altura, 21)
    return pts


def test_tamanho_e_raio_da_mao():
    pts = _mao(200.0, 120.0)
    assert tamanho_da_mao(pts) == pytest.approx(200.0)
    assert raio_do_disco(pts) == pytest.approx(100.0)


def test_pontas_sao_indicador_medio_anelar_minimo():
    pts = np.arange(42, dtype=float).reshape(21, 2)
    pp = pontas(pts)
    assert pp.shape == (4, 2)
    assert pp[0].tolist() == pts[8].tolist()
    assert pp[3].tolist() == pts[20].tolist()


def _listras(theta_graus: float, n: int = 64) -> np.ndarray:
    """Imagem com listras finas paralelas a ``theta_graus``."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    r = np.radians(theta_graus)
    dist = -xx * np.sin(r) + yy * np.cos(r)
    return np.cos(2 * np.pi * dist / 8.0)


@pytest.mark.parametrize("theta", [0.0, 30.0, 60.0, 120.0])
def test_tensor_recupera_direcao_das_listras(theta):
    img = _listras(theta)
    gy, gx = np.gradient(img)
    got, coer = tensor_da_orientacao(gx, gy, np.array([32.0, 32.0]), 20.0)
    diff = abs((got - theta + 90.0) % 180.0 - 90.0)
    assert diff < 3.0
    assert coer > 0.8


def test_tensor_fora_da_imagem_da_zero():
    gx = np.zeros((10, 10))
    assert tensor_da_orientacao(gx, gx, np.array([500.0, 500.0]), 5.0) == (0.0, 0.0)


def test_media_de_orientacoes_trata_180_graus_como_mesma_reta():
    theta, coer = media_de_orientacoes([(2.0, 1.0), (178.0, 1.0)])
    diff = abs((theta - 0.0 + 90.0) % 180.0 - 90.0)
    assert diff < 1e-6
    assert coer > 0.9


def test_base_do_braco_u_para_direita_e_n_para_baixo():
    u, n = base_do_braco(170.0)
    assert u[0] > 0
    assert n[1] > 0
    assert np.dot(u, n) == pytest.approx(0.0, abs=1e-12)


def test_amostrar_interpola_e_zera_fora():
    img = np.arange(16, dtype=float).reshape(4, 4)
    v = amostrar(img, np.array([1.5, 10.0]), np.array([1.0, 0.0]))
    assert v[0] == pytest.approx(img[1, 1] + 0.5)
    assert v[1] == 0.0


def test_perfil_longitudinal_mostra_corda_reta():
    img = np.zeros((80, 80))
    img[30, :] = 1.0  # corda horizontal em y = 30
    t, perfil = perfil_longitudinal(
        img,
        np.array([40.0, 40.0]),
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
        30.0,
        20.0,
    )
    assert t[np.argmax(perfil)] == pytest.approx(-10.0)


def test_achar_cordas_pega_grupo_de_espacamento_parecido():
    t = np.arange(-100.0, 101.0)
    perfil = np.zeros_like(t)
    cordas = [-40.0, -28.0, -16.0, -4.0, 8.0, 20.0]
    for c in cordas:
        perfil[int(c + 100)] = 1.0
    perfil[60 + 100] = 0.9  # pico isolado, espaçamento diferente
    achadas = achar_cordas(t, perfil, minimo_frac=0.5, distancia=5)
    assert len(achadas) == 6
    assert achadas[0] == pytest.approx(-40.0)
    assert achadas[-1] == pytest.approx(20.0)


def test_achar_cordas_sem_grupo_devolve_vazio():
    t = np.arange(0.0, 50.0)
    perfil = np.zeros_like(t)
    perfil[[5, 30]] = 1.0
    assert achar_cordas(t, perfil) == []


def test_achar_trastes_acha_picos_do_perfil():
    s = np.arange(0.0, 200.0)
    sinal = np.zeros_like(s)
    for c in (30, 70, 110, 150):
        sinal[c] = 1.0
    assert achar_trastes(s, sinal, distancia=10) == [30.0, 70.0, 110.0, 150.0]


def test_x_da_casa_segue_lei_das_12_notas():
    assert x_da_casa(0) == pytest.approx(0.0)
    assert x_da_casa(12) == pytest.approx(0.5)


def _trastes_ideais(comprimento: float, numeros: list[int]) -> list[float]:
    """Posições ``s`` de trastes ideais (sem perspectiva) para uns números."""
    return [comprimento * (1 - 2 ** (-n / 12)) for n in numeros]


@pytest.mark.parametrize("sentido", ["crescente", "decrescente"])
def test_numerar_trastes_recupera_sentido_e_residuo_zero(sentido):
    numeros = [3, 4, 5, 6, 7, 8]
    s = _trastes_ideais(1000.0, numeros)
    if sentido == "decrescente":
        s = [1000.0 - v for v in s][::-1]
    res = numerar_trastes(s)
    assert res is not None
    assert res["sentido"] == sentido
    assert res["residuo"] < 1e-3
    numeros_achados = res["numeros"]
    # numeros consecutivos, na ordem de s; o deslocamento absoluto NAO e identificavel
    assert np.all(np.diff(numeros_achados) == (1 if sentido == "crescente" else -1))


def test_numerar_trastes_deslocamento_nao_e_identificavel():
    """Mesmo resíduo zero para outro deslocamento: a lei das 12 notas é projetiva.

    Por isso o número do primeiro traste (e a posição do nut) não sai só dos trastes;
    precisa de âncora externa (o nut visível ou um traste de referência).
    """
    s = _trastes_ideais(1000.0, [3, 4, 5, 6, 7, 8])
    res_a = numerar_trastes(s, max_inicio=0)
    res_b = numerar_trastes(s, max_inicio=12)
    assert res_a is not None and res_b is not None
    assert res_b["residuo"] <= res_a["residuo"] + 1e-6


def test_numerar_trastes_exige_quatro():
    assert numerar_trastes([10.0, 20.0, 30.0]) is None


def test_base_e_eixo_coerentes_com_tensor():
    u, _ = base_do_braco(45.0)
    assert np.hypot(*u) == pytest.approx(1.0)
