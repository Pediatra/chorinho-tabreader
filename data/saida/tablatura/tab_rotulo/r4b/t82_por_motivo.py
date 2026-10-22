"""R4b: na T8.2, cada nota "não" por motivo, escore das técnicas sem ataque, atq × atqg (s1)."""

import json
import sys
from collections import defaultdict

sys.path.insert(0, "/app/data/saida/tab_rotulo/r4a")
from folha_erros import escores  # noqa: E402

from tab import ataque_r4 as A  # noqa: E402
from tab import caminhos, detector_tab, leitor, painel  # noqa: E402
from tab.ataque_base import parear  # noqa: E402

r2 = caminhos.TAB_ROTULO / "r2"
ferr = caminhos.SAIDA / "t82" / "ferramenta"
indice = {int(r["id"]): r for r in json.loads((ferr / "indice.json").read_text())}
mods = {v: detector_tab.carregar(A.modelo_da_dobra(v, 0, 1)) for v in ("atq", "atqg")}
tab = defaultdict(lambda: defaultdict(list))
for tela, notas in sorted(A.gabarito_por_tela(r2 / "conferir_novos" / "ataque_t82.json").items()):
    r = indice[tela]
    q = leitor.quadro_em(str(caminhos.acervo() / r["video"]), float(r["t"]))
    c = painel.escolher_ou_mascara(q) if q is not None else None
    if c is None:
        continue
    for v, m in mods.items():
        pred = escores(m, c.roi, c.grade.linhas_y, c.passo)
        for p in pred:
            p["x_centro_quadro"] = p["x"] + c.x0
        pares = parear(notas, pred, c.passo)
        for i, n in enumerate(notas):
            if n["ataque"] == "nao":
                e = pred[pares[i]]["escore"] if i in pares else None
                tab[(r["canal"][:14], n["nota"], n["motivo"])][v] = e
for k, d in sorted(tab.items(), key=lambda kv: kv[0][2]):
    f = lambda e: "-" if e is None else f"{e:.2f}"  # noqa: E731
    print(k[2], k[0], k[1], "atq", f(d["atq"]), "atqg", f(d["atqg"]))
