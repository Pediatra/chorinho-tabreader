"""Pautas achadas no mela (t=23, 92), com e sem a passada de completar 4 linhas."""

import sys

from tab import partitura_pauta as pp
from tab.caminhos import acervo
from tab.leitor import quadro_em

VIDEO = "ギタロー ⧸ guitarous/【無料タブ譜】mela! - 緑黄色社会 - ソロギタータブ譜.mp4"


def main() -> None:
    for t in map(float, sys.argv[1:]):
        q = quadro_em(str(acervo() / VIDEO), t)
        depois = pp.achar_pautas(q)
        original = pp._completar_grupos_de_quatro
        pp._completar_grupos_de_quatro = lambda *a, **k: []
        try:
            antes = pp.achar_pautas(q)
        finally:
            pp._completar_grupos_de_quatro = original
        print(f"t={t:.0f} antes={len(antes)} depois={len(depois)}")
        for p in antes:
            print("  antes ys:", p.ys, "x0..x1:", p.x0, p.x1)
        for p in depois:
            print("  depois ys:", p.ys, "x0..x1:", p.x0, p.x1)


if __name__ == "__main__":
    main()
