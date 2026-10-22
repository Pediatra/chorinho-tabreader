"""Previa PNG de trechos do MusicXML, desenhada a partir do proprio XML."""

import xml.etree.ElementTree as ET

import cv2
import numpy as np

raiz = ET.parse("data/saida/produto/mvp.musicxml").getroot()
medidas = {m.get("number"): m for m in raiz.findall("part/measure")}
ROTULOS = [("tela 2 (c5-c8)", ["5", "6", "7", "8"]), ("tela 10 (c37-c40)", ["37", "38", "39", "40"]),
           ("tela 11 (c41-c44)", ["41", "42", "43", "44"])]
LARG = 300
TOP, PASSO = 60, 30
ALT_LINHA = 230
img = np.full((ALT_LINHA * len(ROTULOS) + 40, 4 * LARG + 60, 3), 255, np.uint8)
for r, (rotulo, nums) in enumerate(ROTULOS):
    oy = 40 + r * ALT_LINHA
    cv2.putText(img, rotulo, (20, oy - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    for linha in range(6):
        y = oy + TOP + linha * PASSO
        cv2.line(img, (30, y), (30 + 4 * LARG, y), (0, 0, 0), 1)
    for i, num in enumerate(nums):
        x0 = 30 + i * LARG
        cv2.line(img, (x0, oy + TOP), (x0, oy + TOP + 5 * PASSO), (0, 0, 0), 2)
        cv2.putText(img, "c" + num, (x0 + 4, oy + TOP - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 0, 0), 1)
        colunas = []
        for n in medidas[num].findall("note"):
            if n.find("chord") is not None and colunas:
                colunas[-1].append(n)
            else:
                colunas.append([n])
        k = len(colunas)
        for j, grupo in enumerate(colunas):
            x = x0 + 25 + int((LARG - 50) * (j + 0.5) / max(k, 1))
            for n in grupo:
                corda = int(n.findtext("notations/technical/string"))
                casa = n.findtext("notations/technical/fret")
                y = oy + TOP + (corda - 1) * PASSO
                cv2.rectangle(img, (x - 10, y - 11), (x + 10, y + 11), (255, 255, 255), -1)
                cv2.putText(img, casa, (x - 7, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
cv2.imwrite("data/saida/produto/mvp_previa_tela10_11.png", img)
print("ok", img.shape)
