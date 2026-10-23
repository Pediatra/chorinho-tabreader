"""Testes da rodada 1046 (``tab.maos.braco.capo_aberto``), sem GPU e sem acervo."""

from __future__ import annotations

from tab.maos.braco.capo_aberto import (
    casa_do_dono,
    cruza_braco,
    limiar_por_falsos,
    melhor_caixa,
    nut_pela_conta,
    prever_com_capo,
)

#: Braço horizontal: nut em x=100, trastes a cada 50 px para a direita (o corpo).
PREVISTO = {
    "achou": True,
    "sinalizado": False,
    "nut": [100.0, 50.0],
    "corda1": [[100.0, 40.0], [700.0, 40.0]],
    "corda6": [[100.0, 60.0], [700.0, 60.0]],
    "trastes": [{"numero": n, "ponto": [100.0 + 50.0 * n, 50.0]} for n in range(1, 11)],
}


def _caixa(x0: float, x1: float, nota: float = 0.5, rotulo: str = "capo") -> dict:
    """Caixa de teste que cobre as duas cordas entre x0 e x1.

    Args:
        x0: borda esquerda.
        x1: borda direita.
        nota: nota do detector.
        rotulo: rótulo do detector.

    Returns:
        A caixa.
    """
    return {"caixa": [x0, 30.0, x1, 70.0], "nota": nota, "rotulo": rotulo}


def test_cruza_braco_exige_as_duas_cordas():
    assert cruza_braco(_caixa(240, 260)["caixa"], PREVISTO) is True
    assert cruza_braco([240.0, 35.0, 260.0, 45.0], PREVISTO) is False


def test_melhor_caixa_ignora_outros_rotulos_e_fora_do_braco():
    caixas = [
        _caixa(240, 260, 0.9, "hand"),
        _caixa(240, 260, 0.4),
        {"caixa": [0.0, 200.0, 10.0, 210.0], "nota": 0.8, "rotulo": "capo"},
    ]
    assert melhor_caixa(caixas, PREVISTO)["nota"] == 0.4


def test_nut_pela_conta_capo_entre_os_trastes_2_e_3():
    novo = nut_pela_conta(PREVISTO, _caixa(230, 250))
    assert novo["capo_casa"] == 3
    assert novo["nut"] == [250.0, 50.0]
    assert novo["trastes"][0] == {"numero": 1, "ponto": [300.0, 50.0]}
    assert novo["corda1"][0] == [250.0, 40.0]


def test_nut_pela_conta_recusa_capo_longe_do_traste():
    caixa = {"caixa": [100.0, 30.0, 104.0, 70.0], "nota": 0.5, "rotulo": "capo"}
    previsto = dict(PREVISTO, trastes=[{"numero": 3, "ponto": [250.0, 50.0]}])
    previsto["trastes"].append({"numero": 4, "ponto": [300.0, 50.0]})
    assert nut_pela_conta(previsto, caixa) is None


def test_prever_com_capo_sinaliza_na_faixa_de_duvida():
    antigo = {"ordem": ["q1"], "quadros": {"q1": PREVISTO}}
    caixas = {"q1": {"capo.": [_caixa(230, 250, 0.35)]}}
    doc = prever_com_capo(antigo, caixas, "capo.", 0.3)
    assert doc["quadros"]["q1"]["capo"]["casa"] == 3
    assert doc["quadros"]["q1"]["sinalizado"] is True
    doc = prever_com_capo(antigo, caixas, "capo.", 0.5)
    assert doc["quadros"]["q1"]["capo"] == {"visto": False}


def test_limiar_por_falsos():
    notas = [0.0] * 98 + [0.6, 0.4]
    assert limiar_por_falsos(notas, 0.02) == 0.05
    assert abs(limiar_por_falsos([0.0] * 97 + [0.6, 0.4, 0.3], 0.02) - 0.3) < 1e-5


def test_casa_do_dono():
    assert casa_do_dono({"obs": "capotraste casa 3"}) == 3
    assert casa_do_dono({"obs": "previsto"}) is None
