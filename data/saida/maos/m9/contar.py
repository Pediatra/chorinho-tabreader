"""Notas, ambíguas e erros do D1 nos vídeos da confirmação (antes de qualquer janela)."""
import tab.maos_corda_sem_direita as m
from tab.caminhos import SAIDA

for i in (1, 2, 3, 5, 6, 7):
    notas, fora = m.carregar_notas(SAIDA / "maos" / "m3d" / f"sky_{i}.json")
    at = m.agrupar_ataques(notas)
    combos = [m.combinacoes_do_ataque(a)[0] for a in at]
    sem = [[None] * len(a.notas) for a in at]
    import dataclasses
    d1 = m.decodificar(combos, sem, dataclasses.replace(m.PESOS_PRIORI, beta=0.0))
    amb = er = er_amb = 0
    for a, c in zip(at, d1):
        for n, (s, _) in zip(a.notas, c):
            ab = len(m.candidatos_da_altura(m.altura_midi(n.corda, n.casa))) > 1
            amb += ab; er += s != n.corda; er_amb += ab and s != n.corda
    print(f"sky_{i}: notas {len(notas)} fora {fora} ataques {len(at)} ambiguas {amb} erros_D1 {er} (amb {er_amb})")
