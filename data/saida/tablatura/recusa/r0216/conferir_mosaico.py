"""Mosaico das telas que a triagem chamou de errado ou dúvida (conferência da 0216).

Recorta cada tile da folha pela ordem das telas na folha e junta em ``conferir_*.jpg``.

Uso:
    python data/saida/tablatura/recusa/r0216/conferir_mosaico.py
"""

from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np

from tab.comum.arquivos import ler_json

PASTA = Path(__file__).resolve().parent
COLUNAS = 4
LINHAS = 3


def tiles_da_folha(folha: Path) -> list[np.ndarray]:
    """Corta a folha nos 12 tiles da grade.

    Args:
        folha: caminho da folha jpg.

    Returns:
        Os tiles, em ordem de linha.
    """
    img = cv2.imread(str(folha))
    h, w = img.shape[0] // LINHAS, img.shape[1] // COLUNAS
    return [
        img[i * h : (i + 1) * h, j * w : (j + 1) * w]
        for i in range(LINHAS)
        for j in range(COLUNAS)
    ]


def main() -> None:
    """Grava o mosaico das marcadas e a lista de folhas sorteadas para conferir."""
    telas = [t for t in ler_json(PASTA / "telas_r0216.json") if t["tem_painel"]]
    triagem = {(t["k"], t["tela"]): t["veredito"] for t in ler_json(PASTA / "triagem.json")}
    por_folha: dict[str, list[dict]] = {}
    for t in ler_json(PASTA / "telas_r0216.json"):
        por_folha.setdefault(t["folha"], []).append(t)
    marcadas = []
    for t in telas:
        if triagem[(t["k"], t["tela"])] == "certo":
            continue
        indice = por_folha[t["folha"]].index(t)
        tile = tiles_da_folha(PASTA / "folhas" / t["folha"])[indice].copy()
        rotulo = f"k{t['k']} t{t['tela']} {triagem[(t['k'], t['tela'])]}"
        cv2.putText(tile, rotulo, (5, 40), 0, 0.9, (0, 255, 255), 2)
        marcadas.append(cv2.resize(tile, (480, 292)))
    for n in range(0, len(marcadas), 12):
        grupo = marcadas[n : n + 12]
        grupo += [np.zeros_like(grupo[0])] * (12 - len(grupo))
        linhas = [np.hstack(grupo[i : i + 4]) for i in range(0, 12, 4)]
        cv2.imwrite(str(PASTA / f"conferir_{n // 12 + 1}.jpg"), np.vstack(linhas))
    limpas = sorted(
        f
        for f, ts in por_folha.items()
        if all(triagem.get((t["k"], t["tela"]), "certo") == "certo" for t in ts)
    )
    print("marcadas", len(marcadas), "folhas limpas", len(limpas))
    print("sorteio", random.Random(16).sample(limpas, max(1, len(limpas) // 10)))


if __name__ == "__main__":
    main()
