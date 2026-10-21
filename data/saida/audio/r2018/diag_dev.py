"""2018: diagnóstico das notas a mais no vídeo de desenvolvimento."""
import json, sys, statistics
from collections import Counter
sys.path.insert(0, "/app")
from tab import audio_som_medir as M
nome = "retrato_brasileiro_v2"
som = json.load(open(f"/app/data/saida/audio/r2018/som/{nome}.json"))["notas"]
conf, pre = M.telas_do_ouro(nome)
rel = Counter(); amp_par=[]; amp_extra=[]; dur_par=[]; dur_extra=[]; extras_por_ev=Counter()
for t in conf:
    p = pre[t["id"]]
    col = M.colunas_do_gabarito(t["notas"], float(p["passo"]), 0)
    best=None
    for t0,t1 in p["exibicoes"]:
        ev = M.eventos_do_som(som, t0-M.FOLGA_S, t1+M.FOLGA_S)
        pares = M.parear(col, ev)
        g=sum(x[2] for x in pares)
        if best is None or g>best[0]: best=(g,ev,pares,t0,t1)
    g,ev,pares,t0,t1 = best
    if not pares: continue
    print(t["id"], f"exib {t0:.1f}-{t1:.1f}", "colunas", len(col), "eventos", len(ev), "pareados", len(pares), "gab", sum(len(c) for c in col), "som trecho", sum(len(ev[j]) for j in range(pares[0][1], pares[-1][1]+1)))
    pj = {j:i for i,j,_ in pares}
    gold_midis = sorted({n["midi"] for c in col for n in c})
    for j in range(pares[0][1], pares[-1][1]+1):
        e = ev[j]
        if j in pj:
            alvo = Counter(n["midi"] for n in col[pj[j]])
        else:
            alvo = Counter()
        usados = Counter()
        for n in e:
            if alvo[n["midi"]] > usados[n["midi"]]:
                usados[n["midi"]] += 1; amp_par.append(n["amplitude"]); dur_par.append(n["t_fim"]-n["t_ini"])
            else:
                amp_extra.append(n["amplitude"]); dur_extra.append(n["t_fim"]-n["t_ini"])
                # relação com a coluna pareada vizinha (anterior) 
                ref = [m["midi"] for c in col for m in c]
                d = min((n["midi"]-r for r in ref), key=abs)
                rel["no_evento_pareado" if j in pj else "evento_sem_coluna"] += 1
                rel[f"d={d}"] += 1
        extras_por_ev[sum(1 for _ in e)] += 0
q=lambda v:[round(statistics.quantiles(v,n=4)[k],3) for k in range(3)]
print("amp par", q(amp_par), "amp extra", q(amp_extra))
print("dur par", q(dur_par), "dur extra", q(dur_extra))
print(rel.most_common(25))
