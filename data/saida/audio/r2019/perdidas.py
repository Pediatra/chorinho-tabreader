"""2019: notas do gabarito não ouvidas, por corda e por contexto (diagnóstico)."""
import json, sys
from collections import Counter
sys.path.insert(0, "/app")
from tab import audio_som_medir as M
R = "/app/data/saida/audio/r2019"
capos = json.load(open(M.CAPO))
lista = [x for x in json.load(open("/app/data/saida/audio/r2018/lista.json")) if x["papel"] == "ouro" and x["nome"] != "retrato_brasileiro_v2"]
for x in lista:
    som = json.load(open(f"{R}/som_fl/{x['nome']}.json"))["notas"]
    capo = M.capo_do_video(x["video"], capos)
    conf, pre = M.telas_do_ouro(x["nome"])
    por_corda = Counter(); tot_corda = Counter(); repetida = Counter(); tot_rep = Counter()
    for t in conf:
        pt = pre[t["id"]]
        col = M.colunas_do_gabarito(t["notas"], float(pt["passo"]), capo)
        best = None
        for t0, t1 in pt["exibicoes"]:
            ev = M.eventos_do_som(som, t0 - M.FOLGA_S, t1 + M.FOLGA_S)
            pares = M.parear(col, ev)
            s = sum(z[2] for z in pares)
            if best is None or s > best[0]:
                best = (s, pares, ev)
        _, pares, ev = best
        pj = {i: j for i, j, _ in pares}
        for i, c in enumerate(col):
            ouv = Counter(n["midi"] for n in ev[pj[i]]) if i in pj else Counter()
            ant = {n["midi"] for n in col[i - 1]} if i > 0 else set()
            for n in c:
                ok = ouv[n["midi"]] > 0
                if ok:
                    ouv[n["midi"]] -= 1
                tot_corda[n["corda"]] += 1
                por_corda[n["corda"]] += ok
                k = "repete_anterior" if n["midi"] in ant else "nova"
                tot_rep[k] += 1; repetida[k] += ok
    print(x["nome"][:25], "por corda:", " ".join(f"c{c} {por_corda[c]}/{tot_corda[c]}" for c in sorted(tot_corda)),
          "|", " ".join(f"{k} {repetida[k]}/{tot_rep[k]}" for k in tot_rep))
