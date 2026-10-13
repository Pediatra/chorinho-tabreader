"""Testes do tempo por exibição (Fase 5): funções puras, sem GPU e sem acervo.

Cobre o estado do marcador (posição e cor), a estabilidade, as passagens, a coerência, a
escolha do observador e os invariantes do JSON v1 (T5.5).
"""

from __future__ import annotations

from types import SimpleNamespace

import cv2
import numpy as np

from tab.cursor import detectar_cursor
from tab.estado import (
    SATURACAO_MARCADOR,
    Amostra,
    Corrida,
    corridas_estaveis,
    estados_cor,
    estados_posicao,
    faixa_translucida,
    observar,
    passagens_de,
    refinar_inicios,
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


def test_refinar_inicios_leva_o_onset_ao_quadro_nativo_da_transicao():
    """O início do trecho sai da amostra de 6 qps para o quadro nativo da transição (T5.2).

    Transição real em 0,25 s; a 1ª amostra de 6 qps que mostra a coluna nova é 0,333 s. O quadro
    nativo (30 qps) em que a coluna aparece é 0,267 s, que está entre a amostra anterior e a atual.
    """
    ts = [k / 6 for k in range(4)]
    estados = [0 if t < 0.25 else 1 for t in ts]
    amostras = [Amostra(t=t, x=None, cores=[]) for t in ts]
    corridas = corridas_estaveis(estados, ts, minimo=1)
    assert abs(corridas[-1].t_ini - 1 / 3) < 1e-9

    def ler_fino(t_a, t_b):
        n = round((t_b - t_a) * 30)
        return [Amostra(t=t_a + i / 30, x=None, cores=[]) for i in range(n + 1)]

    def estados_de(lidas):
        return [1 if a.t >= 0.25 else 0 for a in lidas]

    refinar_inicios(corridas, amostras, ler_fino, estados_de, fps=30.0)
    refinado = corridas[-1].t_ini
    assert abs(refinado - 0.267) < 0.001
    assert 1 / 6 < refinado <= 1 / 3  # dentro de (amostra anterior, amostra atual]


def test_refinar_inicios_mantem_trecho_sem_amostra_anterior():
    """Trecho que começa na 1ª amostra da exibição não tem janela para refinar: fica como está."""
    ts = [0.0, 1 / 6, 2 / 6]
    estados = [1, 1, 1]
    amostras = [Amostra(t=t, x=None, cores=[]) for t in ts]
    corridas = corridas_estaveis(estados, ts, minimo=1)

    def ler_fino(t_a, t_b):
        raise AssertionError("não deve ler quadros para o trecho inicial")

    refinar_inicios(corridas, amostras, ler_fino, lambda lidas: [], fps=30.0)
    assert corridas[0].t_ini == 0.0


def test_faixa_clara_do_marcador_so_aparece_com_corte_de_saturacao_baixo():
    """Faixa azul-clara (saturação 38, como o marcador do retrato) some com o corte 60 do cursor.

    Medido na Fase 5: o detector padrão (saturação > 60) perdia a faixa em vários quadros, e a
    régua lia a coluna anterior. Com ``sat_min=SATURACAO_MARCADOR`` (20) a faixa é achada.
    """
    quadro = np.full((120, 200, 3), 235, np.uint8)
    faixa = cv2.cvtColor(np.uint8([[[110, 38, 239]]]), cv2.COLOR_HSV2BGR)[0, 0]
    quadro[:, 90:98] = faixa
    assert detectar_cursor(quadro) is None  # padrão: saturação > 60
    det = detectar_cursor(quadro, sat_min=SATURACAO_MARCADOR)
    assert det is not None
    assert abs(det[0] - 90) <= 1 and abs(det[1] - 97) <= 1


def _papel_com_cordas(altura: int = 150, largura: int = 400) -> np.ndarray:
    """Papel claro com cinco cordas escuras (duas linhas de pixel cada), como a tablatura."""
    quadro = np.full((altura, largura, 3), 245, np.uint8)
    for y in (30, 50, 70, 90, 110):
        quadro[y : y + 2, :] = 60
    return quadro


def test_marcador_translucido_mostra_as_cordas_por_dentro():
    """Tinta translúcida sobre o papel: as cordas aparecem através da faixa, então ela é marcador."""
    quadro = _papel_com_cordas()
    cor = np.array([200, 120, 60], np.float32)  # BGR, azul-clara
    x0, x1 = 200, 245
    faixa = quadro[:, x0 : x1 + 1].astype(np.float32)
    quadro[:, x0 : x1 + 1] = (0.75 * faixa + 0.25 * cor).astype(np.uint8)
    assert faixa_translucida(quadro, x0, x1)


def test_moldura_solida_nao_e_marcador():
    """Moldura verde sólida (12 px) por cima da tablatura não mostra as cordas: não é marcador.

    Caso medido no ``retrato brasileiro`` (239 a 244 s): faixa de 12 px, saturação 118, sem
    nenhum pixel de tinta por dentro, sobre a ilustração das mãos.
    """
    quadro = _papel_com_cordas()
    x0, x1 = 200, 211
    quadro[:, x0 : x1 + 1] = (136, 253, 177)  # verde sólido, BGR
    assert not faixa_translucida(quadro, x0, x1)


def test_faixa_estreita_translucida_ainda_conta():
    """Faixa de 3 px (o mínimo de largura) translúcida com cordas por dentro conta como marcador."""
    quadro = _papel_com_cordas()
    x0, x1 = 100, 102
    faixa = quadro[:, x0 : x1 + 1].astype(np.float32)
    quadro[:, x0 : x1 + 1] = (0.75 * faixa + 0.25 * np.array([200, 120, 60])).astype(
        np.uint8
    )
    assert faixa_translucida(quadro, x0, x1)


def test_cursor_fino_com_pouca_tinta_ainda_conta():
    """Cursor fino do ``greensleeves``: só uma corda aparece por dentro (~1,3 % de tinta).

    Com o limiar antigo (0,02) esse marcador era recusado e a coluna ficava pulada.
    """
    quadro = np.full((150, 400, 3), 245, np.uint8)
    quadro[70:72, :] = 60
    x0, x1 = 200, 203
    faixa = quadro[:, x0 : x1 + 1].astype(np.float32)
    quadro[:, x0 : x1 + 1] = (0.75 * faixa + 0.25 * np.array([60, 200, 60])).astype(
        np.uint8
    )
    assert faixa_translucida(quadro, x0, x1)
