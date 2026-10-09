"""Contrato do gabarito rotulado à mão.

Se este teste quebrar, o número oficial do projeto mudou de base — e isso é uma
decisão consciente, não um detalhe. Ver AGENTS.md.
"""

from __future__ import annotations

import json

from tab.caminhos import GABARITO

#: Total de glifos rotulados à mão na rodada 65.
GLIFOS_ESPERADOS = 96

#: Canais com amostra rotulada.
CANAIS_ESPERADOS = 4

#: Rótulos `junk` do canal raman korshun (alcançáveis só com a regra de rejeição).
JUNK_ESPERADOS = 7


def _gabarito() -> dict:
    return json.loads(GABARITO.read_text(encoding="utf-8"))


def test_total_de_glifos_rotulados() -> None:
    """O gabarito tem exatamente 96 glifos rotulados."""
    amostras = _gabarito()["amostras"]
    assert sum(len(a["rotulos"]) for a in amostras) == GLIFOS_ESPERADOS


def test_um_canal_por_amostra() -> None:
    """Cada amostra é de um canal distinto, e são 4."""
    amostras = _gabarito()["amostras"]
    canais = [a["canal"] for a in amostras]
    assert len(canais) == CANAIS_ESPERADOS
    assert len(set(canais)) == CANAIS_ESPERADOS


def test_rotulos_junk_do_raman() -> None:
    """Os 7 rótulos `junk` existem — é o que a regra de rejeição tem de alcançar."""
    rotulos = [v for a in _gabarito()["amostras"] for v in a["rotulos"].values()]
    assert rotulos.count("junk") == JUNK_ESPERADOS


def test_cada_amostra_aponta_para_um_video() -> None:
    """Toda amostra registra de onde veio (vídeo + faixa + passo)."""
    for amostra in _gabarito()["amostras"]:
        assert amostra.get("video"), amostra["canal"]
        assert amostra.get("faixa") in {"topo", "meio", "base"}, amostra["canal"]
        assert amostra.get("passo", 0) > 0, amostra["canal"]
