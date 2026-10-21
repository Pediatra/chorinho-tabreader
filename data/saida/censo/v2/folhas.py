"""Folhas de conferência das mudanças do censo v2. NÃO é código do projeto.

Lê ``mudancas.json`` (gerado por ``comparar.py``) e os quadros de presença do cache
(``tab.cache``). Se um quadro não estiver no cache, decodifica do vídeo (só leitura).

- ``mudaram_tab_para_sem*.jpg``: TODOS os instantes TAB->SEM. Caixa amarela = caixa antiga.
- ``mudaram_sem_para_tab*.jpg``: até 40 instantes SEM->TAB, espalhados entre canais.
  Caixa vermelha = caixa nova.

Cada quadro tem cabeçalho ``#NN canal t=…s i=k`` e ``censo neste instante: TAB|SEM``
(veredito SÓ do instante, nunca do vídeo). Até 20 quadros por folha.

Uso (dentro do container, a partir da raiz do repo):
    python data/saida/censo/v2/folhas.py
"""

import collections
import json
import os
import random
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from tab import cache  # noqa: E402
from tab.caminhos import acervo  # noqa: E402
from tab.leitor import Leitor  # noqa: E402

PASTA = os.path.join(ROOT, "data", "saida", "censo", "v2")
MODO = cache.ModoCache(usar=True, formato="png")
POR_FOLHA = 20
COLUNAS = 4
LARGURA = 480
MAX_ALTURA = 360
MAX_SEM_PARA_TAB = 40


def ascii_canal(canal):
    """Nome do canal só com ASCII (cv2 não escreve japonês); vazio vira 'canal'."""
    s = unicodedata.normalize("NFKD", canal).encode("ascii", "ignore").decode()
    return " ".join(s.split()) or "canal"


def quadro(m, faltas):
    """Quadro de presença do instante ``m``: do cache, ou decodificado do vídeo."""
    pasta = cache.pasta_do_video(m["chave"], MODO)
    arq = cache.caminho_do_quadro(pasta, f"presenca_{m['k']:02d}", MODO.formato)
    if arq.exists():
        return cache.ler_quadro(arq)
    faltas.append(f"{m['arquivo']} k={m['k']}")
    lei = Leitor(os.path.join(str(acervo()), m["arquivo"]))
    try:
        return lei.ler(m["t"])
    finally:
        lei.fechar()


def desenhar(m, img, veredito, numero):
    """Caixa(s) no quadro cheio, depois redimensiona e põe o cabeçalho."""
    img = img.copy()
    if m["sentido"] == "TAB->SEM" and m.get("rect_antigo"):
        x0, y0, x1, y1 = m["rect_antigo"]
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 255), 6)
    if m.get("rect_novo"):
        x0, y0, x1, y1 = m["rect_novo"]
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), 6)
    h, w = img.shape[:2]
    escala = min(LARGURA / w, MAX_ALTURA / h)
    nw, nh = int(round(w * escala)), int(round(h * escala))
    red = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    img = np.zeros((MAX_ALTURA, LARGURA, 3), np.uint8)
    y0, x0 = (MAX_ALTURA - nh) // 2, (LARGURA - nw) // 2
    img[y0 : y0 + nh, x0 : x0 + nw] = red
    cab = np.zeros((52, LARGURA, 3), np.uint8)
    cv2.putText(
        cab,
        f"#{numero:02d} {ascii_canal(m['canal'])} t={m['t']:.1f}s i={m['k']}",
        (6, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cor = (0, 0, 255) if veredito == "TAB" else (0, 200, 255)
    cv2.putText(
        cab,
        f"censo neste instante: {veredito}",
        (6, 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        cor,
        2,
    )
    return np.vstack([cab, img])


def folhas(nome_base, itens, veredito, faltas, indice):
    """Grava as folhas de ``itens`` (20 por folha; sufixo _N só se houver mais de uma)."""
    if not itens:
        print(f"{nome_base}: nada a desenhar")
        return
    blocos = []
    for n, m in enumerate(itens, start=1):
        img = quadro(m, faltas)
        blocos.append(desenhar(m, img, veredito, n))
        indice.append(
            f"#{n:02d} | {nome_base} | {m['sentido']} | {m['canal']} | {m['arquivo']} | "
            f"k={m['k']} t={m['t']}s | veredito_instante={veredito}"
        )
    paginas = [blocos[i : i + POR_FOLHA] for i in range(0, len(blocos), POR_FOLHA)]
    for p, pagina in enumerate(paginas, start=1):
        linhas = []
        for i in range(0, len(pagina), COLUNAS):
            linha = pagina[i : i + COLUNAS]
            while len(linha) < COLUNAS:
                linha.append(np.zeros_like(pagina[0]))
            linhas.append(np.hstack(linha))
        folha = np.vstack(linhas)
        sufixo = f"_{p}" if len(paginas) > 1 else ""
        caminho = os.path.join(PASTA, f"{nome_base}{sufixo}.jpg")
        cv2.imwrite(caminho, folha, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"{caminho} ({len(pagina)} quadros)")


def escolher_sem_para_tab(ms, n):
    """Até ``n`` instantes SEM->TAB, em rodízio entre canais, com semente fixa."""
    por = collections.defaultdict(list)
    for m in sorted(ms, key=lambda m: (m["canal"], m["arquivo"], m["k"])):
        por[m["canal"]].append(m)
    rnd = random.Random(7)
    for c in por:
        rnd.shuffle(por[c])
    escolhidos = []
    canais = sorted(por)
    while len(escolhidos) < n and any(por.values()):
        for c in canais:
            if por[c] and len(escolhidos) < n:
                escolhidos.append(por[c].pop())
    return sorted(escolhidos, key=lambda m: (m["canal"], m["arquivo"], m["k"]))


def main():
    """Gera as duas famílias de folhas e o índice ``folhas_indice.txt``."""
    with open(os.path.join(PASTA, "mudancas.json"), encoding="utf-8") as fh:
        mudancas = json.load(fh)
    tab_sem = sorted(
        (m for m in mudancas if m["sentido"] == "TAB->SEM"),
        key=lambda m: (m["canal"], m["arquivo"], m["k"]),
    )
    sem_tab = [m for m in mudancas if m["sentido"] == "SEM->TAB"]
    print(f"TAB->SEM: {len(tab_sem)} | SEM->TAB: {len(sem_tab)}")
    escolhidos = escolher_sem_para_tab(sem_tab, MAX_SEM_PARA_TAB)
    indice = []
    faltas = []
    folhas("mudaram_tab_para_sem", tab_sem, "SEM", faltas, indice)
    folhas("mudaram_sem_para_tab", escolhidos, "TAB", faltas, indice)
    with open(os.path.join(PASTA, "folhas_indice.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(indice) + "\n")
    print(f"quadros decodificados (fora do cache): {len(faltas)}")
    for f in faltas[:20]:
        print("   ", f)


if __name__ == "__main__":
    main()
