import json, cv2, numpy as np
from pathlib import Path
p = Path("data/saida/maos/m36")
ix = json.load(open(p / "indice.json"))["quadros"]
cel = []
for it in ix:
    im = cv2.imread(str(p / it["png"]))
    h, w = im.shape[:2]
    e = 300 / h
    im = cv2.resize(im, (int(w * e), 300))
    c = np.zeros((300, 300, 3), np.uint8)
    c[:, : min(300, im.shape[1])] = im[:, :300]
    cv2.putText(c, it["id"], (4, 20), 0, 0.6, (0, 255, 255), 2)
    cel.append(c)
linhas = [np.hstack(cel[i : i + 8]) for i in range(0, 32, 8)]
cv2.imwrite(str(p / "amostra.jpg"), np.vstack(linhas))
print(ix[0]["largura"], ix[0]["altura"])
