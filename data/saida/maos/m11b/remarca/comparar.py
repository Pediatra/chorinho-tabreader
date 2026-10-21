"""Compara a remarcação cega com a marcação original do dono."""
import json
from tab.maos_braco_tempo import marcas_do_registro, erros, classificar
r = json.load(open("data/saida/maos/m11b/remarca/ouro_cego.json"))["quadros"]
g = json.load(open("data/gold/maos/braco_m11b.json"))["quadros"]
mapa = json.load(open("data/saida/maos/m11b/remarca/mapa_NAO_ABRIR.json"))
t = json.load(open("data/saida/maos/m11b/teste_cadeia_a.json"))
cls = {e["alvo"]: (e["classe"], e["erros"] and round(e["erros"]["perp_cordas"], 2)) for e in t["pares"]}
for rid, q in sorted(mapa.items()):
    if not r[rid].get("respondido_em"):
        print(rid, "sem resposta"); continue
    a, b = marcas_do_registro(r[rid]), marcas_do_registro(g[q])
    e = erros(a, b)
    print(q, "vão_px", round(e["vao_px"], 1), "cordas", round(e["perp_cordas"], 2), "nut", round(e["nut_casas"], 2),
          "pior_traste", round(e["pior_traste_casas"], 2), "->", classificar(e, achou=True, braco_alvo="sim"),
          "| rastreador:", cls[q])
