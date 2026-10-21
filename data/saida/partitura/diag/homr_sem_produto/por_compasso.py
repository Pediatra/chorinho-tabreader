"""Clique de faltando x acréscimo do homr, por compasso e degrau (rodada 3024).

Acréscimo do homr = nota do homr que sobra na diferença de multiconjuntos de degraus
(homr menos Audiveris) dentro do mesmo compasso. Clique = compasso pela posição x entre
as barras do Audiveris (``compassos[].x_quadro`` do documento) e degrau pela posição y.
Recuperado = clique com acréscimo no mesmo compasso e degrau (um a um; com folga de ±1).
"""
import json
import re
from collections import Counter
from pathlib import Path

from tab.partitura_gabarito import _e_nota, ler_partitura

SP = Path("data/saida/partitura/sem_produto")
DH = Path("data/saida/partitura/diag/homr_sem_produto/homr")
GAB = json.loads(Path("data/gold/partitura/leitura_sem_produto.json").read_text("utf-8"))
LETRAS = "CDEFGAB"
SI4 = 4 * 7 + 6


def diatonico(nome: str) -> int:
    """Índice diatônico (C0 = 0) de um nome como ``Bb4``."""
    casa = re.fullmatch(r"([A-G])[#b]*(-?\d+)", nome)
    return int(casa.group(2)) * 7 + LETRAS.index(casa.group(1))


def degraus(doc: dict) -> list[Counter]:
    """Multiconjunto de degraus de cada compasso."""
    return [
        Counter(diatonico(s["nome"]) for s in c["simbolos"] if _e_nota(s))
        for c in doc["compassos"]
    ]


tot = Counter()
for rid, r in sorted(GAB["recortes"].items()):
    curto, rec = rid.rsplit("_", 1)
    slug = next(s.name for s in SP.iterdir() if s.name.startswith(curto))
    ent = next(
        e
        for e in json.loads((SP / slug / "recortes/indice.json").read_text("utf-8"))
        if e.get("id") == rec
    )
    pauta = next(
        p
        for p in json.loads((SP / slug / f"{slug}.partitura.json").read_text("utf-8"))[
            "pautas"
        ]
        if p["recorte"] == rec
    )
    x0 = ent["caixa_recorte"][0]
    inicios = [c["x_quadro"] - x0 for c in pauta["compassos"]]
    a = degraus(ler_partitura(SP / slug / f"omr/audiveris/x2_margem_herdada/{rec}/saida.musicxml"))
    h = degraus(ler_partitura(DH / curto / rec / "saida.musicxml"))
    if len(a) != len(h):
        print(f"{rid}: compassos audiveris {len(a)} homr {len(h)} — sem comparação")
        continue
    acres = [hc - ac for ac, hc in zip(a, h, strict=True)]
    ymeio = ent["ys"][2] - ent["caixa_recorte"][1]
    meia = ent["entrelinha"] / 2
    cliques = []
    for c in r["faltando"]:
        k = max(i for i, xi in enumerate(inicios) if xi <= c["x"] + 5) if c["x"] + 5 >= inicios[0] else 0
        cliques.append((k, SI4 - round((c["y"] - ymeio) / meia)))
    for folga in (0, 1):
        sobra = [Counter(x) for x in acres]
        n = 0
        for k, d in cliques:
            for dd in sorted(sobra[k], key=lambda v: abs(v - d)):
                if abs(dd - d) <= folga and sobra[k][dd] > 0:
                    sobra[k][dd] -= 1
                    n += 1
                    break
        if folga == 0:
            rec0, inv0 = n, sum(sum(s.values()) for s in sobra)
        else:
            rec1, inv1 = n, sum(sum(s.values()) for s in sobra)
    total_acres = sum(sum(x.values()) for x in acres)
    por_comp = Counter(k for k, _ in cliques)
    print(
        f"{rid}: faltando {len(cliques)} (por compasso {dict(sorted(por_comp.items()))}),"
        f" acréscimos {total_acres}, recuperadas {rec0} (±1 degrau {rec1}),"
        f" sem clique {inv0} (±1: {inv1})"
    )
    tot.update(faltando=len(cliques), acrescimos=total_acres, rec0=rec0, rec1=rec1, inv0=inv0, inv1=inv1)
print("total", dict(tot))
