"""Mede o .partitura.json do produto contra a tab do gabarito (todas as telas do ouro)."""

import json
import sys
from pathlib import Path

from tab.partitura_avaliar import _carregar_ouro, contar, referencia_do_recorte
from tab.partitura_video import eventos_do_produto

STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]
P1 = {  # recorte P1 -> (stem idx, tela)
    "R01": (0, 1), "R02": (0, 2), "R03": (0, 3), "R04": (0, 4),
    "R05": (1, 1), "R06": (1, 2), "R07": (1, 3),
    "R08": (2, 1), "R09": (2, 3), "R10": (2, 5), "R11": (2, 7), "R12": (2, 9),
}
CHAVES = ["referencia", "certas", "altura_errada", "faltando", "inventada"]


def somar(a, b):
    for k in CHAVES:
        a[k] = a.get(k, 0) + b[k]


def main():
    ouro = _carregar_ouro()
    base = {}
    for rid, chave in P1.items():
        doc = json.loads(Path(f"data/saida/partitura/p3/pareamento/{rid}.json").read_text())
        base[chave] = doc["resumo"]["tab_depois"]
    tot = {"p1_12": {}, "novo_12": {}, "novo_extra": {}, "tabprod_19": {}}
    for i, stem in enumerate(STEMS):
        produto = json.loads(Path(f"data/saida/fase8/rede/{stem}.json").read_text())
        gab = ouro[produto["video"]["arquivo"]]
        assert len(gab) == 1, stem
        telas = {t["id"]: t for t in gab[0]["telas"]}
        doc = json.loads(
            Path(f"data/saida/partitura/video/{stem}/{stem}.partitura.json").read_text()
        )
        for pauta in doc["pautas"]:
            tela = pauta["tela"]
            x0, _, x1, _ = pauta["caixa_quadro"]
            if tela not in telas:
                print(f"{stem[:12]} tela {tela}: sem gabarito")
                continue
            ref = referencia_do_recorte(telas[tela]["notas"], x0, x1)
            lib = [frozenset(s["midi_escrito"] for s in e["simbolos"]) for e in pauta["eventos"]]
            c, _ = contar(lib, ref, "exato")
            tp = [e.midis for e in eventos_do_produto(produto["notas"], tela, x0, x1)]
            ct, _ = contar(tp, ref, "exato")
            somar(tot["tabprod_19"], ct)
            linha = f"{stem[:12]} tela {tela:2d}: novo {[c[k] for k in CHAVES]}"
            if (i, tela) in base:
                somar(tot["p1_12"], base[(i, tela)])
                somar(tot["novo_12"], c)
                linha += f"  P1 {[base[(i, tela)][k] for k in CHAVES]}"
            else:
                somar(tot["novo_extra"], c)
            linha += f"  tab-produto {[ct[k] for k in CHAVES]}"
            print(linha)
    print("ordem:", CHAVES)
    for k, v in tot.items():
        print(k, [v.get(c, 0) for c in CHAVES])


if __name__ == "__main__":
    sys.exit(main())
