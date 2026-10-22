"""Folha de conferencia: quadro no instante do ouro + coluna que o JSON diz acesa (so visual)."""

import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, "/app")

from tab import leitor  # noqa: E402

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
dados = json.load(open("/app/data/saida/fase5/mvp.json", encoding="utf-8"))
ouro = json.load(open("/app/data/gold/ouro_video/retrato_brasileiro_v2.json", encoding="utf-8"))
pasta = Path("/app/data/saida/fase5/conferencia")
pasta.mkdir(parents=True, exist_ok=True)
instantes = [i for i in ouro["instantes"]]
escolhidos = [instantes[k] for k in (0, 6, 12, 19, 27, 36)]
for inst in escolhidos:
    t = float(inst["t"])
    tela = next(x for x in dados["telas"] if x["id"] == inst["tela"])
    ex = next(e for e in tela["exibicoes"] if e["t0"] <= t <= e["t1"])
    notas = [n for n in dados["notas"] if n["tela"] == tela["id"] and n.get("t_ini") is not None and n["t_ini"] <= t]
    notas = [n for n in notas if n.get("exibicao") == tela["exibicoes"].index(ex)]
    quadro = leitor.quadro_em(VIDEO, t)
    if quadro is None:
        print("sem quadro em", t)
        continue
    x0, y0, x1, y1 = tela["painel"]
    passo = tela["passo"] or 20
    cv2.rectangle(quadro, (x0, y0), (x1, y1), (255, 200, 0), 1)
    if notas:
        mais_recente = max(notas, key=lambda n: (n["t_ini"], n["x_centro_quadro"]))
        xc = mais_recente["x_centro_quadro"]
        cv2.rectangle(quadro, (int(xc - passo / 2), y0), (int(xc + passo / 2), y1), (0, 255, 0), 3)
        cor = (0, 255, 0)
        msg = f"JSON: coluna x={xc:.0f} t_ini={mais_recente['t_ini']:.2f} | ouro x={inst['coluna_x_quadro']:.0f}"
    else:
        msg = f"JSON: sem coluna | ouro x={inst['coluna_x_quadro']:.0f}"
    ouro_x = inst["coluna_x_quadro"]
    cv2.line(quadro, (int(ouro_x), y0 - 25), (int(ouro_x), y0 - 5), (0, 0, 255), 3)
    cv2.putText(quadro, f"t={t} tela {tela['id']}  {msg}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    recorte = quadro[max(0, y0 - 80) : min(quadro.shape[0], y1 + 60), :]
    cv2.imwrite(str(pasta / f"t{int(t)}_tela{tela['id']:02d}.png"), recorte)
    print("ok", t, msg)
