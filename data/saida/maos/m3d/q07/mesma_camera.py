import json, sys, cv2, numpy as np
ALVO = "/app/data/saida/maos/m3d/q07"
q = json.load(open("/app/data/gold/maos/braco.json"))["quadros"]["q07"]
pts = [p for p in q["corda1"] + q["corda6"]] + [q["nut"]] + q["trastes"]
xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
M = 40
im_q = cv2.imread("/app/data/saida/maos/m3b/quadros/q07.png")
H, W = im_q.shape[:2]
x0, x1 = max(0, int(min(xs)) - M), min(W, int(max(xs)) + M)
y0, y1 = max(0, int(min(ys)) - M), min(H, int(max(ys)) + M)
caixa = (x0, y0, x1, y1)
tpl = im_q[y0:y1, x0:x1]
res = {"caixa_q07": caixa, "frames": []}
for p in sys.argv[1:]:
    fr = cv2.imread(p)
    r = cv2.matchTemplate(fr, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    dx, dy = loc[0] - x0, loc[1] - y0
    res["frames"].append({"arquivo": p.split("/")[-1], "dx": int(dx), "dy": int(dy), "score": round(float(mx), 4)})
print(json.dumps(res, indent=1))
