"""Funções puras do cálculo do braço fora do MVP (estabilidade, quadro, contagem)."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos.braco.fora import (
    achar_quadro,
    avaliar_confianca,
    contar_notas,
    estabilidade,
)

H_BASE = np.array([[1100.0, 40.0, 250.0], [15.0, 880.0, 180.0], [2e-4, 1e-5, 1.0]])


def test_estabilidade_de_homografias_iguais_e_zero() -> None:
    """Três conjuntos com a mesma H dão diferença zero entre todos os pares."""
    estab = estabilidade([H_BASE, H_BASE.copy(), H_BASE.copy()])
    assert [p["par"] for p in estab["entre_conjuntos"]] == ["0-1", "0-2", "1-2"]
    assert all(p["mediana_px"] < 1e-9 for p in estab["entre_conjuntos"])
    assert estab["resumo"]["mediana_px_media"] < 1e-9
    assert estab["resumo"]["mediana_px_amplitude"] < 1e-9


def test_estabilidade_mede_o_deslocamento_de_um_conjunto() -> None:
    """Um conjunto deslocado em x aparece como diferença nos pares que o incluem."""
    desloc = H_BASE.copy()
    desloc[0, 2] += 3.0
    estab = estabilidade([H_BASE, H_BASE.copy(), desloc])
    por_par = {p["par"]: p["mediana_px"] for p in estab["entre_conjuntos"]}
    assert por_par["0-1"] < 1e-9
    assert por_par["0-2"] > 1.0
    assert por_par["1-2"] > 1.0


def test_achar_quadro_devolve_a_entrada_e_falha_sem_ela() -> None:
    """O quadro pedido é achado pelo id; id ausente levanta ValueError."""
    indice = {"quadros": [{"id": "q02", "t": 1.0}, {"id": "q16", "t": 284.87}]}
    assert achar_quadro(indice, "q16")["t"] == pytest.approx(284.87)
    with pytest.raises(ValueError, match="q99"):
        achar_quadro(indice, "q99")


def test_contar_notas_conta_pisadas_instantes_e_mao_esquerda() -> None:
    """Só notas com casa > 0 entram; instantes com mão esquerda são os com pontas."""
    produto = [
        {"t_ini": 1.0, "casa": 3},
        {"t_ini": 1.0, "casa": 0},
        {"t_ini": 2.0, "casa": 5},
        {"t_ini": 2.0, "casa": 4},
        {"t_ini": 3.0, "casa": 0},
    ]
    pontas = [
        {"t_ini": 1.0, "maos": [{"lado": "esquerda"}]},
        {"t_ini": 2.0, "maos": [{"lado": "direita"}]},
    ]
    contagem = contar_notas(produto, pontas)
    assert contagem["notas_pisadas"] == 3
    assert contagem["instantes_pisados"] == 2
    assert contagem["instantes_com_mao_esquerda"] == 1
    assert contagem["instantes_pontas"] == 2


#: Contagem que passa em todas as regras (6 casas com ≥ 5 notas, vão 5).
CONTAGEM_BOA = {1: 20, 2: 30, 3: 25, 4: 40, 5: 10, 6: 8}


def test_confianca_passa_quando_nenhuma_regra_e_violada() -> None:
    """Casas, vão e estabilidade dentro dos limites: confiável, sem motivos."""
    conf = avaliar_confianca(CONTAGEM_BOA, 0.5)
    assert conf["confiavel"] is True
    assert conf["motivos"] == []
    assert conf["casas_que_contam"] == [1, 2, 3, 4, 5, 6]
    assert conf["vao_casas"] == 5
    assert conf["estabilidade_mediana_px"] == pytest.approx(0.5)


def test_confianca_recusa_por_poucas_casas() -> None:
    """Só 4 casas com ≥ 5 notas: recusa pela regra de casas, só por ela."""
    conf = avaliar_confianca({1: 20, 2: 30, 3: 25, 6: 8}, 0.5)
    assert conf["confiavel"] is False
    assert len(conf["motivos"]) == 1
    assert "casas com" in conf["motivos"][0]
    assert conf["casas_que_contam"] == [1, 2, 3, 6]


def test_confianca_recusa_por_vao_curto() -> None:
    """5 casas que contam mas vão de 4: recusa pela regra de vão, só por ela."""
    conf = avaliar_confianca({1: 20, 2: 30, 3: 25, 4: 40, 5: 10}, 0.5)
    assert conf["confiavel"] is False
    assert len(conf["motivos"]) == 1
    assert "vão de 4" in conf["motivos"][0]
    assert conf["vao_casas"] == 4


def test_confianca_recusa_por_estabilidade_acima_do_limite() -> None:
    """Estabilidade de 2,5 px passa do limite de 2 px: recusa só por ela."""
    conf = avaliar_confianca(CONTAGEM_BOA, 2.5)
    assert conf["confiavel"] is False
    assert len(conf["motivos"]) == 1
    assert "estabilidade" in conf["motivos"][0]


def test_confianca_aceita_estabilidade_no_limite() -> None:
    """Exatamente 2,0 px ainda é aceito (o limite é inclusivo)."""
    assert avaliar_confianca(CONTAGEM_BOA, 2.0)["confiavel"] is True


def test_confianca_casa_com_quatro_notas_nao_conta() -> None:
    """Casa 1 com 4 notas fica fora: sobram 5 casas, com vão de 4, e recusa."""
    conf = avaliar_confianca({1: 4, 2: 30, 3: 25, 4: 40, 5: 10, 6: 8}, 0.5)
    assert conf["casas_que_contam"] == [2, 3, 4, 5, 6]
    assert conf["confiavel"] is False
    assert "vão de 4" in conf["motivos"][0]


def test_confianca_q22_recusa_por_casas_vao_e_estabilidade() -> None:
    """Contagem do q22 (rodada 1008) com estabilidade 85,5 px: recusa nas três."""
    q22 = {1: 31, 2: 170, 3: 4, 4: 150, 5: 57, 7: 1}
    conf = avaliar_confianca(q22, 85.5)
    assert conf["confiavel"] is False
    assert conf["casas_que_contam"] == [1, 2, 4, 5]
    assert conf["vao_casas"] == 4
    assert len(conf["motivos"]) == 3
    assert "casas com" in conf["motivos"][0]
    assert "vão de 4" in conf["motivos"][1]
    assert "estabilidade" in conf["motivos"][2]


def test_confianca_sem_nenhuma_casa_recusa_sem_quebrar() -> None:
    """Nenhuma casa com notas suficientes: recusa, vão 0, sem erro."""
    conf = avaliar_confianca({}, 0.1)
    assert conf["confiavel"] is False
    assert conf["casas_que_contam"] == []
    assert conf["vao_casas"] == 0
