"""Folha dos quadros que ganharam pauta da rodada 3 para a 6 (conferência visual)."""
import json
import cv2
import numpy as np
from tab import cache

a = {json.loads(l)["chave"]: json.loads(l) for l in open("data/saida/partitura/p0_rodada3/amostra.jsonl")}
b = {json.loads(l)["chave"]: json.loads(l) for l in open("data/saida/partitura/p0/amostra.jsonl")}
cel = []
for k in sorted(a):
    for i, (qa, qb) in enumerate(zip(a[k]["quadros"], b[k]["quadros"])):
        if qb["pautas"] and not qa["pautas"]:
            q = cache.ler_quadro(cache.caminho_do_quadro(cache.pasta_do_video(k, cache.ModoCache()), f"presenca_{i:02d}", "png"))
            for p in qb["pautas"]:
                x0, y0, x1, y1 = p["caixa"]
                cv2.rectangle(q, (x0, y0), (x1, y1), (0, 200, 0), 4)
            h, w = q.shape[:2]
            s = min(480 / w, 270 / h)
            m = cv2.resize(q, (round(w * s), round(h * s)))
            c = np.full((300, 480, 3), 40, np.uint8)
            c[:m.shape[0], (480 - m.shape[1]) // 2 : (480 - m.shape[1]) // 2 + m.shape[1]] = m
            txt = f"G{len(cel)+1:02d} {b[k]['canal']} q{i}".encode("ascii", "replace").decode()
            cv2.putText(c, txt, (5, 292), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cel.append(c)
while len(cel) % 4:
    cel.append(np.full((300, 480, 3), 40, np.uint8))
linhas = [np.hstack(cel[j : j + 4]) for j in range(0, len(cel), 4)]
cv2.imwrite("data/saida/partitura/diag/ganhos_r3_r6.jpg", np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(len(cel))
