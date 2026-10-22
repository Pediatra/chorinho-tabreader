"""Recortes das regiões do dono na T8.4 que não ficaram ligadas a nenhuma nota do ataque."""
import json
from pathlib import Path

import cv2

B = Path("/app/data/saida/tablatura")
A = json.loads((B / "tab_rotulo/r2/conferir_t84/ataque_t84.json").read_text())
C = json.loads((B / "t84/passe_ataque/conferencia_t84_servida.json").read_text())
PRE = {int(t["id"]): t for t in json.loads((B / "t84/ferramenta/pre.json").read_text())["telas"]}
OUT = B / "t84/passe_ataque/regioes_soltas"
usadas = {x.get("regiao") for x in A["notas"]}
notas = {}
for x in A["notas"]:
    notas.setdefault(x["tela"], []).append(x)
for t in C["telas"]:
    i = int(t["id"]); p = PRE[i]
    img = cv2.imread(str(B / "t84/ferramenta" / p["arquivo"]))
    for k, r in enumerate(t.get("regioes") or []):
        rid = f"t{i}-r{k}"
        if rid in usadas:
            continue
        e = p["escala"]; px, py = p["painel"][0], p["painel"][1]
        ly = [(y - py) * e for y in p["linhas_y"]]; ps = p["passo"] * e
        X = lambda x: (x - px) * e  # noqa: E731
        x0, x1 = X(min(r["x_quadro"])), X(max(r["x_quadro"]))
        c0, c1 = min(r["cordas"]), max(r["cordas"])
        im = img.copy()
        cv2.rectangle(im, (int(x0), int(ly[c0 - 1] - ps / 2)), (int(x1), int(ly[c1 - 1] + ps / 2)), (0, 0, 255), 2)
        for x in notas.get(i, []):
            if abs(X(x["x_centro_quadro"]) - (x0 + x1) / 2) < 6 * ps:
                cor = (0, 160, 0) if x["ataque"] == "sim" else (255, 0, 255)
                cx, cy = int(X(x["x_centro_quadro"])), int(ly[x["corda"] - 1])
                cv2.circle(im, (cx, cy), int(ps * 0.45), cor, 2)
        y0 = max(0, int(ly[0] - 2.5 * ps)); y1 = min(im.shape[0], int(ly[-1] + 1.5 * ps))
        xa = max(0, int(x0 - 5 * ps)); xb = min(im.shape[1], int(x1 + 5 * ps))
        rec = im[y0:y1, xa:xb]
        cv2.putText(rec, f"{rid} {''.join(r['tecnica']) or '(arco)'}", (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        cv2.imwrite(str(OUT / f"{rid}.jpg"), rec)
print("ok")
