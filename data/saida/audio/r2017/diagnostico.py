"""Rodada 2017: colunas que perderam o tempo e colunas só do produto novo, por vídeo."""

import collections
import json
import statistics
import sys

sys.path.insert(0, "data/saida/audio/r2017")
import comparar as C  # noqa: E402

ap = sys.argv[1]
item = next(x for x in C.LISTA if x["apelido"] == ap)
pa, aa = C.ler(item["produto_antigo"]), C.ler(item["alinhado_antigo"])
pn = C.ler(C.R / "produtos" / f"{ap}.json")
an = C.ler(C.R / f"alinhado_{ap}.json")
telas = C.mapa_telas(pa, pn)
cols = C.mapa_colunas(pa, pn, telas)
ta, tn = C.tempos(aa), C.tempos(an)


def notas(p):
    d = collections.defaultdict(list)
    for n in p["notas"]:
        d[(n["tela"], n["coluna"])].append((n["corda"], n["casa"], n["x_centro_quadro"]))
    return d


na, nn = notas(pa), notas(pn)
mot_n = {(c["tela"], c["exibicao"], c["coluna"]): c["motivo"] for c in an["colunas"]}
inv = {v: k for k, v in cols.items()}
print("== perderam tempo (antigo com, novo sem)")
for chave, t in sorted(ta.items()):
    nova = C.chave_nova(chave, telas, cols)
    if t is not None and nova in tn and tn[nova] is None:
        x = statistics.median(v[2] for v in na[(chave[0], chave[2])])
        print(chave, "→", nova, f"x={x:.0f}", sorted(v[:2] for v in na[(chave[0], chave[2])]),
              "novo:", sorted(v[:2] for v in nn[(nova[0], nova[2])]), mot_n[nova])
print("== colunas só do novo (sem par antigo)")
cont = collections.Counter()
for (t, e, c), tt in sorted(tn.items()):
    if (t, c) in inv:
        continue
    cont["com" if tt is not None else "sem"] += 1
    x = statistics.median(v[2] for v in nn[(t, c)]) if nn[(t, c)] else None
    print((t, e, c), f"x={x}", sorted(v[:2] for v in nn[(t, c)]), tt, mot_n[(t, e, c)])
print(cont)
print("== colunas antigas sem par")
for (t, e, c), tt in sorted(ta.items()):
    if C.chave_nova((t, e, c), telas, cols) is None:
        x = statistics.median(v[2] for v in na[(t, c)]) if na[(t, c)] else None
        print((t, e, c), f"x={x}", sorted(v[:2] for v in na[(t, c)]), tt)
