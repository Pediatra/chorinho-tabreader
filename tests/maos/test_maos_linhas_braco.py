"""Testes das funções puras de linhas do braço (M3c). Sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos.linhas_braco import (
    achar_linhas,
    mapa_retificacao,
    perfil_linhas,
    pico_na_janela,
    ruido_do_perfil,
)


def _imagem_com_linhas(
    altura: int, largura: int, linhas_h: list[float], linhas_v: list[float]
) -> np.ndarray:
    """Fundo escuro com linhas claras horizontais e verticais, em posições dadas.

    Args:
        altura: altura, em pixels.
        largura: largura, em pixels.
        linhas_h: ``y`` (em pixels) das linhas horizontais, claras.
        linhas_v: ``x`` (em pixels) das linhas verticais, claras.

    Returns:
        Imagem ``float32`` com fundo 40 e linhas 200.
    """
    img = np.full((altura, largura), 40.0, dtype=np.float32)
    for y in linhas_h:
        img[round(y), :] = 200.0
    for x in linhas_v:
        img[:, round(x)] = 200.0
    return img


def test_mapa_retificacao_e_a_inversa_de_h_vezes_escala() -> None:
    """O mapa leva um pixel da retificada ao pixel da imagem que H dá para ``(u, v)``."""
    H = np.array([[800.0, 30.0, 1100.0], [-10.0, 700.0, 520.0], [3e-4, -1e-4, 1.0]])
    ku, kv, u0, v0 = 2000.0, 800.0, -0.03, -0.2
    M = mapa_retificacao(H, ku, kv, u0, v0)
    x, y = 300.0, 150.0
    origem = np.linalg.inv(M) @ np.array([x, y, 1.0])
    origem = origem[:2] / origem[2]
    u, v = u0 + x / ku, v0 + y / kv
    esperado = H @ np.array([u, v, 1.0])
    esperado = esperado[:2] / esperado[2]
    assert np.allclose(origem, esperado)


def test_perfil_horizontal_acha_a_linha_clara() -> None:
    """A linha clara horizontal aparece como pico no perfil em ``y``."""
    img = _imagem_com_linhas(200, 300, linhas_h=[57.0], linhas_v=[])
    perfil = perfil_linhas(img, "horizontal", (50, 250), janela=21)
    assert int(np.argmax(perfil)) == 57


def test_perfil_vertical_acha_a_linha_clara() -> None:
    """A linha clara vertical aparece como pico no perfil em ``x``."""
    img = _imagem_com_linhas(200, 300, linhas_h=[], linhas_v=[123.0])
    perfil = perfil_linhas(img, "vertical", (20, 180), janela=11)
    assert int(np.argmax(perfil)) == 123


def test_perfil_recusa_orientacao_desconhecida() -> None:
    """Uma orientação fora de horizontal e vertical é recusada."""
    with pytest.raises(ValueError):
        perfil_linhas(np.zeros((10, 10)), "diagonal", (0, 10), janela=3)


def test_pico_com_refino_parabolico_e_subpixel() -> None:
    """Um pico entre dois índices sai com a posição fracionária do vértice."""
    perfil = np.array([0.0, 1.0, 4.0, 5.0, 3.0, 0.0, 0.0])
    pico = pico_na_janela(perfil, centro=3.0, meia=2.0)
    assert pico is not None
    assert 2.5 < pico["posicao"] < 3.5
    assert pico["contraste"] == pytest.approx(5.0)
    assert pico["sinal_pico"] == 1


def test_pico_fora_da_janela_nao_conta() -> None:
    """Um pico forte fora da janela prevista não é achado."""
    perfil = np.zeros(100)
    perfil[80] = 10.0
    assert pico_na_janela(perfil, centro=20.0, meia=5.0) is None


def test_pico_abaixo_do_minimo_nao_conta() -> None:
    """Contraste igual ou menor que o mínimo não conta como linha."""
    perfil = np.zeros(50)
    perfil[25] = 2.0
    assert pico_na_janela(perfil, centro=25.0, meia=3.0, minimo=2.0) is None
    assert pico_na_janela(perfil, centro=25.0, meia=3.0, minimo=1.0) is not None


def test_pico_qualquer_sinal_acha_linha_escura() -> None:
    """Com ``sinal="qualquer"`` a linha escura (negativa) é achada, com ``sinal_pico=-1``."""
    perfil = np.zeros(40)
    perfil[12] = -6.0
    pico = pico_na_janela(perfil, centro=12.0, meia=3.0, sinal="qualquer")
    assert pico is not None
    assert pico["sinal_pico"] == -1
    assert pico_na_janela(perfil, centro=12.0, meia=3.0, sinal="claro") is None


def test_pico_recusa_sinal_desconhecido() -> None:
    """Um sinal que não é ``claro`` nem ``qualquer`` é recusado."""
    with pytest.raises(ValueError):
        pico_na_janela(np.zeros(10), centro=5.0, meia=2.0, sinal="azul")


def test_achar_linhas_marca_as_achadas_e_as_que_faltam() -> None:
    """Cada posição prevista sai com ``achado`` verdadeiro ou falso, sem trocar a ordem."""
    perfil = np.zeros(200)
    perfil[50] = 8.0
    perfil[150] = 8.0
    saida = achar_linhas(
        perfil,
        previstos=[50.0, 100.0, 151.0],
        meias=[3.0, 3.0, 3.0],
        sinal="claro",
        minimo=1.0,
    )
    assert [s["achado"] for s in saida] == [True, False, True]
    assert saida[0]["posicao"] == pytest.approx(50.0)
    assert saida[1]["posicao"] is None
    assert saida[2]["previsto"] == 151.0


def test_achar_linhas_recusa_listas_de_tamanhos_diferentes() -> None:
    """Previstos e meias precisam ter o mesmo tamanho."""
    with pytest.raises(ValueError):
        achar_linhas(np.zeros(10), [1.0, 2.0], [1.0], "claro", 0.0)


def test_ruido_do_perfil_e_robusto_a_um_pico_forte() -> None:
    """Um pico isolado quase não muda o ruído estimado pelo desvio mediano."""
    rng = np.random.default_rng(0)
    base = rng.normal(0.0, 1.0, size=500)
    limpo = ruido_do_perfil(base)
    base[250] = 1000.0
    assert ruido_do_perfil(base) == pytest.approx(limpo, rel=0.05)
