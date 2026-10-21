"""Diagnostico: quanto de margem cada recorte ganhou na condicao x2_margem (7 e 7 entrelinhas)."""

import json
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset/data/saida/partitura/p1")
orig = {i["id"]: i for i in json.loads((RAIZ / "recortes/indice.json").read_text())
        if i.get("id")}
marg = {i["id"]: i for i in json.loads((RAIZ / "recortes_margem/indice.json").read_text())
        if i.get("id")}
linhas = []
for id_ in sorted(orig):
    o, m = orig[id_], marg[id_]
    e = o["entrelinha"]
    assert (o["caixa_recorte"][0], o["caixa_recorte"][2]) == (m["caixa_recorte"][0], m["caixa_recorte"][2]), id_
    ganho_cima = (o["caixa_recorte"][1] - m["caixa_recorte"][1])
    ganho_baixo = (m["caixa_recorte"][3] - o["caixa_recorte"][3])
    linhas.append({
        "id": id_, "video": o["video"].split("/")[-1][:30], "entrelinha": e,
        "ganho_cima_px": ganho_cima, "ganho_baixo_px": ganho_baixo,
        "ganho_cima_entrelinhas": round(ganho_cima / e, 2),
        "ganho_baixo_entrelinhas": round(ganho_baixo / e, 2),
        "meta_entrelinhas": 3,
        "caixa_original": o["caixa_recorte"], "caixa_margem": m["caixa_recorte"],
    })
    print(f"{id_} {o['video'][:28]:28} e={e:5} cima +{ganho_cima:3}px ({ganho_cima/e:4.2f} e) "
          f"baixo +{ganho_baixo:3}px ({ganho_baixo/e:4.2f} e)  caixa {o['caixa_recorte']} -> {m['caixa_recorte']}")
(RAIZ / "variantes/margem_ganha.json").write_text(json.dumps(linhas, indent=2, ensure_ascii=False) + "\n")
