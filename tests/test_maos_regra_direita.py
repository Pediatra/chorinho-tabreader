"""Testes da regra do dedo da mão direita (M5): exemplos do dono e um caso por regra."""

from __future__ import annotations

import pytest

from tab.maos_regra_direita import (
    ALTERNAR_MA_PADRAO,
    JANELA_POLEGAR_S,
    JANELA_SEQUENCIA_S,
    REGRA_ACORDE_INSUFICIENTE,
    REGRA_EXCECAO,
    REGRA_PADRAO,
    REGRA_SEQUENCIA,
    REGRA_SEQUENCIA_ACIMA,
    REGRA_SEQUENCIA_ALTERNA,
    REGRA_SEQUENCIA_GRAVE,
    REGRA_SEQUENCIA_REINICIA,
    V1_ALTERNAR_MA,
    V1_JANELA_POLEGAR_S,
    V1_JANELA_SEQUENCIA_S,
    atribuir_dedos_direita,
)

#: Parâmetros da regra v1 (a que o dono viu nos ímpares), passados explicitamente.
V1 = {
    "janela_polegar_s": V1_JANELA_POLEGAR_S,
    "janela_sequencia_s": V1_JANELA_SEQUENCIA_S,
    "alternar_ma": V1_ALTERNAR_MA,
}


def _n(corda: int, t: float, casa: int = 0) -> dict:
    """Nota mínima do compasso: corda, casa e tempo."""
    return {"corda": corda, "casa": casa, "t_ini": t}


def _dedos(notas: list[dict]) -> list[str]:
    """Só os dedos, na ordem de ``t_ini`` (e de corda dentro do ataque)."""
    return [n["dedo"] for n in atribuir_dedos_direita(notas)]


def _dedos_com(notas: list[dict], **kwargs) -> list[str]:
    """Só os dedos, com parâmetros opcionais da regra."""
    return [n["dedo"] for n in atribuir_dedos_direita(notas, **kwargs)]


def _regras(notas: list[dict]) -> list[str]:
    """Só as regras que decidiram, na mesma ordem."""
    return [n["regra"] for n in atribuir_dedos_direita(notas)]


# --- regra 1: padrão por corda -------------------------------------------------


def test_padrao_por_corda_com_notas_isoladas():
    notas = [_n(c, 10.0 * k) for k, c in enumerate((6, 5, 4, 3, 2, 1))]
    assert _dedos(notas) == ["p", "p", "p", "i", "m", "a"]
    assert set(_regras(notas)) == {REGRA_PADRAO}


def test_corda_invalida_levanta_erro():
    with pytest.raises(ValueError):
        atribuir_dedos_direita([_n(7, 1.0)])


def test_saida_preserva_casa_e_tempo_e_ordena_por_tempo():
    notas = [_n(2, 5.0, casa=3), _n(3, 1.0, casa=4)]
    saida = atribuir_dedos_direita(notas)
    assert [(n["corda"], n["casa"], n["t_ini"]) for n in saida] == [
        (3, 4, 1.0),
        (2, 3, 5.0),
    ]
    assert [n["dedo"] for n in saida] == ["i", "m"]


# --- regra 2: exceção do bordão ------------------------------------------------


def test_bordao_mais_corda_4_no_mesmo_ataque_manda_i_na_4():
    saida = atribuir_dedos_direita([_n(6, 1.0), _n(4, 1.0)])
    dedos = {n["corda"]: n["dedo"] for n in saida}
    assert dedos == {6: "p", 4: "i"}
    assert {n["corda"]: n["regra"] for n in saida}[4] == REGRA_EXCECAO


def test_bordao_no_ataque_anterior_ate_025s_manda_i_na_corda_4():
    saida = atribuir_dedos_direita([_n(5, 1.0), _n(4, 1.25)])
    assert [n["dedo"] for n in saida] == ["p", "i"]
    assert saida[1]["regra"] == REGRA_EXCECAO


