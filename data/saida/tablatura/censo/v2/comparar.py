"""Compara o censo antigo com o censo v2 (painel por máscara). NÃO é código do projeto.

Chave de comparação: o campo ``arquivo`` (caminho relativo à raiz do acervo). Quando um
vídeo aparece mais de uma vez, vale a última linha. Status por vídeo:
TAB (tablatura True), SEM (tablatura False), ERRO (registro com ``erro``).

Uso (dentro do container, a partir da raiz do repo):
    python data/saida/censo/v2/comparar.py
"""

import collections
import json
import os
import re

ANTIGO = "data/saida/censo/censo_cache.jsonl"
NOVO = "data/saida/censo/v2/censo_v2_completo.jsonl"
PASTA = "data/saida/censo/v2"
FRACOES = [round(0.05 + k * (0.90 / 11), 3) for k in range(12)]


def carregar(caminho):
    """Lê um JSONL do censo; devolve (linhas, dict arquivo -> último registro)."""
    linhas = 0
    por_arquivo = {}
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            if not linha.strip():
                continue
            linhas += 1
            r = json.loads(linha)
            por_arquivo[r["arquivo"]] = r
    return linhas, por_arquivo


def canais_fora():
    """Canais com ``rollout: fora`` em configs/canais.yaml (parse de texto; sem PyYAML)."""
    fora = set()
    canal = None
    with open("configs/canais.yaml", encoding="utf-8") as fh:
        for linha in fh:
            m = re.match(r'^  "?([^":]+?)"?:\s*$', linha)
            if m:
                canal = m.group(1)
                continue
            if canal and re.match(r"^\s+rollout:\s*fora\b", linha):
                fora.add(canal)
    return fora


def status(r):
    """TAB, SEM ou ERRO para um registro do censo."""
    if "erro" in r:
        return "ERRO"
    return "TAB" if r.get("tablatura") else "SEM"


def duracao(r):
    """Duração do vídeo em segundos (0 se o registro não a tem)."""
    return float((r.get("info") or {}).get("duracao_s") or 0.0)


