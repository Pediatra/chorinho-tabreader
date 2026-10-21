"""M1, M2, M3, M5 a partir de atraso_mvp.json e mvp.json (sem vídeo)."""
import json, statistics as st, math

A = "/var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/a1/atraso_mvp.json"
P = "/var/home/gabriel/Projects/chorinho-dataset/data/saida/conserto_v2/mvp.json"
OUT = "/var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/a1b/"

ev = json.load(open(A))["eventos"]
prod = json.load(open(P))

# Extrai (tela, exib, coluna, t_ini, t_som, delta) com t_som válido
rows = []
for e in ev:
    f = e["passada2"]["fluxo"]
    t_som = f.get("t_som")
    d = f.get("delta_ms")
    rows.append(dict(tela=e["tela"], exib=e["exibicao"], pas=e["passagem"],
                     col=e["coluna"], t_ini=e["t_ini"], t_som=t_som, delta=d))
com = [r for r in rows if r["t_som"] is not None]
print(f"eventos={len(rows)} com_t_som={len(com)} sem={len(rows)-len(com)}")
print("chaves passada2.fluxo:", sorted(ev[0]["passada2"]["fluxo"].keys()))

# Agrupa por exibição, em ordem de tempo (ordem de t_ini mediano)
grupos = {}
for r in com:
    grupos.setdefault((r["tela"], r["exib"]), []).append(r)
for k in grupos:
    grupos[k].sort(key=lambda r: r["t_ini"])
ordem = sorted(grupos, key=lambda k: grupos[k][0]["t_ini"])
print("exibicoes com eventos:", len(ordem))

def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs)/n, sum(ys)/n
    sxx = sum((x-mx)**2 for x in xs)
    if sxx == 0:
        return 0.0, my, 0.0
    b = sum((x-mx)*(y-my) for x, y in zip(xs, ys))/sxx
    a = my - b*mx
    res = [y-(a+b*x) for x, y in zip(xs, ys)]
    sd = math.sqrt(sum(r*r for r in res)/max(n-2, 1))
    return b, a, sd

print("\n== M1: rampa dentro de cada exibicao (Δ ms vs t_ini s) ==")
print("tela exib  n   t_ini_ini   t_ini_fim  inclin(ms/s)  Δprev_ini  Δprev_fim  resid_sd_ms  mediana_Δ")
m1 = []
for k in ordem:
    g = grupos[k]
    xs = [r["t_ini"] for r in g]
    ys = [r["delta"] for r in g]
    b, a, sd = ols(xs, ys)
    dini = a + b*xs[0]
    dfim = a + b*xs[-1]
    med = st.median(ys)
    m1.append((k, b, dini, dfim, sd, med, len(g)))
    print(f"{k[0]:>4} {k[1]:>4} {len(g):>3}  {xs[0]:>9.3f}  {xs[-1]:>9.3f}  {b:>12.2f}  {dini:>9.1f}  {dfim:>9.1f}  {sd:>11.1f}  {med:>9.1f}")

print("\n== M2: andamento (intervalos consecutivos marcador vs som) ==")
print("tela exib  n_int   soma_marc_s  soma_som_s  razao(som/marc)  mediana_dif_ms(som-marc)")
m2 = []
for k in ordem:
    g = grupos[k]
    # só pares consecutivos com mesmo 'pas' (mesma passagem)
    difs = []
    for a1, a2 in zip(g, g[1:]):
        if a1["pas"] != a2["pas"]:
            continue
        dm = a2["t_ini"]-a1["t_ini"]
        ds = a2["t_som"]-a1["t_som"]
        difs.append((dm, ds))
    if not difs:
        print(f"{k[0]:>4} {k[1]:>4}   0   (sem pares)")
        continue
    sm = sum(d[0] for d in difs)
    ss = sum(d[1] for d in difs)
    mdif = st.median([(d[1]-d[0])*1000 for d in difs])
    m2.append((k, len(difs), sm, ss, ss/sm, mdif))
    print(f"{k[0]:>4} {k[1]:>4} {len(difs):>5}  {sm:>11.3f}  {ss:>10.3f}  {ss/sm:>14.4f}  {mdif:>12.1f}")

