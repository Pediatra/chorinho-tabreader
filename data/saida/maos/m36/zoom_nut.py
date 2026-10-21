import cv2, json, numpy as np, sys
p = json.load(open("data/saida/maos/m36/previsto.json"))["quadros"]
out = []
for i in sys.argv[2:]:
    x = p[i]; im = cv2.imread(f"data/saida/maos/m36/quadros/{i}.png")
    cx, cy = map(int, x["nut"])
    h, w = im.shape[:2]
    y0, x0 = max(0, cy - 250), max(0, cx - 450)
    c = im[y0:cy + 250, x0:w].copy()
    cv2.circle(c, (cx - x0, cy - y0), 8, (0, 0, 255), 2)
    for t in x["trastes"]:
        a, b = int(t["ponto"][0]) - x0, int(t["ponto"][1]) - y0
        cv2.putText(c, str(t["numero"]), (a - 6, b - 10), 0, 0.7, (0, 255, 255), 2)
    cv2.putText(c, i, (10, 30), 0, 1, (0, 0, 255), 2)
    out.append(cv2.resize(c, (600, int(600 * c.shape[0] / c.shape[1]))))
cv2.imwrite(sys.argv[1], np.vstack(out))
