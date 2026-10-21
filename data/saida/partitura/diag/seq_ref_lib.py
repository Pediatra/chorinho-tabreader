"""Imprime referência × homr para alguns recortes (diagnóstico P1)."""

import json
import sys
from pathlib import Path

from tab import partitura_avaliar as A

idx = json.load(open("data/saida/partitura/p1/recortes/indice.json"))
ouro = A._carregar_ouro()


def nome(m):
    return "C C# D D# E F F# G G# A A# B".split()[m % 12] + str(m // 12 - 1)


for rid in sys.argv[2:]:
    it = next(i for i in idx if i["id"] == rid)
    ref = A._referencia_do_item(it, ouro)
    p = Path(f"data/saida/partitura/p1/omr/{sys.argv[1]}/{rid}/saida.musicxml")
    lib = A.eventos_da_biblioteca(A.ler_musicxml(p).notas)
    print(rid, "REF", [" ".join(nome(m) for m in sorted(e)) for e in ref])
    print(rid, "LIB", [" ".join(nome(m) for m in sorted(e)) for e in lib])
