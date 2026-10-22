"""Testes das funções puras da E1 da partitura (sem acervo e sem GPU)."""

from tab.partitura.completar_pauta import _compasso_de_x, _figura_do_deficit


def test_figura_do_deficit_cabe_numa_figura_so():
    assert _figura_do_deficit(2.0) == ("half", False)
    assert _figura_do_deficit(1.5) == ("quarter", True)
    assert _figura_do_deficit(0.6) == (None, False)


def test_compasso_de_x_pega_o_ultimo_compasso_que_comeca_antes():
    compassos = [
        {"numero": "1", "x_quadro": 100.0},
        {"numero": "2", "x_quadro": 300.0},
    ]
    assert _compasso_de_x(310.0, compassos) == "2"
    assert _compasso_de_x(50.0, compassos) is None
    assert _compasso_de_x(None, compassos) is None
