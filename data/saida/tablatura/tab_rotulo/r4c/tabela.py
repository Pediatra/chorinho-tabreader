"""Tabela das rodadas 0203/0204: limiar escolhido nos ouros e números por semente.

Uso (host): python3 data/saida/tab_rotulo/r4c/tabela.py atqg atqc
"""
import json
import sys
from collections import Counter

P = "data/saida/tab_rotulo/r4a/medida_{}_s{}.json"
LIM = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]


def regra(m):
    return Counter({k[6:]: v for k, v in m.items() if k.startswith("regra:")})


def tx(m):
    m = regra(m)
    return (m["nao|sim"], m["nao|sim"] + m["nao|nao"], m["sim|nao"],
            m["sim|nao"] + m["sim|sim"])


for v in sys.argv[1:]:
    M = {s: json.load(open(P.format(v, s))) for s in (1, 2, 3)}
    esc = 0.5
    for lim in LIM:
        soma = Counter()
        for s in (1, 2, 3):
            soma.update(M[s]["ouros"]["por_limiar"][str(lim)])
        a, b, c, d = tx(soma)
        print(f"{v} {lim} ouros soma: sf {a}/{b} nf {c}/{d} ({100 * c / d:.2f}%)")
        if c / d <= 0.01 and esc == 0.5 and lim < 0.5:
            esc = lim
    print("== escolhido", v, esc)
    for lim in sorted({esc, 0.5}):
        for t in ("ouros", "t82"):
            lin = []
            for s in (1, 2, 3):
                m = M[s][t]["por_limiar"][str(lim)]
                a, b, c, d = tx(m)
                lin.append(f"{a}/{b} nf {c}/{d} casa {m['casa_certa']}/{m['casadas']}")
            print(v, lim, t, " · ".join(lin))
