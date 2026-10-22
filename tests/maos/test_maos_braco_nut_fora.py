"""Testes das funções puras da rodada 1031 (nut fora): combinação, aplicação e medida."""

from tab.maos.braco.nut_fora import (
    aplicar,
    classe_do_caso,
    combinar,
    numero_na_referencia,
    nut_suspeito,
)


def _previsto(
    pontos_x: list[float],
    numeros: list[int],
    *,
    achou: bool = True,
    sinalizado: bool = False,
) -> dict:
    """Monta uma previsão com trastes em uma linha horizontal.

    Args:
        pontos_x: posições x dos trastes.
        numeros: números dos trastes, na mesma ordem.
        achou: valor de ``achou``.
        sinalizado: valor de ``sinalizado``.

    Returns:
        Previsão no formato do detector, com ``trastes`` e as flags.
    """
    return {
        "achou": achou,
        "sinalizado": sinalizado,
        "trastes": [
            {"numero": n, "ponto": [x, 130.0]}
            for x, n in zip(pontos_x, numeros, strict=True)
        ],
    }


def _quadro_nut(
    nut: list[float], corda1: list[list[float]], corda6: list[list[float]]
) -> dict:
    """Monta um quadro denso com nut e cordas para a regra de nut suspeito.

    Args:
        nut: ponto do nut, ou None.
        corda1: pontas da corda 1.
        corda6: pontas da corda 6.

    Returns:
        Registro com ``previsto`` e ``dimensoes`` de 1280 x 720.
    """
    return {
        "dimensoes": [1280, 720],
        "previsto": {
            "achou": True,
            "sinalizado": False,
            "nut": nut,
            "corda1": corda1,
            "corda6": corda6,
        },
    }


def test_combinar_concordam_devolve_k_sem_sinal():
    """V e J com o mesmo k decidem k, sem sinalizar."""
    saida = combinar({"k": 1}, {"k": 1}, suspeito=True)
    assert saida["k"] == 1
    assert saida["sinaliza"] is False
    assert saida["motivo"] == "concordam"


def test_combinar_discordam_sinaliza_sem_k():
    """V e J com k diferentes não decidem e sinalizam."""
    saida = combinar({"k": 1}, {"k": 2}, suspeito=False)
    assert saida["k"] is None
    assert saida["sinaliza"] is True
    assert saida["motivo"] == "discordam"


def test_combinar_so_v_decide():
    """Só V com k decide com o k de V."""
    saida = combinar({"k": 2}, None, suspeito=False)
    assert saida["k"] == 2
    assert saida["sinaliza"] is False
    assert saida["motivo"] == "só V"


def test_combinar_so_j_decide():
    """Só J com k decide com o k de J."""
    saida = combinar(None, {"k": -1}, suspeito=False)
    assert saida["k"] == -1
    assert saida["sinaliza"] is False
    assert saida["motivo"] == "só J"


def test_combinar_nenhum_decide_com_suspeito_sinaliza():
    """Nenhum método decide e o nut é suspeito: sinaliza."""
    saida = combinar({"k": None}, {"k": None}, suspeito=True)
    assert saida["k"] is None
    assert saida["sinaliza"] is True
    assert saida["motivo"] == "nenhum decide"


def test_combinar_nenhum_decide_sem_suspeito_nao_sinaliza():
    """Nenhum método decide e o nut não é suspeito: não sinaliza."""
    saida = combinar(None, None, suspeito=False)
    assert saida["k"] is None
    assert saida["sinaliza"] is False


def test_aplicar_soma_k_sem_mutar_entrada():
    """Com k=1 cada número sobe 1, e a previsão original não muda."""
    previsto = _previsto([100.0, 200.0], [3, 4])
    saida = aplicar(previsto, 1, False)
    assert [t["numero"] for t in saida["trastes"]] == [4, 5]
    assert [t["numero"] for t in previsto["trastes"]] == [3, 4]


def test_aplicar_k_none_ou_zero_nao_muda_numeros():
    """Com k None ou 0 os números ficam como estão."""
    previsto = _previsto([100.0, 200.0], [3, 4])
    for k in (None, 0):
        saida = aplicar(previsto, k, False)
        assert [t["numero"] for t in saida["trastes"]] == [3, 4]


def test_aplicar_sinaliza_marca_sinalizado():
    """Com sinaliza True o quadro sai com sinalizado True."""
    previsto = _previsto([100.0], [3])
    saida = aplicar(previsto, None, True)
    assert saida["sinalizado"] is True
    assert previsto["sinalizado"] is False


