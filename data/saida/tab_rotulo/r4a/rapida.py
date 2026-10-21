"""Checagem rápida do R4a: dobra 4 (EOB e Room 335), versão e semente dadas."""

import json
import sys
from collections import Counter

from tab import ataque_r4 as A
from tab import caminhos, detector_tab

versao, semente = sys.argv[1], int(sys.argv[2])
r2 = caminhos.TAB_ROTULO / "r2"
m = detector_tab.carregar(A.modelo_da_dobra(versao, 4, semente))
total = Counter()
for slug in A.DOBRAS[4]:
    sub, fonte = A.GABARITOS[slug]
    ouro = json.loads((r2 / sub / f"{slug}.json").read_text())
    q = {int(t["id"]): float(t["quadro_ref_s"]) for t in ouro["telas"]}
    for tela, notas in sorted(A.gabarito_por_tela(r2 / sub / f"ataque_{fonte}.json").items()):
        pred, passo = A.ler_tela(m, caminhos.acervo() / ouro["video"], q[tela])
        total += A.contar(notas, pred, passo)
t = A.taxas(total)
print(f"rapida {versao} s{semente} dobra4: sim_falso {t['sim_falso']} nao_falso {t['nao_falso']} casa {total['casa_certa']}/{total['casadas']}")