def main():
    """Escreve comparacao.txt, so_no_antigo.txt, so_no_novo.txt e mudancas.json."""
    fora = canais_fora()
    n_ant, ant = carregar(ANTIGO)
    n_novo, novo = carregar(NOVO)
    comuns = sorted(set(ant) & set(novo))
    so_ant = sorted(set(ant) - set(novo))
    so_novo = sorted(set(novo) - set(ant))
    out = []
    p = out.append

    p("=== CENSO ANTIGO x V2 (painel por máscara) ===")
    p(f"linhas no antigo: {n_ant} | vídeos únicos: {len(ant)}")
    p(f"linhas no v2:     {n_novo} | vídeos únicos: {len(novo)}")
    p(f"em comum: {len(comuns)} | só no antigo: {len(so_ant)} | só no v2: {len(so_novo)}")
    p(f"canais fora do rollout (excluídos dos totais ativos): {sorted(fora)}")
    p("")

    def ativo(canal):
        return canal not in fora

    canais = sorted({r["canal"] for r in list(ant.values()) + list(novo.values())})
    p("=== POR CANAL (ativos) ===")
    p(
        f"{'canal':<34}{'vids_ant':>9}{'vids_v2':>8}"
        f"{'TAB ant->v2':>13}{'SEM ant->v2':>13}{'ERRO ant->v2':>13}"
        f"{'SEM->TAB':>10}{'TAB->SEM':>10}{'so_ant':>8}{'so_v2':>7}"
    )
    tot = collections.Counter()
    for canal in canais:
        if not ativo(canal):
            continue
        a = [r for r in ant.values() if r["canal"] == canal]
        b = [r for r in novo.values() if r["canal"] == canal]
        sa = collections.Counter(status(r) for r in a)
        sb = collections.Counter(status(r) for r in b)
        st = collections.Counter()
        for arq in comuns:
            if novo[arq]["canal"] != canal:
                continue
            x, y = status(ant[arq]), status(novo[arq])
            if x == "SEM" and y == "TAB":
                st["SEM->TAB"] += 1
            if x == "TAB" and y == "SEM":
                st["TAB->SEM"] += 1
        so_a = sum(1 for arq in so_ant if ant[arq]["canal"] == canal)
        so_b = sum(1 for arq in so_novo if novo[arq]["canal"] == canal)
        p(
            f"{canal[:33]:<34}{len(a):>9}{len(b):>8}"
            f"{sa['TAB']:>6}->{sb['TAB']:<6}{sa['SEM']:>6}->{sb['SEM']:<6}"
            f"{sa['ERRO']:>6}->{sb['ERRO']:<6}"
            f"{st['SEM->TAB']:>10}{st['TAB->SEM']:>10}{so_a:>8}{so_b:>7}"
        )
    p("")

    p("=== POR CANAL FORA (só informativo, fora dos totais) ===")
    for canal in sorted(fora):
        a = sum(1 for r in ant.values() if r["canal"] == canal)
        b = sum(1 for r in novo.values() if r["canal"] == canal)
        p(f"{canal}: antigo={a} v2={b}")
    p("")

    # totais ativos
    p("=== TOTAIS (canais ativos) ===")
    for nome, base in (("antigo", ant), ("v2", novo)):
        regs = [r for r in base.values() if ativo(r["canal"])]
        cont = collections.Counter(status(r) for r in regs)
        validos = cont["TAB"] + cont["SEM"]
        h_total = sum(duracao(r) for r in regs) / 3600
        h_tab = sum(duracao(r) for r in regs if status(r) == "TAB") / 3600
        h_eq = (
            sum(
                duracao(r) * float(r.get("frac_tablatura") or 0.0)
                for r in regs
                if status(r) != "ERRO"
            )
            / 3600
        )
        p(
            f"{nome}: vídeos={len(regs)} TAB={cont['TAB']} SEM={cont['SEM']} "
            f"ERRO={cont['ERRO']}"
        )
        p(
            f"   % TAB sobre válidos (TAB+SEM): {100 * cont['TAB'] / max(validos, 1):.1f}%"
            f" | % TAB sobre todos: {100 * cont['TAB'] / max(len(regs), 1):.1f}%"
        )
        p(
            f"   horas totais={h_total:.1f} | horas com TAB (vídeo com >=1 instante "
            f"com TAB)={h_tab:.1f} | horas-equivalentes (duração x frac_tablatura)={h_eq:.1f}"
        )
    p("")

    # instantes (videos em comum)
    p("=== INSTANTES (vídeos em comum; índice k = presenca_KK, 0..11) ===")
    cont_inst = collections.Counter()
    por_canal_inst = collections.defaultdict(collections.Counter)
    por_k = collections.defaultdict(collections.Counter)
    mudancas = []
    for arq in comuns:
        ra, rb = ant[arq], novo[arq]
        if not ativo(rb["canal"]):
            continue
        ia = ra.get("instantes") or []
        ib = rb.get("instantes") or []
        for k in range(min(len(ia), len(ib))):
            ta, tb = ia[k].get("tab"), ib[k].get("tab")
            if ta is None or tb is None:
                cont_inst["sem_quadro_em_algum"] += 1
                continue
            cont_inst["comparados"] += 1
            if ta == tb:
                continue
            if not ta and tb:
                cont_inst["SEM->TAB"] += 1
                por_canal_inst[rb["canal"]]["SEM->TAB"] += 1
                por_k[k]["SEM->TAB"] += 1
                sentido = "SEM->TAB"
            else:
                cont_inst["TAB->SEM"] += 1
                por_canal_inst[rb["canal"]]["TAB->SEM"] += 1
                por_k[k]["TAB->SEM"] += 1
                sentido = "TAB->SEM"
            mudancas.append(
                {
                    "arquivo": arq,
                    "canal": rb["canal"],
                    "chave": rb["chave"],
                    "k": k,
                    "t": ib[k]["t"],
                    "sentido": sentido,
                    "rect_antigo": ia[k].get("rect"),
                    "rect_novo": ib[k].get("rect"),
                }
            )
    p(
        f"instantes comparados: {cont_inst['comparados']} | "
        f"sem quadro em algum dos dois: {cont_inst['sem_quadro_em_algum']}"
    )
    p(f"SEM->TAB: {cont_inst['SEM->TAB']} | TAB->SEM: {cont_inst['TAB->SEM']}")
    p("por canal (SEM->TAB / TAB->SEM):")
    for canal in sorted(por_canal_inst):
        c = por_canal_inst[canal]
        p(f"   {canal}: {c['SEM->TAB']} / {c['TAB->SEM']}")
    p("por índice k (SEM->TAB / TAB->SEM):")
    for k in sorted(por_k):
        p(f"   k={k:02d} (frac {FRACOES[k]}): {por_k[k]['SEM->TAB']} / {por_k[k]['TAB->SEM']}")
    p("")

    with open(os.path.join(PASTA, "comparacao.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    with open(os.path.join(PASTA, "so_no_antigo.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(so_ant) + "\n")
    with open(os.path.join(PASTA, "so_no_novo.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(so_novo) + "\n")
    with open(os.path.join(PASTA, "mudancas.json"), "w", encoding="utf-8") as fh:
        json.dump(mudancas, fh, ensure_ascii=False, indent=0)
    print("\n".join(out))


if __name__ == "__main__":
    main()
