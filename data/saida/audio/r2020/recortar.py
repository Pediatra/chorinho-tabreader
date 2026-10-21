"""Rodada 2020: recortes das telas para mostrar ao dono (paolo e charagua)."""

import cv2

T = "/app/data/saida/audio/r2018/ferramenta_acordes/telas"
S = "/app/data/saida/audio/r2020"
VERMELHO = (0, 0, 230)

# paolo, tela 1 do gabarito: os 5 rasgueados do fim (colunas 45-49 do produto)
im = cv2.imread(f"{T}/001.png")
for x in (1682, 1728, 1778, 1829, 1879):  # x no quadro; a tela está em escala 2
    cv2.rectangle(im, (2 * x - 22, 108), (2 * x + 22, 144), VERMELHO, 3)
cv2.imwrite(f"{S}/paolo_tela1_final.png", cv2.resize(im[40:300, 2980:3840], None, fx=1.5, fy=1.5))

# charagua, tela 3 do gabarito: a ponta da seta lida como "4" na corda 1 (colunas 2, 4, 7)
im = cv2.imread(f"{T}/003.png")
for x in (392, 743, 1452):
    cv2.rectangle(im, (2 * x - 30, 105), (2 * x + 30, 160), VERMELHO, 3)
cv2.imwrite(f"{S}/charagua_tela3_setas.png", im[60:440, 0:3000])
