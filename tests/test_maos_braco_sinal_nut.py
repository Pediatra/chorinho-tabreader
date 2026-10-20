"""Testes do sinal de nut suspeito v2 (rodada 1033), com imagens sintéticas."""

import numpy as np

from tab.maos_braco_sinal_nut import distancia_da_ponta, linhas_de_painel, suspeito


def _tela_dividida() -> np.ndarray:
    """Quadro 720 x 1280: painel claro em cima (até y = 300) e escuro embaixo.

    Returns:
        Imagem BGR uint8.
    """
    imagem = np.full((720, 1280, 3), 40, dtype=np.uint8)
    imagem[:300] = 230
    return imagem


def _previsto(x_nut: float, y_nut: float) -> dict:
    """Braço horizontal com o nut em ``(x_nut, y_nut)`` e as cordas a ±30 px.

    Args:
        x_nut: x do nut.
        y_nut: y do nut.

    Returns:
        Previsão com ``nut``, ``corda1`` e ``corda6``.
    """
    return {
        "achou": True,
        "nut": [x_nut, y_nut],
        "corda1": [[x_nut, y_nut - 30], [100.0, y_nut - 30]],
        "corda6": [[x_nut, y_nut + 30], [100.0, y_nut + 30]],
    }


def test_linha_de_painel_horizontal_e_achada():
    """A divisão entre os painéis vira linha de painel; a borda do quadro não."""
    ys, xs = linhas_de_painel(_tela_dividida())
    assert ys and all(abs(y - 299) <= 3 for y in ys)
    assert xs == []
    ys_lisa, xs_lisa = linhas_de_painel(np.full((720, 1280, 3), 90, dtype=np.uint8))
    assert ys_lisa == [] and xs_lisa == []


def test_ponta_rente_ao_painel_e_suspeita():
    """A ponta das cordas a 5 px do painel é suspeita; longe de tudo, não."""
    paineis = linhas_de_painel(_tela_dividida())
    perto = distancia_da_ponta(_previsto(900.0, 335.0), (1280, 720), paineis)
    assert perto is not None and perto <= 10
    assert suspeito(perto, (1280, 720), 0.02)
    longe = distancia_da_ponta(_previsto(900.0, 500.0), (1280, 720), paineis)
    assert not suspeito(longe, (1280, 720), 0.02)


def test_sem_nut_e_suspeito_e_borda_do_quadro_conta():
    """Sem nut é suspeito; a ponta rente à borda do quadro também."""
    assert suspeito(None, (1280, 720), 0.02)
    distancia = distancia_da_ponta(_previsto(1270.0, 500.0), (1280, 720), ([], []))
    assert distancia == 10.0
    assert suspeito(distancia, (1280, 720), 0.02)
