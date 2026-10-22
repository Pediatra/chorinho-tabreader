"""Testes da janela que o ``tab.transcrever`` grava no JSON (``janela_s``).

A função ``janela_serie`` é pura: nenhum destes testes lê vídeo, GPU ou acervo.
"""

from __future__ import annotations

from tab.tablatura.produto.transcrever import janela_serie


def test_janela_serie_vai_de_t0_ate_t0_mais_a_janela():
    assert janela_serie(239.2, 30.0, 678.0) == (239.2, 269.2)


def test_janela_serie_e_cortada_na_duracao_do_video():
    assert janela_serie(660.0, 30.0, 678.0) == (660.0, 678.0)


def test_janela_serie_sem_duracao_conhecida_nao_corta():
    assert janela_serie(10.0, 30.0, 0.0) == (10.0, 40.0)
