"""Prévia PNG dos primeiros compassos, desenhada a partir do próprio MusicXML."""

import xml.etree.ElementTree as ET

import cv2
import numpy as np

raiz = ET.parse("data/saida/produto/mvp.musicxml").getroot()
medidas = raiz.findall("part/measure")[:8]
LARG_COMP = 300
ALT = 420
TOP, PASSO = 110, 40
img = np.full((ALT, 8 * LARG_COMP + 60, 3), 255, np.uint8)
cv2.putText(img, "Previa do MusicXML (primeiros 8 compassos, a partir do XML)", (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
for linha in range(6):
    y = TOP + linha * PASSO
    cv2.line(img, (30, y), (30 + 8 * LARG_COMP, y), (0, 0, 0), 1)
for i, m in enumerate(medidas):
    x0 = 30 + i * LARG_COMP
    cv2.line(img, (x0, TOP), (x0, TOP + 5 * PASSO), (0, 0, 0), 2)
    cv2.putText(img, f"c{m.get('number')}", (x0 + 5, TOP - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 0, 0), 2)
    if i == 0:
        cv2.putText(img, "TAB", (x0 + 2, TOP + 3 * PASSO), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 0), 1)
    colunas = []
    for n in m.findall("note"):
        if n.find("chord") is not None and colunas:
            colunas[-1].append(n)
        else:
            colunas.append([n])
    k = len(colunas)
    for j, grupo in enumerate(colunas):
        x = x0 + 25 + int((LARG_COMP - 50) * (j + 0.5) / max(k, 1))
        for n in grupo:
            corda = int(n.findtext("notations/technical/string"))
            casa = n.findtext("notations/technical/fret")
            y = TOP + (corda - 1) * PASSO
            cv2.rectangle(img, (x - 12, y - 14), (x + 12, y + 14), (255, 255, 255), -1)
            cv2.putText(img, casa, (x - 8, y + 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
cv2.imwrite("data/saida/produto/mvp_previa.png", img)
print("ok", img.shape)
