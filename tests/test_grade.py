"""Agrupamento de glifos em tokens (a regra de fusão por corda).

Sem esta regra a razão medida era 1,44 glifo por nota — `12` virava `1` + `2` e
`<7>` virava `<` + `7` + `>`, cada pedaço recebendo o rótulo do token inteiro
(acurácia de treino 0,58). O intervalo entre notas distintas é >= 1 passo.
"""

from __future__ import annotations

from tab.tabseg import Glifo, agrupar_tokens

PASSO = 20.0  # gap de fusão = 0,25 * passo = 5 px


def _glifo(x0: int, x1: int, corda: int = 1, coluna: int = 0) -> Glifo:
    """Glifo de teste: só a geometria horizontal importa para a fusão."""
    return Glifo(
        x0=x0, y0=0, x1=x1, y1=10, corda=corda, coluna=coluna, area=(x1 - x0) * 10
    )


def test_funde_componentes_colados_na_mesma_corda() -> None:
    """`1` e `2` quase colados viram um token só (o `12`)."""
    tokens = agrupar_tokens([_glifo(100, 108), _glifo(110, 118)], PASSO)
    assert len(tokens) == 1
    assert tokens[0].partes == 2
    assert (tokens[0].x0, tokens[0].x1) == (100, 118)


def test_separa_notas_com_intervalo_de_um_passo() -> None:
    """Notas distintas estão a >= 1 passo e não podem ser fundidas."""
    tokens = agrupar_tokens([_glifo(100, 108), _glifo(130, 138)], PASSO)
    assert len(tokens) == 2


def test_nao_funde_cordas_diferentes() -> None:
    """Glifos sobrepostos em x mas em cordas distintas são notas distintas."""
    tokens = agrupar_tokens(
        [_glifo(100, 108, corda=1), _glifo(105, 113, corda=2)], PASSO
    )
    assert len(tokens) == 2
    assert {t.corda for t in tokens} == {1, 2}


def test_limite_exato_do_gap() -> None:
    """O limite é inclusivo: gap de exatamente 0,25 passo funde, 1 px a mais separa."""
    assert len(agrupar_tokens([_glifo(100, 108), _glifo(113, 120)], PASSO)) == 1
    assert len(agrupar_tokens([_glifo(100, 108), _glifo(114, 120)], PASSO)) == 2
