import json
from tab.maos_braco_ciclo import marcas_do_previsto
from tab.maos_braco_tempo import marcas_do_registro, erros, numerar_trastes
g = json.load(open("data/gold/maos/braco_m36.json"))["quadros"]
p = json.load(open("data/saida/maos/m36/previsto.json"))["quadros"]
for k in sorted(g):
    r = g[k]; x = p[k]
    if r["braco"] != "sim" or not x["achou"]:
        continue
    a = marcas_do_registro(r)
    if a is None:
        print(k, "incompleto"); continue
    e = erros(marcas_do_previsto(x), a)
    nums = sorted(n["numero"] for n in numerar_trastes(r) if n["numero"] is not None)
    capo = [round(v) for v in r["capo"]] if r.get("capo") else None
    nutg = [round(v) for v in r["nut"]] if isinstance(r.get("nut"), list) else r.get("nut")
    nutp = [round(v) for v in x["nut"]] if x.get("nut") else None
    pt = {n: round(v, 2) for n, v in e["por_traste"].items()}
    print(k, "nut_g", nutg, "nut_p", nutp, "capo", capo, "nutc", e["nut_casas"] and round(e["nut_casas"], 2),
          "perp", round(e["perp_cordas"], 2), "ref", r.get("traste_referencia") and r["traste_referencia"]["numero"], "nums", nums[:3], nums[-1:], "pt", dict(list(pt.items())[:4]))
