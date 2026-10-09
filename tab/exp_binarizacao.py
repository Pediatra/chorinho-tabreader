"""Experimento: qual binarização faz a detecção de 6 cordas funcionar em TODAS as famílias?

Compara variantes determinísticas (sem modelo) sobre as 5 capturas de famílias
diferentes e sobre uma amostra das 163 linhas do acervo (para não regredir).
"""

from __future__ import annotations

import glob
import os

import cv2
import numpy as np

from . import tabseg
from .caminhos import PARTES


def _fundo(gray: np.ndarray, k: int) -> np.ndarray:
    """Estimativa do fundo local: fechamento morfológico grande + suavização."""
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, se)
    return cv2.GaussianBlur(bg, (0, 0), max(1.0, k / 4))


def v0(gray):  # atual: Otsu + polaridade
    return tabseg.binarizar(gray)


def _por_contraste_local(gray, k, delta):
    bg = _fundo(gray, k)
    d = gray.astype(np.int16) - bg.astype(np.int16)
    escura = d < -delta
    clara = d > delta
    if escura.mean() <= clara.mean():
        return escura
    return clara


def v1(gray, k=31, delta=25):
    return _por_contraste_local(gray, k, delta)


def v2(gray, k=51, delta=15):
    return _por_contraste_local(gray, k, delta)


def v3(gray, k=15, delta=10):
    return _por_contraste_local(gray, k, delta)


def avaliar(nome, func, imagens, esperado=6, verbose=False):
    ok, res = 0, []
    for p in imagens:
        img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        gray = img
        if gray.ndim == 3:
            if gray.shape[2] == 4:
                a = gray[:, :, 3:4].astype(np.float32) / 255
                gray = (gray[:, :, :3].astype(np.float32) * a + 255 * (1 - a)).astype(
                    np.uint8
                )
            gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
        tinta = func(gray)
        linhas, passo = tabseg.achar_cordas(tinta, esperado)
        bom = len(linhas) == esperado
        ok += bom
        res.append((p.split("/")[-1][-14:], len(linhas), round(passo, 1), bom))
    print(f"{nome:<28} {ok}/{len(imagens)}")
    if verbose:
        for r in res:
            print(
                f"    {r[0]:<16} linhas={r[1]:<3} passo={r[2]:<6} {'OK' if r[3] else 'FALHA'}"
            )
    return ok


def main() -> int:
    novas = sorted(glob.glob(str(PARTES / "clipes" / "diferentes" / "*.png")))
    # amostra do acervo antigo: 2 linhas por canal (regressão)
    antigas = []
    for d in sorted(glob.glob(str(PARTES / "clipes" / "*"))):
        antigas += sorted(glob.glob(os.path.join(d, "linha_*_tablatura.png")))[:2]
    print("=== FAMÍLIAS DIFERENTES (5 capturas) ===")
    for nome, f in [
        ("v0 Otsu (atual)", v0),
        ("v1 contraste k=31 d=25", v1),
        ("v2 contraste k=51 d=15", v2),
        ("v3 contraste k=15 d=10", v3),
    ]:
        avaliar(nome, f, novas, verbose=True)
    print(f"\n=== REGRESSÃO NO ACERVO ANTIGO ({len(antigas)} linhas) ===")
    for nome, f in [
        ("v0 Otsu (atual)", v0),
        ("v1 contraste k=31 d=25", v1),
        ("v2 contraste k=51 d=15", v2),
        ("v3 contraste k=15 d=10", v3),
    ]:
        avaliar(nome, f, antigas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
