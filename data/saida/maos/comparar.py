"""Rascunho: compara afirmações (E, D) de um jsonl do censo de mãos com o rótulo do agente."""
import json, sys
sys.path.insert(0, "/app") if False else None
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tab.maos_tabela import resumo_do_quadro
rot = json.load(open("data/saida/maos/rotulo_agente_piloto.json"))["rotulos"]
regs = {json.loads(l)["arquivo"]: json.loads(l) for l in open(sys.argv[1])}
ok_quadro = n_quadro = 0
cont = {"E": [0, 0, 0], "D": [0, 0, 0]}  # achadas, visiveis, falsas
for r in rot:
    q = next(q for q in regs[r["arquivo"]]["quadros"] if q["i"] == r["quadro"])
    a = resumo_do_quadro(q)
    certo = True
    for lado, chave, v in (("E", "esquerda", r["esquerda"]), ("D", "direita", r["direita"])):
        if v is None:
            continue
        if v:
            cont[lado][1] += 1
            cont[lado][0] += a[chave]
        else:
            cont[lado][2] += a[chave]
        certo &= bool(a[chave]) == bool(v)
    n_quadro += 1
    ok_quadro += certo
print(sys.argv[1], f"quadro certo {ok_quadro}/{n_quadro}",
      " ".join(f"{l}: {c[0]}/{c[1]} achadas, {c[2]} falsas" for l, c in cont.items()))
