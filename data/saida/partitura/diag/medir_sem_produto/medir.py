"""Conta os estados do gabarito sem produto (rodada 3023), como a 3004 fez com R01-R21."""

import collections
import json

GAB = "data/gold/partitura/leitura_sem_produto.json"


def main() -> None:
    """Imprime a contagem por recorte e no total."""
    rec = json.load(open(GAB, encoding="utf-8"))["recortes"]
    total = collections.Counter()
    notac = collections.Counter()
    falt = 0
    for k in sorted(rec):
        r = rec[k]
        c = collections.Counter()
        for s in r["simbolos"]:
            c[("pausa" if s["palpite"]["pausa"] else "nota", s["dono"])] += 1
            notac.update(s.get("notacoes_dono", {}).values())
        total.update(c)
        falt += len(r["faltando"])
        lidos = sum(c.values())
        certos = sum(v for (_, e), v in c.items() if e == "certo")
        print(
            f"{k}: lidos {lidos}, certos {certos}, {dict(sorted(c.items()))},"
            f" faltando {len(r['faltando'])}, clave {r['clave_certa']},"
            f" armadura {r['armadura_certa']}, obs {r['obs']!r}"
        )
    lidos = sum(total.values())
    certos = sum(v for (_, e), v in total.items() if e == "certo")
    print(f"total: lidos {lidos}, certos {certos} ({certos / lidos:.1%}),"
          f" {dict(sorted(total.items()))}, faltando {falt}")
    print(f"cobertura: {certos} certos de {certos + falt} notas que existem"
          f" ({certos / (certos + falt):.1%})")
    print("notações:", dict(notac))


if __name__ == "__main__":
    main()
