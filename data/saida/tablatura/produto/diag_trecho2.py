"""Diagnostico: todos os compassos do XML atual, com a tela e as notas."""

import json
import xml.etree.ElementTree as ET

from tab.musicxml import _colunas_da_tela, _compassos_da_tela, _notas_distintas_v1

R = json.load(open("data/saida/produto/mvp.json", encoding="utf-8"))
telas = {t["id"]: t for t in R["telas"]}
por_tela = _notas_distintas_v1({"notas": R["notas"]})
raiz = ET.parse("data/saida/produto/mvp.musicxml").getroot()
medidas = raiz.findall("part/measure")
numero = 0
i = 0
for tid, notas in por_tela.items():
    t = telas[tid]
    compassos, _ = _compassos_da_tela(_colunas_da_tela(notas), t["barlines_x"], float(t["passo"]))
    for c in compassos:
        numero += 1
        m = medidas[numero - 1]
        cols = []
        for n in m.findall("note"):
            if n.find("chord") is not None and cols:
                cols[-1].append(n)
            else:
                cols.append([n])
        txt = " ".join(
            "+".join("%s:%s" % (n.findtext("notations/technical/string"), n.findtext("notations/technical/fret")) for n in g)
            for g in cols
        )
        xs = [round(x) for x, _ in c]
        print("c%02d tela %2d | %s | x=%s" % (numero, tid, txt, xs))
