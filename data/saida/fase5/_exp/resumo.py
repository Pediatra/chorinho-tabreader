"""Resume um JSON v1 do tempo por exibicao (so leitura)."""

import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
r = d["resumo"]
print("resumo:", r)
for t in d["telas"]:
    for e, ex in enumerate(t["exibicoes"]):
        tp = ex["tempo"]
        ob = {n: (v["coerencia"], v["cobertura"], v["transicoes"]) for n, v in ex.get("observadores", {}).items()}
        print(f"tela {t['id']:>2} exib {e} [{ex['t0']:.1f},{ex['t1']:.1f}] medido={tp['medido']} "
              f"obs={tp.get('observador')} coe={tp.get('coerencia')} cov={tp.get('cobertura')} "
              f"pass={len(ex.get('passagens', []))} ob={ob}")
        if not tp["medido"]:
            print("      motivo:", tp["motivo"])
