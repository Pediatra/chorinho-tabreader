"""Conta os estados do gabarito do dono (rodada 3004). Uso: python3 medir_gabarito.py"""

import collections
import json

GAB = "data/gold/partitura/leitura_p1.json"
GRUPOS = {
    "R01-R12": [f"R{i:02d}" for i in range(1, 13)],
    "R13-R21": [f"R{i:02d}" for i in range(13, 22)],
}


def main() -> None:
    """Imprime a contagem por grupo e por recorte."""
    rec = json.load(open(GAB, encoding="utf-8"))["recortes"]
    for nome, ids in GRUPOS.items():
        c = collections.Counter()
        notac = collections.Counter()
        falt = 0
        for k in ids:
            falt += len(rec[k]["faltando"])
            for s in rec[k]["simbolos"]:
                c[("pausa" if s["palpite"]["pausa"] else "nota", s["dono"])] += 1
                notac.update(s.get("notacoes_dono", {}).values())
        print(nome, dict(sorted(c.items())), "faltando", falt, "notacoes", dict(notac))
    for k in sorted(rec):
        c = collections.Counter(s["dono"] for s in rec[k]["simbolos"])
        print(k, dict(c), "faltando", len(rec[k]["faltando"]))


if __name__ == "__main__":
    main()
