"""Zoom de 4 recortes por folha — lupa para a leitura dos rotulos do portao.

Nao faz parte do motor: existe so para conferir, em 4x a resolucao da folha de 16, o
que cada recorte contem. Uso (dentro do container):

    python data/saida/zoom_portao.py D00,D03,D05,D06
"""

from __future__ import annotations

import glob
import json
import sys

import cv2
import numpy as np

CASOS = "/app/data/saida/portao_casos"
FRAMES = "/app/data/saida/frames"
MAPA = "/app/data/saida/portao_novos/folhas_D.json"
MANIFESTOS = "/app/data/saida/portao_novos/coleta_*.json"

LARG, ALT = 960, 225
FAIXA = 26


def carregar(etiquetas: list[str]) -> list[tuple[str, str]]:
    """Etiqueta -> arquivo, na ordem pedida."""
    mapa = json.load(open(MAPA, encoding="utf-8"))
    casos: list[dict] = []
    for padrao in sorted(glob.glob(MANIFESTOS)):
        casos.extend(json.load(open(padrao, encoding="utf-8")))
    achados = []
    for etiqueta in etiquetas:
        for itens in mapa.values():
            for nome, indice in itens.items():
                if nome == etiqueta:
                    achados.append((etiqueta, casos[indice]["arquivo"]))
    return achados


def main() -> int:
    """Monta uma folha de zoom com os recortes pedidos."""
    pedidos = [p.strip() for p in sys.argv[1].split(",") if p.strip()]
    itens = carregar(pedidos)
    linhas = (len(itens) + 1) // 2
    tela = np.full((linhas * ALT, 2 * LARG, 3), 255, np.uint8)
    for k, (etiqueta, arquivo) in enumerate(itens):
        img = cv2.imread(f"{CASOS}/{arquivo}")
        if img is None:
            continue
        lin, col = divmod(k, 2)
        y0, x0 = lin * ALT, col * LARG
        cv2.rectangle(tela, (x0, y0), (x0 + LARG - 1, y0 + ALT - 1), (170, 170, 170), 1)
        escala = min(LARG / img.shape[1], (ALT - FAIXA) / img.shape[0])
        nova = cv2.resize(
            img,
            (max(1, int(img.shape[1] * escala)), max(1, int(img.shape[0] * escala))),
            interpolation=cv2.INTER_AREA if escala < 1 else cv2.INTER_CUBIC,
        )
        tela[y0 + FAIXA : y0 + FAIXA + nova.shape[0], x0 : x0 + nova.shape[1]] = nova
        cv2.putText(
            tela,
            etiqueta,
            (x0 + 4, y0 + 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 220),
            2,
            cv2.LINE_AA,
        )
    saida = f"{FRAMES}/zoom_{pedidos[0]}.png"
    cv2.imwrite(saida, tela)
    print(saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
