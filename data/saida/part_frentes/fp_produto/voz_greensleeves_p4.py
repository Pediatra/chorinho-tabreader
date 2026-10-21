"""Ajuste 2 (P4): vozes do compasso 8 do greensleeves T03, e as pausas do recorte. Só lê."""

import json
from pathlib import Path

from tab import partitura_video as pv
from tab.partitura_gabarito import ler_partitura

STEM = "greensleeves_guia_de_estudio_partitura_tab_pdf"
PASTA = Path("/app/data/saida/part_frentes/fp_produto/video") / STEM
indice = json.loads((PASTA / "recortes" / "indice.json").read_text(encoding="utf-8"))
entrada = next(e for e in indice if e["id"] == "T03")
omr = PASTA / "omr"
vozes = pv._vozes_do_recorte(entrada, omr)
print("vozes por compasso (T03):", {k: sorted(v) for k, v in vozes.items()})
print("pausas x (T03):", [round(x, 1) for x in pv._pausas_do_recorte(entrada, omr)])
leitura = ler_partitura(omr / "audiveris" / "x2_margem_herdada" / "T03" / "saida.musicxml")
for compasso in leitura["compassos"]:
    if compasso["numero"] == "8":
        print("compasso 8, símbolos:")
        for s in compasso["simbolos"]:
            print(
                f"  voz {s['voz']} pausa {s['pausa']} midi {s['midi']}"
                f" figura {s['figura']} t {s['t']}"
            )
