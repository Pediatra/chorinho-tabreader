"""painel_do_quadro (censo) x painel.escolher nos instantes das páginas do South American."""

import glob

from tab import leitor
from tab.painel import escolher
from tab.telas import painel_do_quadro

V = glob.glob("/acervo/guitar dell*/south american music (easy)*")[0]
for t in [32.0, 50.0, 80.0, 100.0, 140.0, 170.0, 182.0]:
    q = leitor.quadro_em(V, t)
    c = escolher(q)
    print(t, "censo:", painel_do_quadro(q), "escolher:", c and (c.y0, c.y1, round(c.passo, 1)))
