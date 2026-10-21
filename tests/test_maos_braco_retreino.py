"""Testes do retreino com a regra do capo (``tab.maos_braco_retreino``, rodada 1037).

Sem GPU e sem acervo: só a separação das fontes, os critérios e a calibração.
"""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_braco_retreino import (
    EXCLUIDOS,
    avaliar_criterios,
    calibracao,
    chave_do_r,
    com_capo,
    cortar_no_nut,
    separar,
    tem_capo,
)
from tab.maos_braco_tempo import Marcas


def _registro(origem: str, chave: str, arquivo: str = "canal/v.mp4") -> dict:
    return {
        "id": f"{origem}-{chave}",
        "origem": origem,
        "chave": chave,
        "arquivo": arquivo,
    }


def test_chave_do_r():
    assert chave_do_r("/app/data/saida/maos/m21/R/q10_+3.jpg") == "q10"
    assert chave_do_r("q04_-10.jpg") == "q04"


def test_separar_tira_excluidos_e_videos_de_medida():
    registros = [
        _registro("R", "q10"),
        _registro("G", "q10"),
        _registro("R", "q04"),
        _registro("M32", "q14"),
        _registro("M32", "q15"),
        _registro("C", "q139"),
        _registro("M29", "q01", arquivo="canál/medida.mp4"),
    ]
    proibidos = {"canál/medida.mp4"}
    ficam, relatorio = separar(registros, proibidos, EXCLUIDOS)
    assert [r["id"] for r in ficam] == ["R-q04", "M32-q15"]
    assert relatorio["R"]["usados"] == 1
    assert [f["id"] for f in relatorio["R"]["fora"]] == ["R-q10"]
    assert relatorio["G"]["usados"] == 0
    assert relatorio["M29"]["fora"][0]["motivo"] == "vídeo de um conjunto de medida"


def test_excluidos_sao_os_do_pre_registro():
    assert set(EXCLUIDOS["M3b"]) == {"q10"}
    assert set(EXCLUIDOS["M32"]) == {"q14", "q45"}
    assert set(EXCLUIDOS["C"]) == {"q139"}


def test_tem_capo_e_com_capo():
    gabaritos = {
        "M32": {"q01": {"capo": [10.0, 20.0]}, "q02": {"capo": None}},
        "R": {"q04": {"capo": [1.0, 2.0]}},
    }
    registros = [
        _registro("M32", "q01"),
        _registro("M32", "q02"),
        _registro("R", "q04"),
    ]
    assert [r["id"] for r in com_capo(registros, gabaritos)] == ["M32-q01", "R-q04"]
    assert not tem_capo({})


def _totais(certos: int, falsos: int, medidos: int) -> dict:
    return {
        "entregue_certo": certos,
        "falsos_passam_n": falsos,
        "falsos_passam": falsos / medidos,
        "medidos": medidos,
    }


def _medida(todos: tuple, capo: tuple, sem: tuple) -> dict:
    return {"todos": _totais(*todos), "capo": _totais(*capo), "sem_capo": _totais(*sem)}


def test_criterios_passam():
    novo = {
        "M36": _medida((20, 1, 32), (12, 1, 16), (8, 0, 16)),
        "N": _medida((15, 0, 23), (3, 0, 4), (12, 0, 19)),
    }
    antigo = {
        "M36": _medida((9, 1, 32), (6, 1, 16), (3, 0, 16)),
        "N": _medida((15, 2, 23), (0, 2, 4), (15, 0, 19)),
    }
    resultado = avaliar_criterios(novo, antigo)
    assert resultado["seguranca"]
    assert resultado["capo"]
    assert resultado["sem_capo"]
    assert resultado["numeros"]["capo_certos_novo_antigo"] == [15, 6]


def test_criterios_reprovam():
    novo = {
        "M36": _medida((20, 2, 32), (12, 2, 16), (8, 0, 16)),
        "N": _medida((10, 0, 23), (3, 0, 4), (7, 2, 19)),
    }
    antigo = {
        "M36": _medida((9, 1, 32), (6, 1, 16), (3, 0, 16)),
        "N": _medida((15, 0, 23), (0, 0, 4), (15, 0, 19)),
    }
    resultado = avaliar_criterios(novo, antigo)
    assert not resultado["seguranca"]  # 2/32 = 6,25 % na M36
    assert not resultado["capo"]  # 2 falsos com capo
    assert not resultado["sem_capo"]  # 2 falsos contra 0, e 15 certos contra 18


def test_calibracao_por_sinal_e_tercos():
    linhas = [
        {"id": f"q{i}", "sinalizado": i >= 4, "correto": i not in (2, 5)}
        for i in range(6)
    ]
    previstos = {f"q{i}": {"achou": True, "S1": i / 10} for i in range(6)}
    previstos["q5"] = {"achou": False, "S1": None}
    resultado = calibracao(linhas, previstos)
    assert resultado["sem_sinal"] == [3, 4]
    assert resultado["sinalizados"] == [1, 2]
    assert resultado["tercos_S1"] == [[1, 1, 0.0], [1, 2, 0.2], [2, 2, 0.4]]


def test_cortar_no_nut_leva_a_ponta_perto_ao_nut_marcado():
    # cordas horizontais, do nut verdadeiro (x = 0) ao corpo (x = 100); capo em x = 20
    marcas = Marcas(
        nut=np.array([20.0, 15.0]),
        trastes={1: np.array([30.0, 15.0])},
        corda1=np.array([[100.0, 10.0], [0.0, 10.0]]),
        corda6=np.array([[0.0, 20.0], [100.0, 20.0]]),
    )
    cortadas = cortar_no_nut(marcas)
    np.testing.assert_allclose(cortadas.corda1, [[100.0, 10.0], [20.0, 10.0]])
    np.testing.assert_allclose(cortadas.corda6, [[20.0, 20.0], [100.0, 20.0]])
    np.testing.assert_allclose(marcas.corda1, [[100.0, 10.0], [0.0, 10.0]])
    assert cortadas.trastes is marcas.trastes


def test_cortar_no_nut_sem_nut_falha():
    marcas = Marcas(
        nut=None,
        trastes={},
        corda1=np.zeros((2, 2)),
        corda6=np.ones((2, 2)),
    )
    with pytest.raises(ValueError):
        cortar_no_nut(marcas)
