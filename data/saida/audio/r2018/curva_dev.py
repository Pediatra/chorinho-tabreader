"""2018: curva de corte por amplitude no vídeo de desenvolvimento (só nele)."""
import json, sys
sys.path.insert(0, "/app")
from tab import audio_som_medir as M
nome = "retrato_brasileiro_v2"
som = json.load(open(f"/app/data/saida/audio/r2018/som/{nome}.json"))["notas"]
conf, pre = M.telas_do_ouro(nome)
for corte in [0.0, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]:
    s = [n for n in som if n["amplitude"] >= corte]
    r=[]; c=[]
    for t in conf:
        p = pre[t["id"]]; col = M.colunas_do_gabarito(t["notas"], float(p["passo"]), 0)
        ex=[tuple(e) for e in p["exibicoes"]]
        r.append(M.melhor_exibicao(col, s, ex)); c.append(M.melhor_exibicao(col, s, ex, 1))
    a=M.somar(r); b=M.somar(c)
    print(f"corte {corte:.2f} notas {len(s):5d} rev {a['revocacao']:.3f} prec {a['precisao']:.3f} controle {b['revocacao']:.3f}")
