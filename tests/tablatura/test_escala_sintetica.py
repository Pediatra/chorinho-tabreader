"""A escala do algarismo no gerador: o padrão não muda, a opção nova é reprodutível.

Medido na rodada 0009: o algarismo real do ouro tem 0,93 passo de altura, e o gerador
antigo, no máximo, 0,75. `--escala larga` cobre esse tamanho sem mexer no padrão, que
reproduz os pesos `oficial_*`.
"""

from __future__ import annotations

import random

import numpy as np

from tab.tablatura.treino.sintetico import _parser, gerar_linha


def test_padrao_nao_muda_com_a_flag_desligada() -> None:
    """Sem a flag, `gerar_linha` é o de antes: mesma imagem para a mesma semente."""
    sem_arg, notas_a = gerar_linha(random.Random(3))
    com_falso, notas_b = gerar_linha(random.Random(3), escala_larga=False)
    assert np.array_equal(sem_arg, com_falso)
    assert notas_a == notas_b


def test_escala_larga_e_reprodutivel_e_muda_a_imagem() -> None:
    """Com a flag, a mesma semente dá a mesma linha, e ela difere da normal."""
    larga_1, _ = gerar_linha(random.Random(5), escala_larga=True)
    larga_2, _ = gerar_linha(random.Random(5), escala_larga=True)
    normal, _ = gerar_linha(random.Random(5), escala_larga=False)
    assert np.array_equal(larga_1, larga_2)
    assert not np.array_equal(larga_1, normal)


def test_cli_escala_padrao_e_normal() -> None:
    """Padrão da CLI é `normal`; `--escala larga` seleciona o candidato."""
    assert _parser().parse_args([]).escala == "normal"
    assert _parser().parse_args(["--escala", "larga"]).escala == "larga"
