"""0211 fase 2: desenha a entrada normalizada do treino com o cache alto e o antigo."""
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, "/app/data/saida/n4")
import treinar_ft as T  # noqa: E402
from tab import detector_tab as D  # noqa: E402

for alto in (False, True):
    telas = T.carregar_telas(T.DOBRAS[4], ataque=True, t82=True, alto=alto)
    print("alto" if alto else "antigo", len(telas), T.contar_alvos(telas))
    for t in telas:
        if t["slug"] == "t82" and int(t["tela"]) in (1, 10, 20):
            arr, _, _ = D.normalizar_sistema(t["img"], t["linhas_y"], t["passo"])
            a = arr[:, :900]
            a = (255 * (a - a.min()) / max(1e-6, a.max() - a.min())).astype(np.uint8)
            cv2.imwrite(f"/app/data/saida/tab_rotulo/r4g/olhar/t82_t{t['tela']}_{'alto' if alto else 'antigo'}.png", a)
    T.amostra_real(telas[0], random.Random(0))
