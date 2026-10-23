"""Testes da rodada 1044 (``tab.maos.braco.validadores``), sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np

from tab.maos.braco.tempo import Marcas
from tab.maos.braco.validadores import (
    concordam,
    escolher_hipotese,
    faixas_das_marcas,
    medidas,
    validar,
)

#: Escala de 650 mm a 1 px por mm, braço horizontal, nut em x=0.
POSICOES = [650.0 * (1 - 2 ** (-n / 12)) for n in range(0, 10)]


def _marcas(posicoes: list[float], largura_nut: float = 43.0) -> Marcas:
    """Braço de teste: nut e trastes em ``posicoes``, alargando para o corpo.

    Args:
        posicoes: posição x do nut e dos trastes.
        largura_nut: largura no nut (cresce 13 mm até o traste 12).

    Returns:
        As marcas.
    """
    fim = 325.0
    meia_fim = (largura_nut + 13.0) / 2
    return Marcas(
        nut=np.array([posicoes[0], 0.0]),
        trastes={n: np.array([x, 0.0]) for n, x in enumerate(posicoes) if n > 0},
        corda1=np.array([[0.0, -largura_nut / 2], [fim, -meia_fim]]),
        corda6=np.array([[0.0, largura_nut / 2], [fim, meia_fim]]),
    )


def test_medidas_do_braco_fisico():
    m = medidas(_marcas(POSICOES))
    assert abs(m["escada"] - 2 ** (-1 / 12)) < 1e-6
    assert m["irregular"] < 1e-6
    assert 43.0 < m["largura_mm"] < 50.0
    assert m["alarga"] > 1.0
    assert m["cruzam"] == 0.0
    assert abs(m["nut"] - 2 ** (1 / 12)) < 1e-6


def test_braco_invertido_tem_escada_acima_de_um():
    invertido = POSICOES[::-1]
    assert medidas(_marcas(invertido))["escada"] > 1.0


def test_faixas_e_validar():
    dono = [medidas(_marcas(POSICOES, w)) for w in np.linspace(40, 48, 50)]
    faixas = faixas_das_marcas(dono)
    assert faixas["V2_escada"]["aprovadas"][0] >= 49
    assert validar(_marcas(POSICOES, 44.0), faixas)["passa"] is True
    amontoados = [x * 0.3 if n > 4 else x for n, x in enumerate(POSICOES)]
    assert validar(_marcas(amontoados, 44.0), faixas)["passa"] is False
    assert validar(None, faixas)["passa"] is False


def test_concordam_ate_um_quarto_de_casa():
    a = _marcas(POSICOES)
    perto = _marcas([x + 3.0 for x in POSICOES])
    longe = _marcas([x + 20.0 for x in POSICOES])
    assert concordam(a, perto) is True
    assert concordam(a, longe) is False


def _previsto(posicoes: list[float]) -> dict:
    """Entrada de ``previsto.json`` com o braço de teste.

    Args:
        posicoes: posição x do nut e dos trastes.

    Returns:
        A entrada.
    """
    m = _marcas(posicoes)
    return {
        "achou": True,
        "sinalizado": False,
        "nut": m.nut.tolist(),
        "corda1": m.corda1.tolist(),
        "corda6": m.corda6.tolist(),
        "trastes": [{"numero": n, "ponto": p.tolist()} for n, p in m.trastes.items()],
    }


def test_escolher_hipotese_exige_grupo():
    dono = [medidas(_marcas(POSICOES, w)) for w in np.linspace(40, 48, 50)]
    faixas = faixas_das_marcas(dono)
    certas = {f"h{i}": _previsto(POSICOES) for i in range(6)}
    assert escolher_hipotese(certas, faixas)["entregue"] == "h0"
    poucas = {f"h{i}": _previsto(POSICOES) for i in range(5)}
    assert escolher_hipotese(poucas, faixas)["entregue"] is None
