"""Roda o homr nativo nos 3 recortes do gabarito sem produto (rodada 3024)."""
import json
from pathlib import Path

from tab.partitura_omr import rodar_um

D = Path("data/saida/partitura/diag/homr_sem_produto").resolve()
SP = Path("data/saida/partitura/sem_produto").resolve()
PARES = [
    ("agua_de_beber_a.c_jobim_arrangement_for_guitar_tutorial_with_sheet_and_tab", "P01a"),
    ("athletic_theme_from_super_mario_world_guitar_tab_and_standard_notation_tvonguitar", "P01a"),
    ("canon_de_pachelbel_para_guitarra_niveles_1-4", "P06a"),
]
for slug, rid in PARES:
    indice = json.loads((SP / slug / "recortes/indice.json").read_text(encoding="utf-8"))
    item = next(e for e in indice if e.get("id") == rid)
    base = D / "homr" / slug[:16]
    base.mkdir(parents=True, exist_ok=True)
    r = rodar_um("homr", "nativo", item, base, origem=SP / slug / "recortes" / f"{rid}.png")
    print(slug[:16], rid, r["ok"], r["motivo"], r["segundos"], flush=True)
