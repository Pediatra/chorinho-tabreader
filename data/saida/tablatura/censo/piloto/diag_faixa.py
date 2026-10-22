"""Medidas da faixa escura do quadro: portoes de painel_do_quadro (Fase 7.1)."""
import sys

import cv2
import numpy as np

from tab import leitor, painel
from tab.caminhos import acervo

video, t = sys.argv[1], float(sys.argv[2])
y0, y1 = int(sys.argv[3]), int(sys.argv[4])
q = leitor.quadro_em(str(acervo() / video), t)
faixa = q[y0:y1, :]
sat = cv2.cvtColor(faixa, cv2.COLOR_BGR2HSV)[:, :, 1]
cz = cv2.cvtColor(faixa, cv2.COLOR_BGR2GRAY)
print("sat_med", float(np.median(sat)), "cinza_med", float(np.median(cz)),
      "cinza_p90", float(np.percentile(cz, 90)), "unif", round(painel.uniformidade(faixa), 3))
g = painel.segmentar(faixa)
print("linhas_y", g.linhas_y, "passo", round(g.passo, 2), "glifos", len(g.glifos),
      "centrados", g.glifos_centrados, "avisos", g.avisos)
print("espacamento_regular", painel.espacamento_regular(g.linhas_y), "e_pauta", painel.e_pauta(faixa, g.linhas_y))
