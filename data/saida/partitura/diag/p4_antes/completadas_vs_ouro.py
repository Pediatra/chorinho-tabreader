"""Cada nota completada (tab_completada) contra a tab do gabarito do dono, pelo x."""
import json
from collections import Counter
from pathlib import Path

from tab.musicxml import midi_da_corda
from tab.partitura_avaliar import SEMITONS_ESCRITA
from tab.partitura_pareamento import _carregar_ouro

STEMS = ["greensleeves_guia_de_estudio_partitura_tab_pdf",
         "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
         "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"]
TOL = 5.0
ouro = _carregar_ouro()
tot = Counter()
for stem in STEMS:
    produto = json.loads(Path(f"data/saida/fase8/rede/{stem}.json").read_text())
    gab = ouro[produto["video"]["arquivo"]][0]
    telas = {t["id"]: t for t in gab["telas"]}
    doc = json.loads(Path(f"data/saida/partitura/video/{stem}/{stem}.partitura.json").read_text())
    for pauta in doc["pautas"]:
        notas = telas.get(pauta["tela"], {}).get("notas", [])
        for e in pauta["eventos"]:
            for s in e["simbolos"]:
                if s["origem"] != "tab_completada":
                    continue
                perto = [midi_da_corda(int(n["corda"]), int(n["casa"])) for n in notas
                         if abs(float(n["x_centro_quadro"]) - e["x_quadro"]) <= TOL]
                perto = {m + SEMITONS_ESCRITA for m in perto if m is not None}
                grupo = "tela10" if stem.startswith("gym") and pauta["tela"] == 10 else "resto"
                res = "certa" if s["midi_escrito"] in perto else ("outra_altura" if perto else "sem_nota_no_x")
                tot[(grupo, res)] += 1
                if grupo == "resto" and res != "certa":
                    print(stem[:12], pauta["tela"], round(e["x_quadro"], 1), s["nome"], res, sorted(perto))
print(dict(sorted(tot.items())))
