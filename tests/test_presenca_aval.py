"""Medição de caixa e presença por quadro (``tab.presenca_aval``): sem acervo, sem GPU."""

import pytest

from tab.presenca_aval import (
    caixa_sobre_tablatura,
    carregar_gabarito,
    classe,
    iou,
    matriz,
    metricas_caixa,
    metricas_presenca,
)

CAIXA = [100, 500, 900, 700]


def test_classe_cobre_as_quatro_celulas_e_ignora_duvida():
    assert classe(True, "tablatura") == "VP"
    assert classe(True, "nao_tablatura") == "FP"
    assert classe(False, "tablatura") == "FN"
    assert classe(False, "nao_tablatura") == "VN"
    assert classe(True, "duvida") is None


def test_matriz_calcula_precisao_e_revocacao_e_trata_denominador_zero():
    m = matriz(["VP", "VP", "FP", "FN", "VN", None])
    assert (m["VP"], m["FP"], m["VN"], m["FN"]) == (2, 1, 1, 1)
    assert m["precisao"] == round(2 / 3, 3)
    assert m["revocacao"] == round(2 / 3, 3)
    vazia = matriz([])
    assert vazia["precisao"] is None and vazia["revocacao"] is None


def test_iou_de_caixas_identicas_separadas_e_parciais():
    assert iou(CAIXA, CAIXA) == 1.0
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert iou([0, 0, 10, 10], [0, 0, 10, 5]) == pytest.approx(0.5)


def test_caixa_sem_deteccao_nao_tem_rotulo():
    caso = {"codigo": "FN01", "caixa": None, "caixa_sobre_tablatura": None}
    assert caixa_sobre_tablatura(caso, None, []) is None


def test_caixa_igual_ou_quase_igual_usa_o_rotulo_do_dono():
    caso = {"codigo": "VP01", "caixa": CAIXA, "caixa_sobre_tablatura": True}
    assert caixa_sobre_tablatura(caso, CAIXA, []) is True
    deslocada = [CAIXA[0], CAIXA[1] + 2, CAIXA[2], CAIXA[3]]
    assert caixa_sobre_tablatura(caso, deslocada, []) is True


def test_caixa_diferente_usa_rotulo_revisto_e_sem_rotulo_para():
    caso = {
        "codigo": "FP09",
        "caixa": [0, 405, 1920, 555],
        "caixa_sobre_tablatura": False,
    }
    revistas = [
        {"codigo": "FP09", "caixa": [0, 279, 1920, 439], "caixa_sobre_tablatura": False}
    ]
    assert caixa_sobre_tablatura(caso, [0, 279, 1920, 439], revistas) is False
    with pytest.raises(ValueError, match="sem rótulo"):
        caixa_sobre_tablatura(caso, [5, 5, 50, 50], revistas)


def test_metricas_de_caixa_separam_precisao_de_revocacao():
    resultados = [
        {"canal": "a", "tab": True, "caixa_ok": True},  # acerto
        {"canal": "a", "tab": True, "caixa_ok": False},  # caixa no braço, TAB ao lado
        {"canal": "a", "tab": True, "caixa_ok": None},  # TAB sem caixa (FN)
        {"canal": "b", "tab": False, "caixa_ok": False},  # caixa sem TAB
        {"canal": "b", "tab": False, "caixa_ok": None},  # VN
    ]
    m = metricas_caixa(resultados)
    t = m["total"]
    assert (t["caixas"], t["corretas"], t["tablatura"]) == (3, 1, 3)
    assert t["precisao"] == round(1 / 3, 3)
    assert t["revocacao"] == round(1 / 3, 3)
    a = m["por_canal"]["a"]
    assert (a["caixas"], a["corretas"], a["precisao"]) == (2, 1, 0.5)
    assert a["revocacao"] == round(1 / 3, 3)
    b = m["por_canal"]["b"]
    assert (b["caixas"], b["corretas"], b["precisao"]) == (1, 0, 0.0)
    assert b["tablatura"] == 0 and b["revocacao"] is None


def test_presenca_e_so_referencia_e_usa_a_mesma_matriz():
    resultados = [
        {"tab": True, "presenca": True},
        {"tab": False, "presenca": True},
        {"tab": False, "presenca": False},
    ]
    m = metricas_presenca(resultados)
    assert (m["VP"], m["FP"], m["VN"], m["FN"]) == (1, 1, 1, 0)


def test_gabarito_por_quadro_tem_o_contrato_do_dono():
    g = carregar_gabarito()
    casos = g["casos"]
    codigos = [c["codigo"] for c in casos]
    assert len(casos) == 144 and len(set(codigos)) == 144
    com_caixa = [c for c in casos if c["caixa"] is not None]
    assert len(com_caixa) == 118
    assert sum(1 for c in com_caixa if c["caixa_sobre_tablatura"]) == 109
    assert sum(1 for c in casos if c["tablatura_no_quadro"]) == 130
    nao_tab = {c["codigo"] for c in com_caixa if c["caixa_sobre_tablatura"] is False}
    assert nao_tab == {
        "FP02",
        "FP03",
        "FP09",
        "FP10",
        "FP11",
        "FP30",
        "FP31",
        "FP37",
        "FP38",
    }
    for codigo in nao_tab:
        caso = next(c for c in casos if c["codigo"] == codigo)
        assert caso["tablatura_no_quadro"] is True


def test_caixas_revistas_do_dono_2026_10_10():
    g = carregar_gabarito()
    revistas = {(r["codigo"], tuple(r["caixa"])): r for r in g["caixas_revistas"]}
    assert revistas[("FP02", (0, 0, 1920, 106))]["caixa_sobre_tablatura"] is False
    assert revistas[("VN14", (0, 917, 1920, 1077))]["caixa_sobre_tablatura"] is True
    assert revistas[("VN18", (0, 913, 1920, 1080))]["caixa_sobre_tablatura"] is True
    assert revistas[("FP38", (0, 903, 1920, 1080))]["caixa_sobre_tablatura"] is True
    assert revistas[("FP03", (0, 915, 1920, 1076))]["caixa_sobre_tablatura"] is True
    assert len(revistas) == 6
    casos = {c["codigo"]: c for c in g["casos"]}
    assert casos["VN14"]["tablatura_no_quadro"] is True
    assert casos["VN14"]["caixa"] is None
    com_caixa = {c["codigo"] for c in g["casos"] if c["caixa"] is not None}
    com_caixa |= {r["codigo"] for r in g["caixas_revistas"]}
    assert len(com_caixa) == 120
    assert g["quadros"]["com_caixa"] == 120
    assert g["quadros"]["tablatura_no_quadro"] == 130
