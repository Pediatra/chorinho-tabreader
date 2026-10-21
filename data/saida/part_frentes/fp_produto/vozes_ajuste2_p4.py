"""Ajuste 2 (P4): para notas de interesse, o compasso, a corda, a voz da nota isolada e as
pausas próximas (x, voz). Só lê.

Uso (dentro do container, em /app): python vozes_ajuste2_p4.py
"""

import json
from pathlib import Path

from tab import partitura_video as pv
from tab.musicxml import midi_da_corda
from tab.partitura_avaliar import SEMITONS_ESCRITA
from tab.partitura_completar_pauta import _compasso_de_x, _voz_isolada

FRENTE = Path("/app/data/saida/part_frentes/fp_produto/video")
GYM = "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"
ALVOS = [
    ("greensleeves_guia_de_estudio_partitura_tab_pdf", "T03", 1768.1, 73),
    (GYM, "T07", 247.6, 52),
    (GYM, "T02", 708.0, 52),
    (GYM, "T01", 41.4, 64),
]

for stem, rec, x, midi in ALVOS:
    pasta = FRENTE / stem
    indice = json.loads((pasta / "recortes" / "indice.json").read_text(encoding="utf-8"))
    entrada = next(e for e in indice if e["id"] == rec)
    notas = json.loads(
        Path(f"/app/data/saida/fase8/rede/{stem}.json").read_text(encoding="utf-8")
    )["notas"]
    omr = pasta / "omr"
    pauta = pv._pauta_do_recorte(entrada, notas, omr)
    vozes = pv._vozes_do_recorte(entrada, omr)
    pausas = pv._pausas_do_recorte(entrada, omr)
    cordas = sorted(
        {
            int(n["corda"])
            for n in notas
            if n["tela"] == entrada["tela"]
            and midi_da_corda(int(n["corda"]), int(n["casa"])) is not None
            and midi_da_corda(int(n["corda"]), int(n["casa"])) + SEMITONS_ESCRITA == midi
            and abs(float(n["x_centro_quadro"]) - x) <= 6
        }
    )
    corda = cordas[0] if cordas else None
    compasso = _compasso_de_x(x, pauta["compassos"])
    voz = _voz_isolada(midi, {midi: corda} if corda else {}, compasso, vozes)
    print(f"{rec} x {x} midi {midi}: compasso {compasso}, corda {corda}, voz da nota {voz}")
    print(f"  vozes do compasso: {sorted(vozes.get(compasso, set()))}")
    print(f"  pausas a até 12 px (x, voz): {[(round(p, 1), v) for p, v in pausas if abs(p - x) <= 12]}")
