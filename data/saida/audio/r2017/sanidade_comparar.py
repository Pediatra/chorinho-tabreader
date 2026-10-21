"""Sanidade do comparar.py: antigo contra ele mesmo (tem de dar tudo igual)."""

import collections
import sys

sys.path.insert(0, "data/saida/audio/r2017")
import comparar as C  # noqa: E402

pontos = C.pontos_do_gabarito()
print("pontos:", collections.Counter(v[0] for v in pontos.values()), len(pontos))
for item in C.LISTA[:4]:
    pa, aa = C.ler(item["produto_antigo"]), C.ler(item["alinhado_antigo"])
    telas = C.mapa_telas(pa, pa)
    cols = C.mapa_colunas(pa, pa, telas)
    ta = C.tempos(aa)
    p = C.comparar_pares(ta, ta, telas, cols)
    g = C.julgar_pontos(item["video"], ta, ta, telas, cols, pontos)
    print(item["apelido"], p, collections.Counter((x["tipo"], x["classe_antiga"], x["classe_nova"]) for x in g))
