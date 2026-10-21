"""Caixa do recorte com e sem exigir cobertura da estrutura vizinha.

Para cada recorte já gravado (gabarito R01–R21, recortes dos produtos e do piloto sem
produto), relê o quadro, refaz ``processar_quadro`` e compara a caixa da mesma pauta
(mesmos ``ys``) entre a regra atual e a regra com cobertura mínima.
"""
import json
import sys

import numpy as np

import tab.partitura_recortes as pr
from tab.caminhos import SAIDA, acervo
from tab.leitor import quadro_em

LIMIARES = [0.5, 0.6, 0.7, 0.8]
original = pr.estruturas_horizontais


def com_cobertura(quadro):
    """Estruturas e a cobertura de cada uma (colunas com tinta / extensão)."""
    cinza = pr._cinza(quadro)
    escura, clara = pr._mascaras_de_tinta(cinza)
    aberta = pr._abrir(escura if pr._tinta_escura(cinza) else clara, cinza.shape[1])
    contagem = np.count_nonzero(aberta, axis=1)
    linhas = np.flatnonzero(contagem >= pr.FRAC_FRACA * cinza.shape[1])
    saida = []
    for (inicio, fim), s in zip(pr._sequencias(linhas), original(quadro), strict=True):
        tinta = aberta[inicio : fim + 1].any(axis=0)[s.x0 : s.x1 + 1]
        saida.append((s, np.count_nonzero(tinta) / (s.x1 - s.x0 + 1)))
    return saida


def caixas(fonte, quadro, limiar):
    """``{ys: caixa}`` de cada pauta do quadro com o limiar (None = regra atual)."""
    if limiar is None:
        pr.estruturas_horizontais = original
    else:
        pr.estruturas_horizontais = lambda q: [
            s for s, c in com_cobertura(q) if c >= limiar
        ]
    entradas, _, _ = pr.processar_quadro(fonte, quadro, "video", 1, 7.0, 7.0)
    pr.estruturas_horizontais = original
    return {tuple(e["ys"]): e["caixa_recorte"] for e in entradas if not e["sem_pauta"]}


def itens():
    """(grupo, id, entrada) de todos os índices de recortes."""
    p = SAIDA / "partitura"
    for e in json.loads((p / "p1/recortes_margem/indice.json").read_text()):
        if not e["sem_pauta"]:
            yield "gabarito", e["id"], e
    for f in sorted((p / "video").glob("*/recortes/indice.json")):
        for e in json.loads(f.read_text()):
            if not e.get("sem_pauta") and "video" in e:
                yield "produto", f"{f.parts[-3][:12]}/{e['id']}", e
    for f in sorted((p / "sem_produto").glob("*/recortes/indice.json")):
        for e in json.loads(f.read_text()):
            if not e.get("sem_pauta"):
                yield "sem_produto", f"{f.parts[-3][:12]}/{e['id']}", e


cache = {}
resumo = {}
for grupo, rid, e in itens():
    chave = (e["video"], e["t"])
    if chave not in cache:
        quadro = quadro_em(str(acervo() / e["video"]), e["t"])
        fonte = pr.FonteQuadro(origem="video", canal="", video=e["video"], t=e["t"])
        cache.clear()
        cache[chave] = {
            lim: caixas(fonte, quadro, lim) for lim in [None, *LIMIARES]
        }
    por = cache[chave]
    ys = tuple(e["ys"])
    atual = por[None].get(ys)
    r = resumo.setdefault(grupo, {"n": 0, "reproduz": 0, **{l: 0 for l in LIMIARES}})
    r["n"] += 1
    if atual == e["caixa_recorte"]:
        r["reproduz"] += 1
    else:
        print(f"NÃO REPRODUZ {grupo} {rid}: gravada {e['caixa_recorte']} refeita {atual}")
    for lim in LIMIARES:
        nova = por[lim].get(ys)
        if nova != atual:
            r[lim] += 1
            print(f"{lim} {grupo} {rid}: ys0 {ys[0]} ys4 {ys[4]} {atual} -> {nova}")
    sys.stdout.flush()
for g, r in resumo.items():
    print(g, r)
