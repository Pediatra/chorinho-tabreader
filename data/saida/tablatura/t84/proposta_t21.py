"""Tela 21 da T8.4: as 2 notas <12> depois da ligadura, que não estão na lista (palpite)."""
import json

import cv2

B = "/app/data/saida/t84/ferramenta/"
p = {t["id"]: t for t in json.load(open(B + "pre.json"))["telas"]}[21]
c = {t["id"]: t for t in json.load(open(B + "conferencia_t84.json"))["telas"]}[21]
im = cv2.imread(B + p["arquivo"])
x0, y0, e, ly = p["painel"][0], p["painel"][1], p["escala"], p["linhas_y"]
for n in c["notas"]:
    if not n.get("removida"):
        x, y = (n["x_centro_quadro"] - x0) * e, (ly[n["corda"] - 1] - y0) * e
        cv2.circle(im, (int(x), int(y)), 7, (0, 160, 0), 2)
for corda in (2, 3):
    x, y = (1702.5 - x0) * e, (ly[corda - 1] - y0) * e
    cv2.circle(im, (int(x), int(y)), 16, (0, 120, 255), 3)
a = int((1560 - x0) * e)
b = int((1760 - x0) * e)
cv2.imwrite("/app/data/saida/t84/proposta_t21.png", im[:, a:b])
