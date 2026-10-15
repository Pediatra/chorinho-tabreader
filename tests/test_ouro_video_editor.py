"""Folga acima da corda 1 no recorte das telas do ouro de vídeo (função pura, sem GPU)."""

import numpy as np

from tab.ouro_video import FOLGA_ACIMA_PASSOS, folga_acima_da_corda1


def test_folga_sobe_1_5_passo_acima_do_painel() -> None:
    """O topo sobe exatamente 1,5 passo; x e base não mudam."""
    assert folga_acima_da_corda1((100, 200, 900, 300), 20.0) == (100, 170, 900, 300)


def test_folga_arredonda_para_cima_e_nunca_fica_abaixo_de_1_5_passo() -> None:
    """1,5 x 15 = 22,5 px: sobe 23 px, não 22."""
    assert folga_acima_da_corda1((0, 100, 50, 150), 15.0) == (0, 77, 50, 150)


def test_folga_limitada_a_borda_superior() -> None:
    """Painel perto do topo do quadro: y0 para em 0, não fica negativo."""
    assert folga_acima_da_corda1((0, 10, 50, 150), 20.0) == (0, 0, 50, 150)


def test_folga_aceita_passo_numpy_e_devolve_int() -> None:
    """O passo vem de medição numpy; o retângulo tem de sair com inteiros (índice)."""
    x0, y0, x1, y1 = folga_acima_da_corda1((5, 200, 7, 300), np.float64(20.0))
    assert y0 == 170
    assert all(isinstance(v, int) for v in (x0, y0, x1, y1))


def test_constante_da_folga_e_1_5_passo() -> None:
    """A folga é o valor combinado com o dono (1,5 passo)."""
    assert FOLGA_ACIMA_PASSOS == 1.5
