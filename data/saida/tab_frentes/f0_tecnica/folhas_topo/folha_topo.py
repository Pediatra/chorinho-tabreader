"""Folhas da F0.2: recortes com a linha de corte (amarela) por classe do topo.

Uma folha por classe, em grade de 3 colunas, cada célula com legenda (fonte, tela, marca,
técnica do dono, pixels acima e dentro). Gerado a partir de ``topo.json``.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

FRENTE = Path("/app/data/saida/tab_frentes/f0_tecnica")
SAIDA = FRENTE / "folhas_topo"
COLUNAS = 3
LARGURA_CELULA = 330


def celula(img: np.ndarray, legenda: str) -> np.ndarray:
    """Uma célula da grade: recorte escalado e legenda embaixo.

    Args:
        img: recorte BGR.
        legenda: texto da legenda.

    Returns:
        Imagem BGR da célula.
    """
    escala = min(3.0, (LARGURA_CELULA - 10) / img.shape[1])
    peca = cv2.resize(img, None, fx=escala, fy=escala)
    if peca.shape[0] > 300:
        peca = peca[:300]
    cel = np.full((peca.shape[0] + 50, LARGURA_CELULA, 3), 255, np.uint8)
    cel[:peca.shape[0], 5:5 + peca.shape[1]] = peca
    for i, parte in enumerate(legenda.split("|")):
        cv2.putText(cel, parte[:52], (5, peca.shape[0] + 16 + 16 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    return cel


def folha(linhas: list[dict], nome: str) -> None:
    """Grava uma folha em grade com as linhas dadas.

    Args:
        linhas: linhas do ``topo.json``.
        nome: nome do PNG (sem caminho).
    """
    celulas = []
    for ln in linhas:
        img = cv2.imread(str(FRENTE / ln["recorte"]))
        legenda = (
            f"{ln['classe']} {ln['fonte']} t{ln['tela']} r{ln['indice']}|"
            f"dono {ln['tecnica_dono']} cordas {ln['cordas']}|"
            f"acima {ln['acima']} dentro {ln['dentro']}"
        )
        celulas.append(celula(img, legenda))
    while len(celulas) % COLUNAS:
        celulas.append(np.full_like(celulas[0], 255))
    linhas_grade = []
    for i in range(0, len(celulas), COLUNAS):
        linha = celulas[i : i + COLUNAS]
        altura = max(c.shape[0] for c in linha)
        linha = [np.pad(c, ((0, altura - c.shape[0]), (0, 0), (0, 0)), constant_values=255) for c in linha]
        linhas_grade.append(np.hstack(linha))
    if linhas_grade:
        cv2.imwrite(str(SAIDA / nome), np.vstack(linhas_grade))


def main() -> None:
    """Gera as folhas por classe a partir de topo.json."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    rel = json.loads((FRENTE / "topo.json").read_text(encoding="utf-8"))
    linhas = rel["linhas"]
    cortadas = [ln for ln in linhas if ln["classe"] == "cortada"]
    inteiras = [ln for ln in linhas if ln["classe"] == "inteira"]
    folha(cortadas, "folha_cortadas.png")
    folha(inteiras, "folha_inteiras.png")
    print("cortadas", len(cortadas), "inteiras", len(inteiras))


if __name__ == "__main__":
    main()
