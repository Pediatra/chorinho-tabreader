"""Folhas SEM->TAB por canal, com tamanho da caixa no cabeçalho. NÃO é código do projeto.

Reaproveita ``quadro`` e ``ascii_canal`` de ``folhas.py``. Entradas: ``mudancas.json``.
Saídas (só em data/saida/censo/v2/):
- ``cifra_todos.jpg``: todos os SEM->TAB de cifra club;
- ``dellarte_amostra_N.jpg``: 40 SEM->TAB de guitar dell'arte (random.Random(7));
- ``kenneth_amostra.jpg``: 20 SEM->TAB de kenneth acoustic (random.Random(7)).
Cabeçalho: ``#NN canal t=…s i=k caixa WxH px`` e ``censo neste instante: TAB``.
Lista antes do sorteio é ordenada por (arquivo, k), então o sorteio é reproduzível.
Lista ``indice_canal.txt`` com #NN, canal, arquivo, k, t e caixa.
"""

import json
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import folhas  # noqa: E402

PASTA = folhas.PASTA
COLUNAS = 4
POR_FOLHA = 20


def cabecalho_e_tile(m, img, numero):
    """Quadro com caixa nova (vermelha) e cabeçalho com tamanho da caixa."""
    img = img.copy()
    x0, y0, x1, y1 = m["rect_novo"]
    cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), 6)
    h, w = img.shape[:2]
    escala = min(folhas.LARGURA / w, folhas.MAX_ALTURA / h)
    nw, nh = int(round(w * escala)), int(round(h * escala))
    red = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    quadro_fix = np.zeros((folhas.MAX_ALTURA, folhas.LARGURA, 3), np.uint8)
    y_ini, x_ini = (folhas.MAX_ALTURA - nh) // 2, (folhas.LARGURA - nw) // 2
    quadro_fix[y_ini : y_ini + nh, x_ini : x_ini + nw] = red
    cab = np.zeros((58, folhas.LARGURA, 3), np.uint8)
    cv2.putText(
        cab,
        f"#{numero:02d} {folhas.ascii_canal(m['canal'])} t={m['t']:.1f}s i={m['k']}",
        (6, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        cab,
        f"caixa {x1 - x0}x{y1 - y0} px | censo neste instante: TAB",
        (6, 46),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        2,
    )
    return np.vstack([cab, quadro_fix])


def gravar(nome_base, itens, faltas, indice):
    """Folhas de 20; sufixo _N só quando passa de uma folha."""
    blocos = []
    for n, m in enumerate(itens, start=1):
        img = folhas.quadro(m, faltas)
        blocos.append(cabecalho_e_tile(m, img, n))
        x0, y0, x1, y1 = m["rect_novo"]
        indice.append(
            f"#{n:02d} | {nome_base} | {m['canal']} | {m['arquivo']} | "
            f"k={m['k']} t={m['t']}s | caixa {x1 - x0}x{y1 - y0}"
        )
    paginas = [blocos[i : i + POR_FOLHA] for i in range(0, len(blocos), POR_FOLHA)]
    for p, pagina in enumerate(paginas, start=1):
        linhas = []
        for i in range(0, len(pagina), COLUNAS):
            linha = pagina[i : i + COLUNAS]
            while len(linha) < COLUNAS:
                linha.append(np.zeros_like(pagina[0]))
            linhas.append(np.hstack(linha))
        sufixo = f"_{p}" if len(paginas) > 1 else ""
        caminho = os.path.join(PASTA, f"{nome_base}{sufixo}.jpg")
        cv2.imwrite(caminho, np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"{caminho} ({len(pagina)} quadros)")


def main():
    """Gera cifra_todos, dellarte_amostra_N e kenneth_amostra."""
    with open(os.path.join(PASTA, "mudancas.json"), encoding="utf-8") as fh:
        mud = json.load(fh)
    sem_tab = sorted(
        (m for m in mud if m["sentido"] == "SEM->TAB"),
        key=lambda m: (m["arquivo"], m["k"]),
    )
    cifra = [m for m in sem_tab if m["canal"] == "cifra club"]
    dell = [m for m in sem_tab if m["canal"] == "guitar dell ́arte"]
    if not dell:
        dell = [m for m in sem_tab if m["canal"].startswith("guitar dell")]
    kenn = [m for m in sem_tab if m["canal"] == "kenneth acoustic"]
    print(f"cifra club: {len(cifra)} | dell'arte: {len(dell)} | kenneth: {len(kenn)}")

    rnd = random.Random(7)
    dell_amostra = rnd.sample(dell, min(40, len(dell)))
    kenn_amostra = random.Random(7).sample(kenn, min(20, len(kenn)))

    indice = []
    faltas = []
    gravar("cifra_todos", cifra, faltas, indice)
    gravar("dellarte_amostra", dell_amostra, faltas, indice)
    gravar("kenneth_amostra", kenn_amostra, faltas, indice)
    with open(os.path.join(PASTA, "indice_canal.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(indice) + "\n")
    print(f"quadros fora do cache: {len(faltas)}")


if __name__ == "__main__":
    main()
