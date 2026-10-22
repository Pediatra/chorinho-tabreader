"""Relê a página 10 do Gymnopédie com a faixa sem a borda escura de baixo (sem gravar)."""

import glob
import json
import sys
from dataclasses import replace

from tab import leitor
from tab.caminhos import MODELO_PADRAO
from tab.digito import carregar
from tab.ouro_video import ler_notas
from tab.painel import escolher
from tab.reconhecer import carregar_modelo

S = "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"
V = glob.glob("/acervo/robert lunn/gymnop*no.1 (erik satie) - includes*")[0]
pre = json.load(open(f"data/saida/ouro_video/{S}/pre.json"))
tp = next(t for t in pre["telas"] if t["id"] == 10)
q = leitor.quadro_em(V, float(tp["quadro_ref_s"]))
print(V, q.shape, tp["quadro_ref_s"])
topo, base = 880, 1062
c = escolher(q[topo:base])
c = replace(c, y0=c.y0 + topo, y1=c.y1 + topo)
modelo, rotulos, dev = carregar_modelo(str(MODELO_PADRAO))
lido = ler_notas(c, modelo, rotulos, dev, carregar())
print("linhas", [round(y) for y in lido["linhas_y"]], "passo", round(lido["passo"], 1))
print(sorted((n["x_quadro"], n["corda"], n["casa"]) for n in lido["notas"]))
if len(sys.argv) > 1:
    json.dump(lido, open("data/saida/fase8/conserto/gymno_p10_lido.json", "w"))
