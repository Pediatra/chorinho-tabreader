"""Testes da casa do capo pela imagem (``tab.maos_braco_capo_imagem``, rodada 1038)."""

from __future__ import annotations

import pytest

from tab.maos_braco_capo_imagem import (
    casa_do_video,
    classificar_video,
    fracoes,
    voto_do_quadro,
)


def _previsto(nut_x: float, trastes_x: list[float], sinal: bool = False) -> dict:
    """Braço horizontal: cordas em y = 10 e y = 30, nut e trastes em y = 20."""
    return {
        "achou": True,
        "sinalizado": sinal,
        "nut": [nut_x, 20.0],
        "corda1": [[nut_x, 10.0], [500.0, 10.0]],
        "corda6": [[nut_x, 30.0], [500.0, 30.0]],
        "trastes": [
            {"numero": n, "ponto": [x, 20.0]} for n, x in enumerate(trastes_x, start=1)
        ],
    }


#: Antigo: nut verdadeiro em x = 0 e trastes a cada ~40 px.
ANTIGO = _previsto(0.0, [40.0, 78.0, 114.0, 148.0, 180.0])


def test_voto_capo_na_casa_3():
    novo = _previsto(116.0, [150.0, 181.0])
    assert voto_do_quadro(ANTIGO, novo) == 3


def test_voto_zero_quando_os_dois_acham_o_mesmo_nut():
    assert voto_do_quadro(ANTIGO, _previsto(2.0, [41.0])) == 0


def test_sem_voto_entre_trastes_ou_com_sinal():
    assert voto_do_quadro(ANTIGO, _previsto(96.0, [150.0])) is None
    assert voto_do_quadro(ANTIGO, _previsto(116.0, [150.0], sinal=True)) is None
    sem = dict(ANTIGO, achou=False)
    assert voto_do_quadro(sem, _previsto(116.0, [150.0])) is None


@pytest.mark.parametrize(
    ("votos", "casa"),
    [
        ([3, 3, 3, 3, None, 2], 3),
        ([3, 3, None, None, None], None),  # poucos válidos
        ([3, 3, 2, 2, 1], None),  # sem maioria de 60 %
        ([0, 0, 0, 0, 3], None),  # maioria 0 é "nada visto"
    ],
)
def test_casa_do_video(votos, casa):
    assert casa_do_video(votos) == casa


def test_classificar_video():
    assert classificar_video(3, 3) == "acerto"
    assert classificar_video(2, 3) == "erro"
    assert classificar_video(2, 0) == "erro"
    assert classificar_video(None, 3) == "sem_dado"
    assert classificar_video(None, 0) == "sem_dado"
    assert classificar_video(3, None) == "sem_verdade"


def test_fracoes():
    f = fracoes(16)
    assert f[0] == 0.1
    assert f[-1] == 0.9
    assert len(f) == 16
