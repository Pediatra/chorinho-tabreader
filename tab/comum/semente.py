"""Semente fixa e determinismo da GPU, para todo treino do projeto (AGENTS §7.1, 9001).

Copiado sem mudança de ``sintetico.fixar_semente``, que reexporta o nome.
"""

from __future__ import annotations

import random

import numpy as np
import torch


def fixar_semente(seed: int) -> None:
    """Fixa a semente **e** desliga o nondeterminismo da GPU.

    Medido: a MESMA semente, com o mesmo comando, deu 0,927, 0,896 e 0,948
    (amplitude 0,052) — porque a convolução em CUDA usa `atomicAdd` e o cuDNN
    não é determinístico por padrão. Semente fixa sem isto **não** controla a
    variância, e foi sobre essa premissa falsa que o projeto comparou rodadas.

    Args:
        seed: semente para `random`, `numpy` e `torch`.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    # warn_only: se algum op não tiver caminho determinístico, quero saber pelo
    # aviso, não perder o treino inteiro.
    torch.use_deterministic_algorithms(True, warn_only=True)
