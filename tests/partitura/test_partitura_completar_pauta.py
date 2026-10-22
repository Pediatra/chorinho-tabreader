"""Testes da completação da pauta pela tab (P4, rodadas 3027 e Ajuste 1): função pura.

Os dados são montados à mão. Nada de ``data/saida``, de ``artefatos`` nem do acervo.
"""

import copy

from tab.partitura.completar_pauta import _nome, completar_pauta

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
    saida, contagens, motivos = completar_pauta(
        eventos, [_tab(100.0, 7, {60, 64})], COMPASSOS, 1
    )
    assert contagens["acorde"] == 1
    assert sum(contagens.values()) == 1
    assert motivos == []
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
    saida, contagens, _ = completar_pauta(eventos, tab, COMPASSOS, 1)
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
    saida, _, _ = completar_pauta(eventos, [_tab(200.0, 8, {62})], COMPASSOS, 1)
    todas = [s for e in saida for s in e["simbolos"] if s["origem"] == "tab_completada"]
    assert todas and all(s["figura"] is None and s["pontuada"] is False for s in todas)


def test_harmonico_com_oitava_na_pauta_nao_entra():
    eventos = [_evento("1", 100.0, 7, [_simbolo(76)])]
    tab = [_tab(100.0, 7, {64}, harmonico=True)]
    saida, contagens, motivos = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["nao_harmonico"] == 1
    assert contagens["acorde"] == 0
    assert motivos[0]["motivo"] == "harmonico"
    assert saida[0]["simbolos"] == eventos[0]["simbolos"]


def test_harmonico_sem_oitava_na_pauta_entra_marcado():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    tab = [_tab(100.0, 7, {64}, harmonico=True)]
    saida, contagens, _ = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["acorde"] == 1
    assert contagens["nao_harmonico"] == 0
    assert saida[0]["simbolos"][1]["midi_escrito"] == 64
    assert saida[0]["simbolos"][1]["harmonico"] is True


def test_nota_ligada_nao_entra():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    tab = [_tab(100.0, 7, {60, 64}, ligadas={64})]
    saida, contagens, motivos = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["nao_ligada"] == 1
    assert contagens["acorde"] == 0
    assert motivos[0]["motivo"] == "ligada"
    assert len(saida[0]["simbolos"]) == 1


def test_simbolo_existente_fica_intacto():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60), _simbolo(67, figura="half")])]
    original = copy.deepcopy(eventos)
    saida, _, _ = completar_pauta(eventos, [_tab(100.0, 7, {60, 64, 67})], COMPASSOS, 1)
    assert eventos == original
    assert saida[0]["simbolos"][:2] == original[0]["simbolos"]
    assert [s["midi_escrito"] for s in saida[0]["simbolos"][2:]] == [64]


def test_par_de_outra_tela_nao_ocupa_a_coluna():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)], tela=2)]
    saida, contagens, _ = completar_pauta(eventos, [_tab(100.0, 7, {64})], COMPASSOS, 1)
    assert contagens["isolado"] == 1
    assert contagens["acorde"] == 0
    assert len(saida) == 2
    assert saida[0]["simbolos"] == eventos[0]["simbolos"]


def test_pausa_no_mesmo_x_nao_completa_isolado_em_uma_voz():
    # isolado em x 100 (coluna sem par), pausa em x 102, compasso 1 com uma voz: não entra
    eventos = [_evento("1", 50.0, 9, [_simbolo(60)])]
    tab = [_tab(100.0, 7, {64})]
    saida, contagens, motivos = completar_pauta(
        eventos, tab, COMPASSOS, 1, [(102.0, "1")], {"1": {"1"}}
    )
    assert contagens["nao_pausa"] == 1
    assert contagens["isolado"] == 0
    assert len(saida) == 1
    assert motivos == [
        {"x": 100.0, "midi": 64, "tipo": "isolado", "compasso": "1", "motivo": "pausa"}
    ]


def test_pausa_longe_do_x_nao_bloqueia_e_pausa_isolada_conta():
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    _, contagens, motivos = completar_pauta(
        eventos, [_tab(100.0, 7, {60, 64})], COMPASSOS, 1, [(120.0, "1")]
    )
    assert contagens["acorde"] == 1
    assert motivos == []
    # isolado com pausa a 2 px, em compasso de uma voz: não entra
    _, contagens, _ = completar_pauta(
        eventos, [_tab(200.0, 8, {62})], COMPASSOS, 1, [(198.0, "1")], {"2": {"1"}}
    )
    assert contagens["nao_pausa"] == 1
    assert contagens["isolado"] == 0


def test_cabecalho_antes_da_primeira_nota_nao_completa():
    # a primeira nota da pauta está em x 100; a coluna em x 90 cai antes de 100 - 5
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    tab = [_tab(90.0, 8, {62})]
    _, contagens, motivos = completar_pauta(eventos, tab, COMPASSOS, 1)
    assert contagens["nao_cabecalho"] == 1
    assert contagens["isolado"] == 0
    assert motivos[0]["motivo"] == "cabecalho"


