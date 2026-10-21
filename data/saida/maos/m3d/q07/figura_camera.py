import cv2, numpy as np
caixa = (777, 95, 1792, 1080)
ims = [("q07 (dono)", "/app/data/saida/maos/m3b/quadros/q07.png"),
       ("c2 t=380.5", "/app/data/saida/maos/m3d/q07/cena2/f_380.513.png"),
       ("c2 t=493.7", "/app/data/saida/maos/m3d/q07/cena2/f_493.66.png"),
       ("c2 t=607.6", "/app/data/saida/maos/m3d/q07/cena2/f_607.574.png")]
out = []
for nome, p in ims:
    im = cv2.imread(p).copy()
    x0, y0, x1, y1 = caixa
    cv2.rectangle(im, (x0, y0), (x1, y1), (0, 255, 0), 4)
    im = cv2.resize(im, (960, 540))
    cv2.putText(im, nome, (12, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
    out.append(im)
top = np.hstack(out[:2]); bot = np.hstack(out[2:])
cv2.imwrite("/app/data/saida/maos/m3d/q07/mesma_camera.png", np.vstack([top, bot]))
print("ok")
