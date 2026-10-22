"""Toda constante de saída do ``caminhos`` aponta para a pasta da trilha (decisão 9001).

Depois da fase 4 a saída mora em ``data/saida/<trilha>/``; o caminho solto antigo só existe
como link. Constante nova que aponte para ``data/saida/<nome>`` direto é bug de revisão.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tab.comum import caminhos

TRILHAS = {"tablatura", "maos", "audio", "partitura"}
EXCECOES = {"gpu.lock"}


def _constantes_de_saida() -> dict[str, Path]:
    """Constantes ``Path`` do módulo que ficam dentro de ``data/saida``.

    Returns:
        Nome da constante -> caminho.
    """
    return {
        nome: valor
        for nome, valor in vars(caminhos).items()
        if isinstance(valor, Path) and valor.is_relative_to(caminhos.SAIDA)
        if valor != caminhos.SAIDA
    }


def test_ha_constantes_de_saida_para_conferir():
    assert len(_constantes_de_saida()) >= 40


@pytest.mark.parametrize("nome", sorted(_constantes_de_saida()))
def test_constante_de_saida_esta_na_pasta_da_trilha(nome):
    primeiro = _constantes_de_saida()[nome].relative_to(caminhos.SAIDA).parts[0]
    assert primeiro in TRILHAS or primeiro in EXCECOES, (nome, primeiro)