def test_pausa_antes_da_primeira_nota_conta_como_primeiro_evento():
    # com uma pausa em x 80, o primeiro evento da pauta passa a ser 80: x 90 já não é cabeçalho
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    tab = [_tab(90.0, 8, {62})]
    saida, contagens, _ = completar_pauta(eventos, tab, COMPASSOS, 1, [(80.0, "1")])
    assert contagens["nao_cabecalho"] == 0
    assert contagens["isolado"] == 1
    assert len(saida) == 2


def test_oitava_abaixo_na_pauta_nao_completa_no_acorde():
    # a pauta tem 52 (uma oitava abaixo de 64) no mesmo x
    eventos = [_evento("1", 100.0, 7, [_simbolo(52)])]
    _, contagens, motivos = completar_pauta(
        eventos, [_tab(100.0, 7, {52, 64})], COMPASSOS, 1
    )
    assert contagens["nao_oitava"] == 1
    assert contagens["acorde"] == 0
    assert motivos[0]["motivo"] == "oitava"


def test_oitava_acima_na_pauta_nao_completa_no_isolado():
    # a pauta tem 76 (uma oitava acima de 64) a 2 px da coluna da tab, que não tem par
    eventos = [_evento("1", 202.0, 9, [_simbolo(76)])]
    _, contagens, motivos = completar_pauta(
        eventos, [_tab(200.0, 8, {64})], COMPASSOS, 1
    )
    assert contagens["nao_oitava"] == 1
    assert contagens["isolado"] == 0
    assert motivos[0]["tipo"] == "isolado"


def test_pausa_de_isolado_barra_na_mesma_voz():
    # isolado de corda 1 recebe a voz 1; a pausa da voz 1 a 2 px barra
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    _, contagens, motivos = completar_pauta(
        eventos, [_tab(200.0, 8, {62})], COMPASSOS, 1, [(198.0, "1")], {"2": {"1", "2"}}
    )
    assert contagens["nao_pausa"] == 1
    assert contagens["isolado"] == 0
    assert motivos[0]["motivo"] == "pausa"


def test_pausa_de_outra_voz_nao_barra():
    # o compasso 2 tem duas vozes; a pausa é da voz 2 e o isolado recebe a voz 1: não barra
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    saida, contagens, motivos = completar_pauta(
        eventos, [_tab(200.0, 8, {62})], COMPASSOS, 1, [(198.0, "2")], {"2": {"1", "2"}}
    )
    assert contagens["isolado"] == 1
    assert contagens["nao_pausa"] == 0
    assert motivos == []
    assert len(saida) == 2


def test_pausa_nao_barra_nota_de_acorde():
    # a nota pareada no mesmo x (acorde) não é barrada por pausa, mesmo com uma voz só
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    saida, contagens, motivos = completar_pauta(
        eventos, [_tab(100.0, 7, {60, 64})], COMPASSOS, 1, [(102.0, "1")], {"1": {"1"}}
    )
    assert contagens["acorde"] == 1
    assert contagens["nao_pausa"] == 0
    assert motivos == []
    assert saida[0]["simbolos"][1]["midi_escrito"] == 64


def test_isolado_de_corda_4_a_6_vai_para_voz_2_com_duas_vozes():
    # corda 5 (4 a 6) e compasso com voz 2 na leitura: a nota entra na voz 2
    tab = [{**_tab(200.0, 8, {52}), "cordas": {52: 5}}]
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    saida, contagens, _ = completar_pauta(
        eventos, tab, COMPASSOS, 1, [], {"2": {"1", "2"}}
    )
    assert contagens["isolado"] == 1
    assert saida[1]["simbolos"][0]["voz"] == "2"


def test_isolado_de_corda_4_a_6_fica_na_voz_1_sem_voz_2():
    tab = [{**_tab(200.0, 8, {52}), "cordas": {52: 5}}]
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    saida, contagens, _ = completar_pauta(eventos, tab, COMPASSOS, 1, [], {"2": {"1"}})
    assert contagens["isolado"] == 1
    assert saida[1]["simbolos"][0]["voz"] == "1"


def test_pausa_da_voz_2_barra_isolado_de_corda_5():
    tab = [{**_tab(200.0, 8, {52}), "cordas": {52: 5}}]
    eventos = [_evento("1", 100.0, 7, [_simbolo(60)])]
    _, contagens, motivos = completar_pauta(
        eventos, tab, COMPASSOS, 1, [(198.0, "2")], {"2": {"1", "2"}}
    )
    assert contagens["nao_pausa"] == 1
    assert motivos[0]["motivo"] == "pausa"
