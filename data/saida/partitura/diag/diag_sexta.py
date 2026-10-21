"""Diagnóstico: linhas (fortes e fracas) a ~1 entrelinha da pauta, nas trocas 0 e 40."""
import json
import cv2
from tab import cache
from tab import partitura_pauta as pp

trocas = json.load(open("data/saida/partitura/diag/trocas_r3_r4.json"))
for n, (y0, y4, e) in {0: (828.5, 878.0, 12.4), 40: (686.5, 754.5, 17.0)}.items():
    canal, i, _, _, _, _, chave = trocas[n]
    pasta = cache.pasta_do_video(chave, cache.ModoCache())
    q = cache.ler_quadro(cache.caminho_do_quadro(pasta, f"presenca_{i:02d}", "png"))
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    ab = pp._abrir(pp._mascaras_de_tinta(cinza)[0], q.shape[1])
    for l in pp._linhas_da_abertura(ab, q.shape[1], True):
        if abs(y0 - e - l.y) < 4 or abs(y4 + e - l.y) < 4:
            print(n, l)
