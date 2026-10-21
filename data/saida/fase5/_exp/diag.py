"""Diagnostico da Fase 5 (so medicao): cada observador contra os instantes do ouro."""

import json
import sys

sys.path.insert(0, "/app")

from tab import video as V  # noqa: E402

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
OURO = "/app/data/gold/ouro_video/retrato_brasileiro_v2.json"
NOMES = ("posicao", "cor", "cor_acende")

exib = []  # uma entrada por exibicao, na ordem das medicoes
_medir_orig = V.medir_exibicao
_escolher_orig = V.escolher_observador
_ctx = {}


def _medir(video, t0, t1, recorte_y, centros, caixas, passo):
    _ctx["centros"], _ctx["passo"] = centros, passo
    return _medir_orig(video, t0, t1, recorte_y, centros, caixas, passo)


def _escolher(obs):
    exib.append({"obs": obs, "centros": _ctx["centros"], "passo": _ctx["passo"]})
    return _escolher_orig(obs)


V.QPS_EXIBICAO = 12.0
V.ESTAVEL_EXIBICAO = 2
V.medir_exibicao = _medir
V.escolher_observador = _escolher

dados = V.transcrever_video(VIDEO)
json.dump(dados, open("/app/data/saida/fase5/diag_dados.json", "w"),
          ensure_ascii=False, default=str)
ouro = json.load(open(OURO, encoding="utf-8"))
ex_t = [(e for e in dados["telas"][0]["exibicoes"])]  # so para checar formato
TEL = dados["telas"]
# ordem das exibicoes medidas = ordem das telas e das exibicoes (ler_tela)
lista = []
for t in TEL:
    for ex in t["exibicoes"]:
        lista.append((t["id"], ex["t0"], ex["t1"]))
assert len(lista) == len(exib), (len(lista), len(exib))

print(f"{'tela':>4} {'t0':>8} {'t1':>8} {'escolh':>10} | "
      + " | ".join(f"{n:>22}" for n in NOMES) + " | passagens")
for (tid, t0, t1), e in zip(lista, exib, strict=True):
    o = e["obs"]
    cols = " | ".join(
        f"cov{o[n].cobertura:.2f} coe{o[n].coerencia:.2f} tr{o[n].transicoes:>3}"
        for n in NOMES
    )
    print(f"{tid:>4} {t0:8.2f} {t1:8.2f} {'-':>10} | {cols} | "
          f"{len(o['posicao'].passagens)}/{len(o['cor'].passagens)}/"
          f"{len(o['cor_acende'].passagens)}")

print("\nOURO: instante -> observador, centro da coluna acesa vs ouro (tol 0,5 passo)")
acertos = {n: 0 for n in NOMES}
total = 0
for inst in ouro["instantes"]:
    t = float(inst["t"])
    alvo = inst["coluna_x_quadro"]
    idx = [i for i, (tid, a, b) in enumerate(lista) if a <= t <= b]
    if not idx:
        print(f"t={t}: fora de toda exibicao medida")
        continue
    i = idx[0]
    e = exib[i]
    total += 1
    linha = []
    for n in NOMES:
        ob = e["obs"][n]
        ult = [c for c in ob.corridas if c.t_ini <= t]
        if not ult:
            linha.append(f"{n}=sem")
            continue
        c = ult[-1]
        cx = e["centros"][c.coluna]
        ok = abs(cx - alvo) <= 0.5 * e["passo"]
        acertos[n] += ok
        linha.append(f"{n}={'OK' if ok else 'x'}({cx:.0f}/{alvo:.0f},t{c.t_ini:.2f})")
    esc, _ = V.escolher_observador(e["obs"])
    print(f"t={t:6.1f} tela={inst['tela']:>2} esc={esc} " + "  ".join(linha))
print("acertos por observador (ouro): " + ", ".join(f"{n} {acertos[n]} de {total}" for n in NOMES))
