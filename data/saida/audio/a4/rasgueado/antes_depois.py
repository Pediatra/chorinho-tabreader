"""Tabela antes/depois (v2 vs v2.1) por vídeo: colunas com tempo, recusas, alarmes, rasgueados."""

import json
from collections import Counter

RAIZ = "/var/home/gabriel/Projects/chorinho-dataset"
A5 = f"{RAIZ}/data/saida/audio/a5"
A4 = f"{RAIZ}/data/saida/audio/a4/lote1"
PARES = {"mvp": (f"{A5}/mvp.audio.json", f"{A5}/v21_mvp.audio.json")}
for ap in ["iwaki_la_vie_en_rose", "kimny_from_this_place", "shin_izumi_room_335"]:
    PARES[ap] = (f"{A5}/{ap}.audio.json", f"{A5}/v21_{ap}.audio.json")
for ap in json.load(open(f"{A4}/apelidos.json")):
    PARES[ap] = (f"{A4}/{ap}.audio.json", f"{A4}/v21_{ap}.audio.json")
ORDEM = ["mvp", "iwaki_la_vie_en_rose", "kimny_from_this_place", "shin_izumi_room_335",
         "iwaki_michelle", "iwaki_fly_me_to_the_moon", "kimny_gunjo", "kimny_bach_prelude",
         "shin_izumi_giant_steps", "transcriptor_charagua", "transcriptor_campanitas",
         "guitarous_sakura", "shin_izumi_dream_wish", "paolo_those_who_wait"]


def resumo(d):
    cols = d["colunas"]
    com_tempo = sum(1 for c in cols if c["t_audio"] is not None)
    exs = d["exibicoes"]
    recusadas = sum(1 for e in exs if e["recusada"])
    alarmes = sum(1 for e in exs if e["alarme_leitura"])
    rasg = sum(1 for e in exs if e.get("rasgueado"))
    abaf = sum(1 for c in cols if c.get("tipo") == "abafada" and c["t_audio"] is not None)
    motivos = Counter(c["motivo"] for c in cols if c["t_audio"] is None)
    return {"n": len(cols), "com": com_tempo, "exs": len(exs), "rec": recusadas,
            "alarm": alarmes, "rasg": rasg, "abaf": abaf, "motivos": motivos}


print(f"{'video':24}{'colunas':>9}{'com_tempo v2':>14}{'v2.1':>7}{'abaf_aff':>10}"
      f"{'exib_recusadas v2':>19}{'v2.1':>6}{'alarmes v2':>12}{'v2.1':>6}{'rasgueado':>11}")
saida = {}
for ap in ORDEM:
    antes = resumo(json.load(open(PARES[ap][0])))
    depois = resumo(json.load(open(PARES[ap][1])))
    saida[ap] = (antes, depois)
    print(f"{ap:24}{depois['n']:>9}{antes['com']:>14}{depois['com']:>7}{depois['abaf']:>10}"
          f"{antes['rec']:>19}{depois['rec']:>6}{antes['alarm']:>12}{depois['alarm']:>6}"
          f"{depois['rasg']:>11}")
tot = lambda k, i: sum(saida[a][i][k] for a in ORDEM)
print(f"{'TOTAL':24}{tot('n',1):>9}{tot('com',0):>14}{tot('com',1):>7}{tot('abaf',1):>10}"
      f"{tot('rec',0):>19}{tot('rec',1):>6}{tot('alarm',0):>12}{tot('alarm',1):>6}{tot('rasg',1):>11}")
print("\nRecusas por motivo no campanitas (v2 -> v2.1):")
print(" v2  ", dict(saida["transcriptor_campanitas"][0]["motivos"].most_common()))
print(" v2.1", dict(saida["transcriptor_campanitas"][1]["motivos"].most_common()))
