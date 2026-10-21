"""Estruturas horizontais acima das pautas cortadas (agua P01a, canon P06a)."""
import json

import numpy as np

from tab.caminhos import SAIDA, acervo
from tab.partitura_recortes import (
    _abrir,
    _cinza,
    _mascaras_de_tinta,
    _tinta_escura,
    estruturas_horizontais,
)
from tab.leitor import quadro_em

SP = SAIDA / "partitura" / "sem_produto"
for slug, rid in [
    ("agua_de_beber_a.c_jobim_arrangement_for_guitar_tutorial_with_sheet_and_tab", "P01a"),
    ("canon_de_pachelbel_para_guitarra_niveles_1-4", "P06a"),
]:
    ent = next(e for e in json.loads((SP / slug / "recortes/indice.json").read_text())
               if e.get("id") == rid)
    q = quadro_em(str(acervo() / ent["video"]), ent["t"])
    cinza = _cinza(q)
    escura, clara = _mascaras_de_tinta(cinza)
    aberta = _abrir(escura if _tinta_escura(cinza) else clara, cinza.shape[1])
    print(slug[:10], rid, "ys", ent["ys"], "caixa", ent["caixa_recorte"])
    for s in estruturas_horizontais(q):
        if ent["ys"][0] - 120 < s.y < ent["ys"][0]:
            a, b = int(s.y - s.altura / 2 + 0.5), int(s.y + s.altura / 2 + 0.5)
            cob = np.count_nonzero(aberta[a : b + 1].any(axis=0)[s.x0 : s.x1 + 1])
            print(f"  y {s.y} x {s.x0}-{s.x1} alt {s.altura} cobertura {cob/(s.x1-s.x0+1):.2f}")
