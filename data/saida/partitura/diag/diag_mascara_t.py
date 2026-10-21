"""Diagnóstico: máscara de tinta de dois instantes e onde elas diferem.

Grava, em ``--saida``, a região das pautas de cada instante (cinza), a máscara de tinta
(``_tinta``) e uma imagem com a diferença (vermelho: só no primeiro; azul: só no segundo).
Imprime a fração de tinta de cada máscara e a diferença de assinatura.

    python data/saida/partitura/diag/diag_mascara_t.py --busca greensleeves --a 16.6 --b 73 \
        --saida data/saida/partitura/diag/mascara_t
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import achar_pautas
from tab.partitura_recortes import _cinza, _tinta_escura
from tab.partitura_video import (
    MARGEM_ASSINATURA_ENTRELINHAS,
    _tinta,
    assinatura,
    diferenca,
)


def _regiao(quadro: np.ndarray) -> tuple[int, int]:
    """Faixa vertical da região das pautas, como em ``assinatura``.

    Args:
        quadro: quadro BGR.

    Returns:
        ``(y0, y1)``.
    """
    pautas = achar_pautas(quadro)
    primeira = min(pautas, key=lambda p: p.ys[0])
    ultima = max(pautas, key=lambda p: p.ys[4])
    y0 = max(0, int(primeira.ys[0] - MARGEM_ASSINATURA_ENTRELINHAS * primeira.entrelinha))
    y1 = min(
        quadro.shape[0],
        int(ultima.ys[4] + MARGEM_ASSINATURA_ENTRELINHAS * ultima.entrelinha) + 1,
    )
    return y0, y1


def main() -> None:
    """Compara as máscaras de dois instantes e grava as imagens."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--busca", required=True, help="trecho do nome na piloto_videos.txt")
    parser.add_argument("--a", type=float, required=True)
    parser.add_argument("--b", type=float, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)
    lista = (RAIZ / "data/saida/partitura/diag/piloto_videos.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    video = next(linha for linha in lista if args.busca.lower() in linha.lower())
    caminho = str(acervo() / video)
    masks, regs = [], []
    for t in (args.a, args.b):
        quadro = quadro_em(caminho, t)
        cinza = _cinza(quadro)
        y0, y1 = _regiao(quadro)
        mask = _tinta(quadro, cinza)[y0:y1]
        print(
            f"t={t}: escura_fundo_claro={_tinta_escura(cinza)} regiao y {y0}-{y1}"
            f" tinta {mask.mean():.4f} V_mediana_regiao"
            f" {np.median(cv2.cvtColor(quadro, cv2.COLOR_BGR2HSV)[y0:y1, :, 2]):.0f}"
        )
        masks.append(mask)
        regs.append(cinza[y0:y1])
        cv2.imwrite(str(args.saida / f"regiao_{t:07.2f}.png"), cinza[y0:y1])
    a, b = masks
    if a.shape == b.shape:
        img = np.zeros((*a.shape, 3), np.uint8)
        img[a & ~b] = (0, 0, 255)
        img[b & ~a] = (255, 0, 0)
        img[a & b] = (120, 120, 120)
        cv2.imwrite(str(args.saida / "diferenca_mascaras.png"), img)
        print(f"pixels so em a {int((a & ~b).sum())}, so em b {int((b & ~a).sum())},"
              f" em ambas {int((a & b).sum())}")
    sa = assinatura(quadro_em(caminho, args.a), achar_pautas(quadro_em(caminho, args.a)))
    sb = assinatura(quadro_em(caminho, args.b), achar_pautas(quadro_em(caminho, args.b)))
    print(f"diferenca de assinaturas: {diferenca(sa, sb):.3f}")


if __name__ == "__main__":
    main()
