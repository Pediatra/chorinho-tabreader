"""Calibração descritiva do detector antigo nos ciclos 1026–1036 (marcas atuais do dono)."""
import json
from tab.maos_braco_ciclo import RODADAS, ARQUIVO_PREVISTO, medir_quadros
linhas = []
for numero in ("1026", "1027", "1029", "1032", "1036"):
    r = RODADAS[numero]
    prev = json.load(open(r.pasta / ARQUIVO_PREVISTO))
    gab = json.load(open(r.gabarito))
    m = medir_quadros(prev, gab, "x")
    for l in m["linhas"]:
        p = prev["quadros"][l["id"]]
        capo = isinstance(gab["quadros"][l["id"]].get("capo"), list)
        linhas.append((numero, l["id"], p["achou"], p["S1"], l["sinalizado"], l["correto"], capo, l["classe"]))
achados = [x for x in linhas if x[2] and x[3] is not None]
achados.sort(key=lambda x: x[3])
n = len(achados)
print("quadros medidos", len(linhas), "com braço achado e S1", n)
for nome, filtro in (("todos", lambda x: True), ("sem capo", lambda x: not x[6]), ("com capo", lambda x: x[6])):
    sub = [x for x in achados if filtro(x)]
    k = len(sub)
    print(f"\n{nome}: {k} quadros")
    for q in range(5):
        fatia = sub[q * k // 5:(q + 1) * k // 5]
        if fatia:
            print(f"  quinto {q+1}: S1 até {fatia[-1][3]:.3f}: certos {sum(x[5] for x in fatia)} de {len(fatia)}")
    sem = [x for x in sub if not x[4]]; com = [x for x in sub if x[4]]
    print(f"  sem sinal: {sum(x[5] for x in sem)} de {len(sem)} certos; sinalizados: {sum(x[5] for x in com)} de {len(com)}")
