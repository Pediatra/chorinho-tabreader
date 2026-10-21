"""2019: C3 sem o vídeo de referência, pontos de escuta, revocação por tamanho de coluna."""
import json, statistics, sys
from collections import Counter
sys.path.insert(0, "/app")
from tab import audio_som_medir as M
R = "/app/data/saida/audio/r2019"
lista = json.load(open("/app/data/saida/audio/r2018/lista.json"))
DEV = "retrato_brasileiro_v2"
capos = json.load(open(M.CAPO))
for p in ("fl", "gaps"):
    m = json.load(open(f"{R}/medida_{p}.json"))
    fr = [a["fracao"] for a in m["acordes"] if a["video"] != DEV]
    por = {}
    for a in m["acordes"]:
        if a["video"] != DEV:
            por.setdefault(a["video"][:14], []).append(round(a["fracao"], 2))
    print(f"guitar-{p} C3 sem ref: {len(fr)} colunas, mediana {statistics.median(fr):.3f}, >=4/6: {sum(f >= 4/6 - 1e-9 for f in fr)}/{len(fr)}")
    print("   ", por)
    print("    escuta que falhou:", [(x["id"], x["video"][:20], x["t"]) for x in m["pontos"] if not x["acertado"]])
    g = Counter(); q = Counter()
    for x in lista:
        if x["papel"] != "ouro" or x["nome"] == DEV:
            continue
        som = json.load(open(f"{R}/som_{p}/{x['nome']}.json"))["notas"]
        capo = M.capo_do_video(x["video"], capos)
        conf, pre = M.telas_do_ouro(x["nome"])
        for t in conf:
            pt = pre[t["id"]]
            col = M.colunas_do_gabarito(t["notas"], float(pt["passo"]), capo)
            best = None
            for t0, t1 in pt["exibicoes"]:
                pares = M.parear(col, M.eventos_do_som(som, t0 - M.FOLGA_S, t1 + M.FOLGA_S))
                s = sum(z[2] for z in pares)
                if best is None or s > best[0]:
                    best = (s, pares)
            pc = {i: gg for i, _, gg in best[1]}
            for i, c in enumerate(col):
                k = min(len(c), 4); g[k] += len(c); q[k] += pc.get(i, 0)
    print("    por tamanho:", "  ".join(f"{k}{'+' if k == 4 else ''}: {q[k]}/{g[k]} = {q[k]/g[k]:.3f}" for k in sorted(g)))
