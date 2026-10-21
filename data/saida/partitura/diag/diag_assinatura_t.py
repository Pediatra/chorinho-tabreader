"""Diagnóstico: assinatura e quadro de alguns instantes de um vídeo.

Para cada instante, grava a região das pautas (quadro inteiro, reduzido) e imprime a
diferença da assinatura de cada instante para o primeiro, e para o instante de referência
``--ref``. Uso:

    python data/saida/partitura/diag/diag_assinatura_t.py --video CAMINHO --ref 16.6 \
        --t 73 74 76 85 --saida data/saida/partitura/diag/assinatura_t
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import achar_pautas
from tab.partitura_video import assinatura, diferenca


def main() -> None:
    """Lê os instantes pedidos, imprime as diferenças e grava as imagens."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=None)
    parser.add_argument("--busca", default=None, help="trecho do nome na piloto_videos.txt")
    parser.add_argument("--ref", type=float, required=True)
    parser.add_argument("--t", type=float, nargs="+", required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    if args.video is None:
        lista = (RAIZ / "data/saida/partitura/diag/piloto_videos.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        args.video = next(linha for linha in lista if args.busca.lower() in linha.lower())
    caminho = str(acervo() / args.video)
    args.saida.mkdir(parents=True, exist_ok=True)
    instantes = [args.ref, *args.t]
    sigs = {}
    imagens = []
    for t in instantes:
        quadro = quadro_em(caminho, t)
        if quadro is None:
            print(f"t={t}: sem quadro")
            continue
        pautas = achar_pautas(quadro)
        sigs[t] = assinatura(quadro, pautas)
        cv2.imwrite(str(args.saida / f"t{t:07.2f}.jpg"), quadro)
        imagens.append(cv2.resize(quadro, (640, 360)))
        print(f"t={t:.2f} pautas {[p.ys[0] for p in pautas]} e={[round(p.entrelinha,1) for p in pautas]}")
    ref = sigs.get(args.ref)
    for t in args.t:
        if t in sigs and ref is not None and sigs[t] is not None:
            print(f"diferenca t={t:.2f} x ref {args.ref:.2f}: {diferenca(ref, sigs[t]):.3f}")
    if imagens:
        cv2.imwrite(str(args.saida / "lado_a_lado.jpg"), np.vstack(imagens[:4]))


if __name__ == "__main__":
    main()
