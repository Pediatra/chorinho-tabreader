"""Testes das funções puras do tempo do som por ataque (M7, item 1; sem GPU e sem acervo)."""

from __future__ import annotations

import pytest

from tab.maos.direita.audio import (
    ataques_com_t_audio,
    diferencas_ms,
    instantes_audio,
    resumo_diferencas,
    t_audio_por_instante,
)


def _nota(t_ini, tela, exibicao, coluna):
    return {"t_ini": t_ini, "tela": tela, "exibicao": exibicao, "coluna": coluna}


def _coluna(tela, exibicao, coluna, t_audio, motivo=None):
    return {
        "tela": tela,
        "exibicao": exibicao,
        "coluna": coluna,
        "t_audio": t_audio,
        "motivo": motivo,
    }


def test_ataque_leva_o_t_audio_da_sua_coluna() -> None:
    notas = [_nota(10.0, 1, 0, 3)]
    colunas = [_coluna(1, 0, 3, 10.18)]
    ataques = ataques_com_t_audio(notas, colunas)
    assert ataques == [
        {"t_ini": 10.0, "t_audio": 10.18, "colunas": [[1, 0, 3]], "motivo": None}
    ]


def test_coluna_recusada_da_none_com_motivo() -> None:
    notas = [_nota(10.0, 1, 0, 3)]
    colunas = [_coluna(1, 0, 3, None, "fora_do_trecho")]
    (ataque,) = ataques_com_t_audio(notas, colunas)
    assert ataque["t_audio"] is None
    assert ataque["motivo"] == "fora_do_trecho"


def test_coluna_ausente_no_alinhamento_vira_none() -> None:
    (ataque,) = ataques_com_t_audio([_nota(10.0, 2, 0, 9)], [])
    assert ataque["t_audio"] is None
    assert ataque["motivo"] == "coluna ausente no alinhamento"


def test_notas_no_mesmo_instante_geram_um_ataque() -> None:
    notas = [_nota(10.0, 1, 0, 3), _nota(10.0, 1, 0, 4), _nota(10.0, 1, 0, 3)]
    colunas = [_coluna(1, 0, 3, 10.2), _coluna(1, 0, 4, 10.4)]
    ataques = ataques_com_t_audio(notas, colunas)
    assert len(ataques) == 1
    assert ataques[0]["t_audio"] == pytest.approx(10.3)
    assert len(ataques[0]["colunas"]) == 2


def test_colunas_recusadas_nao_entram_na_mediana() -> None:
    notas = [_nota(10.0, 1, 0, 3), _nota(10.0, 1, 0, 4)]
    colunas = [_coluna(1, 0, 3, 10.2), _coluna(1, 0, 4, None, "cosseno_baixo")]
    (ataque,) = ataques_com_t_audio(notas, colunas)
    assert ataque["t_audio"] == pytest.approx(10.2)


def test_notas_sem_t_ini_ou_sem_exibicao_sao_ignoradas() -> None:
    notas = [
        {"t_ini": None, "tela": 1, "exibicao": 0, "coluna": 3},
        {"t_ini": 5.0, "tela": 1, "exibicao": None, "coluna": 3},
    ]
    assert ataques_com_t_audio(notas, [_coluna(1, 0, 3, 5.1)]) == []


def test_ataques_saem_em_ordem_de_t_ini() -> None:
    notas = [_nota(9.0, 1, 0, 1), _nota(3.0, 1, 0, 2)]
    colunas = [_coluna(1, 0, 1, 9.1), _coluna(1, 0, 2, 3.2)]
    ataques = ataques_com_t_audio(notas, colunas)
    assert [a["t_ini"] for a in ataques] == [3.0, 9.0]


def test_diferencas_em_ms_so_com_t_audio() -> None:
    ataques = [
        {"t_ini": 10.0, "t_audio": 10.139, "colunas": [], "motivo": None},
        {"t_ini": 11.0, "t_audio": None, "colunas": [], "motivo": "x"},
    ]
    assert diferencas_ms(ataques) == pytest.approx([139.0])


def test_resumo_mediana_e_percentis() -> None:
    valores = [100.0, 120.0, 140.0, 160.0, 180.0]
    r = resumo_diferencas(valores)
    assert r["n"] == 5
    assert r["mediana_ms"] == 140.0
    assert r["p10_ms"] == pytest.approx(108.0)
    assert r["p90_ms"] == pytest.approx(172.0)


def test_resumo_vazio_declara_none() -> None:
    assert resumo_diferencas([]) == {
        "n": 0,
        "mediana_ms": None,
        "p10_ms": None,
        "p90_ms": None,
    }


def test_instantes_e_mapa_so_com_t_audio() -> None:
    ataques = [
        {"t_ini": 1.0, "t_audio": 1.2, "colunas": [], "motivo": None},
        {"t_ini": 2.0, "t_audio": None, "colunas": [], "motivo": "x"},
        {"t_ini": 3.0, "t_audio": 3.1, "colunas": [], "motivo": None},
    ]
    assert instantes_audio(ataques) == [1.2, 3.1]
    assert t_audio_por_instante(ataques) == {1.0: 1.2, 3.0: 3.1}
