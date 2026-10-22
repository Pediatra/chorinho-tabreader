"""Braço quadro a quadro (M11a): erros, classificação e marcas, sem acervo."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos.braco.tempo import (
    Marcas,
    classificar,
    erros,
    marcas_do_registro,
    transformar,
)

IDENTIDADE = np.eye(3)


def _registro(braco: str = "sim") -> dict:
    """Quadro sintético: braço horizontal, nut em x = 1000, trastes a cada 50 px.

    As cordas 1 e 6 estão em y = 300 e y = 200 (vão de corda = 100 / 5 = 20 px).
    Os trastes ficam à esquerda do nut, com números de 1 a 12.
    """
    trastes = [[1000.0 - 50.0 * n, 250.0] for n in range(12, 0, -1)]
    return {
        "chave": "sintetico",
        "braco": braco,
        "corda1": [[0.0, 300.0], [1200.0, 300.0]],
        "corda6": [[0.0, 200.0], [1200.0, 200.0]],
        "nut": [1000.0, 250.0],
        "trastes": trastes,
        "traste_referencia": None,
        "respondido_em": "2026-10-16T00:00:00",
    }


def _marcas() -> Marcas:
    """Marcas do quadro sintético."""
    marcas = marcas_do_registro(_registro())
    assert marcas is not None
    return marcas


def _transladar(marcas: Marcas, dx: float, dy: float) -> Marcas:
    """Marcas deslocadas por ``(dx, dy)``."""
    h = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy], [0.0, 0.0, 1.0]])
    return transformar(marcas, h)


def test_identidade_nao_erra() -> None:
    """Sem movimento, todos os erros são zero e a classe é certo."""
    m = _marcas()
    e = erros(transformar(m, IDENTIDADE), m)
    assert e["nut_casas"] == pytest.approx(0.0)
    assert e["pior_traste_casas"] == pytest.approx(0.0)
    assert e["perp_cordas"] == pytest.approx(0.0)
    assert e["perp_assinado_px"] == pytest.approx(0.0)
    assert classificar(e, True, "sim") == "certo"


def test_translacao_perpendicular_de_20_px_e_falsa() -> None:
    """20 px perpendiculares ao braço são 1 vão de corda, e a classe é falso."""
    m = _marcas()
    e = erros(_transladar(m, 0.0, 20.0), m)
    assert e["perp_cordas"] == pytest.approx(1.0)
    assert classificar(e, True, "sim") == "falso"


def test_translacao_perpendicular_de_4_px_e_certa() -> None:
    """4 px perpendiculares dão 0,2 vão, abaixo de 1/4: certo."""
    m = _marcas()
    e = erros(_transladar(m, 0.0, 4.0), m)
    assert e["perp_cordas"] == pytest.approx(0.2)
    assert classificar(e, True, "sim") == "certo"


def test_translacao_perpendicular_de_8_px_e_imprecisa() -> None:
    """8 px perpendiculares dão 0,4 vão, entre 1/4 e 1/2: impreciso."""
    m = _marcas()
    e = erros(_transladar(m, 0.0, 8.0), m)
    assert e["perp_cordas"] == pytest.approx(0.4)
    assert classificar(e, True, "sim") == "impreciso"


def test_translacao_ao_longo_do_braco_de_25_px_da_meia_casa() -> None:
    """25 px ao longo do braço (casa de 50 px) dão 0,5 de casa no pior traste."""
    m = _marcas()
    e = erros(_transladar(m, 25.0, 0.0), m)
    assert e["pior_traste_casas"] == pytest.approx(0.5)


def test_translacao_ao_longo_do_braco_de_30_px_e_falsa() -> None:
    """30 px ao longo do braço passam de 1/2 de casa: falso."""
    m = _marcas()
    e = erros(_transladar(m, 30.0, 0.0), m)
    assert e["nut_casas"] == pytest.approx(0.6)
    assert classificar(e, True, "sim") == "falso"


def test_nao_achou_e_nao_achou() -> None:
    """Sem o achado do rastreador, a classe é nao_achou."""
    m = _marcas()
    e = erros(transformar(m, IDENTIDADE), m)
    assert classificar(e, False, "sim") == "nao_achou"


def test_achou_com_braco_nao_e_falso() -> None:
    """Achar braço onde o gabarito diz não haver braço é falso."""
    m = _marcas()
    e = erros(transformar(m, IDENTIDADE), m)
    assert classificar(e, True, "nao") == "falso"


def test_transformar_com_escala_dois_dobra_as_coordenadas() -> None:
    """A homografia de escala 2 dobra nut, trastes e cordas."""
    m = _marcas()
    h = np.diag([2.0, 2.0, 1.0])
    t = transformar(m, h)
    assert t.nut is not None and m.nut is not None
    np.testing.assert_allclose(t.nut, 2.0 * m.nut)
    np.testing.assert_allclose(t.corda1, 2.0 * m.corda1)
    np.testing.assert_allclose(t.corda6, 2.0 * m.corda6)
    for n, ponto in m.trastes.items():
        np.testing.assert_allclose(t.trastes[n], 2.0 * ponto)


def test_marcas_do_registro_none_para_braco_nao() -> None:
    """Quadro sem braço não tem marcas."""
    assert marcas_do_registro(_registro(braco="nao")) is None
