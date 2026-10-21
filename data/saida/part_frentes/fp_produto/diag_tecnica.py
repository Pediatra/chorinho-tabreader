"""Diagnóstico da P4 (só leitura): valores de `tecnica` e chaves das notas dos 3 produtos."""

import collections
import json
import pathlib

RAIZ = pathlib.Path("/app/data/saida/fase8/rede")
STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]

for stem in STEMS:
    produto = json.loads((RAIZ / f"{stem}.json").read_text(encoding="utf-8"))
    notas = produto["notas"]
    tecnicas = collections.Counter(str(n.get("tecnica")) for n in notas)
    print(stem[:24], "notas", len(notas), "tecnica", dict(tecnicas))
    chaves = sorted({k for n in notas for k in n})
    print("  chaves:", chaves)
    print("  enfeite:", collections.Counter(str(n.get("enfeite")) for n in notas))
    harm = [n for n in notas if n.get("tecnica") == "harm"]
    print("  harm exemplos:", [(n["tela"], n["corda"], n["casa"]) for n in harm[:5]])
