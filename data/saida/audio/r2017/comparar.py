"""Rodada 2017: antigo (leitor de glifos) contra novo (leitor rede), mesmo alinhador v2.1.

Roda na imagem base (importa ``tab.audio_produto`` para o alarme de leitura, com a mesma regra
nos dois lados). Medidas e critérios: ``docs/rodadas/2017-regressao-com-o-leitor-rede.md``.

Uso: ``python data/saida/audio/r2017/comparar.py`` (grava ``comparacao.json`` e imprime as
tabelas).
"""

import collections
import json
import statistics
from pathlib import Path

from tab.audio_produto import _linhas_exibicoes

R = Path("data/saida/audio/r2017")
GOLD = Path("data/gold/audio")
LISTA = json.loads((R / "lista.json").read_text("utf-8"))

SOBREPOSICAO_MIN = 0.5
FRACAO_PASSO_COLUNA = 0.5
TOL_PAR_S = 0.030
MANTIDA_S = 0.050
MOVIDA_S = 0.100


def ler(caminho):
    """JSON do caminho, ou None se não existe."""
    p = Path(caminho)
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def sobreposicao(a, b):
    """Segundos de interseção entre dois intervalos ``(t0, t1)``."""
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def centros_colunas(produto):
    """``{(tela, coluna): x}``: mediana de ``x_centro_quadro`` das notas da coluna."""
    xs = collections.defaultdict(list)
    for n in produto["notas"]:
        xs[(int(n["tela"]), int(n["coluna"]))].append(float(n["x_centro_quadro"]))
    for n in produto.get("nao_notas", []):
        chave = (int(n["tela"]), int(n["coluna"]))
        if chave not in xs and n.get("x_centro_quadro") is not None:
            xs.setdefault(("nn",) + chave, []).append(float(n["x_centro_quadro"]))
    centros = {k: statistics.median(v) for k, v in xs.items() if k[0] != "nn"}
    for k, v in xs.items():
        if k[0] == "nn" and k[1:] not in centros:
            centros[k[1:]] = statistics.median(v)
    return centros


def mapa_telas(antigo, novo):
    """``{tela_antiga: (tela_nova, {exib_antiga: exib_nova})}`` por sobreposição no tempo."""
    mapa = {}
    for ta in antigo["telas"]:
        exa = [(float(e["t0"]), float(e["t1"])) for e in ta["exibicoes"]]
        dur = sum(t1 - t0 for t0, t1 in exa)
        melhor, melhor_s = None, 0.0
        for tn in novo["telas"]:
            exn = [(float(e["t0"]), float(e["t1"])) for e in tn["exibicoes"]]
            s = sum(sobreposicao(a, b) for a in exa for b in exn)
            if s > melhor_s:
                melhor, melhor_s = tn, s
        if melhor is None or dur <= 0 or melhor_s < SOBREPOSICAO_MIN * dur:
            continue
        exn = [(float(e["t0"]), float(e["t1"])) for e in melhor["exibicoes"]]
        exibs = {}
        for i, a in enumerate(exa):
            s = [sobreposicao(a, b) for b in exn]
            j = max(range(len(s)), key=s.__getitem__) if s else None
            if j is not None and s[j] >= SOBREPOSICAO_MIN * (a[1] - a[0]):
                exibs[i] = j
        mapa[int(ta["id"])] = (int(melhor["id"]), exibs)
    return mapa


def mapa_colunas(antigo, novo, telas):
    """``{(tela_a, coluna_a): (tela_n, coluna_n)}``: centro mais perto, a até 0,5 passo."""
    ca, cn = centros_colunas(antigo), centros_colunas(novo)
    validos = [float(t["passo"]) for t in antigo["telas"] if t.get("passo")]
    passo_video = statistics.median(validos) if validos else 20.0
    passo = {
        int(t["id"]): float(t["passo"]) if t.get("passo") else passo_video
        for t in antigo["telas"]
    }
    por_tela_n = collections.defaultdict(list)
    for (t, c), x in cn.items():
        por_tela_n[t].append((c, x))
    mapa = {}
    for (t, c), x in ca.items():
        if t not in telas:
            continue
        tn = telas[t][0]
        cand = por_tela_n.get(tn, [])
        if not cand:
            continue
        cbest, xbest = min(cand, key=lambda cx: abs(cx[1] - x))
        if abs(xbest - x) <= FRACAO_PASSO_COLUNA * passo[t]:
            mapa[(t, c)] = (tn, cbest)
    return mapa


def tempos(alinhado):
    """``{(tela, exibicao, coluna): t_audio ou None}``."""
    return {
        (int(c["tela"]), int(c["exibicao"]), int(c["coluna"])): c["t_audio"]
        for c in alinhado["colunas"]
    }


