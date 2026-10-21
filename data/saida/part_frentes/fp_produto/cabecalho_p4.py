"""Diagnóstico da P4 (só leitura): notas isoladas completadas antes do primeiro compasso.

Uma nota da tab que cai à esquerda do primeiro compasso da pauta (clave, armadura, cabeçalho)
não é nota da música. Lista as isoladas nessa situação, por vídeo e recorte.

Uso (dentro do container): python cabecalho_p4.py
"""

import json
from pathlib import Path

NOVO = Path("/app/data/saida/part_frentes/fp_produto/video")
STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]

total = 0
for stem in STEMS:
    doc = json.loads((NOVO / stem / f"{stem}.partitura.json").read_text(encoding="utf-8"))
    for pauta in doc["pautas"]:
        if not pauta["compassos"] or pauta["compassos"][0]["x_quadro"] is None:
            continue
        lidas = [
            e["x_quadro"]
            for e in pauta["eventos"]
            if e["x_quadro"] is not None
            and any(s["origem"] != "tab_completada" for s in e["simbolos"])
        ]
        if not lidas:
            continue
        inicio = min(lidas)
        for evento in pauta["eventos"]:
            isolado = evento["par"] is not None and evento["par"]["metodo"] == "tab"
            if not isolado or evento["x_quadro"] is None:
                continue
            if evento["x_quadro"] < inicio:
                notas = [s["nome"] for s in evento["simbolos"] if s["origem"] == "tab_completada"]
                total += len(notas)
                print(
                    f"{stem[:12]} {pauta['recorte']} x={evento['x_quadro']:.1f}"
                    f" inicio do compasso 1={inicio:.1f} notas {notas}"
                )
print(f"isoladas completadas antes do início do compasso 1: {total}")
