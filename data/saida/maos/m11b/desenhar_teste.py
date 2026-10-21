"""Desenha os pares do teste M11b com previsto (vermelho) e dono (verde)."""
import json
from pathlib import Path
from tab import maos_braco_cadeia as c
pares = tuple((p["chave"], p["alvo"]) for p in json.load(open("data/saida/maos/m11b/pares_teste_emenda3.json")))
sel = {"q58", "q48", "q50", "q51", "q52", "q59", "q73"}
pares = tuple(p for p in pares if p[1] in sel)
saida = Path("data/saida/maos/m11b/desenhos_teste"); saida.mkdir(parents=True, exist_ok=True)
tarefas = c._tarefas(pares, Path("data/saida/maos/m11b/indice.json"), Path("data/gold/maos/braco_m11b.json"), "data/saida/maos/m11b/quadros", c.PARAMETROS_PADRAO, str(saida))
for t in tarefas:
    e = c._executar(t); print(e["alvo"], e["classe"])
