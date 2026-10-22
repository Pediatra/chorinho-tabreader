import cv2
for rid, x0, x1 in [("R08", 250, 560), ("R05", 90, 260), ("R07", 1300, 1920)]:
    im = cv2.imread(f"data/saida/partitura/p1/recortes_margem/{rid}.png")
    c = cv2.resize(im[:, x0:x1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(f"data/saida/part_frentes/fe_completar/casos_sessao/{rid}.png", c)
    print(rid, im.shape)
