"""Mede o deslocamento sistematico entre o leitor e o ouro (so diagnostico)."""

import copy
import json
import subprocess
import sys

arq = sys.argv[1]
base = json.load(open(arq, encoding="utf-8"))
for delta in [-0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4]:
    d = copy.deepcopy(base)
    for n in d["notas"]:
        if n["t_ini"] is not None:
            n["t_ini"] = round(n["t_ini"] + delta, 3)
    saida = "/app/data/saida/fase5/grade/_desl.json"
    json.dump(d, open(saida, "w", encoding="utf-8"))
    out = subprocess.run(
        [sys.executable, "-m", "tab.avaliar_video", "--ouro",
         "data/gold/ouro_video/retrato_brasileiro_v2.json", "--pred", saida],
        capture_output=True, text=True, cwd="/app",
    ).stdout
    linha = [ln for ln in out.splitlines() if ln.startswith("tempo:")]
    print(f"delta {delta:+.1f}: {linha[0] if linha else out[-300:]}")
