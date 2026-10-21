import json
import cv2
import numpy as np
casos = [
    ("M3b q10", "data/gold/maos/braco.json", "data/saida/maos/m3b", "q10"),
    ("M32 q14", "data/gold/maos/braco_m32.json", "data/saida/maos/m32", "q14"),
    ("M32 q45", "data/gold/maos/braco_m32.json", "data/saida/maos/m32", "q45"),
    ("M25 treino q139", "data/gold/maos/braco_m25_treino.json", "data/saida/maos/m25/treino", "q139"),
]
celulas = []
for titulo, ouro, pasta, q in casos:
    r = json.load(open(ouro))["quadros"][q]
    idx = {i["id"]: i for i in json.load(open(f"{pasta}/indice.json"))["quadros"]}
    img = cv2.imread(f"{pasta}/{idx[q]['png']}")
    pts = []
    def p(v): return tuple(int(round(c)) for c in v)
    for corda, cor in (("corda1", (0, 0, 255)), ("corda6", (255, 0, 0))):
        if isinstance(r.get(corda), list) and len(r[corda]) == 2:
            cv2.line(img, p(r[corda][0]), p(r[corda][1]), cor, 2)
    for t in r.get("trastes") or []:
        cv2.circle(img, p(t), 7, (0, 255, 255), 2); pts.append(t)
    if isinstance(r.get("nut"), list):
        cv2.circle(img, p(r["nut"]), 11, (0, 255, 0), 3); pts.append(r["nut"])
    if isinstance(r.get("capo"), list):
        cv2.drawMarker(img, p(r["capo"]), (255, 0, 255), cv2.MARKER_CROSS, 28, 4); pts.append(r["capo"])
    centro = np.mean([pts[-1], pts[-2]] if len(pts) > 1 else pts, axis=0) if pts else np.array([img.shape[1] / 2, img.shape[0] / 2])
    if isinstance(r.get("nut"), list):
        centro = np.asarray(r["nut"], dtype=float)
    x0 = int(np.clip(centro[0] - 350, 0, max(0, img.shape[1] - 700)))
    y0 = int(np.clip(centro[1] - 200, 0, max(0, img.shape[0] - 400)))
    corte = img[y0:y0 + 400, x0:x0 + 700].copy()
    corte = cv2.copyMakeBorder(corte, 0, 400 - corte.shape[0], 0, 700 - corte.shape[1], cv2.BORDER_CONSTANT)
    texto = f"{titulo}  obs: {(r.get('obs') or '')[:40]}"
    cv2.putText(corte, texto, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 5)
    cv2.putText(corte, texto, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    celulas.append(corte)
legenda = np.full((40, 1400, 3), 255, np.uint8)
cv2.putText(legenda, "verde = nut marcado | magenta + = capo (k) | amarelo = trastes | vermelho/azul = cordas 1/6", (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
folha = np.vstack([legenda, np.hstack(celulas[0:2]), np.hstack(celulas[2:4])])
cv2.imwrite("data/saida/maos/m37/conferir/quatro_quadros.jpg", folha, [cv2.IMWRITE_JPEG_QUALITY, 90])
