"""Diagnóstico: um quadro das trocas r3->r4 (argumentos: índice na lista de trocas)."""
import json
import sys
import cv2
from tab import cache
from tab import partitura_pauta as pp

trocas = json.load(open("data/saida/partitura/diag/trocas_r3_r4.json"))
for n in map(int, sys.argv[1:]):
    canal, i, na, nb, _, _, chave = trocas[n]
    pasta = cache.pasta_do_video(chave, cache.ModoCache())
    q = cache.ler_quadro(cache.caminho_do_quadro(pasta, f"presenca_{i:02d}", "png"))
    cv2.imwrite(f"data/saida/partitura/diag/troca_{n}.jpg", q)
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    L = q.shape[1]
    print(n, canal, i, "r3", na, "r4", nb, "agora", [p.caixa for p in pp.achar_pautas(q)])
    for k, m in enumerate(pp._mascaras_de_tinta(cinza)):
        ab = pp._abrir(m, L)
        f = [(l.y, l.espessura) for l in pp._linhas_da_abertura(ab, L, k == 0) if l.forte]
        print("  polaridade", k, "fortes", f)
