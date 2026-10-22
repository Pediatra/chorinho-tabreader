import collections
import json

linhas = [json.loads(x) for x in open("/app/data/saida/tab_frentes/fd_som/d1/notas_ouros.jsonl", encoding="utf-8")]
print("total linhas:", len(linhas))
tab = collections.Counter()
for r in linhas:
    motivo = "medida"
    if r["excluida"]:
        motivo = "excluida"
    elif r["t_som"] is None:
        motivo = "sem_instante"
    elif r["score"] is None:
        motivo = "sem_score"
    tab[(r["video"], r["rotulo"], motivo)] += 1
for k, v in sorted(tab.items()):
    print(k, v)
print("tecnica nao nula:", sum(1 for r in linhas if r["tecnica"] is not None))
