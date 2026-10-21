import random, collections
from tab.sintetico import PRESETS_FONTES, _resolver_fontes
from tab.sintetico_sistema import gerar_sistema
import cv2
f = _resolver_fontes(PRESETS_FONTES["padrao"][0])
c = collections.Counter(); imgs = []
for s in range(300):
    img, info = gerar_sistema(random.Random(s), f)
    v = set(info["variantes"]); c.update(v)
    if "cadeia" in v and len(imgs) < 6:
        imgs.append(img[:, :900] if img.shape[1] >= 900 else img)
print({k: c[k] for k in ("cadeia", "cadeia_letras", "arco_alto", "mordente_tres")})
import numpy as np
w = max(i.shape[1] for i in imgs)
imgs = [np.pad(i, ((0, 8), (0, w - i.shape[1])) + ((0, 0),) * (i.ndim - 2), constant_values=255) for i in imgs]
cv2.imwrite("/app/data/saida/tab_rotulo/r4d/amostra_g11.png", np.vstack(imgs))
