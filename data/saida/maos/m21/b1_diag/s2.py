import numpy as np
from tab import maos_braco_localizador as L
from tab.maos_braco_detector import _imagem
from tab.maos_braco_localizador import pontos_do_rotulo
ent = {e[0]: e for e in L._entradas_prova()}
for nome in ("L2_todos_s1", "L2_todos_s2", "L2_todos_s3"):
    loc = L._carregar_localizador(nome)
    for q in ("q46", "q58"):
        c, e = L.enquadrar(_imagem(L.MAOS_M11B / "quadros" / f"{q}.png"))
        m = L.prever_localizador(loc, [c])[0]
        dec = L.decodificar_quadro(m, e)
        print(nome, q, "max por canal", np.round(m.reshape(m.shape[0], -1).max(1), 2))
        print("  prev", np.round(dec.get("pontos"), 0).tolist() if dec["achou"] else dec)
        print("  rot ", np.round(pontos_do_rotulo(ent[q][2]), 0).tolist())