def test_bordao_mais_de_025s_antes_nao_vale_e_corda_4_fica_p():
    saida = atribuir_dedos_direita([_n(5, 1.0), _n(4, 1.3)], **V1)
    assert [n["dedo"] for n in saida] == ["p", "p"]


def test_excecao_so_muda_a_corda_4_nao_a_3():
    assert _dedos([_n(5, 1.0), _n(3, 1.1)]) == ["p", "i"]


# --- regra 3: acorde -----------------------------------------------------------


def test_acorde_4_3_2_com_excecao_da_i_m_a():
    saida = atribuir_dedos_direita([_n(6, 1.0), _n(4, 1.0), _n(3, 1.0), _n(2, 1.0)])
    dedos = {n["corda"]: n["dedo"] for n in saida}
    assert dedos == {6: "p", 4: "i", 3: "m", 2: "a"}


def test_acorde_3_2_1_vira_i_m_a():
    assert _dedos([_n(3, 1.0), _n(2, 1.0), _n(1, 1.0)]) == ["i", "m", "a"]


def test_acorde_2_1_vira_m_a():
    assert _dedos([_n(2, 1.0), _n(1, 1.0)]) == ["m", "a"]


def test_acorde_3_1_mantem_a_corda_1_em_a():
    assert _dedos([_n(3, 1.0), _n(1, 1.0)]) == ["i", "a"]


def test_acorde_com_mais_de_tres_dedos_sobra_com_padrao_e_avisa():
    notas = [_n(6, 1.0), _n(4, 1.0), _n(3, 1.0), _n(2, 1.0), _n(1, 1.0)]
    saida = atribuir_dedos_direita(notas)
    dedos = {n["corda"]: n["dedo"] for n in saida}
    assert dedos == {6: "p", 4: "i", 3: "m", 2: "a", 1: "a"}
    assert {n["corda"]: n["regra"] for n in saida}[1] == REGRA_ACORDE_INSUFICIENTE


def test_notas_com_tempo_a_0_02s_de_diferenca_formam_um_acorde():
    assert _dedos([_n(3, 1.00), _n(2, 1.01)]) == ["i", "m"]


# --- regra 4: sequência melódica -----------------------------------------------


def test_sequencia_na_mesma_corda_3_casas_4_5_6_vira_i_m_a():
    notas = [_n(3, 0.0, casa=4), _n(3, 0.4, casa=5), _n(3, 0.8, casa=6)]
    assert _dedos(notas) == ["i", "m", "a"]


def test_sequencia_c3_c3_c2_vira_i_m_a():
    notas = [_n(3, 0.0, casa=2), _n(3, 0.5, casa=1), _n(2, 1.0, casa=0)]
    assert _dedos(notas) == ["i", "m", "a"]
    assert _regras(notas)[2] == REGRA_SEQUENCIA


def test_sequencia_repetida_reinicia_depois_de_a():
    notas = [_n(3, t) for t in (0.0, 0.5, 1.0, 1.5)]
    saida = atribuir_dedos_direita(notas, **V1)
    assert [n["dedo"] for n in saida] == ["i", "m", "a", "i"]
    assert saida[3]["regra"] == REGRA_SEQUENCIA_REINICIA


def test_sequencia_para_corda_mais_grave_usa_o_padrao():
    notas = [_n(2, 0.0), _n(3, 0.5)]
    assert _dedos(notas) == ["m", "i"]
    assert _regras(notas)[1] == REGRA_SEQUENCIA_GRAVE


def test_corda_1_e_sempre_a_mesmo_depois_de_sequencia():
    notas = [_n(3, 0.0), _n(1, 0.5)]
    assert _dedos(notas) == ["i", "a"]
    assert _regras(notas)[1] == REGRA_SEQUENCIA_ACIMA
    assert _dedos([_n(1, 0.0)]) == ["a"]