def resumo_alinhado(alinhado):
    """Colunas, colunas com tempo, exibições, recusadas e alarmes (regra atual)."""
    linhas = _linhas_exibicoes(alinhado)
    n = len(alinhado["colunas"])
    com = sum(1 for c in alinhado["colunas"] if c["t_audio"] is not None)
    return {
        "colunas": n,
        "com_tempo": com,
        "fracao": round(com / n, 4) if n else None,
        "exibicoes": len(linhas),
        "recusadas": sum(e["recusada"] for e in linhas),
        "alarmes": sum(e["alarme_leitura"] for e in linhas),
    }


def pares_som_marcador(produto, alinhado):
    """Igual à rodada 2016: ``t_audio - t_ini`` por coluna (1ª passagem, mediana)."""
    grupos = collections.defaultdict(list)
    for n in produto.get("notas", []):
        if n.get("t_ini") is None or n.get("exibicao") is None:
            continue
        grupos[(n["tela"], n["exibicao"], n["coluna"])].append(n)
    t_ini = {}
    for chave, notas in grupos.items():
        primeira = min(n.get("passagem") or 1 for n in notas)
        valores = [n["t_ini"] for n in notas if (n.get("passagem") or 1) == primeira]
        t_ini[chave] = statistics.median(valores)
    pares = []
    for c in alinhado.get("colunas", []):
        if c.get("t_audio") is None:
            continue
        chave = (c["tela"], c["exibicao"], c["coluna"])
        if chave in t_ini:
            pares.append(c["t_audio"] - t_ini[chave])
    if not pares:
        return {"n": 0, "mediana_ms": None, "ate_100_ms": None}
    med = statistics.median(pares)
    dif = [abs(d - med) * 1000 for d in pares]
    return {
        "n": len(pares),
        "mediana_ms": round(med * 1000, 1),
        "ate_100_ms": round(sum(x <= 100 for x in dif) / len(dif), 4),
    }


def chave_nova(chave, telas, colunas):
    """Chave ``(tela, exibicao, coluna)`` nova da chave antiga, ou None."""
    t, e, c = chave
    if t not in telas or (t, c) not in colunas or e not in telas[t][1]:
        return None
    tn, cn = colunas[(t, c)]
    return (tn, telas[t][1][e], cn)


def comparar_pares(ta, tn, telas, colunas):
    """Pares de colunas correspondentes e o que mudou no tempo."""
    pares = ambos = ate30 = perdeu = ganhou = sem_par = 0
    difs = []
    for chave, t_old in ta.items():
        nova = chave_nova(chave, telas, colunas)
        if nova is None or nova not in tn:
            sem_par += 1
            continue
        pares += 1
        t_new = tn[nova]
        if t_old is not None and t_new is not None:
            ambos += 1
            d = abs(t_new - t_old)
            difs.append(d)
            ate30 += d <= TOL_PAR_S
        elif t_old is not None:
            perdeu += 1
        elif t_new is not None:
            ganhou += 1
    return {
        "colunas_antigas": len(ta),
        "sem_par": sem_par,
        "pares": pares,
        "ambos_com_tempo": ambos,
        "ate_30ms": ate30,
        "fracao_ate_30ms": round(ate30 / ambos, 4) if ambos else None,
        "perdeu_tempo": perdeu,
        "ganhou_tempo": ganhou,
        "dif_p90_ms": round(sorted(difs)[int(0.9 * (len(difs) - 1))] * 1000, 1)
        if difs
        else None,
    }


def pontos_do_gabarito():
    """Pontos certos e errados das folhas 1 a 3, sem repetição, por vídeo."""
    pontos = {}
    for nome in ("folha1", "folha2"):
        for it in json.loads((GOLD / f"{nome}.json").read_text("utf-8"))["itens"]:
            if it.get("controle"):
                continue
            tipo = {"certo": "certo", "errado": "errado"}.get(it["resposta_dono"])
            if tipo is None:
                continue
            chave = (it["video"], int(it["tela"]), int(it["exibicao"]), int(it["coluna"]))
            pontos.setdefault(chave, (tipo, float(it["t_clique"]), it["id"]))
    for it in json.loads((GOLD / "folha3.json").read_text("utf-8"))["itens"]:
        if it.get("escolheu") != "alinhador" or abs(int(it["d_ms"])) < 100:
            continue
        chave = (it["video"], int(it["tela"]), int(it["exibicao"]), int(it["coluna"]))
        pontos.setdefault(chave, ("certo", float(it["t_alinhador"]), it["id"]))
    return pontos


def julgar_pontos(video, ta, tn, telas, colunas, pontos):
    """Classe de cada ponto do gabarito deste vídeo no alinhamento antigo e no novo."""
    saida = []
    for (v, t, e, c), (tipo, t_ref, ident) in sorted(pontos.items()):
        if v != video:
            continue
        chave = (t, e, c)
        t_old = ta.get(chave)
        nova = chave_nova(chave, telas, colunas)
        t_new = tn.get(nova) if nova is not None else None

        def classe(tt, existe):
            if not existe:
                return "sem_par"
            if tt is None:
                return "recusada"
            d = abs(tt - t_ref)
            if d <= MANTIDA_S:
                return "mantida"
            if d <= MOVIDA_S:
                return "movida"
            return "fora"

        saida.append(
            {
                "id": ident,
                "tipo": tipo,
                "chave_antiga": chave,
                "chave_nova": nova,
                "t_ref": t_ref,
                "t_antigo": t_old,
                "t_novo": t_new,
                "classe_antiga": classe(t_old, chave in ta),
                "classe_nova": classe(t_new, nova is not None and nova in tn),
            }
        )
    return saida


