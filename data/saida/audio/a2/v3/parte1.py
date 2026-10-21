"""Parte 1 (medição): o que distingue colunas que o marcador NUNCA acende.

Só lê o produto e o alinhado v2 do MVP. Não altera nada do alinhador.
Saídas: data/saida/audio/a2/v3/parte1.json e recortes PNG (ver recortes()).
"""

import collections
import json
import statistics as st

PRODUTO = "data/saida/conserto_v2/mvp.json"
ALINHADO = "data/saida/audio/a2/alinhado_v2_r1.json"
REGUA = "data/saida/audio/a1/atraso_mvp.json"
SAIDA = "data/saida/audio/a2/v3/parte1.json"


def colunas_do_produto(p):
    """(tela, coluna) -> dados medidos: notas, t_ini, confiança, x do centro."""
    por = collections.defaultdict(list)
    for n in p["notas"]:
        por[(n["tela"], n["coluna"])].append(n)
    passo = {t["id"]: t["passo"] for t in p["telas"]}
    nao = collections.defaultdict(list)
    for m in p["nao_notas"]:
        nao[m["tela"]].append(m)
    out = {}
    for (tela, col), notas_brutas in por.items():
        # Uma coluna aparece em mais de uma exibição (telas com 2 exibições): dedup por (corda, casa).
        unicas = {}
        for n in notas_brutas:
            unicas.setdefault((n["corda"], n["casa"]), n)
        notas = list(unicas.values())
        xc = st.mean(n["x_centro_quadro"] for n in notas)
        out[(tela, col)] = {
            "tela": tela,
            "coluna": col,
            "notas": sorted((n["corda"], n["casa"]) for n in notas),
            "marcador_acende": any(n["t_ini"] is not None for n in notas_brutas),
            "confianca_min": min(n["confianca"] for n in notas),
            "confianca_media": st.mean(n["confianca"] for n in notas),
            "x_centro": xc,
            "passo": passo[tela],
            "cordas": sorted({n["corda"] for n in notas}),
        }
    for k, d in out.items():
        tela, col = k
        anteriores = sorted(c for (t, c) in out if t == tela and c < col)
        if anteriores:
            ant = out[(tela, anteriores[-1])]
            d["coluna_anterior"] = ant["coluna"]
            d["notas_anterior"] = ant["notas"]
            d["dist_passos"] = (d["x_centro"] - ant["x_centro"]) / d["passo"]
            d["nota_repetida"] = bool(set(d["notas"]) & set(ant["notas"]))
        else:
            d["coluna_anterior"] = None
            d["notas_anterior"] = None
            d["dist_passos"] = None
            d["nota_repetida"] = False
        # nao_notas perto: na mesma corda, centro à esquerda (até 1 passo) e em volta
        perto_esq = []
        perto_larg = []
        for m in nao[tela]:
            if m["corda"] not in d["cordas"]:
                continue
            dx = (m["x_centro_quadro"] - d["x_centro"]) / d["passo"]
            if -1.0 <= dx <= 0.0:
                perto_esq.append(m["classe"])
            if -1.5 <= dx <= 0.5:
                perto_larg.append(m["classe"])
        d["nao_notas_chegando_1passo_esq"] = perto_esq
        d["nao_notas_em_volta"] = perto_larg
    return out


def tabela(nunca, acesas, rotulo, fn):
    """Tabela X de Y nunca acesas × X de Y acesas, para um predicado."""
    x = sum(1 for d in nunca if fn(d))
    y = sum(1 for d in acesas if fn(d))
    return f"{rotulo}: {x} de {len(nunca)} nunca acesas | {y} de {len(acesas)} acesas"


def main():
    p = json.load(open(PRODUTO, encoding="utf-8"))
    alin = json.load(open(ALINHADO, encoding="utf-8"))
    regua = json.load(open(REGUA, encoding="utf-8"))
    dados = colunas_do_produto(p)
    nunca = [d for d in dados.values() if not d["marcador_acende"]]
    acesas = [d for d in dados.values() if d["marcador_acende"]]
    print("nunca acesas (marcador sem t_ini):", sorted((d["tela"], d["coluna"]) for d in nunca))
    print("total colunas com notas:", len(dados), "| nunca:", len(nunca), "| acesas:", len(acesas))

    # Lista da régua: colunas do trecho alinhador sem par na régua naquela exibição
    regua_chaves = {(e["tela"], e["exibicao"], e["coluna"]) for e in regua["eventos"]}
    sem_par = []
    for ex in alin["exibicoes"]:
        if not ex.get("trecho_colunas"):
            continue
        a, b = ex["trecho_colunas"]
        for c in alin["colunas"]:
            if c["tela"] != ex["tela"] or c["exibicao"] != ex["exibicao"]:
                continue
            if a <= c["coluna"] <= b and (c["tela"], c["exibicao"], c["coluna"]) not in regua_chaves:
                sem_par.append((c["tela"], c["exibicao"], c["coluna"]))
    print("trecho sem par na régua (tela, exib, col):", sorted(sem_par))
    marc = {(d["tela"], d["coluna"]): d["marcador_acende"] for d in dados.values()}
    print("  destes, sem marcador (nunca):", sorted({(t, c) for t, _, c in sem_par if marc.get((t, c)) is False}))
    print("  destes, com marcador (acesas):", sorted({(t, c) for t, _, c in sem_par if marc.get((t, c)) is True}))

    feats = [
        ("(a) nota repetida (mesma corda e casa da coluna anterior)", lambda d: d["nota_repetida"]),
        ("(a) acorde (2 ou mais notas)", lambda d: len(d["notas"]) >= 2),
        ("(a) so corda 1", lambda d: d["cordas"] == [1]),
        ("(b) nao_nota chegando <=1 passo a esq. na mesma corda", lambda d: len(d["nao_notas_chegando_1passo_esq"]) > 0),
        ("(b) nao_nota em volta (-1,5..+0,5 passo) na mesma corda", lambda d: len(d["nao_notas_em_volta"]) > 0),
        ("(c) distancia a coluna anterior <= 1,0 passo", lambda d: d["dist_passos"] is not None and d["dist_passos"] <= 1.0),
        ("(c) distancia a coluna anterior > 1,5 passo", lambda d: d["dist_passos"] is not None and d["dist_passos"] > 1.5),
        ("(d) confianca minima < 0,90", lambda d: d["confianca_min"] < 0.90),
    ]
    linhas = []
    for rot, fn in feats:
        linha = tabela(nunca, acesas, rot, fn)
        print(linha)
        linhas.append(linha)
    print("classes em volta das nunca acesas:", collections.Counter(c for d in nunca for c in d["nao_notas_em_volta"]))
    print("classes em volta das acesas:", collections.Counter(c for d in acesas for c in d["nao_notas_em_volta"]))
    print("dist_passos nunca:", sorted(round(d["dist_passos"], 2) for d in nunca if d["dist_passos"] is not None))
    print("dist_passos acesas (mediana, p10, p90):", round(st.median(d["dist_passos"] for d in acesas if d["dist_passos"] is not None), 2))
    saida = {
        "nunca": [d for d in nunca],
        "acesas_n": len(acesas),
        "tabela": linhas,
        "sem_par_trecho": sorted(sem_par),
    }
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1, sort_keys=True, default=str)
        f.write("\n")
    return dados, nunca, acesas


if __name__ == "__main__":
    main()
