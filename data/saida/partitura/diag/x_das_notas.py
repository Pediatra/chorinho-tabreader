"""Teste: x em px de cada nota do Audiveris a partir do default-x (tenths)."""
import json, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
P1 = Path("data/saida/partitura/p1")
ind = {e["id"]: e for e in json.load(open(P1 / "recortes_margem/indice.json"))}
for rid in [f"R{i:02d}" for i in range(1, 21)]:
    d = P1 / f"omr/audiveris/x2_margem/{rid}"
    r = ET.parse(d / "saida.musicxml").getroot()
    esq = float(r.findtext(".//defaults/page-layout/page-margins/left-margin") or 0)
    xs = []
    acum = None
    for m in r.find("part").iter("measure"):
        sm = m.find(".//system-layout/system-margins/left-margin")
        if acum is None:
            acum = esq + (float(sm.text) if sm is not None else 0)
        for n in m.iter("note"):
            if n.get("default-x") and n.find("pitch") is not None and n.find("chord") is None:
                xs.append(acum + float(n.get("default-x")))
        acum += float(m.get("width"))
    with zipfile.ZipFile(d / "entrada.omr") as z:
        raiz = ET.fromstring(z.read("sheet#1/sheet#1.xml"))
    hx = sorted((int(h.find("bounds").get("x")) + int(h.find("bounds").get("w")) / 2) for h in raiz.iter("head"))
    il = 2 * ind[rid]["entrelinha"]
    esc = il / 40
    # para cada x previsto, distância à cabeça mais próxima
    prev = [x * esc for x in xs]
    import bisect
    def dist(p):
        k = bisect.bisect(hx, p); c = [hx[j] for j in (k - 1, k) if 0 <= j < len(hx)]
        return min(abs(p - q) for q in c)
    ds = sorted(dist(p) for p in prev)
    print(rid, "notas", len(prev), "mediana dist px(2x)", round(ds[len(ds)//2], 1), "max", round(ds[-1], 1), "cabeça larg ~", round(il, 1))
