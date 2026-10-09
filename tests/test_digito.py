"""Discriminador "isto é algarismo?": testes sem acervo e sem GPU.

Ele existe porque o limiar de confiança foi medido e REPROVADO: `p_digito` vai de 0,17 a
1,00 nos algarismos e de 0,11 a 0,92 no lixo, com as distribuições sobrepostas. A pergunta
"isto é algarismo?" precisa de um discriminador próprio, e estes testes travam o encanamento.
"""

from __future__ import annotations

import numpy as np
import torch

from tab.digito import (
    ALTURA,
    LARGURA,
    DigitoCNN,
    montar_conjunto,
    preparar,
    probabilidade,
)


def test_preparar_devolve_a_forma_da_rede() -> None:
    """Cinza e BGR entram e saem no mesmo formato (a convenção é a entrada do modelo)."""
    cinza = np.full((40, 60), 128, np.uint8)
    bgr = np.full((40, 60, 3), 128, np.uint8)
    for img in (cinza, bgr):
        x = preparar(img)
        assert x.shape == (1, ALTURA, LARGURA)
        assert float(x.min()) >= 0.0 and float(x.max()) <= 1.0


def test_rede_devolve_dois_logits() -> None:
    """A saída é binária: 0 = não é algarismo, 1 = é algarismo."""
    modelo = DigitoCNN()
    saida = modelo(torch.zeros(4, 1, ALTURA, LARGURA))
    assert saida.shape == (4, 2)


def test_conjunto_tem_as_duas_classes() -> None:
    """O conjunto vem do que está ROTULADO: algarismos e não-algarismos, ambos presentes."""
    X, y, canais = montar_conjunto()
    assert X.shape[0] == len(y) == len(canais)
    assert X.shape[1:] == (1, ALTURA, LARGURA)
    assert int(y.sum()) > 0, "sem algarismos rotulados"
    assert int((y == 0).sum()) > 0, "sem não-algarismos rotulados"
    assert len(set(canais)) >= 3, "poucos canais para validar por canal deixado de fora"


def test_probabilidade_fica_entre_zero_e_um() -> None:
    """Probabilidade de 'é algarismo' em [0, 1], uma por entrada."""
    modelo = DigitoCNN()
    X = np.random.default_rng(0).random((5, 1, ALTURA, LARGURA)).astype(np.float32)
    p = probabilidade(modelo, "cpu", X)
    assert p.shape == (5,)
    assert float(p.min()) >= 0.0 and float(p.max()) <= 1.0
