"""Folhas 3x3 com o QUADRO INTEIRO de cada tela da T8.5 e o retângulo do painel escolhido.

Lê ``ferramenta/indice.json`` e ``telas/<pasta>/quadro.png`` (o quadro inteiro, já com o
retângulo verde do painel, desenhado pelo ``gerar.py``). Grava ``folha_quadros_<n>.jpg``
na pasta t85. Só desenha id, pasta e instante em ASCII (o nome do canal está no índice).

Uso (container): python data/saida/tablatura/t85/folha_quadros.py
"""

import json
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
T85 = RAIZ / "data" / "saida" / "tablatura" / "t85"
LARGURA = 640
COLUNAS = 3
POR_FOLHA = 9
FONTE = cv2.FONT_HERSHEY_SIMPLEX


def celula(pasta: Path, id_: int, t: float) -> np.ndarray:
    """Uma célula da folha: o quadro reduzido, com uma faixa de legenda em cima.

    Args:
        pasta: pasta da tela (contém ``quadro.png``).
        id_: número da tela na ferramenta.
        t: instante da tela, em segundos.

    Returns:
        Imagem BGR da célula.
    """
    img = cv2.imread(str(pasta / "quadro.png"))
    if img is None:
        img = np.full((360, LARGURA, 3), 40, dtype=np.uint8)
        cv2.putText(img, "quadro nao abriu", (20, 180), FONTE, 0.9, (0, 0, 255), 2)
    h = int(img.shape[0] * LARGURA / img.shape[1])
    img = cv2.resize(img, (LARGURA, h), interpolation=cv2.INTER_AREA)
    faixa = np.full((36, LARGURA, 3), 255, dtype=np.uint8)
    cv2.putText(
        faixa, f"id {id_}  {pasta.name}  t={t:.1f}s", (8, 26), FONTE, 0.7, (0, 0, 0), 2
    )
    return np.vstack([faixa, img])


def folha(celulas: list[np.ndarray]) -> np.ndarray:
    """Monta a grade de até 9 células, 3 por linha, com preenchimento vazio.

    Args:
        celulas: células já prontas (mesma largura).

    Returns:
        A folha inteira em BGR.
    """
    altura = max(c.shape[0] for c in celulas)
    linhas = []
    for i in range(0, POR_FOLHA, COLUNAS):
        fila = []
        for j in range(COLUNAS):
            k = i + j
            if k < len(celulas):
                c = celulas[k]
                c = np.pad(c, ((0, altura - c.shape[0]), (0, 0), (0, 0)), constant_values=255)
            else:
                c = np.full((altura, LARGURA, 3), 255, dtype=np.uint8)
            fila.append(c)
            fila.append(np.full((altura, 8, 3), 128, dtype=np.uint8))
        linhas.append(np.hstack(fila))
    return np.vstack(linhas)


def main() -> None:
    """Grava uma folha JPG por bloco de até 9 telas, em ``T85``."""
    indice = json.loads((T85 / "ferramenta" / "indice.json").read_text(encoding="utf-8"))
    celulas = [
        celula(RAIZ / i["pasta"], i["id"], i["t"]) for i in indice
    ]
    for n, ini in enumerate(range(0, len(celulas), POR_FOLHA), start=1):
        destino = T85 / f"folha_quadros_{n}.jpg"
        cv2.imwrite(str(destino), folha(celulas[ini : ini + POR_FOLHA]),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(destino, "telas", ini + 1, "a", min(ini + POR_FOLHA, len(celulas)))


if __name__ == "__main__":
    main()
