import glob
import json
import os

CA1 = "/app/data/saida/tab_frentes/fd_som/ca1"
tot = {"ouro": 0, "entregues": 0, "casadas": 0, "casa_certa": 0, "inventadas": 0, "perdidas": 0}
for arq in sorted(glob.glob(f"{CA1}/*.aval.json")):
    d = json.load(open(arq))
    n = d["notas"]
    if "total" in n:
        t = n["total"]
        print(os.path.basename(arq)[:40], "total:", t)
        for k in tot:
            tot[k] += t.get(k if k != "ouro" else "notas_ouro", 0)
    else:
        soma = {k: 0 for k in tot}
        for p in n.get("por_tela", []):
            soma["ouro"] += p["notas_ouro"]
            soma["entregues"] += p["entregues"]
            soma["casadas"] += p["casadas"]
            soma["casa_certa"] += p["casa_certa"]
            soma["inventadas"] += p["inventadas"]
            soma["perdidas"] += p["perdidas"]
        print(os.path.basename(arq)[:40], "soma por_tela:", soma)
        for k in tot:
            tot[k] += soma[k]
print("TOTAL DOBRAS:", tot)
