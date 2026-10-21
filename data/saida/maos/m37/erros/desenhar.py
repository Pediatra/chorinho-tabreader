"""Folha: nut previsto por L4 s2 (vermelho), L4 s1 (verde) e o par antigo (azul) na M36."""
import json, sys
import cv2
from tab.caminhos import MAOS_M36, MAOS_M37
ids = sys.argv[1].split(",")
fontes = [("L4_capo_s2+A6_capo_s1", (0, 0, 255)), ("L4_capo_s1+A6_capo_s2", (0, 200, 0)),
          ("L3_todos_s3+A4_100_todos_s1", (255, 120, 0))]
prev = {n: json.load(open(MAOS_M37 / f"previsto_M36_{n}.json"))["quadros"] for n, _ in fontes}
indice = {q["id"]: q for q in json.load(open(MAOS_M36 / "indice.json"))["quadros"]}
gab = json.load(open("data/gold/maos/braco_m36.json"))["quadros"] if len(sys.argv) < 3 else {}
cel = []
for i in ids:
    img = cv2.imread(str(MAOS_M36 / indice[i]["png"]))
    for n, cor in fontes:
        p = prev[n][i]
        if p.get("corda1"):
            for c in ("corda1", "corda6"):
                a, b = p[c]
                cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), cor, 3)
        if p.get("nut"):
            cv2.circle(img, tuple(map(int, p["nut"])), 22, cor, 6)
    g = gab.get(i, {}).get("nut")
    if g:
        cv2.drawMarker(img, tuple(map(int, g)), (255, 255, 255), cv2.MARKER_CROSS, 50, 6)
    h = 520
    img = cv2.resize(img, (int(img.shape[1] * h / img.shape[0]), h))
    cv2.putText(img, i, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cel.append(img)
larg = max(c.shape[1] for c in cel)
cel = [cv2.copyMakeBorder(c, 0, 0, 0, larg - c.shape[1], cv2.BORDER_CONSTANT) for c in cel]
linhas = [cv2.hconcat(cel[k:k + 4]) for k in range(0, len(cel), 4)]
w = max(l.shape[1] for l in linhas)
linhas = [cv2.copyMakeBorder(l, 0, 0, 0, w - l.shape[1], cv2.BORDER_CONSTANT) for l in linhas]
cv2.imwrite(str(MAOS_M37 / "erros/l4_s2_invertido.jpg"), cv2.vconcat(linhas))
