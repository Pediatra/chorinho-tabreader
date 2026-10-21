import json
import cv2
import numpy as np
from tab.maos_braco_sintetico import quadro_em
from tab.caminhos import acervo
tri = json.load(open("data/saida/maos/m39/triagem.json"))["videos"]
celulas = []
for v in tri:
    img = quadro_em(acervo() / v["arquivo"], v["t"])
    h, w = img.shape[:2]
    # metade de cima do quadro (o braço fica acima da tab), em 800 px de largura
    cima = img[: int(h * 0.62)]
    esc = 800 / w
    cima = cv2.resize(cima, (800, int(cima.shape[0] * esc)))
    cv2.putText(cima, str(v["n"]), (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 7)
    cv2.putText(cima, str(v["n"]), (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
    celulas.append(cima)
alt = max(c.shape[0] for c in celulas)
celulas = [cv2.copyMakeBorder(c, 0, alt - c.shape[0], 0, 0, cv2.BORDER_CONSTANT) for c in celulas]
for k in range(0, 40, 6):
    grupo = celulas[k : k + 6]
    while len(grupo) < 6:
        grupo.append(np.zeros_like(celulas[0]))
    folha = np.vstack([np.hstack(grupo[0:3]), np.hstack(grupo[3:6])])
    cv2.imwrite(f"data/saida/maos/m39/triagem_zoom_{k // 6 + 1}.jpg", folha, [cv2.IMWRITE_JPEG_QUALITY, 85])