def test_numero_na_referencia_pega_traste_mais_perto():
    """Ponto a 5 px do traste 2 (espaço local de 100 px) devolve o número 2."""
    previsto = _previsto([100.0, 200.0, 300.0], [1, 2, 3])
    referencia = {"ponto": [205.0, 130.0], "numero": 2}
    assert numero_na_referencia(previsto, referencia) == 2


def test_numero_na_referencia_no_limite_da_tolerancia_conta():
    """Ponto a 50 px do traste 1 (meio do espaço de 100 px) ainda conta: devolve 1."""
    previsto = _previsto([100.0, 200.0, 300.0], [1, 2, 3])
    referencia = {"ponto": [150.0, 130.0], "numero": 1}
    assert numero_na_referencia(previsto, referencia) == 1


def test_numero_na_referencia_longe_de_todo_traste_devolve_none():
    """Ponto a 200 px do traste mais perto (além de meio espaço) devolve None."""
    previsto = _previsto([100.0, 200.0, 300.0], [1, 2, 3])
    referencia = {"ponto": [500.0, 130.0], "numero": 3}
    assert numero_na_referencia(previsto, referencia) is None


def test_numero_na_referencia_sem_braco_devolve_none():
    """Sem braço achado não há número na referência."""
    previsto = _previsto([100.0, 200.0, 300.0], [1, 2, 3], achou=False)
    referencia = {"ponto": [205.0, 130.0], "numero": 2}
    assert numero_na_referencia(previsto, referencia) is None


def test_classe_do_caso_numero_certo_sem_sinal_e_acerto():
    """Número certo e não sinalizado é acerto."""
    previsto = _previsto([100.0, 200.0], [1, 2])
    registro = {"traste_referencia": {"ponto": [205.0, 130.0], "numero": 2}}
    classe, numero = classe_do_caso(previsto, registro)
    assert classe == "acerto"
    assert numero == 2


def test_classe_do_caso_numero_certo_com_sinal_e_acerto_sinalizado():
    """Número certo e sinalizado é acerto sinalizado."""
    previsto = _previsto([100.0, 200.0], [1, 2], sinalizado=True)
    registro = {"traste_referencia": {"ponto": [205.0, 130.0], "numero": 2}}
    classe, _ = classe_do_caso(previsto, registro)
    assert classe == "acerto sinalizado"


def test_classe_do_caso_numero_errado_sem_sinal_e_erro_nao_sinalizado():
    """Número errado e não sinalizado é erro não sinalizado."""
    previsto = _previsto([100.0, 200.0], [1, 2])
    registro = {"traste_referencia": {"ponto": [205.0, 130.0], "numero": 5}}
    classe, numero = classe_do_caso(previsto, registro)
    assert classe == "erro não sinalizado"
    assert numero == 2


def test_classe_do_caso_numero_errado_com_sinal_e_recusa():
    """Número errado e sinalizado é recusa."""
    previsto = _previsto([100.0, 200.0], [1, 2], sinalizado=True)
    registro = {"traste_referencia": {"ponto": [205.0, 130.0], "numero": 5}}
    classe, _ = classe_do_caso(previsto, registro)
    assert classe == "recusa"


def test_nut_suspeito_ponta_rente_a_borda_esquerda():
    """Ponta de corda a 10 px da borda (menos de 2 % de 720 = 14,4 px) é suspeita."""
    registro = _quadro_nut(
        nut=[10.0, 350.0],
        corda1=[[10.0, 300.0], [1200.0, 300.0]],
        corda6=[[10.0, 400.0], [1200.0, 400.0]],
    )
    assert nut_suspeito(registro) is True


def test_nut_suspeito_ponta_longe_da_borda_nao_e_suspeita():
    """Ponta a 100 px da borda não é suspeita."""
    registro = _quadro_nut(
        nut=[100.0, 350.0],
        corda1=[[100.0, 300.0], [1200.0, 300.0]],
        corda6=[[100.0, 400.0], [1200.0, 400.0]],
    )
    assert nut_suspeito(registro) is False


def test_nut_suspeito_sem_nut_e_suspeito():
    """Braço achado sem nut é suspeito."""
    registro = _quadro_nut(
        nut=None,
        corda1=[[100.0, 300.0], [1200.0, 300.0]],
        corda6=[[100.0, 400.0], [1200.0, 400.0]],
    )
    assert nut_suspeito(registro) is True


def test_nut_suspeito_sem_braco_nao_e_suspeito():
    """Sem braço achado não há nut suspeito."""
    registro = _quadro_nut(
        nut=[10.0, 350.0],
        corda1=[[10.0, 300.0], [1200.0, 300.0]],
        corda6=[[10.0, 400.0], [1200.0, 400.0]],
    )
    registro["previsto"]["achou"] = False
    assert nut_suspeito(registro) is False
