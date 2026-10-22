"""Sinais de confiança do detector (rodada 1023): mapas e dados sintéticos, sem GPU."""

from __future__ import annotations

import math

import numpy as np
import pytest

from tab.maos.braco import confianca as conf
from tab.maos.braco.confianca import (
    avaliar,
    escolher_regra,
    marcar,
    sinal_s1,
    sinal_s2,
    sinal_s3,
)
from tab.maos.braco.tempo import Marcas, erros


def _marcas(desloc_corda1: float = 0.0, desloc_nut: float = 0.0) -> Marcas:
    """Braço horizontal de teste: cordas em y = 60 e y = 140, nut e 5 trastes no meio."""
    nut = np.array([100.0 + desloc_nut, 100.0])
    trastes = {
        1: np.array([200.0, 100.0]),
        2: np.array([300.0, 100.0]),
        3: np.array([390.0, 100.0]),
        4: np.array([470.0, 100.0]),
        5: np.array([545.0, 100.0]),
    }
    corda1 = np.array([[0.0, 60.0 + desloc_corda1], [1000.0, 60.0 + desloc_corda1]])
    corda6 = np.array([[0.0, 140.0], [1000.0, 140.0]])
    return Marcas(nut=nut, trastes=trastes, corda1=corda1, corda6=corda6)


def _mapa(maximos: dict[int, float]) -> np.ndarray:
    """Mapas zerados (4, 192, 1024) com o máximo pedido em cada canal."""
    mapa = np.zeros((4, 192, 1024), dtype=np.float32)
    for canal, valor in maximos.items():
        mapa[canal, 10, 10] = valor
    return mapa


def test_s3_pega_o_menor_maximo_entre_corda1_corda6_e_nut() -> None:
    """S3 = 1 - min(max corda1, max corda6, max nut); o canal de trastes não entra."""
    mapa = _mapa({0: 0.9, 1: 0.8, 2: 0.99, 3: 0.7})
    assert sinal_s3(mapa) == pytest.approx(0.3)


def test_s3_zero_quando_os_mapas_sao_fortes() -> None:
    """Mapas com máximo 1 nos três canais dão S3 = 0."""
    assert sinal_s3(_mapa({0: 1.0, 1: 1.0, 3: 1.0})) == pytest.approx(0.0)


def test_s2_soma_inliers_e_picos_nao_inliers() -> None:
    """Inliers 1,2,3,5 (maior 5) e picos 10..50 com 40 fora: 0,2 + 0,2 = 0,4."""
    info = {
        "achou": True,
        "inliers": {1: 10.0, 2: 20.0, 3: 30.0, 5: 50.0},
        "picos": [5, 10, 20, 30, 40, 50],
        "x_nut": 5.0,
    }
    assert sinal_s2(info) == pytest.approx(0.4)


def test_s2_sem_braco_e_infinito() -> None:
    """Sem braço, o S2 é infinito (conta como sinalizado)."""
    assert sinal_s2({"achou": False, "inliers": {}, "picos": [], "x_nut": 0.0}) == (
        math.inf
    )


def test_s1_quadro_identico_e_zero() -> None:
    """Principal e extra iguais: discordância zero."""
    marcas = _marcas()
    assert sinal_s1(marcas, [marcas, marcas, marcas, marcas]) == pytest.approx(0.0)


def test_s1_e_o_maximo_sobre_as_extras() -> None:
    """Com uma extra distante e outra igual, o S1 é a discordância da distante."""
    principal = _marcas()
    perto = _marcas()
    longe = _marcas(desloc_corda1=8.0)
    esperado = erros(principal, longe)["perp_cordas"] / 0.5
    s1 = sinal_s1(principal, [perto, longe, perto, perto])
    assert s1 == pytest.approx(max(esperado, 0.0))
    assert s1 > 0.0


def test_s1_sem_braco_e_infinito() -> None:
    """Principal sem braço, ou extra sem braço, dão infinito."""
    marcas = _marcas()
    assert sinal_s1(None, [marcas]) == math.inf
    assert sinal_s1(marcas, [marcas, None, marcas, marcas]) == math.inf


