"""Diagnóstico 1030 (registro): o método 1 (nut ausente) dispara em quadros com nut visível?"""

import json
from pathlib import Path

from tab import maos_braco_video as V
from tab.maos_braco_detector import PASSOS, _carregar_pesos, _trava_gpu

saida = []
with _trava_gpu():
    dois, _ = _carregar_pesos(V.ESTAGIO2, PASSOS)
    for fonte, gab, pasta in (("1026", "data/gold/maos/braco_m26.json", "data/saida/maos/m26"),
                              ("1027", "data/gold/maos/braco_m27.json", "data/saida/maos/m27")):
        quadros = json.load(open(gab))["quadros"]
        indice = {i["id"]: i for i in json.load(open(f"{pasta}/indice.json"))["quadros"]}
        for k, r in quadros.items():
            if r.get("braco") != "sim" or not isinstance(r.get("nut"), list):
                continue
            it = indice[k]
            caso = V.CasoB(id=f"{fonte}:{k}", fonte=fonte, arquivo=it["arquivo"],
                           png=Path(pasta) / "quadros" / f"{k}.png", largura=it["largura"],
                           altura=it["altura"], corda1=r["corda1"], corda6=r["corda6"], verdade=1)
            res = V.analisar_caso(caso, dois, [])
            saida.append({"id": caso.id, "nut_ausente": res.get("nut_ausente")})
n = len(saida); f = sum(1 for s in saida if s["nut_ausente"])
print(json.dumps({"quadros_com_nut_visivel": n, "disparos": f, "ids": [s["id"] for s in saida if s["nut_ausente"]]}, ensure_ascii=False))
json.dump(saida, open("data/saida/maos/m30/falso_alarme_nut.json", "w"), indent=1)
