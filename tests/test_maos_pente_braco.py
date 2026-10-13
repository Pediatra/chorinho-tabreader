"""Testes do pente do braço, com um braço sintético (sem acervo, sem GPU)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tab.maos_calibrar_por_notas import S_TRASTES, aplicar_homografia, v_corda
from tab.maos_pente_braco import (
    ajustar_cordas,
    ajustar_trastes,
    calibrar_por_pente,
    pares_do_pente,
    retificar_pente,
)

#: Homografia de partida (a da música): o braço cabe na imagem de 1920 x 1080.
H_PARTIDA = np.array([[1100.0, 40.0, 420.0], [-60.0, 520.0, 160.0], [1e-5, 0.0, 1.0]])

#: Verdade do braço, na frame da H de partida. As cordas ficam comprimidas 30% na
#: H de partida: o vão verdadeiro é 1/0,7 do nominal. O nut está deslocado 0,4 casa.
#: Com ``GAMA_VERDADE = 0`` o mapa verdadeiro é uma homografia, e o pente deve
#: recuperá-lo. Com ``gama != 0`` o mapa não é homografia (ver o teste de trastes).
A_VERDADE = 0.05
B_VERDADE = 1.0 / 0.7
ALFA_VERDADE = 1.0
BETA_VERDADE = 0.4 * float(S_TRASTES[1] - S_TRASTES[0])
GAMA_VERDADE = 0.0


def _u_do_traste(n: int, gama: float) -> float:
    """Posição, em ``u`` da verdade, do traste ``n`` (nut em ``n = 0``)."""
    return (ALFA_VERDADE * S_TRASTES[n] + BETA_VERDADE) / (gama * S_TRASTES[n] + 1.0)


def _pontos_da_verdade(gama: float = GAMA_VERDADE) -> np.ndarray:
    """Pixels, na imagem, de cada cruzamento (traste 0..12, corda 1..6) da verdade."""
    pontos = []
    for n in range(13):
        u_n = _u_do_traste(n, gama)
        for j in range(1, 7):
            pontos.append((u_n, A_VERDADE + B_VERDADE * (j - 1) / 5.0))
    return aplicar_homografia(H_PARTIDA, np.asarray(pontos))


def _braco_sintetico(gama: float = GAMA_VERDADE) -> np.ndarray:
    """Mediana sintética: cordas claras e trastes em tom médio sobre fundo escuro.

    Linhas de 1 px com antialias: o braço real tem traços finos, e um traço de 3 px
    vira faixa larga na retificada, que a janela de realce de 11 px não separa.
    """
    img = np.full((1080, 1920, 3), 40, dtype=np.uint8)
    us = np.linspace(-0.03, 0.6, 200)
    for j in range(1, 7):
        v = A_VERDADE + B_VERDADE * (j - 1) / 5.0
        pts = aplicar_homografia(H_PARTIDA, np.column_stack([us, np.full_like(us, v)]))
        cv2.polylines(
            img, [pts.astype(np.int32)], False, (220, 220, 220), 1, cv2.LINE_AA
        )
    vs = np.linspace(-0.6, 1.6, 200)
    for n in range(15):
        pts = aplicar_homografia(
            H_PARTIDA, np.column_stack([np.full_like(vs, _u_do_traste(n, gama)), vs])
        )
        cv2.polylines(
            img, [pts.astype(np.int32)], False, (130, 130, 130), 1, cv2.LINE_AA
        )
    return img


def _grade_da_h(H: np.ndarray) -> np.ndarray:
    """Pixels da grade de 13 trastes x 6 cordas, pela H dada (nominal)."""
    pontos = []
    for n in range(13):
        for j in range(1, 7):
            pontos.append((S_TRASTES[n], v_corda(j)))
    return aplicar_homografia(H, np.asarray(pontos))


@pytest.fixture(scope="module")
def braco() -> np.ndarray:
    """Mediana sintética (verdade homográfica), uma vez por módulo."""
    return _braco_sintetico(GAMA_VERDADE)


def test_pente_recupera_a_grade_de_um_braco_sintetico(braco: np.ndarray) -> None:
    H, resumo = calibrar_por_pente(H_PARTIDA, braco)
    erro = np.linalg.norm(_grade_da_h(H) - _pontos_da_verdade(), axis=1)
    assert erro.max() < 2.0, f"erro máximo {erro.max():.3f} px"
    assert abs(resumo["trastes"]["alfa"] - ALFA_VERDADE) < 0.002
    assert abs(resumo["trastes"]["beta"] - BETA_VERDADE) < 0.0005
    assert abs(resumo["trastes"]["gama"] - GAMA_VERDADE) < 0.002


def test_pente_acha_gama_com_trastes_nao_homograficos() -> None:
    gama = 0.1
    _, resumo = ajustar_trastes(retificar_pente(_braco_sintetico(gama), H_PARTIDA))
    assert abs(resumo["gama"] - gama) < 0.002
    assert abs(resumo["beta"] - BETA_VERDADE) < 0.0005


def test_pente_das_cordas_acha_o_vao_verdadeiro(braco: np.ndarray) -> None:
    retificada = retificar_pente(braco, H_PARTIDA)
    _, resumo = ajustar_cordas(retificada)
    for banda in resumo["bandas"]:
        assert abs(banda["a"] - A_VERDADE) < 0.005, banda
        assert abs(banda["b"] - B_VERDADE) < 0.01, banda
        assert banda["score"] > banda["score_musica"]


def test_pente_dos_trastes_acha_o_nut_verdadeiro(braco: np.ndarray) -> None:
    retificada = retificar_pente(braco, H_PARTIDA)
    (_alfa, beta, _gama), resumo = ajustar_trastes(retificada)
    assert abs(beta - BETA_VERDADE) < 0.0005
    assert resumo["score"] > resumo["score_musica"]


def test_so_trastes_deixa_as_cordas_como_a_musica(braco: np.ndarray) -> None:
    _H, resumo = calibrar_por_pente(H_PARTIDA, braco, componentes=("trastes",))
    assert "cordas" not in resumo
    origem, destino = pares_do_pente(H_PARTIDA, None, (1.0, 0.0, 0.0))
    assert np.allclose(destino, aplicar_homografia(H_PARTIDA, origem), atol=1e-6)


def test_componente_desconhecido_e_erro(braco: np.ndarray) -> None:
    with pytest.raises(ValueError):
        calibrar_por_pente(H_PARTIDA, braco, componentes=("nut",))


def test_pares_sem_pente_sao_a_propria_h() -> None:
    origem, destino = pares_do_pente(H_PARTIDA)
    assert origem.shape == (78, 2)
    assert np.allclose(destino, aplicar_homografia(H_PARTIDA, origem), atol=1e-9)
