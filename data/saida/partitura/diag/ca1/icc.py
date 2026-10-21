"""Correlação dentro do recorte (ICC) nos gabaritos do dono, para dimensionar gabarito novo.

ICC de uma via (ANOVA) sobre o desfecho binário por nota: cobertura = certo / (certo +
faltando) e precisão = certo / lidos. Só lê. Uso: python3 data/saida/partitura/diag/ca1/icc.py
"""

import json


def icc(grupos: list[tuple[int, int]]) -> tuple[float, float, int, int]:
    """Proporção, ICC, notas e recortes de uma lista de (sucessos, total) por recorte."""
    total = sum(n for _, n in grupos)
    k = len(grupos)
    p = sum(s for s, _ in grupos) / total
    msb = sum(n * (s / n - p) ** 2 for s, n in grupos) / (k - 1)
    msw = sum(s * (1 - s / n) for s, n in grupos) / (total - k)
    n0 = (total - sum(n * n for _, n in grupos) / total) / (k - 1)
    return p, (msb - msw) / (msb + (n0 - 1) * msw), total, k


def main() -> None:
    """Imprime p e ICC por gabarito e desfecho."""
    for nome in ["leitura_p1", "leitura_sem_produto"]:
        recortes = json.load(open(f"data/gold/partitura/{nome}.json"))["recortes"]
        cob, prec = [], []
        for r in recortes.values():
            certos = sum(s["dono"] == "certo" for s in r["simbolos"])
            cob.append((certos, certos + len(r["faltando"])))
            prec.append((certos, len(r["simbolos"])))
        for desfecho, grupos in [("cobertura", cob), ("precisao", prec)]:
            p, rho, total, k = icc(grupos)
            print(f"{nome} {desfecho}: p={p:.3f} icc={rho:.3f} notas={total}"
                  f" recortes={k} m={total / k:.1f}")


if __name__ == "__main__":
    main()
