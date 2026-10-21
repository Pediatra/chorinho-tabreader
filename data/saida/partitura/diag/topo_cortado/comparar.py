"""Eventos e sucesso do Audiveris por recorte, antes e depois da cobertura mínima."""
import json
from pathlib import Path

D = Path("data/saida/partitura/diag/topo_cortado")
SP = Path("data/saida/partitura/sem_produto")
tot = {"mudou": [0, 0, 0, 0], "igual": [0, 0, 0, 0]}
for antes in sorted((D / "antes").iterdir()):
    s = antes.name
    idx_a = {e["id"]: e for e in json.loads((antes / "indice.json").read_text()) if e.get("id")}
    idx_d = {e["id"]: e for e in json.loads((SP / s / "recortes/indice.json").read_text()) if e.get("id")}
    doc_a = {p["recorte"]: p for p in json.loads((antes / f"{s}.partitura.json").read_text())["pautas"]}
    doc_d = {p["recorte"]: p for p in json.loads((SP / s / f"{s}.partitura.json").read_text())["pautas"]}
    for rid in idx_a:
        a, d = doc_a[rid], doc_d[rid]
        mudou = idx_a[rid]["caixa_recorte"] != idx_d[rid]["caixa_recorte"]
        ea, ed = len(a["eventos"]), len(d["eventos"])
        oka, okd = "erro" not in a, "erro" not in d
        t = tot["mudou" if mudou else "igual"]
        t[0] += ea; t[1] += ed; t[2] += oka; t[3] += okd
        if mudou or ea != ed or oka != okd:
            print(f"{s[:14]:14} {rid} caixa {'MUDOU' if mudou else 'igual'} "
                  f"eventos {ea}->{ed} ok {oka}->{okd} fifths {a.get('fifths')}->{d.get('fifths')}")
for k, (ea, ed, oa, od) in tot.items():
    print(f"recortes {k}: eventos {ea}->{ed}, ok {oa}->{od}")
