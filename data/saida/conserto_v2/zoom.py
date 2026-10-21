import json, sys
from pathlib import Path
import cv2
from tab.cache import ModoCache, pasta_do_video
rows = {}
for l in open("/app/data/saida/conserto_v2/piloto/censo.jsonl"):
    r = json.loads(l); rows[r["arquivo"]] = r
alvos = [
    ("kimny's guitar/[ tab ] without you - badfinger ｜ fingerstyle guitar cover.mp4", 11),
    ("transcriptor/violeta parra - guitarra - calambito temucano - partitura ⧸ tablatura..mp4", 11),
    ("transcriptor/violeta parra - guitarra - calambito temucano - partitura ⧸ tablatura..mp4", 4),
]
modo = ModoCache()
for k, (arq, i) in enumerate(alvos):
    r = rows[arq]
    img = cv2.imread(str(pasta_do_video(r["chave"], modo) / f"presenca_{i:02d}.png"))
    x0, y0, x1, y1 = (int(v) for v in r["instantes"][i]["rect"])
    m = 120
    H, W = img.shape[:2]
    a, b = max(0, y0 - m), min(H, y1 + m)
    crop = img[a:b, :].copy()
    cv2.rectangle(crop, (x0, y0 - a), (x1, y1 - a), (0, 0, 255), 3)
    cv2.imwrite(f"/app/data/saida/conserto_v2/zoom_{k}.jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(k, arq[:40], i, (x0, y0, x1, y1), (W, H), crop.shape)
