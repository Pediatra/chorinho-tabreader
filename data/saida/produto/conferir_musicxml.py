"""Confere o MusicXML do MVP contra o JSON: ordem, compassos e contagem de notas."""

import json
import xml.etree.ElementTree as ET

from tab.musicxml import TICKS_COMPASSO

R = json.load(open("data/saida/produto/mvp.json", encoding="utf-8"))
raiz = ET.parse("data/saida/produto/mvp.musicxml").getroot()
medidas = raiz.findall("part/measure")
print("compassos no XML:", len(medidas))
erros = []
for m in medidas:
    soma = sum(int(n.findtext("duration")) for n in m.findall("note") if n.find("chord") is None)
    if soma != TICKS_COMPASSO:
        erros.append((m.get("number"), soma))
print("compassos com duracao != 2048:", erros)
notas = raiz.findall("part/measure/note")
print("elementos note:", len(notas), "| com pitch:", sum(1 for n in notas if n.find("pitch") is not None))
print("frets:", len([f for f in raiz.iter("fret")]))
# 1o compasso: colunas da tela 1 antes da 1a barra util (592)
t1 = [n for n in R["notas"] if n["tela"] == 1]
cols = sorted({n["coluna"] for n in t1 if n["x_quadro"] < 592})
print("tela 1: colunas antes da barra 592:", cols, "(", len(cols), ")")
primeiro = [
    (n.findtext("notations/technical/string"), n.findtext("notations/technical/fret"), n.find("chord") is not None)
    for n in medidas[0].findall("note")
]
print("1o compasso (corda, casa, acorde):", primeiro)
por_tela = {}
for n in R["notas"]:
    por_tela.setdefault(n["tela"], set()).add(n["coluna"])
for t in R["telas"]:
    bl = t["barlines_x"]
    print("tela", t["id"], "barras brutas", len(bl), "+1 =", len(bl) + 1,
          "| compassos no XML:", None)
