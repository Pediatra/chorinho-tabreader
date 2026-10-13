"""Testes puros da calibração do braço pelas notas (M3c). Sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_calibrar_por_notas import (
    Conjunto,
    aplicar_homografia,
    avaliar,
    coordenadas_do_braco,
    dlt_homografia,
    pontas_com_recuo,
    pontas_esquerdas,
    ransac,
    s_traste,
    u_casa,
    v_corda,
)

#: Homografia de teste: quase identidade, com perspectiva e escala de pixels.
H_VERDADEIRA = np.array(
    [
        [820.0, 35.0, 1200.0],
        [-18.0, 760.0, 540.0],
        [4.5e-4, -2.0e-4, 1.0],
    ]
)


def _conjunto_sintetico(
    n: int, frac_errada: float, semente: int, ruido_px: float = 0.3
) -> Conjunto:
    """Notas com uma ponta verdadeira (com ruído) e, às vezes, uma ponta errada.

    Args:
        n: número de notas.
        frac_errada: fração das notas cuja ponta candidata extra é errada.
        semente: semente do gerador de números.
        ruido_px: desvio do ruído nas pontas verdadeiras, em px.

    Returns:
        Um :class:`Conjunto` com duas candidatas por nota (a verdadeira e a errada,
        ou duas verdadeiras-com-ruído quando ``frac_errada`` é 0).
    """
    rng = np.random.default_rng(semente)
    cordas = rng.integers(1, 7, size=n)
    casas = rng.integers(1, 13, size=n)
    uv = np.array(
        [
            coordenadas_do_braco(int(c), int(k))
            for c, k in zip(cordas, casas, strict=True)
        ]
    )
    verdade = aplicar_homografia(H_VERDADEIRA, uv)
    verdade = verdade + rng.normal(0.0, ruido_px, size=verdade.shape)
    falsa = rng.uniform([0.0, 0.0], [1900.0, 1000.0], size=(n, 2))
    usar_falsa = rng.random(n) < frac_errada
    cand = np.zeros((n, 2, 2))
    cand[:, 0] = verdade
    cand[:, 1] = np.where(usar_falsa[:, None], falsa, verdade + 0.5)
    mascara = np.ones((n, 2), dtype=bool)
    return Conjunto(
        indices=np.arange(n),
        corda=cordas,
        casa=casas,
        t=np.zeros(n),
        uv=uv,
        cand=cand,
        mascara=mascara,
    )


def _erro_entre_h(h1: np.ndarray, h2: np.ndarray) -> float:
    """Maior diferença, em px, entre duas homografias sobre pontos do braço.

    Args:
        h1: primeira homografia.
        h2: segunda homografia.

    Returns:
        Distância máxima entre as projeções de uma grade de pontos do braço.
    """
    us = np.linspace(0.0, s_traste(12), 9)
    vs = np.linspace(0.0, 1.0, 5)
    pontos = np.array([(u, v) for u in us for v in vs])
    a = aplicar_homografia(h1, pontos)
    b = aplicar_homografia(h2, pontos)
    return float(np.max(np.linalg.norm(a - b, axis=1)))


def test_dlt_recupera_homografia_sintetica() -> None:
    """Com correspondências exatas, a DLT devolve a própria H (escala 1 em H[2,2])."""
    rng = np.random.default_rng(1)
    origem = rng.uniform(0.0, 1.0, size=(8, 2))
    destino = aplicar_homografia(H_VERDADEIRA, origem)
    H = dlt_homografia(origem, destino)
    assert H[2, 2] == pytest.approx(1.0)
    assert _erro_entre_h(H, H_VERDADEIRA / H_VERDADEIRA[2, 2]) < 1e-6


def test_dlt_exige_quatro_correspondencias() -> None:
    """Menos de 4 pares não define uma homografia: a função recusa."""
    pontos = np.zeros((3, 2))
    with pytest.raises(ValueError):
        dlt_homografia(pontos, pontos)


def test_convencao_dos_70_por_cento() -> None:
    """A casa k fica a 70 % do caminho do traste k-1 ao traste k, em u."""
    s0, s1, s2 = s_traste(0), s_traste(1), s_traste(2)
    assert s0 == pytest.approx(0.0)
    assert s1 == pytest.approx(1 - 2 ** (-1 / 12))
    assert u_casa(1) == pytest.approx(s0 + 0.7 * (s1 - s0))
    assert u_casa(2) == pytest.approx(s1 + 0.7 * (s2 - s1))
    assert u_casa(3, frac=0.5) == pytest.approx(
        s_traste(2) + 0.5 * (s_traste(3) - s_traste(2))
    )


def test_cordas_e_casas_fora_do_dominio_recusam() -> None:
    """Corda fora de 1..6 e casa 0 (corda solta, sem ponto) levantam erro."""
    with pytest.raises(ValueError):
        v_corda(0)
    with pytest.raises(ValueError):
        v_corda(7)
    with pytest.raises(ValueError):
        u_casa(0)


def test_v_da_corda_vai_de_0_a_1() -> None:
    """Corda 1 (aguda) fica em v = 0, corda 6 (grave) em v = 1."""
    assert v_corda(1) == 0.0
    assert v_corda(6) == 1.0
    assert coordenadas_do_braco(3, 5) == (u_casa(5), v_corda(3))


def test_tolerancia_e_meia_largura_da_casa() -> None:
    """Inlier se a ponta está a menos de meia largura prevista da casa, em px."""
    H = np.array([[100.0, 0.0, 10.0], [0.0, 100.0, 20.0], [0.0, 0.0, 1.0]])
    corda, casa = 2, 4
    u, v = coordenadas_do_braco(corda, casa)
    previsto = aplicar_homografia(H, np.array([[u, v]]))[0]
    largura = 100.0 * (s_traste(casa) - s_traste(casa - 1))
    tau = 0.5 * largura

    def conjunto(desloc: float) -> Conjunto:
        """Uma nota com uma ponta deslocada de ``desloc`` px, em x."""
        return Conjunto(
            indices=np.array([0]),
            corda=np.array([corda]),
            casa=np.array([casa]),
            t=np.array([0.0]),
            uv=np.array([[u, v]]),
            cand=np.array([[[previsto[0] + desloc, previsto[1]]]]),
            mascara=np.array([[True]]),
        )

    assert avaliar(H, conjunto(0.9 * tau))["n"] == 1
    assert avaliar(H, conjunto(1.1 * tau))["n"] == 0


def test_ransac_recupera_h_com_metade_das_pontas_erradas() -> None:
    """Com metade das pontas candidatas erradas, o RANSAC acha a H verdadeira."""
    c = _conjunto_sintetico(n=120, frac_errada=1.0, semente=7)
    resultado = ransac(c, semente=20261012, iteracoes=3000)
    assert _erro_entre_h(resultado["H"], H_VERDADEIRA / H_VERDADEIRA[2, 2]) < 1.0
    assert resultado["inliers"] >= 0.95 * len(c.indices)


def test_ransac_e_deterministico_pela_semente() -> None:
    """A mesma semente dá exatamente a mesma homografia."""
    c = _conjunto_sintetico(n=80, frac_errada=1.0, semente=3)
    a = ransac(c, semente=99, iteracoes=800)
    b = ransac(c, semente=99, iteracoes=800)
    assert np.array_equal(a["H"], b["H"])
    assert a["inliers"] == b["inliers"]


def _mao_esquerda(dip_em_none: bool = False) -> dict[str, object]:
    """Mão esquerda sintética: pontas em (100, 200) e DIPs 60 px acima delas.

    Args:
        dip_em_none: se ``True``, o DIP do indicador (keypoint 7) é ``None``.

    Returns:
        Registro de mão com ``lado`` e ``pts`` de 21 pontos.
    """
    pts: list[object] = [[0.0, 0.0] for _ in range(21)]
    for k in (8, 12, 16, 20):
        pts[k] = [100.0, 200.0]
        pts[k - 1] = [100.0, 140.0]
    if dip_em_none:
        pts[7] = None
    return {"lado": "esquerda", "pts": pts}


def test_recuo_zero_e_igual_a_ponta_pura() -> None:
    mao = _mao_esquerda()
    pura = pontas_esquerdas([mao])
    assert np.array_equal(pontas_esquerdas([mao], 0.0), pura)
    assert np.array_equal(pontas_com_recuo(mao, 0.0)[1], np.array([100.0, 200.0]))


def test_recuo_meio_vai_ao_ponto_medio_entre_ponta_e_dip() -> None:
    saida = pontas_com_recuo(_mao_esquerda(), 0.5)
    for dedo in (1, 2, 3, 4):
        assert saida[dedo] == pytest.approx((100.0, 170.0))


def test_dip_faltando_usa_a_ponta_pura() -> None:
    saida = pontas_com_recuo(_mao_esquerda(dip_em_none=True), 0.5)
    assert saida[1] == pytest.approx((100.0, 200.0))
    assert saida[2] == pytest.approx((100.0, 170.0))
