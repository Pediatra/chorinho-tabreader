"""P3, primeiro passo: nota do homr só entra se a tab confirma (R01–R12)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tab.partitura_avaliar import _carregar_ouro, _referencia_do_item, alinhar  # noqa: E402
from tab.partitura_gabarito import _e_nota, ler_partitura  # noqa: E402

P1 = Path("data/saida/partitura/p1")


def eventos(caminho: Path) -> list[tuple[float, list[dict]]]:
    """Notas agrupadas por início."""
    leitura = ler_partitura(caminho)
    grupos: dict[float, list[dict]] = {}
    for c in leitura["compassos"]:
        for s in c["simbolos"]:
            if _e_nota(s):
                grupos.setdefault(round(s["t_global"], 6), []).append(s)
    return sorted(grupos.items())


def mapa(lib: list[frozenset], ref: list[frozenset]) -> dict[int, int]:
    """Evento da leitura -> evento da tab casado."""
    return {i: j for op, i, j in alinhar(lib, ref) if op == "casa"}


def main() -> None:
    """Conta faltando da tab recuperadas pelo homr confirmado pela tab."""
    indice = json.loads((P1 / "recortes_margem/indice.json").read_text("utf-8"))
    ouro = _carregar_ouro()
    tot = {"ref": 0, "audiveris_certas": 0, "faltando_tab": 0, "homr_recupera": 0,
           "figura_homr": {}}
    for ent in indice:
        if ent["origem"] != "ouro":
            continue
        rid = ent["id"]
        ref = _referencia_do_item(ent, ouro)
        ea = eventos(P1 / f"omr/audiveris/x2_margem/{rid}/saida.musicxml")
        eh = eventos(P1 / f"omr/homr/nativo/{rid}/saida.musicxml")
        sa = [frozenset(n["midi"] for n in e) for _, e in ea]
        sh = [frozenset(n["midi"] for n in e) for _, e in eh]
        ma, mh = mapa(sa, ref), mapa(sh, ref)
        coberto = [set() for _ in ref]
        for i, j in ma.items():
            coberto[j] |= sa[i] & ref[j]
        homr_por_ref = {j: (i, sh[i]) for i, j in mh.items()}
        rec = 0
        for j, r in enumerate(ref):
            for m in r - coberto[j]:
                tot["faltando_tab"] += 1
                if j in homr_por_ref and m in homr_por_ref[j][1]:
                    rec += 1
                    nota = next(n for n in eh[homr_por_ref[j][0]][1] if n["midi"] == m)
                    f = nota["figura"]
                    tot["figura_homr"][f] = tot["figura_homr"].get(f, 0) + 1
        tot["ref"] += sum(len(r) for r in ref)
        tot["audiveris_certas"] += sum(len(c) for c in coberto)
        tot["homr_recupera"] += rec
        print(rid, "faltando", sum(len(r - coberto[j]) for j, r in enumerate(ref)),
              "homr recupera", rec)
    print(tot)


if __name__ == "__main__":
    main()
