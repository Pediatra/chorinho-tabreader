"""Revisão do modo ataque (dono, 2026-10-23): confere cada gabarito antes de subir.

Para cada fonte: a ferramenta sobe (o ouro não diverge do estado) e as chaves
``t<tela>-n<k>`` do arquivo de ataque apontam, no ouro, para a nota de mesma corda e casa
(a ferramenta numera na ordem do ouro). Imprime os problemas; não grava nada.

Uso (container): python data/saida/tablatura/tab_rotulo/revisao_ataque/conferir_fontes.py
"""

import json
from pathlib import Path

from tab.tablatura.ouro import ouro_video as O

R = Path("/app/data/saida/tablatura")
G = Path("/app/data/gold/ouro_video")
R2 = R / "tab_rotulo" / "r2"
#: nome -> (pasta da ferramenta, ouro, arquivo de ataque)
FONTES = {
    "t85": (R / "t85/passe_ataque/ferramenta", R / "t85/passe_ataque/conferencia_t85_servida.json", R2 / "conferir_t85/ataque_t85.json"),
    "t84": (R / "t84/ferramenta", R / "t84/passe_ataque/conferencia_t84_servida.json", R2 / "conferir_t84/ataque_t84.json"),
    "t83": (R / "t83/ferramenta", R / "t83/ferramenta/conferencia_t83.json", R2 / "conferir_t83/ataque_t83.json"),
    "t82": (R / "t82/ferramenta", R / "t82/ferramenta/conferencia_t82.json", R2 / "conferir_novos/ataque_t82.json"),
}
for nome, slug, arq in (
    ("eob", "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics", "conferir/ataque_end_of_beginning.json"),
    ("lavie", "la_vie_en_rose_edith_piaf_tab", "conferir/ataque_la_vie_en_rose.json"),
    ("pat", "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover", "conferir/ataque_pat_metheny.json"),
    ("room335", "tabroom_335_larry_carlton_fingerstyle_guitar", "conferir/ataque_tabroom_335.json"),
    ("greensleeves", "greensleeves_guia_de_estudio_partitura_tab_pdf", "conferir_novos/ataque_greensleeves.json"),
    ("gymnopedie", "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar", "conferir_novos/ataque_gymnopedie.json"),
    ("retrato", "retrato_brasileiro_v2", "conferir_novos/ataque_retrato.json"),
    ("south", "south_american_music_easy_guitar_tutorial_with_sheet_and_tab", "conferir_novos/ataque_south_american.json"),
):
    FONTES[nome] = (R / "ouro_video" / slug, G / f"{slug}.json", R2 / arq)


def main() -> None:
    """Confere e imprime."""
    for nome, (pasta, ouro_p, ataque_p) in FONTES.items():
        pre = json.loads((pasta / "pre.json").read_text(encoding="utf-8"))
        ouro = json.loads(ouro_p.read_text(encoding="utf-8"))
        ataque = json.loads(ataque_p.read_text(encoding="utf-8"))
        div = O.divergencias_do_estado(pre, ouro)
        telas = {int(t["id"]): t["notas"] for t in ouro["telas"]}
        ruins = []
        for a in ataque["notas"]:
            k = int(a["nota"].split("-n")[1])
            n = telas.get(int(a["tela"]), [])
            if k >= len(n) or (n[k]["corda"], str(n[k]["casa"])) != (a["corda"], str(a["casa"])):
                ruins.append(a["nota"])
        print(f"{nome}: diverge {len(div)} | chaves ruins {len(ruins)} de {len(ataque['notas'])}"
              f" {ruins[:6]} | telas {len(ouro['telas'])}", flush=True)


if __name__ == "__main__":
    main()
