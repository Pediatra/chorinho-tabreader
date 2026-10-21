"""Reprocessa herdar_condicao nos 3 produtos (sem Audiveris) e guarda backups antes."""
import json
import shutil
from pathlib import Path

from tab.caminhos import RAIZ
from tab.partitura_omr import herdar_condicao
from tab.partitura_video import PASTA_VIDEO

DIAG = RAIZ / "data/saida/partitura/diag/herdar_clave"
STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
]

for stem in STEMS:
    pasta = PASTA_VIDEO / stem
    omr = pasta / "omr" / "audiveris"
    herdada_velha = json.loads((omr / "x2_margem_herdada" / "herdada.json").read_text(encoding="utf-8"))
    shutil.copy2(omr / "x2_margem_herdada" / "herdada.json", DIAG / f"{stem}_herdada_antes.json")
    shutil.copytree(omr / "x2_margem_herdada", DIAG / f"{stem}_x2_margem_herdada_antes", dirs_exist_ok=True)
    shutil.copy2(pasta / f"{stem}.partitura.json", DIAG / f"{stem}.partitura_antes.json")
    execucao = json.loads((omr / "x2_margem" / "execucao.json").read_text(encoding="utf-8"))
    indice = json.loads((pasta / "recortes" / "indice.json").read_text(encoding="utf-8"))
    no_exec = {r["id"] for r in execucao}
    do_video = [e for e in indice if not e["sem_pauta"] and e["id"] in no_exec]
    nova = herdar_condicao(execucao, do_video, omr / "x2_margem_herdada", RAIZ)
    velha = {r["id"]: r for r in herdada_velha}
    print(f"== {stem}")
    for r in nova:
        a = velha[r["id"]]["fifths_aplicado"]
        if a != r["fifths_aplicado"]:
            print(f"  {r['id']}: fifths_aplicado {a} -> {r['fifths_aplicado']} (tinha_clave {r['tinha_clave']})")
    print(f"  total recortes {len(nova)}; aplicados depois {sum(r['fifths_aplicado'] is not None for r in nova)}")
