"""Diagnóstico 3005 aplicado ao gabarito sem produto (rodada 3024).

Original: o homr recupera as notas que o Audiveris perdeu? (rodada 3005)

Junta Audiveris x2_margem e homr nativo por alinhamento de eventos. Os acréscimos do
homr são notas que faltam num evento casado (acorde completado) ou eventos inteiros
que só o homr viu. Mede contra o gabarito do dono (cliques de nota faltando: posição
x e degrau da pauta) e, em R01–R12, contra a tab.

Uso (container base): python data/saida/partitura/diag/fusao_homr.py
"""

import json
import re
import sys
import zipfile
from collections import Counter
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tab.partitura_avaliar import _carregar_ouro, _referencia_do_item, alinhar, contar  # noqa: E402
from tab.partitura_gabarito import _e_nota, ler_partitura  # noqa: E402

P1 = Path("data/saida/partitura/p1")
GAB = Path("data/gold/partitura/leitura_sem_produto.json")
SP = Path("data/saida/partitura/sem_produto")
DH = Path("data/saida/partitura/diag/homr_sem_produto/homr")
SLUGS = {p.name[:16]: p.name for p in SP.iterdir()}
LETRAS = "CDEFGAB"
SI4 = 4 * 7 + 6  # índice diatônico da linha do meio (clave de sol, altura escrita)


def diatonico(nome: str) -> int:
    """Índice diatônico (C0 = 0) de um nome como ``Bb4``."""
    casa = re.fullmatch(r"([A-G])[#b]*(-?\d+)", nome)
    return int(casa.group(2)) * 7 + LETRAS.index(casa.group(1))


def eventos(simbolos: list[dict]) -> list[tuple[float, list[dict]]]:
    """Notas agrupadas por início, na ordem do tempo (mesma regra da concordância)."""
    grupos: dict[float, list[dict]] = {}
    for s in simbolos:
        if _e_nota(s):
            grupos.setdefault(round(s["t_global"], 6), []).append(s)
    return sorted(grupos.items())


def colunas_audiveris(omr: Path, escala: float) -> tuple[list[float], list[tuple]]:
    """Colunas de cabeças do Audiveris (x no recorte) e as cabeças (x, y, pitch)."""
    with zipfile.ZipFile(omr) as z:
        raiz = ET.fromstring(z.read("sheet#1/sheet#1.xml"))
    cabecas = []
    for h in raiz.iter("head"):
        b = h.find("bounds")
        x = (int(b.get("x")) + int(b.get("w")) / 2) / escala
        y = (int(b.get("y")) + int(b.get("h")) / 2) / escala
        cabecas.append((x, y, int(h.get("pitch"))))
    xs = sorted(c[0] for c in cabecas)
    colunas: list[list[float]] = []
    for x in xs:
        if colunas and x - colunas[-1][-1] < 6:
            colunas[-1].append(x)
        else:
            colunas.append([x])
    return [sum(c) / len(c) for c in colunas], cabecas


