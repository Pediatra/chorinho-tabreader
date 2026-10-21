"""Rodada 1014: janela fixa (D2 sem teste de câmera) nos 6 vídeos novos, contra o D1.

Método idêntico a data/saida/maos/m8/d2_fixo.py. Uso: confirmar.py <saida.json>.
"""
import hashlib
import json
import sys

import tab.maos_corda_sem_direita as m
from tab.caminhos import SAIDA

M3D = SAIDA / "maos" / "m3d"
M9 = SAIDA / "maos" / "m9"
NOVOS = (
    ("take_five", "sky guitar/take five - guitar lesson + tab.mp4", 1, "q32"),
    ("spanish_tango", "sky guitar/spanish tango (the mask of zorro) - tab & lesson.mp4", 2, "q33"),
    ("fur_elise", "sky guitar/für elise (full version) - guitar lesson + tab.mp4", 3, "q34"),
    ("ghostbusters", "sky guitar/ghostbusters - fingerstyle lesson + tab.mp4", 5, "q35"),
    ("annie_laurie", "sky guitar/annie laurie - guitar lesson + tab.mp4", 6, "q36"),
    ("no_surprises", "sky guitar/no surprises - tab & lesson.mp4", 7, "q22"),
)

orig = m.janela_da_mao_esquerda
m.janela_da_mao_esquerda = lambda maos, ref, desloc: orig(maos, ref, (0.0, 0.0))
m.LIMIAR_CAMERA = -10.0


def medir(nome, entrada, quadro, cache):
    v = m.preparar_video(nome, entrada, quadro, cache)
    d1 = m.decodar(v, "D1", m.PESOS_PRIORI)
    d2 = m.decodar(v, "D2", m.PESOS_PRIORI)
    c1 = m.pontuar(v, d1, "D1")
    c2 = m.pontuar(v, d2, "D2")
    cons, queb, casos = 0, 0, []
    for a, x1, x2, js in zip(v.ataques, d1, d2, v.janelas_d2, strict=True):
        for n, (s1, _), (s2, _), j in zip(a.notas, x1, x2, js, strict=True):
            amb = len(m.candidatos_da_altura(m.altura_midi(n.corda, n.casa))) > 1
            if not amb:
                continue
            c = s1 != n.corda and s2 == n.corda
            q = s1 == n.corda and s2 != n.corda
            cons += c
            queb += q
            if c or q:
                casos.append({"t": a.t, "corda": n.corda, "casa": n.casa, "d1": s1,
                              "d2": s2, "tipo": "conserta" if c else "quebra",
                              "janela": None if j is None else list(j)})
    pred = json.dumps([[d1, d2]], default=str)
    return {"quadro": quadro, "cob": v.cobertura["ataques_com_janela_camera"],
            "presa": v.cobertura["ataques_com_presa"], "D1": c1, "D2fixo": c2,
            "conserta_amb": cons, "quebra_amb": queb, "casos": casos,
            "hash": hashlib.sha256(pred.encode()).hexdigest()}


saida = {"trabalho": {}, "novos": {}}
for nome, entrada in zip(m.NOMES, m.VIDEOS, strict=True):
    saida["trabalho"][nome] = medir(nome, entrada, m.QUADRO_DO_BRACO[nome], m.MAOS_M8)
for nome, arq, i, q in NOVOS:
    ent = {"arquivo": arq, "produto": M3D / f"sky_{i}.json",
           "pontas": (M3D / "pontas_q22.json") if i == 7 else (M9 / f"pontas_sky_{i}.json")}
    saida["novos"][nome] = medir(nome, ent, q, M9)
for grupo, vs in saida.items():
    for nome, r in vs.items():
        a1, a2 = r["D1"], r["D2fixo"]
        print(grupo, nome, "cob", r["cob"], "/", r["presa"], "| D1 erros", a1["erros"],
              "amb", a1["amb_acertos"], "/", a1["amb_n"], "| D2 erros", a2["erros"], "amb",
              a2["amb_acertos"], "| cons", r["conserta_amb"], "queb", r["quebra_amb"],
              "| jan certa", a2["erro_janela_certa"], "errada", a2["erro_janela_errada"],
              "sem", a2["erro_sem_janela"])
json.dump(saida, open(sys.argv[1], "w"), indent=1, ensure_ascii=False, default=str)
