"""Pico de linha na borda do recorte é moldura, não corda.

Medido no `sky guitar` (`(henze) nocturno`, t=228 s): a faixa `topo` tem a partitura (5
linhas) e a tablatura embaixo. O detector pegou as 5 da partitura **mais a borda preta em
y=1**, fechou 6 cordas, passou no portão e leu 112 tokens da partitura — 66 % do que saiu
era bolinha de nota e número de digitação.
"""

from __future__ import annotations

import numpy as np

from tab.tabseg import _picos_de_linha


def _tinta_com_linhas(linhas: list[int], altura: int = 60, largura: int = 120):
    tinta = np.zeros((altura, largura), np.uint8)
    for y in linhas:
        tinta[y, :] = 255
    return tinta


def test_pico_na_borda_e_descartado() -> None:
    """A linha em y=1 (borda) não pode contar como corda."""
    picos = _picos_de_linha(_tinta_com_linhas([1, 20, 26, 32, 38, 44]))
    ys = [round(y) for _v, y in picos]
    assert 1 not in ys, f"a borda entrou como corda: {ys}"
    assert len(ys) == 5, f"esperava as 5 linhas reais, veio {ys}"


def test_cinco_linhas_mais_borda_nao_viram_seis_cordas() -> None:
    """É este o caso que enganava: 5 linhas de pauta + borda davam '6 cordas'."""
    picos = _picos_de_linha(_tinta_com_linhas([1, 10, 16, 22, 28, 34]))
    assert len([y for _v, y in picos]) == 5


def test_linhas_no_meio_continuam_sendo_achadas() -> None:
    """O filtro não pode cegar o detector para linhas legítimas."""
    picos = _picos_de_linha(_tinta_com_linhas([15, 25, 35, 45, 55]))
    ys = sorted(round(y) for _v, y in picos)
    assert len(ys) == 5, ys
    # a suavização de 3 amostras desloca o pico em até 1 px: o que importa é achar as 5
    for esperado, achado in zip([15, 25, 35, 45, 55], ys, strict=True):
        assert abs(achado - esperado) <= 1, (esperado, achado)