def main() -> None:
    """Imprime a conta por recorte e o total."""
    gab = json.loads(GAB.read_text(encoding="utf-8"))["recortes"]
    ouro = _carregar_ouro()
    tot = {"faltando": 0, "recuperadas": 0, "recuperadas_1": 0, "acrescimos": 0}
    tab_antes, tab_depois = {}, {}
    sanidade = [0, 0]
    por_tipo = Counter()
    for rid in sorted(gab):
        curto, rec = rid.rsplit("_", 1)
        slug = SLUGS[curto]
        ent = next(
            e
            for e in json.loads((SP / slug / "recortes/indice.json").read_text("utf-8"))
            if e.get("id") == rec
        )
        omr_dir = SP / slug / "omr/audiveris"
        a = ler_partitura(omr_dir / f"x2_margem_herdada/{rec}/saida.musicxml")
        h = ler_partitura(DH / curto / rec / "saida.musicxml")
        ea = eventos([s for c in a["compassos"] for s in c["simbolos"]])
        eh = eventos([s for c in h["compassos"] for s in c["simbolos"]])
        sa = [frozenset(n["midi"] for n in ev) for _, ev in ea]
        sh = [frozenset(n["midi"] for n in ev) for _, ev in eh]
        ops = alinhar(sa, sh)

        cols, cabecas = colunas_audiveris(
            omr_dir / f"x2_margem/{rec}/entrada.omr", 2.0
        )
        ymeio = ent["ys"][2] - ent["caixa_recorte"][1]
        meia = ent["entrelinha"] / 2
        for x, y, p in cabecas:
            sanidade[0] += 1
            sanidade[1] += round((y - ymeio) / meia) == p
        na = len(ea)

        def x_do_evento(i: int) -> float:
            """x da coluna do evento i do Audiveris (por posto)."""
            if len(cols) == na:
                return cols[i]
            return cols[round(i * (len(cols) - 1) / max(na - 1, 1))]

        # Acréscimos: (x_min, x_max, degrau, midi, posição na sequência fundida)
        acrescimos = []
        fundida: list[frozenset] = []
        ultimo_a = -1
        pendentes = []  # eventos só do homr, esperando o próximo evento do Audiveris
        for op, i, j in ops:
            if op == "casa":
                xa = x_do_evento(i)
                xl = x_do_evento(ultimo_a) if ultimo_a >= 0 else 0.0
                for ev in pendentes:
                    for n in ev:
                        acrescimos.append((xl, xa, diatonico(n["nome"]), "evento"))
                pendentes = []
                novos = [n for n in eh[j][1] if n["midi"] not in sa[i]]
                for n in novos:
                    acrescimos.append((xa, xa, diatonico(n["nome"]), "acorde"))
                fundida.append(sa[i] | frozenset(n["midi"] for n in novos))
                ultimo_a = i
            elif op == "inv":
                xa = x_do_evento(i)
                xl = x_do_evento(ultimo_a) if ultimo_a >= 0 else 0.0
                for ev in pendentes:
                    for n in ev:
                        acrescimos.append((xl, xa, diatonico(n["nome"]), "evento"))
                pendentes = []
                fundida.append(sa[i])
                ultimo_a = i
            else:
                pendentes.append(eh[j][1])
                fundida.append(sh[j])
        xl = x_do_evento(ultimo_a) if ultimo_a >= 0 else 0.0
        for ev in pendentes:
            for n in ev:
                acrescimos.append((xl, float(ent["largura"]), diatonico(n["nome"]), "evento"))

        cliques = [
            (c["x"], SI4 - round((c["y"] - ymeio) / meia)) for c in gab[rid]["faltando"]
        ]
        tol = 1.5 * ent["entrelinha"]

        def casar(folga: int) -> int:
            """Casamento guloso clique × acréscimo (degrau com folga, x no intervalo)."""
            usados = set()
            n = 0
            for cx, cd in cliques:
                for k, (x0, x1, d, _) in enumerate(acrescimos):
                    if k in usados:
                        continue
                    if x0 - tol <= cx <= x1 + tol and abs(d - cd) <= folga:
                        usados.add(k)
                        if folga == 0:
                            por_tipo[acrescimos[k][3] + "_casado"] += 1
                        n += 1
                        break
            return n

        for ac in acrescimos:
            por_tipo[ac[3]] += 1
        rec0, rec1 = casar(0), casar(1)
        tot["faltando"] += len(cliques)
        tot["recuperadas"] += rec0
        tot["recuperadas_1"] += rec1
        tot["acrescimos"] += len(acrescimos)
        linha = (
            f"{rid} faltando {len(cliques):2d} acréscimos {len(acrescimos):2d} "
            f"recuperadas {rec0:2d} (±1 degrau {rec1:2d}) colunas {len(cols)}/{na}"
        )
        if False:
            ref = _referencia_do_item(ent, ouro)
            for nome, seq, acc in (("antes", sa, tab_antes), ("depois", fundida, tab_depois)):
                cont, _ = contar(seq, ref, "exato")
                for k2, v in cont.items():
                    acc[k2] = acc.get(k2, 0) + v
                if nome == "depois":
                    linha += f" | tab depois {cont}"
        print(linha)
    print("total", tot)
    print("por tipo", dict(por_tipo))
    print("tab R01–R12 antes ", tab_antes)
    print("tab R01–R12 depois", tab_depois)
    print(f"sanidade degrau das cabeças do Audiveris: {sanidade[1]}/{sanidade[0]}")


if __name__ == "__main__":
    main()
