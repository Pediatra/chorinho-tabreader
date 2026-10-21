"""Diagnóstico: diferença de assinatura entre dois instantes, regra antiga e nova.

A regra antiga (mediana da linha menos 40, em cinza) está copiada aqui, para comparar
com a nova (``tab.partitura_video.assinatura``) no mesmo par de quadros.

    python data/saida/partitura/diag/diag_antiga_vs_nova.py --busca blackbird --a 2 --b 7
"""

import argparse

import cv2
import numpy as np

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import achar_pautas
from tab.partitura_recortes import _cinza, _tinta_escura
from tab.partitura_video import (
    ALTURA_ASSINATURA,
    LARGURA_ASSINATURA,
    MARGEM_ASSINATURA_ENTRELINHAS,
    assinatura,
    diferenca,
)


def assinatura_antiga(quadro: np.ndarray) -> np.ndarray | None:
    """Assinatura da regra antiga (cinza, mediana da linha menos 40).

    Args:
        quadro: quadro BGR.

    Returns:
        Matriz booleana ``(64, 256)`` ou ``None`` sem pauta.
    """
    pautas = achar_pautas(quadro)
    if not pautas:
        return None
    cinza = _cinza(quadro)
    primeira = min(pautas, key=lambda p: p.ys[0])
    ultima = max(pautas, key=lambda p: p.ys[4])
    y0 = max(0, int(primeira.ys[0] - MARGEM_ASSINATURA_ENTRELINHAS * primeira.entrelinha))
    y1 = min(
        cinza.shape[0],
        int(ultima.ys[4] + MARGEM_ASSINATURA_ENTRELINHAS * ultima.entrelinha) + 1,
    )
    pequena = cv2.resize(
        cinza[y0:y1], (LARGURA_ASSINATURA, ALTURA_ASSINATURA), interpolation=cv2.INTER_AREA
    )
    if not _tinta_escura(cinza):
        pequena = 255 - pequena
    mediana = np.median(pequena, axis=1, keepdims=True)
    return pequena < mediana - 40


def main() -> None:
    """Imprime as diferenças antiga e nova para o par de instantes."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--busca", required=True)
    parser.add_argument("--a", type=float, required=True)
    parser.add_argument("--b", type=float, required=True)
    args = parser.parse_args()
    lista = (RAIZ / "data/saida/partitura/diag/piloto_videos.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    video = next(linha for linha in lista if args.busca.lower() in linha.lower())
    caminho = str(acervo() / video)
    qa = quadro_em(caminho, args.a)
    qb = quadro_em(caminho, args.b)
    print(
        f"antiga {diferenca(assinatura_antiga(qa), assinatura_antiga(qb)):.3f}"
        f" nova {diferenca(assinatura(qa, achar_pautas(qa)), assinatura(qb, achar_pautas(qb))):.3f}"
    )


if __name__ == "__main__":
    main()
