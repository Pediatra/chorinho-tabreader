"""Testes das funções puras do tempo da mão direita (sem GPU e sem acervo)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tab.maos_direita_tempo import (
    PAINEL_ALTURA,
    PAINEL_LARGURA,
    correlacao_por_atraso,
    desenhar_grafico,
    energia_movimento,
    escolher_trechos,
    instantes_distintos,
    janelas_sincronizadas,
    metade_inferior_direita,
    percentil,
    pico_da_curva,
    picos_embaralhados,
    recorte_do_painel,
    trem_de_notas,
    zscore,
)

FPS = 30.0


def _quadros_com_pulso(n: int, eventos: list[int]) -> np.ndarray:
    """Quadros cinza com um bloco que muda de posição em cada evento.

    Args:
        n: quantidade de quadros.
        eventos: quadros em que o bloco se move (a mudança aparece nesse quadro).

    Returns:
        Array ``uint8`` ``(n, PAINEL_ALTURA, PAINEL_LARGURA)``.
    """
    quadros = np.zeros((n, PAINEL_ALTURA, PAINEL_LARGURA), dtype=np.uint8)
    for k in range(n):
        deslocamento = 2 * sum(1 for e in eventos if e <= k)
        quadros[k, 100:140, 40 + deslocamento : 80 + deslocamento] = 255
    return quadros


def test_recorte_do_painel_na_referencia_e_escalado() -> None:
    assert recorte_do_painel(1920, 1080) == (655, 558, 0, 522)
    assert recorte_do_painel(960, 540) == (328, 279, 0, 261)


def test_energia_zero_em_quadro_parado_e_positiva_em_movimento() -> None:
    parado = np.full((5, 10, 10), 7, dtype=np.uint8)
    assert np.allclose(energia_movimento(parado), 0.0)
    movendo = _quadros_com_pulso(10, [5])
    e = energia_movimento(movendo)
    assert len(e) == 10
    assert e[5] > 0
    assert np.allclose(e[1:4], 0.0)


def test_energia_exige_dois_quadros() -> None:
    with pytest.raises(ValueError):
        energia_movimento(np.zeros((1, 4, 4), dtype=np.uint8))


def test_metade_inferior_direita_tem_a_forma_certa() -> None:
    q = np.zeros((3, 280, 328), dtype=np.uint8)
    recorte = metade_inferior_direita(q)
    assert recorte.shape == (3, 140, 164)


def test_zscore_normaliza_e_zera_constante() -> None:
    z = zscore(np.array([1.0, 2.0, 3.0, 4.0]))
    assert abs(z.mean()) < 1e-12
    assert abs(z.std() - 1.0) < 1e-12
    assert np.allclose(zscore(np.ones(5)), 0.0)


def test_trem_de_notas_marca_o_quadro_mais_proximo() -> None:
    n = trem_de_notas([10.0, 10.5], inicio=9.0, fps=FPS, n_quadros=100)
    assert n[30] == 1.0
    assert n[45] == 1.0
    assert n.sum() == 2.0


def test_trem_de_notas_ignora_instantes_fora_do_vetor() -> None:
    n = trem_de_notas([0.0, 100.0], inicio=1.0, fps=FPS, n_quadros=10)
    assert n.sum() == 0.0


def test_instantes_distintos_ignora_sem_tempo_e_arredonda() -> None:
    notas = [
        {"t_ini": 1.00004},
        {"t_ini": 1.00001},
        {"t_ini": None},
        {"corda": 2},
        {"t_ini": 2.5},
    ]
    assert instantes_distintos(notas) == [1.0, 2.5]


def test_escolher_trechos_dentro_da_faixa_e_deterministico() -> None:
    instantes = list(np.arange(10.0, 300.0, 0.5))
    primeiro = escolher_trechos(instantes, semente=20261015)
    assert primeiro == escolher_trechos(instantes, semente=20261015)
    assert len(primeiro) == 3
    assert primeiro == sorted(primeiro)
    for s in primeiro:
        assert instantes[0] <= s
        assert s + 20.0 <= instantes[-1]


def test_escolher_trechos_sem_instantes_suficientes() -> None:
    assert escolher_trechos([]) == []
    assert escolher_trechos([1.0]) == []
    assert escolher_trechos([1.0, 5.0]) == []


def test_correlacao_acha_atraso_conhecido() -> None:
    n_quadros = 400
    n = np.zeros(n_quadros)
    n[[60, 120, 200, 260]] = 1.0
    # Movimento em cada nota, 6 quadros depois, espalhado em 3 quadros.
    e = np.zeros(n_quadros)
    for k in (60, 120, 200, 260):
        e[k + 6 - 1 : k + 6 + 2] += [0.5, 1.0, 0.5]
    e += 0.01 * np.random.default_rng(0).random(n_quadros)
    r = correlacao_por_atraso(e, n, 40, 300, lag=15)
    lags = np.arange(-15, 16)
    atraso, pico = pico_da_curva(r, lags / FPS)
    assert atraso == pytest.approx(6 / FPS)
    assert pico > 0.5


def test_picos_embaralhados_ficam_abaixo_do_pico_real() -> None:
    n_quadros = 400
    n = np.zeros(n_quadros)
    n[[60, 120, 200, 260]] = 1.0
    e = np.zeros(n_quadros)
    for k in (60, 120, 200, 260):
        e[k + 5 : k + 8] += [0.5, 1.0, 0.5]
    e += 0.01 * np.random.default_rng(1).random(n_quadros)
    real = float(np.max(correlacao_por_atraso(e, n, 40, 300, lag=15)))
    nulos = picos_embaralhados(e, n, 40, 300, 15, FPS, n_desloc=50)
    assert nulos.shape == (50,)
    assert percentil(real, nulos) == pytest.approx(100.0)


def test_percentil_conta_valores_abaixo() -> None:
    ref = np.array([0.1, 0.2, 0.3, 0.4])
    assert percentil(0.25, ref) == pytest.approx(50.0)
    assert percentil(0.0, ref) == 0.0


def test_janelas_sincronizadas_centradas_e_descartam_as_da_borda() -> None:
    e_z = np.arange(100, dtype=float)
    j = janelas_sincronizadas(e_z, np.array([10, 50, 99]), lag=3)
    assert j.shape == (2, 7)
    assert j[0].tolist() == [7, 8, 9, 10, 11, 12, 13]
    assert janelas_sincronizadas(e_z, np.array([0]), lag=3).shape == (0, 7)


def test_desenhar_grafico_grava_png(tmp_path) -> None:
    lags = np.linspace(-0.5, 0.5, 31)
    curvas = {
        "a": np.sin(lags * 10),
        "b": np.cos(lags * 10),
    }
    caminho = tmp_path / "tempo.png"
    desenhar_grafico(curvas, lags, caminho)
    img = cv2.imread(str(caminho))
    assert img is not None
    assert img.shape[:2] == (600, 1000)
