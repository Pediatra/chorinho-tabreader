"""Testes do pareamento partitura x tab (funções puras; sem acervo e sem GPU)."""

from __future__ import annotations

import zipfile
from fractions import Fraction
from pathlib import Path

from tab.partitura_pareamento import (
    EventoPartitura,
    EventoTab,
    eventos_da_tab,
    parear,
    x_dos_compassos,
)


def _evento_partitura(indice: int, x: float | None, midis: set[int]) -> EventoPartitura:
    """Evento de partitura mínimo, para os testes de ``parear``."""
    return EventoPartitura(
        indice=indice,
        compasso=1,
        t=float(indice),
        t_global=float(indice),
        x_quadro=x,
        midis=frozenset(midis),
        simbolos=[],
    )


def _evento_tab(
    indice: int, x: float, midis: set[int], t_inis: list[float]
) -> EventoTab:
    """Evento de tab mínimo; cada nota recebe um ``t_ini`` da lista."""
    notas = [{"corda": 1, "casa": 0, "x_centro_quadro": x, "t_ini": t} for t in t_inis]
    return EventoTab(
        indice=indice,
        x_quadro=x,
        midis=frozenset(midis),
        notas=notas,
    )


def test_eventos_da_tab_agrupa_ate_seis_px_e_respeita_janela() -> None:
    notas = [
        {"corda": 6, "casa": 0, "x_centro_quadro": 100.0},  # E2 = 40, +12 = 52
        {"corda": 5, "casa": 0, "x_centro_quadro": 104.0},  # A2 = 45, +12 = 57
        {"corda": 1, "casa": 1, "x_centro_quadro": 150.0},  # F4 = 65, +12 = 77
        {"corda": 1, "casa": 0, "x_centro_quadro": 300.0},  # fora da janela
    ]
    eventos = eventos_da_tab(notas, x0=90.0, x1=200.0)
    assert [e.midis for e in eventos] == [frozenset({52, 57}), frozenset({77})]
    assert eventos[0].x_quadro == 102.0
    assert eventos[1].x_quadro == 150.0
    assert len(eventos[0].notas) == 2


def test_eventos_da_tab_limite_de_seis_px() -> None:
    no_limite = [
        {"corda": 6, "casa": 0, "x_centro_quadro": 100.0},
        {"corda": 5, "casa": 0, "x_centro_quadro": 106.0},
    ]
    alem = [
        {"corda": 6, "casa": 0, "x_centro_quadro": 100.0},
        {"corda": 5, "casa": 0, "x_centro_quadro": 107.0},
    ]
    assert len(eventos_da_tab(no_limite, 0.0, 200.0)) == 1
    assert len(eventos_da_tab(alem, 0.0, 200.0)) == 2


def test_parear_par_perfeito_herda_t_ini_e_confere_x() -> None:
    partitura = [
        _evento_partitura(0, 100.0, {52}),
        _evento_partitura(1, 120.0, {57}),
    ]
    tab = [
        _evento_tab(0, 101.0, {52}, [1.5, 1.5]),
        _evento_tab(1, 119.0, {57}, [2.0]),
    ]
    linhas = parear(partitura, tab, tolerancia_px=3.0)
    assert [linha["par_tab"] for linha in linhas] == [0, 1]
    assert linhas[0]["x_tab"] == 101.0
    assert linhas[0]["distancia_x"] == 1.0
    assert linhas[0]["confere_x"] is True
    assert linhas[0]["t_ini"] == [1.5]
    assert linhas[1]["t_ini"] == [2.0]


def test_parear_evento_a_mais_na_partitura_fica_sem_par() -> None:
    partitura = [
        _evento_partitura(0, 100.0, {52}),
        _evento_partitura(1, 110.0, {70}),
        _evento_partitura(2, 120.0, {57}),
    ]
    tab = [
        _evento_tab(0, 100.0, {52}, [1.0]),
        _evento_tab(1, 120.0, {57}, [2.0]),
    ]
    linhas = parear(partitura, tab, tolerancia_px=3.0)
    sem_par = linhas[1]
    assert sem_par["par_tab"] is None
    assert sem_par["x_tab"] is None
    assert sem_par["distancia_x"] is None
    assert sem_par["confere_x"] is None
    assert sem_par["t_ini"] == []
    assert [linha["par_tab"] for linha in linhas if linha["par_tab"] is not None] == [
        0,
        1,
    ]


def test_parear_confere_x_falso_acima_da_tolerancia() -> None:
    partitura = [_evento_partitura(0, 100.0, {52})]
    tab = [_evento_tab(0, 110.0, {52}, [1.0])]
    linha = parear(partitura, tab, tolerancia_px=5.0)[0]
    assert linha["distancia_x"] == 10.0
    assert linha["confere_x"] is False


def test_parear_sem_x_ou_sem_tolerancia_devolve_none() -> None:
    partitura = [_evento_partitura(0, None, {52})]
    tab = [_evento_tab(0, 100.0, {52}, [1.0])]
    sem_x = parear(partitura, tab, tolerancia_px=5.0)[0]
    assert sem_x["par_tab"] == 0
    assert sem_x["distancia_x"] is None
    assert sem_x["confere_x"] is None

    com_x = [_evento_partitura(0, 100.0, {52})]
    sem_tolerancia = parear(com_x, tab, tolerancia_px=None)[0]
    assert sem_tolerancia["distancia_x"] == 0.0
    assert sem_tolerancia["confere_x"] is None


def test_x_dos_compassos_le_stacks_do_omr(tmp_path: Path) -> None:
    omr = tmp_path / "entrada.omr"
    xml = (
        "<score>"
        '<stack left="10">'
        '<slot time-offset="0" x-offset="5"/>'
        '<slot time-offset="1/4" x-offset="20"/>'
        "</stack>"
        '<stack left="100">'
        '<slot time-offset="0" x-offset="3"/>'
        "</stack>"
        "</score>"
    )
    with zipfile.ZipFile(omr, "w") as arquivo:
        arquivo.writestr("sheet#1/sheet#1.xml", xml)
    compassos = x_dos_compassos(omr)
    assert compassos == [
        (10.0, {Fraction(0): 5.0, Fraction(1, 4): 20.0}),
        (100.0, {Fraction(0): 3.0}),
    ]
