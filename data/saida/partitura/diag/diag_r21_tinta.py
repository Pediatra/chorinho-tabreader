"""Medição da tinta acima da pauta R21: contagem por linha e topo da tinta."""

import cv2
import numpy as np

from tab.cache import ModoCache, caminho_do_quadro, ler_quadro, pasta_do_video
from tab.partitura_pauta import FRAC_FRACA, _abrir, _mascaras_de_tinta
from tab.partitura_recortes import AMOSTRA_P0, carregar_amostra, estruturas_horizontais

CHAVE = "ギタロー ⧸ guitarous/【無料タブ譜】感電 - 米津玄師 - ソロギタータブ譜.mp4|4481331|1791502043"
amostra = carregar_amostra(AMOSTRA_P0)
linha = next(l for l in amostra if l["chave"] == CHAVE)
quadro = ler_quadro(caminho_do_quadro(pasta_do_video(linha["chave"], ModoCache()), "presenca_00", "png"))
cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
largura = cinza.shape[1]
print("FRAC_FRACA", FRAC_FRACA, "limiar px", FRAC_FRACA * largura)
escura, clara = _mascaras_de_tinta(cinza)
aberta = _abrir(escura, largura)
contagem = np.count_nonzero(aberta, axis=1)
print("linhas com contagem >= limiar (aberta escura), 380..470:")
for y in range(380, 470):
    if contagem[y] > 0:
        cols = np.flatnonzero(aberta[y])
        print(y, contagem[y], cols[0], cols[-1])
# topo da tinta escura bruta na faixa da pauta R21 (x 109..1234)
bruta = escura[:, 109:1235]
for y in range(380, 459):
    n = int(np.count_nonzero(bruta[y]))
    if n:
        print("bruta", y, n)