def contar_x(produto):
    """``nao_notas`` de classe ``x`` (o X do rasgueado no leitor rede)."""
    return sum(1 for n in produto.get("nao_notas", []) if n.get("classe") == "x")


def main():
    """Compara os 23 vídeos e grava ``comparacao.json``."""
    pontos = pontos_do_gabarito()
    resultado = []
    for item in LISTA:
        ap = item["apelido"]
        pa, aa = ler(item["produto_antigo"]), ler(item["alinhado_antigo"])
        pn, an = ler(R / "produtos" / f"{ap}.json"), ler(R / f"alinhado_{ap}.json")
        linha = {"apelido": ap, "grupo": item["grupo"], "video": item["video"]}
        if pn is None or an is None:
            linha["faltando"] = True
            resultado.append(linha)
            continue
        telas = mapa_telas(pa, pn)
        colunas = mapa_colunas(pa, pn, telas)
        ta, tn = tempos(aa), tempos(an)
        linha.update(
            {
                "notas": [len(pa["notas"]), len(pn["notas"])],
                "telas": [len(pa["telas"]), len(pn["telas"])],
                "telas_casadas": len(telas),
                "antigo": resumo_alinhado(aa),
                "novo": resumo_alinhado(an),
                "pares": comparar_pares(ta, tn, telas, colunas),
                "marcador": [pares_som_marcador(pa, aa), pares_som_marcador(pn, an)],
                "x_rasgueado_novo": contar_x(pn),
                "gabarito": julgar_pontos(item["video"], ta, tn, telas, colunas, pontos),
            }
        )
        resultado.append(linha)
    (R / "comparacao.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), "utf-8"
    )
    imprimir(resultado)


def imprimir(resultado):
    """Tabelas em texto: colunas, pares, marcador e gabarito."""
    print("apelido | notas a/n | colunas c/tempo antigo | novo | Δpp | recus a/n | alarm a/n")
    for r in resultado:
        if r.get("faltando"):
            print(f"{r['apelido']} | FALTANDO")
            continue
        a, n = r["antigo"], r["novo"]
        dpp = (n["fracao"] - a["fracao"]) * 100
        print(
            f"{r['apelido']} [{r['grupo']}] | {r['notas'][0]}/{r['notas'][1]} | "
            f"{a['com_tempo']}/{a['colunas']} ({a['fracao']:.3f}) | "
            f"{n['com_tempo']}/{n['colunas']} ({n['fracao']:.3f}) | {dpp:+.1f} | "
            f"{a['recusadas']}/{a['exibicoes']} → {n['recusadas']}/{n['exibicoes']} | "
            f"{a['alarmes']} → {n['alarmes']}"
        )
    print()
    print("apelido | telas a/n casadas | sem par | pares | ambos | ≤30ms | perdeu | ganhou | p90 ms")
    for r in resultado:
        if r.get("faltando"):
            continue
        p = r["pares"]
        print(
            f"{r['apelido']} | {r['telas'][0]}/{r['telas'][1]} {r['telas_casadas']} | "
            f"{p['sem_par']} | {p['pares']} | {p['ambos_com_tempo']} | {p['ate_30ms']} "
            f"({p['fracao_ate_30ms']}) | {p['perdeu_tempo']} | {p['ganhou_tempo']} | "
            f"{p['dif_p90_ms']}"
        )
    print()
    print("som × marcador: apelido | antigo n, med, ≤100 | novo n, med, ≤100")
    for r in resultado:
        if r.get("faltando"):
            continue
        a, n = r["marcador"]
        if a["n"] or n["n"]:
            print(
                f"{r['apelido']} | {a['n']}, {a['mediana_ms']}, {a['ate_100_ms']} | "
                f"{n['n']}, {n['mediana_ms']}, {n['ate_100_ms']}"
            )
    print()
    print("gabarito: apelido | tipo | antiga → nova (contagem)")
    for r in resultado:
        if r.get("faltando") or not r["gabarito"]:
            continue
        cont = collections.Counter(
            (g["tipo"], g["classe_antiga"], g["classe_nova"]) for g in r["gabarito"]
        )
        for (tipo, ca, cn), k in sorted(cont.items()):
            print(f"{r['apelido']} | {tipo} | {ca} → {cn} | {k}")
    print()
    print("X do rasgueado (classe x) nos produtos novos:")
    print({r["apelido"]: r["x_rasgueado_novo"] for r in resultado if not r.get("faltando")})


if __name__ == "__main__":
    main()
