"""Testes do tempo por exibição (Fase 5): funções puras, sem GPU e sem acervo.

Cobre o estado do marcador (posição e cor), a estabilidade, as passagens, a coerência, a
escolha do observador e os invariantes do JSON v1 (T5.5).
"""

from __future__ import annotations

from types import SimpleNamespace

from tab.estado import (
    Amostra,
    Corrida,
    corridas_estaveis,
    estados_cor,
    estados_posicao,
    observar,
    passagens_de,
)
from tab.video import (
    colunas_e_caixas,
    entradas_da_nota,
    escolher_observador,
    validar_tempo,
)


def _serie(ts: list[float], xs: list[float | None]) -> list[Amostra]:
    return [Amostra(t=t, x=x, cores=[]) for t, x in zip(ts, xs, strict=True)]


def test_corridas_descartam_amostra_isolada_e_fundem_mesma_coluna():
    estados = [0, 0, 1, 0, 0, None, 0, 0]
    ts = [float(i) for i in range(len(estados))]
    corridas = corridas_estaveis(estados, ts, minimo=2)
    # a coluna 1 isolada (uma amostra) some; as duas corridas da coluna 0 se fundem
    assert [(c.coluna, c.n) for c in corridas] == [(0, 6)]
    assert corridas[0].t_ini == 0.0


def test_corridas_so_aceitam_trecho_com_minimo_de_amostras():
    corridas = corridas_estaveis([2, 3, 3, None, 4], [0.0, 1.0, 2.0, 3.0, 4.0])
    assert [(c.coluna, c.t_ini, c.n) for c in corridas] == [(3, 1.0, 2)]


def test_passagem_comeca_quando_o_estado_volta_para_tras():
    corridas = [
        Corrida(0, 0.0, 2),
        Corrida(1, 1.0, 2),
        Corrida(2, 2.0, 2),
        Corrida(0, 5.0, 2),
        Corrida(1, 6.0, 2),
    ]
    passagens = passagens_de(corridas)
    assert [[c.coluna for c in p] for p in passagens] == [[0, 1, 2], [0, 1]]


def test_observar_mede_coerencia_e_cobertura_de_um_marcador_que_avanca():
    ts = [float(i) for i in range(8)]
    xs = [10, 10, 30, 30, 50, 50, 70, 70]
    amostras = _serie(ts, [float(x) for x in xs])
    estados = estados_posicao(amostras, [10.0, 30.0, 50.0, 70.0], passo=20.0)
    obs = observar("posicao", amostras, estados)
    assert obs.transicoes == 3
    assert obs.avancos == 3
    assert obs.coerencia == 1.0
    assert obs.cobertura == 1.0
    assert obs.passagens == [{0: 0.0, 1: 2.0, 2: 4.0, 3: 6.0}]


def test_observar_conta_salto_para_tras_como_nova_passagem_e_nao_avanco():
    ts = [float(i) for i in range(6)]
    xs = [10, 10, 30, 30, 10, 10]
    amostras = _serie(ts, [float(x) for x in xs])
    estados = estados_posicao(amostras, [10.0, 30.0], passo=20.0)
    obs = observar("posicao", amostras, estados)
    assert obs.transicoes == 2
    assert obs.avancos == 1
    assert obs.coerencia == 0.5
    assert len(obs.passagens) == 2


def test_posicao_fora_da_faixa_de_colunas_nao_tem_estado():
    amostras = _serie([0.0, 1.0, 2.0], [None, 500.0, 10.0])
    estados = estados_posicao(amostras, [10.0, 30.0], passo=20.0)
    assert estados == [None, None, 0]


def test_cor_destaque_pega_o_algarismo_que_se_destaca():
    amostras = [
        Amostra(0.0, None, [1.0, 1.0, 1.0]),
        Amostra(1.0, None, [1.0, 22.0, 1.0]),
        Amostra(2.0, None, [0.5, 0.5, 0.5]),
    ]
    assert estados_cor(amostras, "destaque") == [None, 1, None]


def test_cor_acende_segue_a_ultima_coluna_que_acendeu_cumulativa():
    amostras = [
        Amostra(0.0, None, [1.0, 1.0, 1.0]),
        Amostra(1.0, None, [1.0, 12.0, 1.0]),  # coluna 1 acendeu
        Amostra(2.0, None, [1.0, 12.0, 1.0]),  # continua acesa, sem subida nova
        Amostra(3.0, None, [1.0, 12.0, 15.0]),  # coluna 2 acendeu
        Amostra(4.0, None, [1.0, 12.0, 15.0]),
    ]
    assert estados_cor(amostras, "acende") == [None, 1, 1, 2, 2]


def test_cor_modo_desconhecido_levanta_erro():
    try:
        estados_cor([], "outro")
    except ValueError:
        return
    raise AssertionError("esperava ValueError")


def _obs(nome: str, coerencia: float, cobertura: float, transicoes: int):
    return SimpleNamespace(
        observador=nome,
        coerencia=coerencia,
        cobertura=cobertura,
        transicoes=transicoes,
    )


def test_escolhe_o_observador_de_maior_coerencia_que_passa_o_minimo():
    obs = {
        "posicao": _obs("posicao", 0.9, 0.8, 10),
        "cor": _obs("cor", 0.95, 0.9, 2),  # poucas trocas: não conta
        "cor_acende": _obs("cor_acende", 0.6, 0.7, 9),
    }
    nome, motivo = escolher_observador(obs)
    assert nome == "posicao"
    assert motivo == ""


