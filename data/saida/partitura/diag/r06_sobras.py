import json, sys
sys.path.insert(0, "/app")
from pathlib import Path
from tab.partitura_avaliar import ler_musicxml, eventos_da_biblioteca, _carregar_ouro, _referencia_do_item, alinhar
ent = next(e for e in json.load(open("data/saida/partitura/p1/recortes_margem/indice.json")) if e["id"] == "R06")
ref = _referencia_do_item(ent, _carregar_ouro())
lib = eventos_da_biblioteca(ler_musicxml(Path("data/saida/partitura/p1/omr/audiveris/x2_margem_armadura/R06/saida.musicxml")).notas)
N="C C# D D# E F F# G G# A A# B".split()
nm=lambda s: sorted(N[m%12]+str(m//12-1) for m in s)
for op,i,j in alinhar(lib,ref):
    a = lib[i] if i>=0 else frozenset(); b = ref[j] if j>=0 else frozenset()
    if a != b: print(op, i, j, "lido", nm(a), "tab", nm(b))
