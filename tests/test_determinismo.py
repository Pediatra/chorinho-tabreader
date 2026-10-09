"""O treino é reprodutível? Estes testes guardam um conserto que custou medição.

Medido: sem estes ajustes, a **mesma** semente, com o mesmo comando, deu **0,927,
0,896 e 0,948** (amplitude 0,052). A variação era da GPU (convolução em CUDA usa
`atomicAdd`; o cuDNN não é determinístico por padrão), não da semente. O projeto
comparava rodadas sobre a premissa de que "semente fixa" bastava — não bastava.
"""

from __future__ import annotations

import torch

from tab.glyph_bench import GlifoCNN
from tab.sintetico import fixar_semente


def test_fixar_semente_desliga_nondeterminismo_da_gpu() -> None:
    """Remover estes dois flags reintroduz variação de 0,05 na mesma semente."""
    fixar_semente(0)
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False


def test_mesma_semente_produz_a_mesma_inicializacao() -> None:
    """Duas redes criadas com a mesma semente têm pesos idênticos."""
    fixar_semente(7)
    primeira = GlifoCNN(5)
    fixar_semente(7)
    segunda = GlifoCNN(5)
    pares = zip(
        primeira.state_dict().items(), segunda.state_dict().items(), strict=True
    )
    for (nome_a, peso_a), (nome_b, peso_b) in pares:
        assert nome_a == nome_b
        assert torch.equal(peso_a, peso_b), nome_a
