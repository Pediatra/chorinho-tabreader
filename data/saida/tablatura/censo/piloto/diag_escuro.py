"""Diagnostico do painel escuro: quais portoes rejeitam o quadro (Fase 7.1)."""
import sys

import cv2
import numpy as np

from tab import leitor, painel, telas
from tab.caminhos import acervo

video, t = sys.argv[1], float(sys.argv[2])
q = leitor.quadro_em(str(acervo() / video), t)
cv2.imwrite("data/saida/censo/piloto/diag/quadro.jpg", q)
print("quadro", q.shape)
for c in painel.candidatos_quadro(q):
    print("cand", c.nome, c.y0, c.y1, "passo", round(c.passo, 1), "unif", round(c.uniformidade, 3),
          "glifos", len(c.grade.glifos), "x0", c.x0, "linhas", c.grade.linhas_y)
    roi = c.roi
    sat = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 1]
    cz = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    print("   sat_med", float(np.median(sat)), "cinza_med", float(np.median(cz)), "papel", round(painel.papel_branco(roi), 3))
for nome, y0, y1 in painel.FAIXAS:
    r = q[y0:min(y1, q.shape[0]), :]
    try:
        g = painel.segmentar(r)
        print("faixa", nome, "linhas", len(g.linhas_y), "glifos", len(g.glifos), "passo", round(g.passo, 1))
    except Exception as e:
        print("faixa", nome, "erro", e)
e = painel.escolher(q)
print("escolher", None if e is None else (e.nome, e.y0, e.y1, round(e.passo,1), round(e.uniformidade,3), e.x0))
print("painel_do_quadro", telas.painel_do_quadro(q))
