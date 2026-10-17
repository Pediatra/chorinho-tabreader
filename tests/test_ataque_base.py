"""Testes da linha de base do ataque (R3)."""

from tab.ataque_base import ataque_previsto, parear, taxas, tela_do_produto


def test_tecnica_de_chegada_e_sem_ataque() -> None:
    assert ataque_previsto(None) == "sim"
    assert ataque_previsto("h") == "nao"
    assert ataque_previsto("\\") == "nao"
    assert ataque_previsto(["lig"]) == "nao"
    assert ataque_previsto("harm") == "sim"
    assert ataque_previsto("vib+p") == "nao"


def test_parear_corda_igual_meio_passo_guloso() -> None:
    ouro = [
        {"corda": 1, "x_centro_quadro": 100.0},
        {"corda": 1, "x_centro_quadro": 108.0},
        {"corda": 2, "x_centro_quadro": 100.0},
    ]
    prev = [
        {"corda": 1, "x_centro_quadro": 107.0},
        {"corda": 3, "x_centro_quadro": 100.0},
    ]
    assert parear(ouro, prev, 20.0) == {1: 0}
    assert parear(ouro, prev, 2.0) == {1: 0}
    assert parear(ouro, prev, 1.0) == {}


def test_tela_do_produto_pela_exibicao() -> None:
    telas = [
        {"id": 1, "exibicoes": [{"t0": 0.0, "t1": 5.0}]},
        {"id": 2, "exibicoes": [{"t0": 6.0, "t1": 9.0}]},
    ]
    assert tela_do_produto(telas, 7.0)["id"] == 2
    assert tela_do_produto(telas, 5.5) is None


def test_taxas_com_denominador() -> None:
    t = taxas(
        {"nao|sim": 8, "nao|nao": 2, "sim|sim": 90, "sim|nao": 1, "nao|nao_lida": 3}
    )
    assert t["sim_falso"] == [8, 10]
    assert t["nao_falso"] == [1, 91]
    assert t["nao_lidas"] == {"sim": 0, "nao": 3}