def test_sem_observador_valido_declara_o_motivo_concreto():
    obs = {
        "posicao": _obs("posicao", 0.9, 0.05, 10),  # cobertura baixa
        "cor": _obs("cor", 0.2, 0.9, 10),  # coerência baixa
        "cor_acende": _obs("cor_acende", 0.0, 0.0, 0),
    }
    nome, motivo = escolher_observador(obs)
    assert nome is None
    assert "posicao: cobertura 0,05" in motivo.replace(".", ",")


def test_colunas_e_caixas_centram_a_coluna_e_atribuem_glifo_pelo_x():
    tokens = [
        {"x_centro_quadro": 100.0},
        {"x_centro_quadro": 102.0},
        {"x_centro_quadro": 200.0},
    ]
    colunas = [1, 1, 2]
    glifos = [
        SimpleNamespace(x0=90, y0=5, x1=110, y1=20),  # centro 100 + x0 0 -> coluna 1
        SimpleNamespace(x0=190, y0=5, x1=210, y1=20),  # coluna 2
        SimpleNamespace(x0=400, y0=5, x1=420, y1=20),  # longe: sem coluna
    ]
    centros, caixas = colunas_e_caixas(tokens, colunas, glifos, x0=0, passo=20.0)
    assert centros == [101.0, 200.0]
    assert caixas[0] == [(90, 5, 110, 20)]
    assert caixas[1] == [(190, 5, 210, 20)]


def test_entrada_sem_medicao_tem_t_ini_nulo_e_exibicao_nula():
    base = {"tela": 1, "coluna": 3, "corda": 2, "casa": 4}
    exibicoes = [{"tempo": {"medido": False, "motivo": "x"}, "passagens": []}]
    assert entradas_da_nota(base, exibicoes) == [
        {**base, "passagem": 1, "exibicao": None, "t_ini": None}
    ]


def test_entrada_por_passagem_quando_a_coluna_tem_onset_em_cada_uma():
    base = {"tela": 1, "coluna": 2, "corda": 5, "casa": 2}
    exibicoes = [
        {
            "tempo": {"medido": True},
            "passagens": [
                [{"coluna": 1, "t_ini": 1.0}, {"coluna": 2, "t_ini": 2.0}],
                [{"coluna": 2, "t_ini": 9.0}],
            ],
        }
    ]
    entradas = entradas_da_nota(base, exibicoes)
    assert [(e["exibicao"], e["passagem"], e["t_ini"]) for e in entradas] == [
        (0, 1, 2.0),
        (0, 2, 9.0),
    ]


def _dados(exibicoes, notas):
    tela = {
        "id": 1,
        "exibicoes": exibicoes,
        "tempo": {"medido": True},
    }
    return {"telas": [tela], "notas": notas}


def test_invariantes_aceitam_tempo_bem_formado():
    ex = [
        {
            "t0": 10.0,
            "t1": 20.0,
            "tempo": {"medido": True},
            "passagens": [[{"coluna": 1, "t_ini": 11.0}, {"coluna": 2, "t_ini": 12.0}]],
        }
    ]
    notas = [
        {"tela": 1, "exibicao": 0, "passagem": 1, "coluna": 1, "t_ini": 11.0},
        {"tela": 1, "exibicao": 0, "passagem": 1, "coluna": 2, "t_ini": 12.0},
    ]
    assert validar_tempo(_dados(ex, notas)) == []


def test_invariantes_pegam_t_ini_fora_da_exibicao():
    ex = [{"t0": 10.0, "t1": 20.0, "tempo": {"medido": True}, "passagens": []}]
    notas = [{"tela": 1, "exibicao": 0, "passagem": 1, "coluna": 1, "t_ini": 25.0}]
    assert any("fora de" in e for e in validar_tempo(_dados(ex, notas)))


def test_invariantes_pegam_onset_decrescente_na_passagem():
    ex = [
        {
            "t0": 10.0,
            "t1": 20.0,
            "tempo": {"medido": True},
            "passagens": [[{"coluna": 1, "t_ini": 15.0}, {"coluna": 2, "t_ini": 12.0}]],
        }
    ]
    assert any("decrescem" in e for e in validar_tempo(_dados(ex, [])))


def test_invariantes_pegam_mesma_coluna_com_tempos_diferentes():
    ex = [{"t0": 10.0, "t1": 20.0, "tempo": {"medido": True}, "passagens": []}]
    notas = [
        {"tela": 1, "exibicao": 0, "passagem": 1, "coluna": 1, "t_ini": 11.0},
        {"tela": 1, "exibicao": 0, "passagem": 1, "coluna": 1, "t_ini": 12.0},
    ]
    assert any("diferentes" in e for e in validar_tempo(_dados(ex, notas)))


def test_invariantes_pegam_medido_falso_sem_motivo():
    ex = [{"t0": 10.0, "t1": 20.0, "tempo": {"medido": False, "motivo": ""}}]
    assert any("sem motivo" in e for e in validar_tempo(_dados(ex, [])))


def test_amostras_sem_recorte_real_nao_quebram_estados_de_cor():
    # guarda contra regressão: cores vazias (sem caixas) não viram coluna
    assert estados_cor([Amostra(0.0, None, [])], "destaque") == [None]
