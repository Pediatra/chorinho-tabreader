"""Colunas: o acorde (notas com o mesmo x) é UMA coluna e recebe UM onset (T1.4 do plano).

Medido no `sky guitar` (`retrato brasileiro`): as duas notas da coluna 1 (cordas 2 e 6, x_quadro 224)
receberam tempos diferentes (264,1 e 243,74 s), porque a célula de uma delas ficava vazia.
"""

from __future__ import annotations

import pytest

from tab.tablatura.produto.colunas import agrupar_colunas
from tab.tablatura.produto.estado import expandir_para_notas, onsets_por_coluna


def test_acorde_de_duas_notas_no_mesmo_x_vira_uma_coluna() -> None:
    """Duas notas com o mesmo x ficam numa coluna só, com x = esse x."""
    colunas = agrupar_colunas([224.0, 224.0, 269.0], passo=21.8)
    assert len(colunas) == 2
    assert colunas[0].indices == [0, 1]
    assert colunas[0].x_quadro == 224.0
    assert colunas[1].indices == [2]


def test_notas_acima_de_tol_vezes_passo_ficam_separadas() -> None:
    """Com passo 20 e tol 0,35 o limite é 7 px: 6 px junta, 8 px separa."""
    juntas = agrupar_colunas([100.0, 106.0], passo=20.0)
    separadas = agrupar_colunas([100.0, 108.0], passo=20.0)
    assert len(juntas) == 1
    assert juntas[0].indices == [0, 1]
    assert len(separadas) == 2


def test_colunas_saem_ordenadas_por_x_e_cobrem_todas_as_notas() -> None:
    """A entrada fora de ordem sai ordenada, e cada nota aparece em exatamente uma coluna."""
    xs = [300.0, 100.0, 301.0, 100.5, 200.0]
    colunas = agrupar_colunas(xs, passo=20.0)
    assert [c.x_quadro for c in colunas] == sorted(c.x_quadro for c in colunas)
    todos = sorted(i for c in colunas for i in c.indices)
    assert todos == list(range(len(xs)))


def test_passo_nao_positivo_e_recusado() -> None:
    """Sem passo válido não há tolerância: falha alto em vez de agrupar errado."""
    with pytest.raises(ValueError):
        agrupar_colunas([1.0, 2.0], passo=0.0)


def test_duas_notas_do_mesmo_x_recebem_o_mesmo_onset() -> None:
    """O caso medido: o acorde não pode deixar uma nota sem tempo."""
    xs = [224.0, 224.0, 269.0]
    colunas = agrupar_colunas(xs, passo=21.8)
    amostras = [
        {"t": 10.0, "x": 224},
        {"t": 11.0, "x": 269},
    ]
    por_coluna = onsets_por_coluna(amostras, colunas)
    por_nota = expandir_para_notas(por_coluna, colunas)
    assert por_nota[0] == por_nota[1] == 10.0
    assert por_nota[2] == 11.0


def test_marcador_por_tres_colunas_da_tres_onsets_crescentes() -> None:
    """Uma série que passa por 3 colunas dá 3 onsets, em ordem crescente de tempo."""
    colunas = agrupar_colunas([100.0, 200.0, 300.0], passo=20.0)
    amostras = [
        {"t": 0.0, "x": 100},
        {"t": 1.0, "x": 160},
        {"t": 2.0, "x": 260},
    ]
    por_coluna = onsets_por_coluna(amostras, colunas)
    assert sorted(por_coluna) == [0, 1, 2]
    tempos = [por_coluna[k] for k in sorted(por_coluna)]
    assert tempos == sorted(tempos)
    assert len(set(tempos)) == 3