def test_ataque_so_de_polegar_nao_quebra_a_sequencia():
    notas = [_n(3, 0.0), _n(6, 0.2), _n(3, 0.4)]
    assert _dedos(notas) == ["i", "p", "m"]


def test_sequencia_expira_depois_de_06s():
    assert _dedos_com([_n(3, 0.0), _n(3, 0.7)], **V1) == ["i", "i"]


def test_acorde_zera_a_sequencia():
    notas = [_n(3, 0.0), _n(3, 0.5), _n(2, 0.5), _n(3, 0.9)]
    saida = atribuir_dedos_direita(notas)
    # o acorde em 0.5 (3 e 2) quebra a cadeia: a 3 de 0.9 volta ao padrão
    assert [n["dedo"] for n in saida][-1] == "i"
    assert saida[-1]["regra"] == REGRA_PADRAO


# --- variantes (parâmetros opcionais; default = produção) ----------------------


def test_alternar_ma_mesma_corda_1_repetida_vira_a_m_a_m():
    notas = [_n(1, t) for t in (0.0, 0.2, 0.4, 0.6)]
    assert _dedos_com(notas, **V1) == ["a", "a", "a", "a"]  # v1: não alterna
    saida = atribuir_dedos_direita(notas, alternar_ma=True)
    assert [n["dedo"] for n in saida] == ["a", "m", "a", "m"]
    assert saida[1]["regra"] == REGRA_SEQUENCIA_ALTERNA


def test_alternar_ma_mesma_corda_3_repetida_vira_i_m_a_m_a():
    notas = [_n(3, 0.1 * k) for k in range(5)]
    saida = atribuir_dedos_direita(notas, alternar_ma=True)
    assert [n["dedo"] for n in saida] == ["i", "m", "a", "m", "a"]


def test_alternar_ma_nao_mexe_em_corda_diferente():
    notas = [_n(1, 0.0), _n(3, 0.3)]
    assert _dedos(notas) == ["a", "i"]
    assert atribuir_dedos_direita(notas, alternar_ma=True)[1]["regra"] == (
        REGRA_SEQUENCIA_GRAVE
    )


def test_v1_sem_alternancia_mantem_a_repetida_em_a():
    notas = [_n(1, t) for t in (0.0, 0.2, 0.4)]
    assert _dedos_com(notas, **V1) == ["a", "a", "a"]
    assert _dedos_com(notas, alternar_ma=False) == ["a", "a", "a"]


def test_default_e_a_regra_v2():
    assert JANELA_POLEGAR_S == 1.0
    assert JANELA_SEQUENCIA_S == 1.0
    assert ALTERNAR_MA_PADRAO is True
    notas = [_n(1, 0.0), _n(1, 0.2), _n(5, 0.5), _n(4, 1.2), _n(3, 1.5), _n(3, 2.0)]
    v2 = atribuir_dedos_direita(
        notas, janela_polegar_s=1.0, janela_sequencia_s=1.0, alternar_ma=True
    )
    assert atribuir_dedos_direita(notas) == v2
    assert [n["dedo"] for n in v2] == ["a", "m", "p", "i", "m", "a"]


def test_janela_polegar_maior_pega_bordao_ate_1s_antes_da_corda_4():
    notas = [_n(5, 0.0), _n(4, 0.7)]
    assert _dedos_com(notas, **V1) == ["p", "p"]
    saida = atribuir_dedos_direita(notas, janela_polegar_s=1.0)
    assert [n["dedo"] for n in saida] == ["p", "i"]
    assert saida[1]["regra"] == REGRA_EXCECAO


def test_janela_sequencia_maior_mantem_a_sequencia_ate_1_2s():
    notas = [_n(3, 0.0), _n(3, 0.9)]
    assert _dedos_com(notas, **V1) == ["i", "i"]
    assert _dedos_com(notas, janela_sequencia_s=1.0) == ["i", "m"]
