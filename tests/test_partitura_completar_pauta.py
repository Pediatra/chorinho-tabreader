"""Testes da completação da pauta pela tab (P4, rodada 3027): função pura, sem acervo.

Os dados são montados à mão. Nada de ``data/saida``, de ``artefatos`` nem do acervo.
"""

import copy

from tab.partitura_completar_pauta import _nome, completar_pauta

COMPASSOS = [
    {"numero": "1", "fracao": "4/4", "x_quadro": 90.0},
    {"numero": "2", "fracao": "4/4", "x_quadro": 180.0},
]


def _simbolo(midi, figura="quarter", voz="1"):
    return {
        "nome": _nome(midi),
        "midi_escrito": midi,
        "figura": figura,
        "pontuada": False,
        "voz": voz,
        "ligadura_inicio": False,
        "ligadura_fim": False,
        "notacoes": [],
        "origem": "audiveris",
    }


def _evento(compasso, x, coluna, simbolos, tela=1):
    return {
        "compasso": compasso,
        "t": 0.0,
        "x_quadro": x,
        "par": {
            "tela": tela,
            "coluna": coluna,
            "distancia_x": 0.0,
            "confere_x": True,
            "metodo": "altura",
        },
        "simbolos": simbolos,
        "trocadas": [],
    }


def _tab(x, coluna, midis, harmonico=False, ligadas=()):
    return {
        "x": x,
        "coluna": coluna,
        "midis": set(midis),
        "cordas": dict.fromkeys(midis, 1),
        "harmonico_tab": harmonico,
        "ligadas": set(ligadas),
    }


def test_nome_da_nota_com_oitava():
    assert _nome(69) == "A4"
    assert _nome(61) == "C#4"
    assert _nome(40) == "E2"


def test_acorde_entra_no_evento_pareado():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    original = copy.deepcopy(eventos)
    saida, contagens = completar_pauta(
        eventos, [_tab(100.0, 7, {60, 64})], COMPASSOS, 1
    )
    assert contagens == {"acorde": 1, "isolado": 0, "nao_harmonico": 0, "nao_ligada": 0}
    assert len(saida) == 1
    assert saida[0]["simbolos"][0] == original[0]["simbolos"][0]
    nova = saida[0]["simbolos"][1]
    assert nova["midi_escrito"] == 64
    assert nova["origem"] == "tab_completada"
    assert nova["figura"] is None
    assert nova["pontuada"] is False
    assert eventos == original


def test_isolado_vira_evento_novo_em_ordem_de_x():
    eventos = [
        _evento("1", 100.0, 7, [_simbolo(60)]),
        _evento("2", 300.0, 9, [_simbolo(67)]),
    ]
    tab = [_tab(100.0, 7, {60}), _tab(200.0, 8, {62}), _tab(300.0, 9, {67})]
    saida, contagens = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["isolado"] == 1
    assert contagens["acorde"] == 0
    assert [e["x_quadro"] for e in saida] == [100.0, 200.0, 300.0]
    nova = saida[1]
    assert nova["compasso"] == "2"
    assert nova["t"] is None
    assert nova["trocadas"] == []
    assert nova["par"] == {
        "tela": 1,
        "coluna": 8,
        "distancia_x": 0.0,
        "confere_x": True,
        "metodo": "tab",
    }
    assert [s["midi_escrito"] for s in nova["simbolos"]] == [62]
    assert nova["simbolos"][0]["nome"] == "D4"


def test_figura_fica_null_mesmo_com_deficit_de_figura_so():
    # o compasso 2 está vazio na pauta: o déficit seria uma semibreve, e a figura fica null
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    saida, _ = completar_pauta(eventos, [_tab(200.0, 8, {62})], COMPASSOS, 1)
    todas = [s for e in saida for s in e["simbolos"] if s["origem"] == "tab_completada"]
    assert todas and all(s["figura"] is None and s["pontuada"] is False for s in todas)


def test_harmonico_com_oitava_na_pauta_nao_entra():
    eventos = [_evento("1", 100.0, 7, [_simbolo(76)])]
    tab = [_tab(100.0, 7, {64}, harmonico=True)]
    saida, contagens = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["nao_harmonico"] == 1
    assert contagens["acorde"] == 0
    assert saida[0]["simbolos"] == eventos[0]["simbolos"]


def test_harmonico_sem_oitava_na_pauta_entra_marcado():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    tab = [_tab(100.0, 7, {64}, harmonico=True)]
    saida, contagens = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["acorde"] == 1
    assert contagens["nao_harmonico"] == 0
    assert saida[0]["simbolos"][1]["midi_escrito"] == 64
    assert saida[0]["simbolos"][1]["harmonico"] is True


def test_nota_ligada_nao_entra():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    tab = [_tab(100.0, 7, {60, 64}, ligadas={64})]
    saida, contagens = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["nao_ligada"] == 1
    assert contagens["acorde"] == 0
    assert len(saida[0]["simbolos"]) == 1


def test_simbolo_existente_fica_intacto():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60), _simbolo(67, figura="half")])]
    original = copy.deepcopy(eventos)
    saida, _ = completar_pauta(eventos, [_tab(100.0, 7, {60, 64, 67})], COMPASSOS, 1)
    assert eventos == original
    assert saida[0]["simbolos"][:2] == original[0]["simbolos"]
    assert [s["midi_escrito"] for s in saida[0]["simbolos"][2:]] == [64]


def test_par_de_outra_tela_nao_ocupa_a_coluna():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)], tela=2)]
    saida, contagens = completar_pauta(eventos, [_tab(100.0, 7, {64})], COMPASSOS, 1)
    assert contagens["isolado"] == 1
    assert contagens["acorde"] == 0
    assert len(saida) == 2
    assert saida[0]["simbolos"] == eventos[0]["simbolos"]
