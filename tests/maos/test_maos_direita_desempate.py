"""Testes das funções puras do desempate e do F1 por corda (M7, item 2; sem GPU e sem acervo)."""

from __future__ import annotations

import pytest

from tab.maos.direita.desempate import (
    candidatos,
    contar_f1,
    escolha_casa_baixa,
    escolha_frequente,
    escolha_visual,
    estatisticas_de_ambiguidade,
    nome_do_cenario,
)


def test_altura_sozinha_acha_as_cinco_cordas_da_mi_aguda() -> None:
    # mi4 (MIDI 64) solta: também é a casa 5 da corda 2, a 9 da 3, a 14 da 4 e a 19 da 5.
    cands = candidatos(1, 0, None)
    assert cands == [(1, 0), (2, 5), (3, 9), (4, 14), (5, 19)]


def test_regiao_da_mao_corta_casas_longe_mas_mantem_corda_solta() -> None:
    assert candidatos(1, 0, 2) == [(1, 0)]
    assert candidatos(2, 5, 2) == [(1, 0), (2, 5)]


def test_candidatos_sempre_contem_a_corda_real() -> None:
    for corda in range(1, 7):
        for casa in range(0, 8):
            for raio in (None, 2, 3):
                cordas = [c for c, _ in candidatos(corda, casa, raio)]
                assert corda in cordas


def test_nome_do_cenario() -> None:
    assert nome_do_cenario(None) == "altura"
    assert nome_do_cenario(2) == "altura+-2"


def test_estatisticas_de_ambiguidade_contam_notas_e_candidatos() -> None:
    notas = [{"corda": 1, "casa": 0}, {"corda": 1, "casa": 0}, {"corda": 6, "casa": 40}]
    r = estatisticas_de_ambiguidade(notas, 2)
    assert r["n_notas"] == 2
    assert r["n_ambiguas"] == 0
    assert r["distribuicao"] == {"1": 2}


def test_casa_baixa_prefere_corda_solta_e_empate_vai_para_corda_menor() -> None:
    assert escolha_casa_baixa([(2, 5), (1, 0)]) == 1
    assert escolha_casa_baixa([(3, 4), (2, 4)]) == 2


def test_frequente_escolhe_a_corda_mais_usada() -> None:
    assert escolha_frequente([(1, 0), (2, 5)], {2: 10, 1: 3}) == 2
    assert escolha_frequente([(1, 0), (2, 5)], {}) == 1


def test_visual_so_escolhe_entre_as_candidatas() -> None:
    # Retas horizontais y = 10 k (a corda 2 está em y = 20, a mais perto do ponto).
    cordas = [{"corda": k, "a": 0.0, "b": 1.0, "c": 10.0 * k} for k in range(1, 7)]
    ponto = (0.0, 21.0)
    assert escolha_visual(ponto, cordas, [1, 2, 3, 4, 5, 6]) == 2
    assert escolha_visual(ponto, cordas, [1, 3]) == 3


def test_visual_sem_candidatas_levanta_erro() -> None:
    with pytest.raises(ValueError):
        escolha_visual((0.0, 0.0), [], [])


def test_f1_por_corda_e_micro() -> None:
    verdade = [{1}, {2}]
    previstas = [{1}, {1}]
    tab = contar_f1(verdade, previstas)
    assert tab["1"] == {
        "tp": 1,
        "fp": 1,
        "fn": 0,
        "precisao": 0.5,
        "revocacao": 1.0,
        "f1": pytest.approx(0.6667, abs=1e-4),
    }
    assert tab["2"]["tp"] == 0
    assert tab["2"]["fn"] == 1
    micro = tab["micro"]
    assert (micro["tp"], micro["fp"], micro["fn"]) == (1, 1, 1)
    assert micro["f1"] == 0.5


def test_f1_sem_predicao_declara_none() -> None:
    tab = contar_f1([{3}], [set()])
    assert tab["3"]["precisao"] is None
    assert tab["3"]["f1"] is None
