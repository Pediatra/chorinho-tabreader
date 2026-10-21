"""Desenha as regiões ambíguas da T8.4 (roxo) e as notas da tela (verde), para olhar."""
import json

import cv2

B = "/app/data/saida/t84/ferramenta/"
pre = {t["id"]: t for t in json.load(open(B + "pre.json"))["telas"]}
conf = {t["id"]: t for t in json.load(open(B + "conferencia_t84.json"))["telas"]}
res = json.load(open("/app/data/saida/tab_rotulo/r2/conferir_t84/resumo.json"))["fontes"]["t84"]
amb = {}
for a in res["ambiguos"]:
    amb.setdefault(a["tela"], []).append(a["regiao"])
for tid, rids in amb.items():
    p, c = pre[tid], conf[tid]
    im = cv2.imread(B + p["arquivo"])
    x0, y0, e = p["painel"][0], p["painel"][1], p["escala"]
    ly = p["linhas_y"]
    recortes = []
    for n in c["notas"]:
        if n.get("removida"):
            continue
        x, y = (n["x_centro_quadro"] - x0) * e, (ly[n["corda"] - 1] - y0) * e
        cv2.circle(im, (int(x), int(y)), 6, (0, 160, 0), 2)
    for k, r in enumerate(c.get("regioes") or []):
        r = dict(r, id=f"t{tid}-r{k}")
        xs = sorted(r["x_quadro"]); cs = sorted(r["cordas"])
        cor = (255, 0, 160) if r["id"] in rids else (180, 180, 180)
        ya = (ly[cs[0] - 1] - y0) * e - 0.6 * p["passo"] * e
        yb = (ly[cs[-1] - 1] - y0) * e + 0.6 * p["passo"] * e
        cv2.rectangle(im, (int((xs[0] - x0) * e), int(ya)), (int((xs[-1] - x0) * e), int(yb)), cor, 3)
        if r["id"] in rids:
            recortes.append((r["id"], int((xs[0] - x0) * e), int((xs[-1] - x0) * e)))
            cv2.putText(im, r["id"], (int((xs[0] - x0) * e), max(15, int(ya) - 5)), 0, 0.7, cor, 2)
    for rid, a, b in recortes:
        cv2.imwrite(f"/app/data/saida/t84/ambiguo_{rid}.png", im[:, max(0, a - 350) : b + 350])
    print(tid, im.shape)