print("\n== M3: trocas de pagina consecutivas ==")
# Ordena todas as exibições; troca = fim de uma exibição seguida de início de outra
trocas = []
for i in range(len(ordem)-1):
    k1, k2 = ordem[i], ordem[i+1]
    g1, g2 = grupos[k1], grupos[k2]
    last = g1[-1]; first = g2[0]
    # só se for a mesma passagem ou adjacente no tempo
    dm = (first["t_ini"]-last["t_ini"])
    ds = (first["t_som"]-last["t_som"])
    med_antes = st.median([r["delta"] for r in g1])
    med_depois = st.median([r["delta"] for r in g2])
    trocas.append(dict(k1=k1, k2=k2, t_troca=last["t_ini"], dm=dm, ds=ds,
                       dif_ms=(ds-dm)*1000, med_antes=med_antes, med_depois=med_depois,
                       last=last, first=first))
    print(f"troca {k1}->{k2} t_last={last['t_ini']:.3f} t_first={first['t_ini']:.3f} "
          f"int_marc={dm*1000:.1f}ms int_som={ds*1000:.1f}ms dif={ (ds-dm)*1000:+.1f}ms "
          f"med_antes={med_antes:.1f} med_depois={med_depois:.1f}")

print("\n== M3 detalhe 6->7 (ultimas 8 da (6,0), primeiras 8 da (7,0)) ==")
def mostra(k, lst):
    for r in lst:
        print(f"  {k}: col={r['col']:>2} pas={r['pas']} t_ini={r['t_ini']:.3f} t_som={r['t_som']:.3f} delta={r['delta']:.1f}")
mostra((6,0), grupos.get((6,0),[])[-8:])
mostra((7,0), grupos.get((7,0),[])[:8])

print("\n== M5: mediana movel de Delta (15 eventos, ordem de tempo) e saltos >50ms em 30 eventos ==")
todos = sorted(com, key=lambda r: r["t_ini"])
ds = [r["delta"] for r in todos]
ts = [r["t_ini"] for r in todos]
mm = []
for i in range(len(ds)):
    lo = max(0, i-7); hi = min(len(ds), i+8)
    mm.append(st.median(ds[lo:hi]))
# Saltos: para cada i, compara mediana em i com mediana em i-30 (janela de 30 eventos)
saltos = []
for i in range(30, len(mm)):
    dif = mm[i]-mm[i-30]
    if abs(dif) > 50:
        saltos.append((ts[i], mm[i-30], mm[i], dif))
print("eventos ordenados:", len(todos), " intervalo t_ini:", f"{ts[0]:.3f}-{ts[-1]:.3f}")
if saltos:
    # agrupa em blocos contíguos
    blocos = []
    for s in saltos:
        if blocos and s[0]-blocos[-1][-1][0] < 3.0:
            blocos[-1].append(s)
        else:
            blocos.append([s])
    for b in blocos:
        print(f"  bloco t_ini {b[0][0]:.2f}-{b[-1][0]:.2f}s: med30_antes {b[0][1]:.1f} -> med_depois {b[-1][2]:.1f}; maior |dif| {max(abs(x[3]) for x in b):.1f}ms (n_pontos={len(b)})")
else:
    print("  nenhum ponto com |dif|>50ms em 30 eventos")
# mínimo e máximo da mediana móvel por faixa
print("mediana movel: min", round(min(mm),1), "max", round(max(mm),1))
for lim in (448.0,):
    antes = [m for m, t in zip(mm, ts) if t <= lim]
    depois = [m for m, t in zip(mm, ts) if t > lim]
    print(f"  <= {lim}s: n={len(antes)} med_movel mediana={st.median(antes):.1f}; > {lim}s: n={len(depois)} mediana={st.median(depois):.1f}")

# Salva resultados em JSON para o relatório
json.dump({
  "m1": [dict(tela=k[0], exib=k[1], n=n, inclin_ms_s=b, delta_ini_ms=di, delta_fim_ms=df, resid_sd_ms=sd, mediana_ms=med)
         for (k, b, di, df, sd, med, n) in m1],
  "m2": [dict(tela=k[0], exib=k[1], n_int=n, soma_marc_s=sm, soma_som_s=ss, razao=r, mediana_dif_ms=md)
         for (k, n, sm, ss, r, md) in m2],
  "m3": [dict(k1=list(t["k1"]), k2=list(t["k2"]), t_troca=t["t_troca"], int_marc_ms=t["dm"]*1000,
              int_som_ms=t["ds"]*1000, dif_ms=t["dif_ms"], med_antes=t["med_antes"], med_depois=t["med_depois"]) for t in trocas],
  "m5_saltos": saltos,
}, open(OUT+"resultado_json.json","w"), ensure_ascii=False, indent=1)
