"""Testes das funções puras das frentes F0 da partitura (sem acervo e sem GPU)."""

from tab.partitura.regua import _duracao_por_voz, _seminimas
from tab.partitura.regua_troca import _certos, _oitavas


def test_seminimas_converte_fracao_em_semininimas():
    assert _seminimas("3/4") == 3.0
    assert _seminimas("6/8") == 3.0
    assert _seminimas(None) is None


def test_duracao_por_voz_nao_conta_acorde_duas_vezes():
    simbolos = [
        {"voz": "1", "duracao": 1.0, "acorde": False},
        {"voz": "1", "duracao": 1.0, "acorde": True},
        {"voz": "2", "duracao": 2.0, "acorde": False},
    ]
    assert _duracao_por_voz(simbolos) == 2.0


def test_certos_marca_so_as_notas_em_comum():
    lib = [frozenset({60, 64}), frozenset({67})]
    ref = [frozenset({60, 64, 67}), frozenset({67})]
    certo = _certos(lib, ref)
    assert certo[0] == frozenset({60, 64})
    assert certo[1] == frozenset({67})


def test_oitavas_conta_evento_deslocado_de_doze_semitons():
    lib = [frozenset({72})]
    ref = [frozenset({60})]
    assert _oitavas(lib, ref) == 1
    assert _oitavas(ref, ref) == 0
