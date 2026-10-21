"""Mede colunas abafadas (rasgueado) nos 14 produtos. Só lê JSON.

Regra final (validada no passo 1): coluna abafada = (tela, coluna) com ao menos
4 ``nao_notas`` de classe ``tecnica`` em cordas distintas, sem nota na mesma
(tela, coluna), e ao menos 4 desses glifos com top-1 ``"15"``. A regra de 3 cordas
(linha de base) é impressa só para comparação.
"""

import json
import statistics
from collections import Counter, defaultdict

RAIZ = "/var/home/gabriel/Projects/chorinho-dataset"
L1 = f"{RAIZ}/data/saida/audio/a4/lote1"
A2P = f"{RAIZ}/data/saida/audio/a2/produtos"

VIDEOS = {
    "mvp": f"{RAIZ}/data/saida/conserto_v2/mvp.json",
    "iwaki_la_vie_en_rose": f"{A2P}/iwaki_la_vie_en_rose.json",
    "kimny_from_this_place": f"{A2P}/kimny_from_this_place.json",
    "shin_izumi_room_335": f"{A2P}/shin_izumi_room_335.json",
}
for _ap in json.load(open(f"{L1}/apelidos.json")):
    VIDEOS[_ap] = f"{L1}/{_ap}.json"

BOAS = [
    "mvp", "iwaki_la_vie_en_rose", "kimny_from_this_place", "iwaki_michelle",
    "iwaki_fly_me_to_the_moon", "kimny_gunjo", "kimny_bach_prelude",
    "shin_izumi_dream_wish", "paolo_those_who_wait",
]


def top1(nao_nota):
    """Top-1 do classificador de glifo, ou None se ausente."""
    simbolo = nao_nota.get("simbolo_cru") or {}
    top3 = simbolo.get("top3") or [[None]]
    return top3[0][0]


def candidatas(produto, min_cordas=4, min_quinze=4):
    """Colunas abafadas: dict (tela, coluna) -> cordas, pela regra."""
    notas_pos = {(int(n["tela"]), int(n["coluna"])) for n in produto["notas"]}
    grupos = defaultdict(list)
    for n in produto["nao_notas"]:
        if n.get("classe") == "tecnica":
            grupos[(int(n["tela"]), int(n["coluna"]))].append(n)
    saida = {}
    for chave, lista in grupos.items():
        if chave in notas_pos:
            continue
        cordas = sorted({int(n["corda"]) for n in lista})
        quinze = sum(1 for n in lista if top1(n) == "15")
        if len(cordas) >= min_cordas and quinze >= min_quinze:
            saida[chave] = cordas
    return saida


def candidatas_base(produto):
    """Linha de base (3 cordas, sem exigir top-1 15), só para comparação."""
    return candidatas(produto, min_cordas=3, min_quinze=0)


def main():
    print("Regra final: >=4 cordas tecnica distintas, sem nota na coluna, >=4 glifos top-1 '15'")
    cab = (
        f"{'video':24}{'tecn':>6}{'tec_c/nota':>11}{'base3':>7}{'abaf':>6}"
        f"{'telas':>7}{'tel_c/abaf':>11}{'frac_max':>10}{'frac_med':>10}"
    )
    print(cab)
    tabela = {}
    for ap, caminho in VIDEOS.items():
        p = json.load(open(caminho))
        tecnicas = [n for n in p["nao_notas"] if n.get("classe") == "tecnica"]
        notas_pos = {(int(n["tela"]), int(n["coluna"])) for n in p["notas"]}
        colunas = defaultdict(set)
        for n in p["notas"] + p["nao_notas"]:
            colunas[int(n["tela"])].add(int(n["coluna"]))
        cand = candidatas(p)
        base = candidatas_base(p)
        por_tela = Counter(t for t, _ in cand)
        fracs = [por_tela.get(t, 0) / len(c) for t, c in colunas.items()]
        r = {
            "tecnicas": len(tecnicas),
            "tec_em_nota": sum(
                1 for n in tecnicas if (int(n["tela"]), int(n["coluna"])) in notas_pos
            ),
            "base3": len(base),
            "abafadas": len(cand),
            "telas": len(colunas),
            "telas_com": sum(1 for t in colunas if por_tela.get(t, 0) > 0),
            "frac_max": max(fracs),
            "frac_med": statistics.median(fracs),
            "cand": cand,
        }
        tabela[ap] = r
        print(
            f"{ap:24}{r['tecnicas']:>6}{r['tec_em_nota']:>11}{r['base3']:>7}"
            f"{r['abafadas']:>6}{r['telas']:>7}{r['telas_com']:>11}"
            f"{r['frac_max']:>10.3f}{r['frac_med']:>10.3f}"
        )
    print("\nOs 9 bons: abafadas =", {a: tabela[a]["abafadas"] for a in BOAS})
    print("\nAmostra campanitas tela 10 (tela, coluna, cordas):")
    amostra = [(k, v) for k, v in sorted(tabela["transcriptor_campanitas"]["cand"].items()) if k[0] == 10]
    for (tela, coluna), cordas in amostra[:10]:
        print(f"  tela={tela} coluna={coluna} cordas={cordas}")
    camp = json.load(open(VIDEOS["transcriptor_campanitas"]))
    notas_t10 = sorted({int(n["coluna"]) for n in camp["notas"] if int(n["tela"]) == 10})
    print("\nColunas de NOTA da tela 10:", notas_t10[:20])
    print("Colunas ABAFADAS da tela 10:", sorted(c for (t, c) in tabela["transcriptor_campanitas"]["cand"] if t == 10)[:20])
    print("Interseção (deve ser vazia):", set(notas_t10) & {c for (t, c) in tabela["transcriptor_campanitas"]["cand"] if t == 10})


if __name__ == "__main__":
    main()
