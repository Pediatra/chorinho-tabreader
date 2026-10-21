"""Folha de erros de um vídeo: casa errada, inventada e perdida, recortes do quadro_ref.

Uso (container): python /app/data/saida/fase8/erros/folha.py SLUG PRED.json
"""

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "/app")
from tab.avaliar_video import (  # noqa: E402
    FRACAO_PASSO, casar_notas, casar_telas, casar_sem_instante, ler_predicao,
    notas_distintas, so_conferidas,
)

slug, pred_path = sys.argv[1], sys.argv[2]
ouro = so_conferidas(json.loads(Path(f"/app/data/gold/ouro_video/{slug}.json").read_text()))
pred = ler_predicao(json.loads(Path(pred_path).read_text()))
video = "/acervo/" + ouro["video"]
ids = [int(t["id"]) for t in ouro["telas"]]
mapa = casar_telas(ids, ouro.get("instantes", []), pred.telas)
mapa, _ = casar_sem_instante(ouro["telas"], mapa, pred.telas)
por_id = {t.id: t for t in pred.telas}
dados = json.loads(Path(pred_path).read_text())
y_painel = {t["id"]: t["painel"] for t in dados["telas"]}
recortes = []
for tela in ouro["telas"]:
    pid = mapa.get(int(tela["id"]))
    if pid is None:
        continue
    tp = por_id[pid]
    prev = notas_distintas([n for n in tp.notas if n.casa is not None])
    pares = casar_notas(tela["notas"], prev, FRACAO_PASSO * tp.passo)
    usados_o = {i for i, _ in pares}
    usados_p = {j for _, j in pares}
    erros = [("casa", tela["notas"][i], prev[j].casa) for i, j in pares
             if tela["notas"][i]["casa"] != prev[j].casa]
    erros += [("perdida", n, None) for i, n in enumerate(tela["notas"]) if i not in usados_o]
    erros += [("inventada", {"corda": p.corda, "casa": None, "x_centro_quadro": p.x}, p.casa)
              for j, p in enumerate(prev) if j not in usados_p]
    if not erros:
        continue
    f = "/tmp/q.png"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(tela["quadro_ref_s"]),
                    "-i", video, "-frames:v", "1", f], check=True)
    img = cv2.imread(f)
    x0p, y0p, x1p, y1p = y_painel[pid]
    passo = tp.passo
    for tipo, n, lido in erros:
        x = int(n.get("x_centro_quadro") or n["x_quadro"])
        a, b = max(0, x - int(3 * passo)), min(img.shape[1], x + int(3 * passo))
        c = img[y0p:y1p, a:b].copy()
        c = cv2.resize(c, (int(c.shape[1] * 64 / passo / 3), int(c.shape[0] * 64 / passo / 3)))
        cx = int((x - a) * 64 / passo / 3)
        cv2.line(c, (cx, 0), (cx, 8), (0, 0, 255), 2)
        txt = f"t{tela['id']} c{n['corda']} {tipo} ouro={n.get('casa')} lido={lido}"
        faixa = np.full((22, max(c.shape[1], 360), 3), 255, np.uint8)
        cv2.putText(faixa, txt, (2, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        tile = np.full((22 + c.shape[0], faixa.shape[1], 3), 255, np.uint8)
        tile[:22] = faixa
        tile[22:, : c.shape[1]] = c
        recortes.append(tile)
print(len(recortes), "erros")
largura = max(t.shape[1] for t in recortes)
linhas = []
for i in range(0, len(recortes), 3):
    grupo = [np.pad(t, ((0, 0), (0, largura - t.shape[1]), (0, 0)), constant_values=255)
             for t in recortes[i:i + 3]]
    altura = max(g.shape[0] for g in grupo)
    grupo = [np.pad(g, ((0, altura - g.shape[0]), (0, 0), (0, 0)), constant_values=255) for g in grupo]
    while len(grupo) < 3:
        grupo.append(np.full_like(grupo[0], 255))
    linhas.append(np.hstack(grupo))
folha = np.vstack(linhas)
cv2.imwrite(f"/app/data/saida/fase8/erros/{slug[:30]}.jpg", folha)
