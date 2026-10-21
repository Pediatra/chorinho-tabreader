"""Diagnóstico do revisor: D2 com grade fixa (sem teste de câmera), pesos a priori."""
import json
import tab.maos_corda_sem_direita as m

orig = m.janela_da_mao_esquerda
m.janela_da_mao_esquerda = lambda maos, ref, desloc: orig(maos, ref, (0.0, 0.0))
m.LIMIAR_CAMERA = -10.0
saida = {}
tot = {}
for nome, entrada in zip(m.NOMES, m.VIDEOS, strict=True):
    v = m.preparar_video(nome, entrada, m.QUADRO_DO_BRACO[nome], m.MAOS_M8)
    d1 = m.decodar(v, "D1", m.PESOS_PRIORI)
    d2 = m.decodar(v, "D2", m.PESOS_PRIORI)
    c1 = m.pontuar(v, d1, "D1"); c2 = m.pontuar(v, d2, "D2")
    cons = queb = 0
    for a, x1, x2 in zip(v.ataques, d1, d2, strict=True):
        for n, (s1, _), (s2, _) in zip(a.notas, x1, x2, strict=True):
            amb = len(m.candidatos_da_altura(m.altura_midi(n.corda, n.casa))) > 1
            if not amb: continue
            cons += (s1 != n.corda and s2 == n.corda); queb += (s1 == n.corda and s2 != n.corda)
    saida[nome] = {"cob": v.cobertura["ataques_com_janela_camera"], "presa": v.cobertura["ataques_com_presa"],
                   "D1": c1, "D2fixo": c2, "conserta_amb": cons, "quebra_amb": queb}
    print(nome, "cob", saida[nome]["cob"], "/", saida[nome]["presa"], "D1 erros", c1["erros"], "amb", c1["amb_acertos"], "/", c1["amb_n"],
          "| D2fixo erros", c2["erros"], "amb", c2["amb_acertos"], "| cons", cons, "queb", queb,
          "| janela_certa", c2["erro_janela_certa"], "janela_errada", c2["erro_janela_errada"], "sem", c2["erro_sem_janela"])
json.dump(saida, open("/s/d2_fixo.json", "w"), indent=1)
