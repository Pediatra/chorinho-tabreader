"""P3: pareamento partitura × tab, conferido pela posição x na tela (R01–R12).

A pauta fica em cima da tab, alinhada na vertical. Se o pareamento por sequência
(Needleman-Wunsch) estiver certo, a nota da partitura e a coluna da tab pareada caem no
mesmo x do quadro. O x da partitura vem do .omr do Audiveris (stack.left + slot.x-offset,
na imagem 2x). Também mede os instantes do gabarito de tempo (coluna tocando em t).
"""

import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tab.partitura_avaliar import _carregar_ouro, alinhar  # noqa: E402
from tab.partitura_gabarito import _e_nota, ler_partitura  # noqa: E402
from tab.musicxml import midi_da_corda  # noqa: E402

P1 = Path("data/saida/partitura/p1")
COND = "x2_margem_herdada"


def stacks(omr: Path) -> list[tuple[float, dict[Fraction, float]]]:
    """(left, {time-offset: x-offset}) de cada compasso do .omr, na ordem."""
    with zipfile.ZipFile(omr) as z:
        raiz = ET.fromstring(z.read("sheet#1/sheet#1.xml"))
    saida = []
    for st in raiz.iter("stack"):
        slots = {Fraction(s.get("time-offset")): float(s.get("x-offset")) for s in st.iter("slot")}
        saida.append((float(st.get("left")), slots))
    return saida


def eventos_com_x(rid: str, x0: float) -> list[tuple[float | None, frozenset]]:
    """Eventos da leitura com o x no quadro (None se o slot não foi achado)."""
    leitura = ler_partitura(P1 / f"omr/audiveris/{COND}/{rid}/saida.musicxml")
    pilhas = stacks(P1 / f"omr/audiveris/x2_margem/{rid}/entrada.omr")
    grupos: dict[float, tuple[float | None, set]] = {}
    for k, comp in enumerate(leitura["compassos"]):
        for s in comp["simbolos"]:
            if not _e_nota(s):
                continue
            x = None
            if k < len(pilhas):
                left, slots = pilhas[k]
                off = Fraction(s["t"]).limit_denominator(64) / 4
                if off in slots:
                    x = x0 + (left + slots[off]) / 2
            chave = round(s["t_global"], 6)
            xa, conj = grupos.get(chave, (x, set()))
            conj.add(s["midi"])
            grupos[chave] = (xa if xa is not None else x, conj)
    return [(grupos[t][0], frozenset(grupos[t][1])) for t in sorted(grupos)]


def ref_com_x(notas: list[dict], x0: float, x1: float) -> list[tuple[float, frozenset]]:
    """Mesma referência da avaliação (tab → altura escrita), guardando o x do evento."""
    pontos = []
    for n in notas:
        x = float(n["x_centro_quadro"])
        soado = midi_da_corda(int(n["corda"]), int(n["casa"]))
        if x0 <= x <= x1 and soado is not None:
            pontos.append((x, soado + 12))
    pontos.sort()
    grupos: list[list] = []
    for x, m in pontos:
        if grupos and x - grupos[-1][2] <= 6:
            grupos[-1][1].add(m)
            grupos[-1][2] = x
        else:
            grupos.append([x, {m}, x])
    return [((g[0] + g[2]) / 2, frozenset(g[1])) for g in grupos]


def main() -> None:
    """Imprime a concordância de x dos pares e a conta dos instantes de tempo."""
    indice = json.loads((P1 / "recortes_margem/indice.json").read_text("utf-8"))
    ouro = _carregar_ouro()
    tot = {"pares": 0, "com_x": 0, "x_ok": 0, "instantes": 0, "instantes_com_nota": 0}
    dist_todas = []
    for ent in indice:
        if ent["origem"] != "ouro":
            continue
        rid = ent["id"]
        gab = ouro[ent["video"]][0]
        tela = next(t for t in gab["telas"] if t["id"] == ent["tela"])
        x0, _, x1, _ = ent["caixa_recorte"]
        lib = eventos_com_x(rid, x0)
        ref = ref_com_x(tela["notas"], x0, x1)
        tol = 1.0 * ent["entrelinha"]
        pares = [(i, j) for op, i, j in alinhar([e[1] for e in lib], [e[1] for e in ref]) if op == "casa"]
        dists = [abs(lib[i][0] - ref[j][0]) for i, j in pares if lib[i][0] is not None]
        ok = sum(d <= tol for d in dists)
        dist_todas += dists
        # instantes: coluna tocando em t, nesta tela e dentro do recorte
        par_por_ref = {j: i for i, j in pares}
        n_inst = n_ok = 0
        for inst in gab["instantes"]:
            cx = inst.get("coluna_x_quadro")
            if inst.get("tela") != ent["tela"] or cx is None or not x0 <= cx <= x1:
                continue
            n_inst += 1
            j = min(range(len(ref)), key=lambda j: abs(ref[j][0] - cx))
            if abs(ref[j][0] - cx) <= tol and j in par_por_ref:
                xi = lib[par_por_ref[j]][0]
                if xi is not None and abs(xi - cx) <= tol:
                    n_ok += 1
        tot["pares"] += len(pares)
        tot["com_x"] += len(dists)
        tot["x_ok"] += ok
        tot["instantes"] += n_inst
        tot["instantes_com_nota"] += n_ok
        mediana = sorted(dists)[len(dists) // 2] if dists else None
        print(f"{rid} eventos lidos {len(lib)} tab {len(ref)} pares {len(pares)} "
              f"com x {len(dists)} x ok {ok} (mediana {mediana and round(mediana, 1)} px, "
              f"tol {tol:.0f}) instantes {n_ok}/{n_inst}")
    print(tot)


if __name__ == "__main__":
    main()
