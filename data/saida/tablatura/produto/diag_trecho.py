"""Diagnostico: compassos do XML atual com a tela de origem, e colunas por tela."""

import json
import xml.etree.ElementTree as ET

from tab.musicxml import _colunas_da_tela, _compassos_da_tela, _notas_distintas_v1

R = json.load(open("data/saida/produto/mvp.json", encoding="utf-8"))
telas = {t["id"]: t for t in R["telas"]}
por_tela = _notas_distintas_v1({"notas": R["notas"]})
numero = 0
mapa = []
for tid, notas in por_tela.items():
    t = telas[tid]
    compassos, _ = _compassos_da_tela(_colunas_da_tela(notas), t["barlines_x"], float(t["passo"]))
    for c in compassos:
        numero += 1
        mapa.append((numero, tid, [(g[0]["corda"], g[0]["casa"], len(g)) for _, g in c]))
for num, tid, cols in mapa:
    if tid in (2, 10, 11):
        print("c%d tela %d:" % (num, tid), " ".join("%d:%s%s" % (corda, casa, "+" if n > 1 else "") for corda, casa, n in cols))
xml = ET.parse("data/saida/produto/mvp.musicxml").getroot()
print("xml compassos:", len(xml.findall("part/measure")), "mapa:", len(mapa))
