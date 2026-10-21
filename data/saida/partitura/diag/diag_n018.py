"""Diagnóstico: por que N018 (rodada 1) voltou a falhar com ESPESSURA_MAX=6."""
import json
import cv2
from tab import cache
from tab import partitura_pauta as pp

d = json.load(open("data/saida/partitura/diag/indice_rodada1.json"))
e = [e for e in d["negativos"] if e["numero"] == "N018"][0]
pasta = cache.pasta_do_video(e["chave"], cache.ModoCache())
q = cache.ler_quadro(cache.caminho_do_quadro(pasta, f"presenca_{e['indice_quadro']:02d}", "png"))
cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
L = q.shape[1]
for k, m in enumerate(pp._mascaras_de_tinta(cinza)):
    ab = pp._abrir(m, L)
    ls = pp._linhas_da_abertura(ab, L, k == 0)
    fortes = [l for l in ls if l.forte and 650 < l.y < 820]
    print(k, [(l.y, l.espessura, l.x0, l.x1) for l in fortes])
    for i in range(len(fortes) - 4):
        g = fortes[i : i + 5]
        p = pp._pauta_do_grupo(g, L)
        if p:
            print("  grupo", p.ys, "crista", [pp._linha_e_crista(l, p, cinza) for l in g],
                  "sexta", pp._ha_sexta_linha(p, ls, L), "janela", pp._ha_sexta_na_janela(p, ab))
ab = pp._abrir(pp._mascaras_de_tinta(cinza)[0], L)
for l in pp._linhas_da_abertura(ab, L, True):
    if 690 < l.y < 712 or 802 < l.y < 820:
        print("candidata a sexta", l)
