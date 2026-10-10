"""O gerador desenha TODAS as casas 0-24? Este teste guarda uma lacuna medida.

Medido em 2026-10-10: a lista de sorteio tinha só 18 casas distintas. As casas 11, 13,
16, 18, 20, 22 e 23 nunca eram desenhadas, então o modelo não tinha essas classes e o
`13` do ouro de vídeo não podia sair certo. Regra 6 do AGENTS.md: o gargalo é cobertura
do gerador, não regra de visão.
"""

from __future__ import annotations

from tab.sintetico import CASAS_SORTEAVEIS


def test_gerador_desenha_todas_as_casas_de_0_a_24() -> None:
    """Se uma casa sair da lista, o modelo perde a classe e ninguém percebe."""
    assert set(CASAS_SORTEAVEIS) == set(range(25))


def test_casas_antigas_continuam_na_lista() -> None:
    """A mudança só acrescenta casas; as que já existiam não podem sumir."""
    antigas = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 17, 19, 21, 24}
    assert antigas <= set(CASAS_SORTEAVEIS)


def test_casas_baixas_continuam_com_mais_peso() -> None:
    """As casas 0-5 são as mais comuns no acervo; não podem virar minoria."""
    baixas = sum(1 for casa in CASAS_SORTEAVEIS if casa <= 5)
    assert baixas / len(CASAS_SORTEAVEIS) >= 0.35
