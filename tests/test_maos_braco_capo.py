"""Testes da casa do capo por vídeo (``tab.maos_braco_capo``). Sem acervo."""

from __future__ import annotations

import pytest

from tab.maos_braco_capo import casa_da_observacao, juntar, sem_capo


@pytest.mark.parametrize(
    ("obs", "casa"),
    [
        ("previsto (sinalizado) capotraste casa 3", 3),
        ("capotraste na casa 2", 2),
        ("capostraste casa 1", 1),
        ("visto (não sinalizado) capotraste 6 casa", 6),
        ("só metade da boca, capotraste na 2 casa", 2),
        ("previsto (sinalizado), capotraste 1 casa", 1),
        ("previsto (sinalizado) 2 braços", None),
        ("", None),
        (None, None),
    ],
)
def test_casa_da_observacao(obs, casa):
    assert casa_da_observacao(obs) == casa


def test_juntar_por_video_so_com_capo_marcado():
    registros = [
        ("m32:q01", "k/a.mp4", {"capo": [1, 2], "obs": "capotraste 6 casa"}),
        ("m32:q02", "k/a.mp4", {"capo": [1, 2], "obs": "capotraste 6 casa"}),
        ("m32:q03", "k/a.mp4", {"capo": None, "obs": "capotraste 6 casa"}),
        ("m36:q01", "v/b.mp4", {"capo": [1, 2], "obs": "capotraste casa 3"}),
        ("m36:q02", "v/b.mp4", {"capo": [1, 2], "obs": "capotraste casa 4"}),
        ("m11b:q01", "x/c.mp4", {"capo": [1, 2], "obs": ""}),
    ]
    por = {v["arquivo"]: v for v in juntar(registros)}
    assert por["k/a.mp4"]["casa"] == 6
    assert por["k/a.mp4"]["casas"] == {"6": ["m32:q01", "m32:q02"]}
    assert por["v/b.mp4"]["casa"] is None
    assert por["v/b.mp4"]["conflito"] is True
    assert por["x/c.mp4"]["casa"] is None
    assert por["x/c.mp4"]["casas"] == {"?": ["m11b:q01"]}
    assert por["x/c.mp4"]["conflito"] is False


def test_sem_capo_e_o_controle_negativo():
    registros = [
        ("a:q1", "k/a.mp4", {"capo": [1, 2], "braco": "sim", "corda1": [[0, 0]]}),
        ("a:q2", "k/a.mp4", {"capo": None, "braco": "sim", "corda1": [[0, 0]]}),
        ("a:q3", "k/b.mp4", {"capo": None, "braco": "sim", "corda1": [[0, 0]]}),
        ("a:q4", "k/c.mp4", {"capo": None, "braco": "nao", "corda1": None}),
    ]
    assert sem_capo(registros) == ["k/b.mp4"]
