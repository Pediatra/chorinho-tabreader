"""Testes das funções puras das cordas pela mediana e do pente (M7, item 3; sem GPU)."""

from __future__ import annotations

from itertools import pairwise

import cv2
import numpy as np
import pytest

from tab.maos.direita.cordas_pente import (
    alinhar_quadros,
    amostrar_indices,
    estimar_afim,
    mediana_temporal,
    params_por_ancoras,
    resposta_linha_fina,
    retas_do_pente,
    transformar_reta,
)


def test_retas_do_pente_seis_em_ordem_com_6_em_cima() -> None:
    retas = retas_do_pente((-0.9, 0.0, 200.0, 30.0, 0.0), 655)
    assert [c for c, _, _ in retas] == [1, 2, 3, 4, 5, 6]
    ys = [m * 327.5 + q for _, m, q in retas]
    assert ys[5] < ys[0]
    assert np.allclose(np.diff(ys), -30.0)


def test_retas_do_pente_com_perspectiva_muda_o_espacamento_com_x() -> None:
    retas = retas_do_pente((-0.9, 0.0, 200.0, 30.0, -0.5), 600)
    espaco_esq = [q - q2 for (_, _m, q), (_, _m2, q2) in pairwise(retas)]
    espaco_dir = [
        (m * 600 + q) - (m2 * 600 + q2) for (_, m, q), (_, m2, q2) in pairwise(retas)
    ]
    assert abs(espaco_esq[0]) > abs(espaco_dir[0])


def test_ancoras_recuperam_o_modelo_que_as_gerou() -> None:
    largura = 655
    params = (-0.95, 0.0, 230.0, 36.0, -0.3)
    retas = retas_do_pente(params, largura)
    meio = largura / 2.0
    ancoras = {c: (m, m * meio + q) for c, m, q in retas if c >= 4}
    m0, kappa, y0, d, rho = params_por_ancoras(ancoras, largura)
    assert m0 == pytest.approx(-0.95, abs=1e-6)
    assert kappa == 0.0
    assert y0 == pytest.approx(230.0, abs=1e-4)
    assert d == pytest.approx(36.0, abs=1e-4)
    assert rho == pytest.approx(-0.3, abs=1e-4)


def test_transformar_reta_identidade_e_translacao() -> None:
    identidade = np.float32([[1, 0, 0], [0, 1, 0]])
    theta, y = transformar_reta(-0.5, 120.0, identidade, 600)
    assert theta == pytest.approx(np.arctan(np.tan(-0.5)), abs=1e-6)
    assert y == pytest.approx(120.0, abs=1e-6)
    deslocada = np.float32([[1, 0, 7.0], [0, 1, -4.0]])
    _theta2, y2 = transformar_reta(-0.5, 120.0, deslocada, 600)
    # O ponto (300, 120) vai para (307, 116); a reta em x = 300 passa por
    # 116 - m * 7 = 116 + tan(0,5) * 7.
    assert y2 == pytest.approx(116.0 + np.tan(0.5) * 7.0, abs=1e-4)


def test_resposta_de_linha_fina_positiva_na_linha_clara_e_zero_no_fundo() -> None:
    img = np.zeros((120, 200), dtype=np.float32)
    m, q = 0.5, 30.0
    for x in range(200):
        y = int(np.rint(m * x + q))
        if 0 <= y < 120:
            img[y, x] = 200.0
    resp = resposta_linha_fina(img, m, q)
    assert resp.size > 0
    assert resp.mean() > 100.0
    assert np.abs(resposta_linha_fina(np.zeros_like(img), m, q)).max() == 0.0


def test_resposta_de_degrau_largo_fica_perto_de_zero() -> None:
    img = np.zeros((120, 200), dtype=np.float32)
    img[:, 100:] = 200.0
    resp = resposta_linha_fina(img, 0.0, 60.0)
    assert np.abs(resp[20:-20]).max() < 1.0


def test_mediana_ignora_nan_e_zera_pixel_sem_dado() -> None:
    pilha = np.full((3, 2, 2, 3), np.nan, dtype=np.float32)
    pilha[0, 0, 0] = 10.0
    pilha[1, 0, 0] = 30.0
    pilha[2, 0, 0] = 200.0
    med = mediana_temporal(pilha)
    assert med[0, 0, 0] == 30
    assert med[1, 1, 1] == 0


def test_amostrar_indices_espalha_e_inclui_as_pontas() -> None:
    idx = amostrar_indices(100, 5)
    assert len(idx) == 5
    assert idx[0] == 0
    assert idx[-1] == 99
    assert np.all(np.diff(idx) > 0)
    assert list(amostrar_indices(3, 10)) == [0, 1, 2]


def test_estimar_afim_recupera_translacao_de_textura() -> None:
    rng = np.random.default_rng(20261015)
    ref = rng.integers(0, 256, size=(300, 300), dtype=np.uint8)
    ref = cv2.GaussianBlur(ref, (3, 3), 0)
    # quadro = referência deslocada por (+10, -6): a afim do quadro para a referência
    # tem translação (-10, +6).
    quadro = np.roll(np.roll(ref, 10, axis=1), -6, axis=0)
    orb = cv2.ORB_create(nfeatures=1500)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref_kp, ref_des = orb.detectAndCompute(ref, None)
    m, n_in = estimar_afim(orb, bf, ref_kp, ref_des, quadro)
    assert m is not None
    assert n_in > 40
    assert m[0, 2] == pytest.approx(-10.0, abs=1.0)
    assert m[1, 2] == pytest.approx(6.0, abs=1.0)


def test_alinhar_quadros_marca_invalidos_e_preserva_tamanho() -> None:
    rng = np.random.default_rng(1)
    base = cv2.GaussianBlur(
        rng.integers(0, 256, size=(200, 200, 3), dtype=np.uint8), (3, 3), 0
    )
    quadros = np.stack([base, base, np.zeros_like(base)])
    pilha, validos, medidas = alinhar_quadros(quadros)
    assert pilha.shape == quadros.shape
    assert validos[0] and validos[1]
    assert not validos[2]
    assert len(medidas) == 3
    assert np.isnan(pilha[2]).all()


def test_resposta_linha_fina_usa_distancia_perpendicular() -> None:
    # Com m = 0 a distância perpendicular é a vertical; uma linha a 2 px não conta no centro.
    img = np.zeros((60, 60), dtype=np.float32)
    img[30, :] = 255.0
    centro = resposta_linha_fina(img, 0.0, 30.0)
    assert centro.mean() == pytest.approx(255.0, abs=1e-3)
    deslocada = resposta_linha_fina(img, 0.0, 32.0)
    assert deslocada.mean() < 0.0
