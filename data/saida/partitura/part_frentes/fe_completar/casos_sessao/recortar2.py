import cv2
for rid in ("R09", "R10", "R11", "R12"):
    im = cv2.imread(f"data/saida/partitura/p1/recortes_margem/{rid}.png")
    cv2.imwrite(f"data/saida/part_frentes/fe_completar/casos_sessao/{rid}_inteiro.png", im)
