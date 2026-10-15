"""Testes das funções puras da média sincronizada ao t_audio (M7; sem GPU e sem acervo)."""

from __future__ import annotations

import pytest

from tab.maos_direita_tempo_audio import instantes_no_trecho, pico_media


def test_instantes_no_trecho_usa_inicio_fechado_e_fim_aberto() -> None:
    instantes = [9.9, 10.0, 15.0, 29.99, 30.0]
    assert instantes_no_trecho(instantes, 10.0) == [10.0, 15.0, 29.99]


def test_pico_media_devolve_atraso_e_valor_do_maximo() -> None:
    lags = [-0.1, -0.05, 0.0, 0.05, 0.1]
    curva = [0.1, 0.3, 0.9, 0.2, 0.0]
    r = pico_media(curva, lags)
    assert r["atraso_s"] == pytest.approx(0.0)
    assert r["valor"] == pytest.approx(0.9)
