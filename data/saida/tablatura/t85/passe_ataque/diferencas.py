import json, collections, sys
sys.path.insert(0, "/app/data/saida/tablatura/tab_rotulo/r2")
import converter as cv
from pathlib import Path
S = Path("/app/data/saida/tablatura/t85/passe_ataque/conferencia_t85_servida.json")
cv.SEM_REGIAO_E_SEM_TECNICA = {"t85"}; cv.PROLONGAMENTO_UMA_NOTA_ATACADA = {"t85"}
antes, _ = cv.processar_fonte("t85", S)
A = {n["nota"]: n for n in antes["notas"]}
D = json.load(open("/app/data/saida/tablatura/tab_rotulo/r2/conferir_t85/ataque_t85.json"))
c = collections.Counter()
for n in D["notas"]:
    a = A.get(n["nota"])
    de = (a["ataque"], a["motivo"]) if a else ("ambigua", "")
    if de != (n["ataque"], n["motivo"]):
        c[(de, (n["ataque"], n["motivo"]))] += 1
for k, v in c.most_common(): print(v, k)
print("sumiram", set(A) - {n["nota"] for n in D["notas"]})
srv = {t["id"]: t for t in json.load(open(S))["telas"]}
for n in D["notas"]:
    a = A.get(n["nota"])
    if a and (a["ataque"], a["motivo"]) == ("sim", "sustentada") and n["ataque"] == "nao":
        t = srv[n["tela"]]; i = int(a["regiao"].split("-r")[1]); r = t["regioes"][i]
        print(n["nota"], n["corda"], n["casa"], n["x_centro_quadro"], r["cordas"], r["x_quadro"], r["tecnica"], r.get("obs"))
