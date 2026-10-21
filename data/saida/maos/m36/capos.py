import json, sys
import numpy as np
from tab.maos_braco_tempo import marcas_do_registro, _largura_pestana, eixo_do_braco, _orientar
for f in sys.argv[1:]:
    g = json.load(open(f))["quadros"]
    for k, r in g.items():
        if not r.get("capo"):
            continue
        a = marcas_do_registro(r)
        nut = r.get("nut")
        d = None
        if a is not None and isinstance(nut, list):
            _, u = eixo_do_braco(a.corda1.tolist(), a.corda6.tolist())
            u = _orientar(u, a)
            w = _largura_pestana(a.nut, a.trastes, u)
            d = float(np.dot(np.asarray(r["capo"]) - a.nut, u)) / w if w else None
        print(f.split("/")[-1], k, r["braco"], "nut" if isinstance(nut, list) else nut,
              "capo-nut(casas)", None if d is None else round(d, 2), "|", (r.get("obs") or "")[-40:])
