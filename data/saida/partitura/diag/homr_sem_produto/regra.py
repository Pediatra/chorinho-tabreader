"""Regra por compasso para aceitar notas do homr, nos dois gabaritos (rodada 3024).

Para cada compasso: acréscimo do homr = degraus do homr que sobram na diferença de
multiconjuntos (homr menos Audiveris). Regra: aceitar os acréscimos de um compasso só se
o homr tem pelo menos ``razao`` vezes as notas do Audiveris nesse compasso (razao 0 =
união cega, em todos os compassos). Mede contra os cliques de faltando do dono (compasso
pela posição x entre as barras do ``.omr``, degrau pela posição y). Acréscimo aceito sem
clique conta como inventado. No R20 o dono não clicou a 2ª metade (adendo da 3005):
ele entra só na conta de recuperadas, não na de inventadas.
"""
import json
import re
from collections import Counter
from pathlib import Path

from tab.partitura_gabarito import _e_nota, ler_partitura
from tab.partitura_video import x_dos_compassos

SP = Path("data/saida/partitura/sem_produto")
P1 = Path("data/saida/partitura/p1")
DH = Path("data/saida/partitura/diag/homr_sem_produto/homr")
LETRAS = "CDEFGAB"
SI4 = 4 * 7 + 6
RAZOES = [0, 1.25, 1.5, 2, 3]


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


def itens():
    """(grupo, id, entrada, cliques, xml audiveris, omr, xml homr, conta_inventadas)."""
    gab = json.loads(Path("data/gold/partitura/leitura_p1.json").read_text("utf-8"))
    indice = {
        e["id"]: e
        for e in json.loads((P1 / "recortes_margem/indice.json").read_text("utf-8"))
    }
    for rid, r in sorted(gab["recortes"].items()):
        if r["fonte"] != "audiveris/x2_margem":
            continue
        base = P1 / "omr/audiveris/x2_margem" / rid
        yield ("R01-R21", rid, indice[rid], r["faltando"], base / "saida.musicxml",
               base / "entrada.omr", P1 / "omr/homr/nativo" / rid / "saida.musicxml",
               rid != "R20")
    gab = json.loads(Path("data/gold/partitura/leitura_sem_produto.json").read_text("utf-8"))
    for rid, r in sorted(gab["recortes"].items()):
        curto, rec = rid.rsplit("_", 1)
        slug = next(s.name for s in SP.iterdir() if s.name.startswith(curto))
        ent = next(
            e
            for e in json.loads((SP / slug / "recortes/indice.json").read_text("utf-8"))
            if e.get("id") == rec
        )
        omr = SP / slug / "omr/audiveris"
        yield ("sem_produto", rid, ent, r["faltando"],
               omr / "x2_margem_herdada" / rec / "saida.musicxml",
               omr / "x2_margem" / rec / "entrada.omr", DH / curto / rec / "saida.musicxml",
               True)


tot = {}
for grupo, rid, ent, faltando, xa, omr, xh, conta_inv in itens():
    a = degraus(ler_partitura(xa))
    h = degraus(ler_partitura(xh))
    inicios = [p[0] / 2.0 for p in x_dos_compassos(omr)]
    if len(a) != len(h) or not inicios:
        print(f"{grupo} {rid}: compassos audiveris {len(a)} homr {len(h)}"
              f" barras {len(inicios)} — fora (cliques {len(faltando)})")
        t = tot.setdefault((grupo, "fora"), Counter())
        t.update(recortes=1, faltando=len(faltando))
        continue
    ymeio = ent["ys"][2] - ent["caixa_recorte"][1]
    meia = ent["entrelinha"] / 2
    cliques = []
    for c in faltando:
        antes = [i for i, xi in enumerate(inicios) if xi <= c["x"] + 5]
        k = min(max(antes) if antes else 0, len(a) - 1)
        cliques.append((k, SI4 - round((c["y"] - ymeio) / meia)))
    linha = f"{grupo} {rid}: faltando {len(cliques):2d}"
    for razao in RAZOES:
        sobra = [
            (hc - ac) if sum(hc.values()) >= razao * sum(ac.values()) else Counter()
            for ac, hc in zip(a, h, strict=True)
        ]
        aceitos = sum(sum(s.values()) for s in sobra)
        n = 0
        for k, d in cliques:
            if sobra[k][d] > 0:
                sobra[k][d] -= 1
                n += 1
        inv = sum(sum(s.values()) for s in sobra) if conta_inv else 0
        t = tot.setdefault((grupo, razao), Counter())
        t.update(faltando=len(cliques), recuperadas=n, inventadas=inv, aceitos=aceitos)
        linha += f" | r{razao}: +{n} inv {inv}"
    print(linha)
print()
for (grupo, razao), t in sorted(tot.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
    print(grupo, f"razão {razao}", dict(t))
