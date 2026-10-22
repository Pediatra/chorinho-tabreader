"""Checagem rápida do R4b na T8.2 (dobra 0): versão e semente dadas, com a regra do slide."""

import json
import sys
from collections import Counter

from tab import ataque_r4 as A
from tab import caminhos, detector_tab

versao, semente = sys.argv[1], int(sys.argv[2])
r2 = caminhos.TAB_ROTULO / "r2"
ferr = caminhos.SAIDA / "t82" / "ferramenta"
indice = {int(r["id"]): r for r in json.loads((ferr / "indice.json").read_text())}
m = detector_tab.carregar(A.modelo_da_dobra(versao, 0, semente))
c = Counter()
for tela, notas in sorted(A.gabarito_por_tela(r2 / "conferir_novos" / "ataque_t82.json").items()):
    r = indice[tela]
    pred, passo = A.ler_tela(m, caminhos.acervo() / r["video"], float(r["t"]))
    c += A.contar(notas, pred, passo)
t, g = A.taxas(c), A.taxas(A.regra(c))
print(f"rapida_t82 {versao} s{semente}: sim_falso {t['sim_falso']} (regra {g['sim_falso']}) nao_falso {t['nao_falso']} (regra {g['nao_falso']}) casa {c['casa_certa']}/{c['casadas']}")
