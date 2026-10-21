"""Compara alinhamento v2 (antigo) com v2.1 (novo) nos 9 bons. Só lê JSON."""

import json
import sys

RAIZ = "/var/home/gabriel/Projects/chorinho-dataset"
L1 = f"{RAIZ}/data/saida/audio/a4/lote1"
A2 = f"{RAIZ}/data/saida/audio/a2"
PAR = {
    "mvp": (f"{A2}/alinhado_v2_r1.json", f"{A2}/alinhado_v21_mvp.json"),
}
for ap in ["iwaki_la_vie_en_rose", "kimny_from_this_place", "shin_izumi_room_335"]:
    PAR[ap] = (f"{A2}/produtos/alinhado_{ap}.json", f"{A2}/produtos/alinhado_v21_{ap}.json")
for ap in ["iwaki_michelle", "iwaki_fly_me_to_the_moon", "kimny_gunjo", "kimny_bach_prelude",
           "shin_izumi_giant_steps", "transcriptor_charagua", "transcriptor_campanitas",
           "guitarous_sakura", "shin_izumi_dream_wish", "paolo_those_who_wait"]:
    PAR[ap] = (f"{L1}/alinhado_{ap}.json", f"{L1}/alinhado_v21_{ap}.json")

BOAS = ["mvp", "iwaki_la_vie_en_rose", "kimny_from_this_place", "iwaki_michelle",
        "iwaki_fly_me_to_the_moon", "kimny_gunjo", "kimny_bach_prelude",
        "shin_izumi_dream_wish", "paolo_those_who_wait"]
NOVOS_EX = {"n_abafadas_casadas", "rasgueado"}


def comparar(ap):
    antigo = json.load(open(PAR[ap][0]))
    novo = json.load(open(PAR[ap][1]))
    col_ok = 0
    col_dif = []
    for a, n in zip(antigo["colunas"], novo["colunas"], strict=True):
        chave = (a["tela"], a["exibicao"], a["coluna"])
        ok = all(a[k] == n[k] for k in ("t_audio", "motivo", "confianca", "cos"))
        ok = ok and (a["tela"], a["exibicao"], a["coluna"]) == (n["tela"], n["exibicao"], n["coluna"])
        if ok:
            col_ok += 1
        else:
            col_dif.append(chave)
    ex_ok = 0
    ex_dif = []
    for a, n in zip(antigo["exibicoes"], novo["exibicoes"], strict=True):
        campos = set(a) | set(n)
        diff = [k for k in campos if k not in NOVOS_EX and a.get(k) != n.get(k)]
        if not diff:
            ex_ok += 1
        else:
            ex_dif.append((a["tela"], a["exibicao"], diff))
    novos_ex_ok = all(
        n.get("rasgueado") is False and n.get("n_abafadas_casadas") == 0
        for n in novo["exibicoes"]
    )
    tipos_ok = all(n["tipo"] == "nota" for n in novo["colunas"])
    return {
        "n_col": len(novo["colunas"]), "col_ok": col_ok, "col_dif": col_dif[:5],
        "n_ex": len(novo["exibicoes"]), "ex_ok": ex_ok, "ex_dif": ex_dif[:3],
        "novos_ex_ok": novos_ex_ok, "tipos_ok": tipos_ok,
        "len_iguais": len(antigo["colunas"]) == len(novo["colunas"]),
    }


if __name__ == "__main__":
    for ap in BOAS:
        r = comparar(ap)
        print(
            f"{ap}: colunas identicas {r['col_ok']} de {r['n_col']}; "
            f"exibicoes identicas {r['ex_ok']} de {r['n_ex']}; "
            f"novos campos (rasgueado False, n_abafadas 0) {r['novos_ex_ok']}; "
            f"tipo nota {r['tipos_ok']}"
        )
        if r["col_dif"] or r["ex_dif"]:
            print("   dif colunas:", r["col_dif"], " dif exibicoes:", r["ex_dif"])
