"""Aferição padronizada no gabarito real — é o número oficial do projeto.

Roda as 4 amostras rotuladas à mão (96 glifos) e imprime o acerto por canal. O
AGENTS.md manda reportar a **média de 3 sementes**, nunca uma execução só.

Uso:
    python -m tab.avaliar [--modelo CAMINHO]
"""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np

from .caminhos import GABARITO, MODELO_PADRAO, PARTES, acervo
from .inventario import ler_quadro
from .reconhecer import carregar_modelo, reconhecer_linha

#: Recorte de onde a amostra da `sky guitar` foi rotulada.
RECORTE_SKY = PARTES / "clipes" / "-6rawhontyg_000120_000200" / "linha_01_tablatura.png"


def imagem_da_amostra(am: dict) -> np.ndarray:
    """Imagem que originou os rótulos de uma amostra do gabarito.

    A amostra da `sky guitar` foi rotulada de um recorte local; as outras vêm do
    quadro do vídeo no acervo, na faixa (topo/base) registrada no gabarito.

    Args:
        am: uma entrada de ``amostras`` do gabarito.

    Returns:
        Imagem BGR (ou em tons de cinza, no caso do recorte local).
    """
    if not am.get("video") or am["video"].startswith("sky guitar"):
        return cv2.imread(str(RECORTE_SKY), cv2.IMREAD_UNCHANGED)
    frame, _ = ler_quadro(str(acervo() / am["video"]), 0.5)
    return frame[620:1080, :] if am["faixa"] == "base" else frame[0:400, :]


def avaliar(caminho_modelo: str) -> list[tuple[str, int, int]]:
    """Aferição glifo a glifo no gabarito rotulado à mão.

    Args:
        caminho_modelo: pesos do classificador de glifos.

    Returns:
        Uma tupla ``(canal, acertos, total)`` por amostra do gabarito.
    """
    modelo, rotulos, dev = carregar_modelo(caminho_modelo)
    dados = json.loads(GABARITO.read_text(encoding="utf-8"))
    linhas: list[tuple[str, int, int]] = []
    for am in dados["amostras"]:
        img = imagem_da_amostra(am)
        r = reconhecer_linha(img, modelo, rotulos, dev)
        previsto = [n["casa"] for n in r["notas"]]
        indices = sorted(int(k) for k in am["rotulos"])
        # Token que a segmentação não produziu conta como erro, não como exceção.
        acertos = sum(
            1
            for i in indices
            if i < len(previsto) and previsto[i] == am["rotulos"][str(i)]
        )
        linhas.append((am["canal"], acertos, len(indices)))
    return linhas


def main() -> int:
    """Imprime o acerto por canal e o total."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    args = ap.parse_args()

    linhas = avaliar(args.modelo)
    acertos = sum(o for _, o, _ in linhas)
    total = sum(t for _, _, t in linhas)
    resumo = " ".join(f"{c.split()[0][:6]}={o}/{t}" for c, o, t in linhas)
    print(f"RESULTADO {resumo} | TOTAL={acertos}/{total}={acertos / total:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
