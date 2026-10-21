"""Mede as saídas do SMT (sem treino) com a mesma régua da avaliação (diagnóstico)."""

import json
from pathlib import Path

from tab import partitura_avaliar as A

idx = {i["id"]: i for i in json.load(open("data/saida/partitura/p1/recortes/indice.json"))}
ouro = A._carregar_ouro()
base = Path("data/saida/partitura/p1/omr/smt")
for pasta in sorted(base.iterdir()):
    ex = pasta / "crop" / "execucao.json"
    if not ex.exists():
        continue
    regs = {r["id"]: r for r in json.load(open(ex))}
    tot = A._zero()
    for rid in [f"R{k:02d}" for k in range(1, 13)]:
        ref = A._referencia_do_item(idx[rid], ouro)
        r = regs.get(rid)
        notas = []
        if r and r["ok"]:
            notas = A.ler_musicxml(Path(r["saida"])).notas
        c, _ = A.contar(A.eventos_da_biblioteca(notas), ref, "exato")
        tot = A.somar(tot, c)
    ok = sum(1 for r in regs.values() if r["ok"])
    print(pasta.name, "saidas", ok, "/12", tot)
