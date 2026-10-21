"""Rodada 2017: recorte da tablatura com a leitura de cada leitor escrita embaixo."""

import json
import sys

import cv2
import numpy as np

quadro, prod_novo, prod_antigo, tela_n, tela_a, x0, x1, y0, y1, saida = sys.argv[1:11]
x0, x1, y0, y1 = int(x0), int(x1), int(y0), int(y1)
im = cv2.imread(quadro)[y0:y1, x0:x1].copy()
cinza = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
escuro = (cinza < 128).mean(axis=1)
linhas = [i for i in range(1, len(escuro) - 1) if escuro[i] > 0.6 and escuro[i] >= escuro[i - 1]]
cordas = []
for y in linhas:
    if not cordas or y - cordas[-1] > 4:
        cordas.append(y)
cordas = cordas[:6]
esc = 2
im = cv2.resize(im, None, fx=esc, fy=esc, interpolation=cv2.INTER_CUBIC)
h, w = im.shape[:2]
faixa = 6 * 30 + 20
tela = np.full((h + 2 * faixa, w, 3), 255, np.uint8)
tela[:h] = im


def escrever(prod, tela_id, cor, base, nome):
    """Escreve a leitura de um produto numa faixa embaixo, uma linha por corda."""
    cv2.putText(tela, nome, (5, base + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor, 2)
    for c in range(6):
        y = base + 40 + c * 28
        cv2.line(tela, (60, y - 6), (w, y - 6), (220, 220, 220), 1)
        cv2.putText(tela, f"c{c + 1}", (5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)
    for n in json.load(open(prod))["notas"]:
        if n["tela"] != int(tela_id):
            continue
        x = (n["x_centro_quadro"] - x0) * esc
        if not 0 <= x < w:
            continue
        y = base + 40 + (n["corda"] - 1) * 28
        cv2.putText(tela, str(n["casa"]), (int(x) - 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)
        cv2.line(tela, (int(x), h - 4), (int(x), h), cor, 2)


escrever(prod_novo, tela_n, (0, 0, 220), h, "leitor novo (rede)")
escrever(prod_antigo, tela_a, (200, 80, 0), h + faixa, "leitor antigo (glifos)")
cv2.imwrite(saida, tela)
print(saida, tela.shape, "cordas", cordas)
