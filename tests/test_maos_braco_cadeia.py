"""Testes sintéticos do rastreio em cadeia (M11b). Sem acervo e sem GPU."""

from __future__ import annotations

import cv2
import numpy as np

from tab.maos_braco_cadeia import (
    ParametrosCadeia,
    _caixa_do_braco,
    _janela_recuperacao,
    rastrear_cadeia,
)
from tab.maos_braco_tempo import Marcas

ALTURA = 480
LARGURA = 720


def _marcas() -> Marcas:
    """Marcas sintéticas de um braço horizontal, com cinco trastes numerados.

    Returns:
        Marcas com cordas 1 e 6 e trastes 1 a 5 no meio do quadro.
    """
    corda1 = np.array([[120.0, 200.0], [620.0, 215.0]])
    corda6 = np.array([[120.0, 290.0], [620.0, 305.0]])
    trastes = {n: np.array([160.0 + 90.0 * n, 250.0 + 0.5 * n]) for n in range(1, 6)}
    return Marcas(nut=None, trastes=trastes, corda1=corda1, corda6=corda6)


def _textura(semente: int) -> np.ndarray:
    """Imagem BGR de textura aleatória, com cantos suficientes para o ORB.

    Args:
        semente: semente do gerador.

    Returns:
        Imagem ``(ALTURA, LARGURA, 3)`` uint8.
    """
    rng = np.random.default_rng(semente)
    ruido = rng.integers(0, 256, size=(ALTURA, LARGURA), dtype=np.uint8)
    cinza = cv2.GaussianBlur(ruido, (3, 3), 0)
    return cv2.cvtColor(cinza, cv2.COLOR_GRAY2BGR)


def _deslocada(img: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Desloca a imagem por ``(dx, dy)`` px, com borda replicada.

    Args:
        img: imagem BGR.
        dx: deslocamento horizontal, em px.
        dy: deslocamento vertical, em px.

    Returns:
        Imagem deslocada.
    """
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(img, m, (LARGURA, ALTURA), borderMode=cv2.BORDER_REPLICATE)


def _params() -> ParametrosCadeia:
    """Parâmetros de teste: os padrões, com janela de recuperação maior.

    Returns:
        ``ParametrosCadeia`` para os testes sintéticos.
    """
    return ParametrosCadeia(folga_px=60, folga_recuperacao_px=200)


def test_caixa_do_braco_escolhe_o_painel_com_mais_braco() -> None:
    """Com duas caixas, a máscara da caixa é a que contém o braço, não a outra."""
    mascara = np.zeros((ALTURA, LARGURA), dtype=np.uint8)
    mascara[200:300, 100:300] = 255
    paineis = [[[0, 0], [360, 480]], [[360, 0], [720, 480]]]
    caixa = _caixa_do_braco(paineis, mascara)
    assert caixa is not None
    assert caixa[100, 50] == 255
    assert caixa[100, 500] == 0


def test_caixa_do_braco_sem_painel_e_quadro_inteiro() -> None:
    """Sem painel (``nao``) ou sem caixa com braço, não há máscara de caixa."""
    mascara = np.full((ALTURA, LARGURA), 255, dtype=np.uint8)
    assert _caixa_do_braco("nao", mascara) is None
    assert _caixa_do_braco(None, mascara) is None
    assert _caixa_do_braco([[[0, 0], [10, 10]]], np.zeros_like(mascara)) is None


def test_janela_recuperacao_respeita_a_caixa() -> None:
    """A janela de recuperação nunca sai da caixa do painel do braço."""
    mascara = np.zeros((ALTURA, LARGURA), dtype=np.uint8)
    mascara[200:300, 100:300] = 255
    caixa = np.zeros_like(mascara)
    caixa[:, :360] = 255
    janela = _janela_recuperacao(mascara, 100, caixa)
    assert np.count_nonzero(janela[:, 360:]) == 0
    assert janela[250, 200] == 255


def test_composicao_de_homografias_aplica_a_do_passo_depois_da_anterior() -> None:
    """``h_passo @ h_prev`` leva o quadro-chave ao passo novo, na ordem certa."""
    h_prev = np.array([[1.02, 0.01, 5.0], [0.0, 0.99, -3.0], [0.0, 0.0, 1.0]])
    h_passo = np.array([[1.0, 0.0, 12.0], [0.0, 1.0, -7.0], [0.0, 0.0, 1.0]])
    ponto = np.array([[[100.0, 200.0]]], dtype=np.float32)
    composta = cv2.perspectiveTransform(ponto, h_passo @ h_prev)
    em_dois_passos = cv2.perspectiveTransform(
        cv2.perspectiveTransform(ponto, h_prev), h_passo
    )
    assert np.allclose(composta, em_dois_passos, atol=1e-4)


def test_rastreio_acha_por_ancora_e_nao_acha_sem_casamento() -> None:
    """Um quadro deslocado é achado; uma textura sem relação com a chave, não."""
    chave = _textura(1)
    marcas = _marcas()
    alvo_bom = _deslocada(chave, 6.0, -4.0)
    alvo_ruim = _textura(2)
    h_bom, info_bom = rastrear_cadeia(
        [(1.0, alvo_bom)], chave, marcas, "nao", _params()
    )
    h_ruim, info_ruim = rastrear_cadeia(
        [(1.0, alvo_ruim)], chave, marcas, "nao", _params()
    )
    assert h_bom is not None
    assert info_bom["ancora"] + info_bom["ancora+cadeia"] == 1
    assert h_ruim is None
    assert info_ruim["perdido"] == 1


def test_estado_perdido_nao_volta_por_cadeia_so_por_ancora() -> None:
    """Depois de uma troca de plano, o quadro que casa só com o anterior não é "achei".

    Sequência: a chave, um quadro deslocado (acha), uma textura diferente (troca de
    plano, perdido), uma segunda textura deslocada (casa só com a anterior). A cadeia
    não pode recuperar o estado; o último quadro é "não achei".
    """
    chave = _textura(3)
    marcas = _marcas()
    antes = _deslocada(chave, 4.0, 2.0)
    troca = _textura(4)
    depois = _deslocada(troca, 3.0, 1.0)
    h, info = rastrear_cadeia(
        [(1.0, antes), (2.0, troca), (3.0, depois)], chave, marcas, "nao", _params()
    )
    assert h is None
    assert info["perdido"] >= 2


def test_estado_perdido_volta_por_ancora_direta() -> None:
    """Depois de perder o braço, um quadro que casa com a chave é "achei" de novo."""
    chave = _textura(5)
    marcas = _marcas()
    antes = _deslocada(chave, 4.0, 2.0)
    troca = _textura(6)
    volta = _deslocada(chave, 8.0, 3.0)
    h, info = rastrear_cadeia(
        [(1.0, antes), (2.0, troca), (3.0, volta)], chave, marcas, "nao", _params()
    )
    assert h is not None
    assert info["perdido"] == 1


def test_rastreio_e_determinista() -> None:
    """Duas chamadas com a mesma entrada dão a mesma homografia e o mesmo diagnóstico."""
    chave = _textura(7)
    marcas = _marcas()
    alvo = _deslocada(chave, 5.0, -3.0)
    h1, info1 = rastrear_cadeia([(1.0, alvo)], chave, marcas, "nao", _params())
    h2, info2 = rastrear_cadeia([(1.0, alvo)], chave, marcas, "nao", _params())
    assert h1 is not None and h2 is not None
    assert np.array_equal(h1, h2)
    assert info1 == info2
