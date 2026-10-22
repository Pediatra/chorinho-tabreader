"""Testes da rodada 1042 (``tab.maos.braco.retreino_1042``), sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np

from tab.maos.braco import retreino_1042
from tab.maos.braco.retreino_1042 import (
    contar_inversoes,
    criterio_sem_capo,
    escolher_com_veto,
    invertido,
)
from tab.maos.braco.tempo import Marcas

#: Braço horizontal: nut em x=100, corpo para a direita (x=1000).
MARCAS = Marcas(
    nut=np.array([100.0, 50.0]),
    trastes={},
    corda1=np.array([[100.0, 40.0], [1000.0, 40.0]]),
    corda6=np.array([[100.0, 60.0], [1000.0, 60.0]]),
)


def _marcas(registro: dict) -> Marcas | None:
    """Substituto de ``marcas_do_registro``: o registro ``ok`` tem o braço de teste.

    Args:
        registro: registro de teste.

    Returns:
        ``MARCAS`` ou None.
    """
    return MARCAS if registro.get("ok") else None


def _linha(nome: str, certos: int, inversoes: int, falsos: int = 0) -> dict:
    """Linha da tabela da escolha, com as inversões na M36.

    Args:
        nome: nome do estágio 1.
        certos: entregues certos.
        inversoes: quadros invertidos na M36.
        falsos: falsos que passam.

    Returns:
        A linha.
    """
    return {
        "estagio1": nome,
        "estagio2": "A",
        "soma_sementes": 2,
        "falsos_passam_n": falsos,
        "entregue_certo": certos,
        "sinalizados": 5,
        "inversoes_m36": [inversoes, 28],
    }


def test_invertido_pelo_lado_do_corpo(monkeypatch):
    monkeypatch.setattr(retreino_1042, "marcas_do_registro", _marcas)
    assert invertido([110.0, 50.0], {"ok": True}) is False
    assert invertido([900.0, 50.0], {"ok": True}) is True
    assert invertido(None, {"ok": True}) is None
    assert invertido([900.0, 50.0], {"ok": False}) is None


def test_contar_inversoes_ignora_sem_braco(monkeypatch):
    monkeypatch.setattr(retreino_1042, "marcas_do_registro", _marcas)
    previsto = {
        "ordem": ["q1", "q2", "q3", "q4"],
        "quadros": {
            "q1": {"achou": True, "nut": [105.0, 50.0]},
            "q2": {"achou": True, "nut": [950.0, 50.0]},
            "q3": {"achou": False, "nut": [950.0, 50.0]},
            "q4": {"achou": True, "nut": [950.0, 50.0]},
        },
    }
    gabarito = {"quadros": {"q1": {"ok": True}, "q2": {"ok": True}, "q3": {"ok": True}}}
    assert contar_inversoes(previsto, gabarito) == [1, 2]


def test_veto_tira_o_par_que_inverte():
    referencia = _linha("antigo", certos=14, inversoes=0)
    tabela = [
        _linha("inverte", certos=20, inversoes=7),
        _linha("sao", certos=13, inversoes=0, falsos=1),
    ]
    assert escolher_com_veto(tabela, referencia)["estagio1"] == "sao"


def test_veto_e_piso_juntos_podem_nao_escolher():
    referencia = _linha("antigo", certos=14, inversoes=0)
    tabela = [_linha("inverte", certos=20, inversoes=1), _linha("fraco", 5, 0)]
    assert escolher_com_veto(tabela, referencia) is None


def test_criterio_sem_capo_no_n():
    def medida(falsos: int, certos: int) -> dict:
        return {"sem_capo": {"falsos_passam_n": falsos, "entregue_certo": certos}}

    assert criterio_sem_capo(medida(2, 13), medida(1, 15))["passa"] is True
    assert criterio_sem_capo(medida(3, 15), medida(1, 15))["passa"] is False
    assert criterio_sem_capo(medida(1, 12), medida(1, 15))["passa"] is False
