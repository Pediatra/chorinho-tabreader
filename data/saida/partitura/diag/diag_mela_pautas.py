"""Por que achar_pautas perde pautas no mela: testes de cada janela de 5 linhas fortes."""

import sys

import cv2
import numpy as np

from tab.caminhos import acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import (
    _abrir, _espessura_limite, _ha_sexta_linha, _ha_sexta_na_janela, _linhas_da_abertura,
    _linhas_sao_crista, _mascaras_de_tinta, _pauta_do_grupo, N_LINHAS,
)

VIDEO = "ギタロー ⧸ guitarous/【無料タブ譜】mela! - 緑黄色社会 - ソロギタータブ譜.mp4"


def main():
    for t in map(float, sys.argv[1:]):
        q = quadro_em(str(acervo() / VIDEO), t)
        cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(f"data/saida/partitura/diag/mela_{t:.0f}.jpg", q)
        L = cinza.shape[1]
        print(f"== t={t} forma {q.shape}")
        for k, m in enumerate(_mascaras_de_tinta(cinza)):
            ab = _abrir(m, L)
            linhas = _linhas_da_abertura(ab, L, escura=(k == 0))
            fortes = [x for x in linhas if x.forte]
            print(f" polaridade {k}: {len(linhas)} linhas, {len(fortes)} fortes")
            print("  fortes:", [(round(x.y), x.x0, x.x1, x.espessura) for x in fortes])
            print("  fracas:", [(round(x.y), x.x0, x.x1, x.espessura) for x in linhas if not x.forte])
            for i in range(len(fortes) - N_LINHAS + 1):
                g = fortes[i:i + N_LINHAS]
                p = _pauta_do_grupo(g, L)
                if p is None:
                    continue
                esp = [x.espessura for x in g]
                med = round(float(np.median(esp)))
                print(f"  grupo y0={p.ys[0]} e={p.entrelinha} esp_ok={max(esp) <= _espessura_limite(med)}"
                      f" crista={_linhas_sao_crista(g, p, cinza)} sexta={_ha_sexta_linha(p, linhas, L, med)}"
                      f" janela={_ha_sexta_na_janela(p, ab)}")


if __name__ == "__main__":
    main()
