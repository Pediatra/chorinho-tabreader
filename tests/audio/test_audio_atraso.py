"""Testes da medição de atraso (`tab/audio_atraso.py`): agrupamento, janelas, pico e borda.

Sem acervo, sem GPU e sem ffmpeg: as entradas são listas de notas e arrays pequenos.
"""

import numpy as np
import pytest

from tab.audio.atraso import (
    TETO_JANELA_S,
    agrupar_eventos,
    janelas,
    na_borda,
    pico_mais_proximo,
)


def _nota(tela, exibicao, passagem, coluna, corda, casa, t_ini):
    """Nota mínima do produto, com os campos usados pelo agrupamento.

    Args:
        tela: id da tela.
        exibicao: índice da exibição.
        passagem: índice da passagem.
        coluna: coluna.
        corda: corda de 1 a 6.
        casa: casa pisada.
        t_ini: instante do marcador, ou ``None``.

    Returns:
        Dicionário no formato de ``notas`` do produto.
    """
    return {
        "tela": tela,
        "exibicao": exibicao,
        "passagem": passagem,
        "coluna": coluna,
        "corda": corda,
        "casa": casa,
        "t_ini": t_ini,
    }


def test_acorde_e_um_evento_e_mesma_coluna_em_passagens_diferentes_sao_dois():
    """Notas da mesma (tela, exibição, passagem, coluna) viram um evento; passagens distintas,
    dois eventos, mesmo com a mesma coluna."""
    notas = [
        _nota(1, 0, 1, 5, 1, 0, 2.0),
        _nota(1, 0, 1, 5, 3, 2, 2.0),
        _nota(1, 0, 1, 5, 6, 0, 2.0),
        _nota(1, 0, 2, 5, 2, 1, 4.0),
    ]
    eventos = agrupar_eventos(notas)
    assert len(eventos) == 2
    assert eventos[0].t_ini == 2.0
    assert eventos[0].notas == ((1, 0), (3, 2), (6, 0))
    assert eventos[1].passagem == 2
    assert eventos[1].notas == ((2, 1),)


def test_nota_sem_t_ini_e_ignorada_e_eventos_saem_ordenados():
    """Nota com ``t_ini`` None não entra; a saída segue a ordem de tempo."""
    notas = [
        _nota(1, 0, 1, 1, 1, 0, 5.0),
        _nota(1, 0, 1, 2, 1, 0, None),
        _nota(1, 0, 1, 3, 1, 0, 3.0),
    ]
    eventos = agrupar_eventos(notas)
    assert [e.t_ini for e in eventos] == [3.0, 5.0]


def test_acorde_com_t_ini_diferentes_falha():
    """Notas da mesma coluna com instantes distintos são erro, não um evento escondido."""
    notas = [_nota(1, 0, 1, 1, 1, 0, 2.0), _nota(1, 0, 1, 1, 2, 0, 2.5)]
    with pytest.raises(ValueError):
        agrupar_eventos(notas)


def test_janelas_de_meia_distancia_com_teto():
    """Meia-distância até o vizinho de cada lado; teto de 0,30 s; sem vizinho, o teto."""
    assert TETO_JANELA_S == 0.30
    larguras = janelas([1.0, 1.2, 3.0])
    assert larguras[0] == pytest.approx((TETO_JANELA_S, 0.1))
    assert larguras[1] == pytest.approx((0.1, 0.3))
    assert larguras[2] == pytest.approx((0.3, TETO_JANELA_S))


def test_janela_respeita_o_teto_com_vizinho_longe():
    """Vizinho a 2 s não estende a janela além de 0,30 s."""
    larguras = janelas([0.0, 2.0])
    assert larguras[0] == pytest.approx((TETO_JANELA_S, TETO_JANELA_S))
    assert larguras[1] == pytest.approx((TETO_JANELA_S, TETO_JANELA_S))


def test_pico_mais_proximo_dentro_da_janela():
    """Entre os picos dentro de [a, b], vence o mais próximo do centro; fora, não conta."""
    tp = np.array([0.95, 1.03, 1.2])
    j = pico_mais_proximo(tp, 0.9, 1.1, 1.0)
    assert j == 1
    assert pico_mais_proximo(tp, 1.4, 1.6, 1.5) is None


def test_pico_mais_proximo_do_centro_na_passada_2():
    """O centro desloca a escolha: com centro em 0,94, o pico 0,95 vence."""
    tp = np.array([0.95, 1.03])
    assert pico_mais_proximo(tp, 0.9, 1.1, 0.94) == 0


def test_na_borda_so_perto_de_um_quadro():
    """Pico a menos de um quadro de uma borda marca na_borda; no meio não."""
    quadro = 256 / 22050
    assert na_borda(1.0 + 0.5 * quadro, 1.0, 1.3, quadro) is True
    assert na_borda(1.3 - 0.5 * quadro, 1.0, 1.3, quadro) is True
    assert na_borda(1.15, 1.0, 1.3, quadro) is False
