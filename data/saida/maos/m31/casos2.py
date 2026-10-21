import json
from tab.caminhos import *
for nome,p,qs in (("1027",MAOS_M27,"q49 q50 q51 q52 q53 q54 q55 q56"),("M11B",MAOS_M11B,"q34"),("1029",MAOS_M29,"q19 q20 q24 q46 q50"),("1031",MAOS_M31,"q13 q14 q15")):
    for f in ("indice.json","lote.json"):
        try: ind=json.load(open(p/f)); break
        except FileNotFoundError: ind=None
    print(nome, f, list(ind)[:5] if ind else None)
    q=ind.get("quadros",ind)
    for k in qs.split():
        r=q[k] if isinstance(q,dict) else None
        print(" ",k,{c:r.get(c) for c in r if c not in ("previsto",)} if r else None)
