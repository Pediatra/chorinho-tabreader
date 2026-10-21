"""2018: análise pré-registrada depois do C1 reprovar (faixa de confiança), C3 sem o
vídeo de desenvolvimento, ponto de escuta que falhou e amplitude por vídeo."""
import json, statistics, sys
sys.path.insert(0, "/app")
from tab import audio_som_medir as M
R = "/app/data/saida/audio/r2018"
lista = json.load(open(f"{R}/lista.json"))
DEV = "retrato_brasileiro_v2"
for arq in ("medida.json", "medida_cru.json"):
    m = json.load(open(f"{R}/{arq}"))
    fr = [a["fracao"] for a in m["acordes"] if a["video"] != DEV]
    por = {}
    for a in m["acordes"]:
        if a["video"] != DEV:
            por.setdefault(a["video"], []).append(a["fracao"])
    print(arq, "C3 sem dev:", len(fr), "colunas, mediana", round(statistics.median(fr), 3),
          {k[:20]: [round(x, 2) for x in v] for k, v in por.items()})
    print("  pontos que falharam:", [(p["id"], p["video"][:25], p["t"]) for p in m["pontos"] if not p["acertado"]])
# faixa de confiança na prova (pré-registrado para o caso de C1 reprovar)
prova = [x for x in lista if x["papel"] == "ouro" and x["nome"] != DEV]
print("\ncorte  rev(prova)          prec(prova)        controle")
for corte in [0.0, 0.3, 0.4, 0.5, 0.6, 0.7]:
    m = M.medir(prova, __import__("pathlib").Path(f"{R}/som"), __import__("pathlib").Path(f"{R}/ferramenta_acordes"), corte)
    g = sum(v["real"]["n_gabarito"] for v in m["por_video"].values())
    p = sum(v["real"]["n_pareadas"] for v in m["por_video"].values())
    s = sum(v["real"]["n_som_trecho"] for v in m["por_video"].values())
    pc = sum(v["controle"]["n_pareadas"] for v in m["por_video"].values())
    print(f"{corte:.1f}   {p}/{g} = {p/g:.3f}   {p}/{s} = {p/s:.3f}   {pc/g:.3f}")
# amplitude das notas pareadas (cru) por vídeo
m = json.load(open(f"{R}/medida_cru.json"))
print("\namplitude das notas do som (cru), mediana e quartis, por vídeo:")
for x in lista:
    som = json.load(open(f"{R}/som/{x['nome']}.json"))["notas"]
    a = [n["amplitude"] for n in som]
    q = statistics.quantiles(a, n=4)
    print(f"  {x['nome'][:35]:35s} n {len(a):5d} q1 {q[0]:.2f} med {q[1]:.2f} q3 {q[2]:.2f}")