def _quadros_sinteticos(
    n_certos: int, n_falsos: int, s1_falsos: float = 2.0
) -> list[dict]:
    """Quadros com S1 separando falsos (valores altos) de certos (abaixo de 1)."""
    quadros = []
    for i in range(n_certos):
        quadros.append(
            {
                "id": f"c{i}",
                "canal": "x",
                "achou": True,
                "falso": False,
                "S1": i / (n_certos + n_falsos),
                "S2": 0.1,
                "S3": 0.1,
            }
        )
    for i in range(n_falsos):
        quadros.append(
            {
                "id": f"f{i}",
                "canal": "x",
                "achou": True,
                "falso": True,
                "S1": s1_falsos + i,
                "S2": 0.1,
                "S3": 0.1,
            }
        )
    return quadros


def test_escolha_pega_o_sinal_que_separa_os_falsos() -> None:
    """S1 separa os 20 falsos; a escolha tem 0 falsos que passam e 20 sinalizados."""
    quadros = _quadros_sinteticos(180, 20)
    escolha = escolher_regra(quadros)
    escolhida = escolha["escolhida"]
    assert escolhida["regra"] == "S1"
    assert escolhida["percentis"] == {"S1": 90}
    assert escolhida["falsos_nao_sinalizados"] == 0
    assert escolhida["sinalizados"] == 20
    assert escolha["passou"] is True


def test_escolha_respeita_o_teto_de_30_por_cento() -> None:
    """Com metade dos quadros falsos, nenhuma candidata cabe nos 30 %."""
    quadros = _quadros_sinteticos(100, 100)
    escolha = escolher_regra(quadros)
    assert escolha["escolhida"] is not None
    assert escolha["escolhida"]["fracao_sinalizada"] <= 0.30
    assert escolha["passou"] is False


def test_escolha_sem_candidata_quando_tudo_nao_acha() -> None:
    """Se todo quadro não acha o braço, todas as regras sinalizam 100 %: sem escolha."""
    quadros = [
        {
            "id": str(i),
            "canal": "x",
            "achou": False,
            "falso": False,
            "S1": math.inf,
            "S2": math.inf,
            "S3": 0.5,
        }
        for i in range(10)
    ]
    escolha = escolher_regra(quadros)
    assert escolha["escolhida"] is None
    assert escolha["passou"] is False


def test_nao_achou_conta_como_sinalizado() -> None:
    """Quadro sem braço é sinalizado mesmo com todos os sinais baixos."""
    quadros = [
        {
            "id": "a",
            "canal": "x",
            "achou": False,
            "falso": True,
            "S1": 0.0,
            "S2": 0.0,
            "S3": 0.0,
        },
        {
            "id": "b",
            "canal": "x",
            "achou": True,
            "falso": False,
            "S1": 0.0,
            "S2": 0.0,
            "S3": 0.0,
        },
    ]
    resultado = avaliar(quadros, ("S1",), {"S1": 1.0})
    assert resultado["sinalizados"] == 1
    assert resultado["falsos_nao_sinalizados"] == 0
    assert marcar(quadros, ("S1",), {"S1": 1.0}).tolist() == [True, False]


def test_regra_ou_marca_quando_qualquer_sinal_passa_o_limiar() -> None:
    """S1 OU S2: basta um dos dois acima do seu limiar."""
    quadros = [
        {
            "id": "a",
            "canal": "x",
            "achou": True,
            "falso": False,
            "S1": 2.0,
            "S2": 0.0,
            "S3": 0.0,
        },
        {
            "id": "b",
            "canal": "x",
            "achou": True,
            "falso": False,
            "S1": 0.0,
            "S2": 2.0,
            "S3": 0.0,
        },
        {
            "id": "c",
            "canal": "x",
            "achou": True,
            "falso": False,
            "S1": 0.0,
            "S2": 0.0,
            "S3": 0.0,
        },
    ]
    mascara = marcar(quadros, ("S1", "S2"), {"S1": 1.0, "S2": 1.0})
    assert mascara.tolist() == [True, True, False]


def test_confirmar_falha_sem_regra_congelada(tmp_path, monkeypatch) -> None:
    """Sem regra congelada, ``confirmar`` levanta erro claro."""
    monkeypatch.setattr(conf, "REGRA_CONGELADA", None)
    monkeypatch.setattr(conf, "LIMIARES_CONGELADOS", None)
    with pytest.raises(RuntimeError, match="não congelada"):
        conf.confirmar(tmp_path / "nao_grava.json")


def test_regra_congelada_da_1023() -> None:
    """A regra congelada é a escolhida no desenvolvimento da 1023 (S1 ou S2)."""
    assert conf.REGRA_CONGELADA == ("S1", "S2")
    assert set(conf.LIMIARES_CONGELADOS) == {"S1", "S2"}
