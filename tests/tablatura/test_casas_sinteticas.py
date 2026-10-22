"""Quais casas o gerador sorteia? Duas listas, uma oficial e uma experimental.

`oficial` (padrão) é a lista que gerou os pesos `oficial_*` e a régua de 0,949: se ela
mudar, o comando registrado em `artefatos/LEIA-ME.md` deixa de reproduzir os pesos.
`todas` (0-24, `--casas todas`) é a experimental que gerou `casas24_*`. Medido em
2026-10-10: a lista oficial nunca desenhava as casas 11, 13, 16, 18, 20, 22 e 23.
"""

from __future__ import annotations

import inspect

import pytest

from tab.tablatura.treino.sintetico import (
    CASAS_OFICIAIS,
    CASAS_TODAS,
    LISTAS_CASAS,
    _parser,
    gerar_linha,
)

ANTIGAS_CASAS = (
    0,
    0,
    0,
    1,
    1,
    2,
    2,
    3,
    3,
    4,
    5,
    5,
    6,
    7,
    8,
    9,
    10,
    12,
    12,
    14,
    15,
    17,
    19,
    21,
    24,
)


@pytest.mark.parametrize("lista", [CASAS_OFICIAIS, CASAS_TODAS])
def test_casas_baixas_continuam_com_mais_peso(lista: tuple[int, ...]) -> None:
    """As casas 0-5 são as mais comuns no acervo; não podem virar minoria."""
    baixas = sum(1 for casa in lista if casa <= 5)
    assert baixas / len(lista) >= 0.35


def test_lista_oficial_e_a_de_antes_de_f76e73ca() -> None:
    """A lista padrão tem que ser EXATAMENTE a antiga, senão a régua 0,949 não reproduz."""
    assert CASAS_OFICIAIS == ANTIGAS_CASAS
    assert set(CASAS_OFICIAIS) == {
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        12,
        14,
        15,
        17,
        19,
        21,
        24,
    }


def test_lista_todas_desenha_de_0_a_24() -> None:
    """A experimental tem que cobrir todas as casas 0-24, e manter as antigas."""
    assert set(CASAS_TODAS) == set(range(25))
    assert set(ANTIGAS_CASAS) <= set(CASAS_TODAS)


def test_padrao_do_gerador_e_a_lista_oficial() -> None:
    """Sem argumento, `gerar_linha` e a CLI usam a lista oficial."""
    assert inspect.signature(gerar_linha).parameters["casas"].default is CASAS_OFICIAIS
    assert _parser().parse_args([]).casas == "oficial"
    assert LISTAS_CASAS["oficial"] is CASAS_OFICIAIS


def test_flag_casas_seleciona_a_lista_todas() -> None:
    """`--casas todas` é a única forma de sair da lista oficial."""
    assert _parser().parse_args(["--casas", "todas"]).casas == "todas"
    assert LISTAS_CASAS["todas"] is CASAS_TODAS
