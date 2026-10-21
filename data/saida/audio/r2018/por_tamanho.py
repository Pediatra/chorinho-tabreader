"""2018: revocação por tamanho de coluna (1, 2, 3, 4+ notas) na prova, cru e com corte."""
import json, sys
from collections import Counter
sys.path.insert(0, "/app")
from tab import audio_som_medir as M
R = "/app/data/saida/audio/r2018"
capos = json.load(open(M.CAPO))
lista = [x for x in json.load(open(f"{R}/lista.json")) if x["papel"] == "ouro" and x["nome"] != "retrato_brasileiro_v2"]
for corte in (0.0, 0.5):
    g = Counter(); p = Counter(); room = Counter(); roomp = Counter()
    for x in lista:
        som = [n for n in json.load(open(f"{R}/som/{x['nome']}.json"))["notas"] if n["amplitude"] >= corte]
        capo = M.capo_do_video(x["video"], capos)
        conf, pre = M.telas_do_ouro(x["nome"])
        for t in conf:
            pt = pre[t["id"]]
            col = M.colunas_do_gabarito(t["notas"], float(pt["passo"]), capo)
            best = None
            for t0, t1 in pt["exibicoes"]:
                ev = M.eventos_do_som(som, t0 - M.FOLGA_S, t1 + M.FOLGA_S)
                pares = M.parear(col, ev)
                s = sum(q[2] for q in pares)
                if best is None or s > best[0]:
                    best = (s, pares)
            pc = {i: gg for i, _, gg in best[1]}
            for i, c in enumerate(col):
                k = min(len(c), 4)
                g[k] += len(c); p[k] += pc.get(i, 0)
    print(f"corte {corte}: " + "  ".join(f"{k}{'+' if k == 4 else ''} notas: {p[k]}/{g[k]} = {p[k]/g[k]:.3f}" for k in sorted(g)))
