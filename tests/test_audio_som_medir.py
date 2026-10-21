"""Testes das funções puras de ``tab.audio_som_medir`` (rodada 2018)."""

from tab.audio_som_medir import (
    casa_inteira,
    colunas_do_gabarito,
    eventos_do_som,
    iguais,
    instante_acertado,
    medir_exibicao,
    midi_da_nota,
    parear,
)


def _nota(corda: int, casa: object, x: float) -> dict:
    return {"corda": corda, "casa": casa, "x_centro_quadro": x}


def _som(t: float, midi: int) -> dict:
    return {"t_ini": t, "t_fim": t + 0.3, "midi": midi, "amplitude": 0.7}


def test_midi_da_nota_soma_corda_casa_e_capo() -> None:
    assert midi_da_nota(6, 0) == 40
    assert midi_da_nota(1, 0) == 64
    assert midi_da_nota(2, 3, capo=2) == 64


def test_casa_inteira_recusa_texto_que_nao_e_numero() -> None:
    assert casa_inteira("11") == 11
    assert casa_inteira(7) == 7
    assert casa_inteira("x") is None
    assert casa_inteira(True) is None


def test_colunas_juntam_por_x_e_pulam_removidas() -> None:
    notas = [
        _nota(1, 0, 100),
        _nota(2, 1, 103),
        _nota(3, "x", 101),
        {**_nota(4, 2, 102), "removida": True},
        _nota(1, 3, 140),
    ]
    colunas = colunas_do_gabarito(notas, passo=20, capo=0)
    assert [[n["midi"] for n in c] for c in colunas] == [[64, 60], [67]]


def test_eventos_encadeiam_inicios_proximos() -> None:
    som = [_som(1.00, 40), _som(1.05, 45), _som(1.10, 50), _som(1.30, 52)]
    eventos = eventos_do_som(som, 0.0, 2.0)
    assert [len(e) for e in eventos] == [3, 1]


def test_iguais_conta_multiconjunto_e_desvio() -> None:
    col = [{"midi": 60}, {"midi": 60}, {"midi": 64}]
    ev = [{"midi": 60}, {"midi": 64}, {"midi": 61}]
    assert iguais(col, ev) == 2
    assert iguais(col, ev, desvio=1) == 1


def test_parear_e_monotonico_e_pula_evento_extra() -> None:
    colunas = [[{"midi": 60}], [{"midi": 62}], [{"midi": 64}]]
    eventos = [[{"midi": 60}], [{"midi": 70}], [{"midi": 62}], [{"midi": 64}]]
    assert parear(colunas, eventos) == [(0, 0, 1), (1, 2, 1), (2, 3, 1)]


def test_medir_exibicao_conta_precisao_so_no_trecho_pareado() -> None:
    colunas = colunas_do_gabarito(
        [_nota(1, 0, 10), _nota(1, 2, 50), _nota(1, 4, 90)], passo=20, capo=0
    )
    som = [
        _som(0.5, 30 + 40),  # antes do trecho: não conta na precisão
        _som(1.0, 64),
        _som(1.5, 71),  # a mais, dentro do trecho
        _som(2.0, 66),
        _som(3.0, 68),
    ]
    m = medir_exibicao(colunas, som, 1.0, 3.0)
    assert (m["n_gabarito"], m["n_pareadas"], m["n_som_trecho"]) == (3, 3, 4)


def test_medir_exibicao_acorde_cheio_e_oitava() -> None:
    acorde = [_nota(c, 0, 10) for c in range(1, 7)]
    colunas = colunas_do_gabarito(acorde, passo=20, capo=0)
    som = [_som(1.0 + 0.01 * k, m) for k, m in enumerate([40, 45, 50, 55, 71])]
    m = medir_exibicao(colunas, som, 0.9, 1.5)
    assert m["acordes"] == [round(4 / 6, 4)]
    assert m["oitava"] == 1  # 71 é o 59 da corda 2 uma oitava acima
    assert m["semitom"] == 0


def test_instante_acertado_usa_tolerancia() -> None:
    som = [_som(1.0, 60)]
    assert instante_acertado(1.09, som)
    assert not instante_acertado(1.2, som)
