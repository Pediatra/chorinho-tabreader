"""Ajuste 2 da P4 (rodada 3027): notas da tab que voltaram a entrar desde o Ajuste 1.

Só lê. Compara as completadas (símbolos `tab_completada`) dos documentos do Ajuste 1
(`fp_produto/ajuste1/`) com os novos (`fp_produto/video/`). A chave de cada nota é
(vídeo, recorte, x do evento, altura escrita, tipo). Imprime as que voltaram e as que saíram,
e as 5 primeiras de acorde fora da tela 10, em ordem de vídeo, tela e x.

Uso (dentro do container): python voltaram_p4.py
"""

import json
from pathlib import Path

from tab.partitura_completar_pauta import _nome

ANTIGO = Path("/app/data/saida/part_frentes/fp_produto/ajuste1")
NOVO = Path("/app/data/saida/part_frentes/fp_produto/video")
GYM = "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"
CURTO = {
    "greensleeves_guia_de_estudio_partitura_tab_pdf": "greensleeves",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab": "south",
    GYM: "gym",
}


def chaves(raiz, stem):
    """Notas completadas de um documento, com a chave de cada uma."""
    doc = json.loads((raiz / f"{stem}.partitura.json").read_text(encoding="utf-8"))
    saida = {}
    for pauta in doc["pautas"]:
        for evento in pauta["eventos"]:
            tipo = "isolado" if evento["par"] and evento["par"]["metodo"] == "tab" else "acorde"
            for simbolo in evento["simbolos"]:
                if simbolo["origem"] != "tab_completada":
                    continue
                chave = (
                    stem, pauta["recorte"], round(evento["x_quadro"], 1),
                    simbolo["midi_escrito"], tipo,
                )
                saida[chave] = {
                    "tela": pauta["tela"],
                    "compasso": evento["compasso"],
                }
    return saida


def main():
    voltaram = []
    sairam = []
    for stem in CURTO:
        antes = chaves(ANTIGO, stem)
        depois = chaves(NOVO / stem, stem)
        for chave in sorted(set(depois) - set(antes), key=lambda c: (c[1], c[2])):
            voltaram.append((chave, depois[chave]))
        for chave in sorted(set(antes) - set(depois), key=lambda c: (c[1], c[2])):
            sairam.append((chave, antes[chave]))
    print(f"voltaram a entrar: {len(voltaram)}; saíram desde o Ajuste 1: {len(sairam)}")
    for (stem, recorte, x, midi, tipo), info in voltaram:
        print(
            f"  volta: {CURTO[stem]} tela {info['tela']} {recorte} x {x} {_nome(midi)}"
            f" {tipo} compasso {info['compasso']}"
        )
    for (stem, recorte, x, midi, tipo), info in sairam:
        print(
            f"  sai:   {CURTO[stem]} tela {info['tela']} {recorte} x {x} {_nome(midi)}"
            f" {tipo} compasso {info['compasso']}"
        )
    print("cinco de acorde fora da tela 10 que voltaram:")
    escolhidas = [
        (chave, info)
        for chave, info in voltaram
        if chave[4] == "acorde" and not (chave[0] == GYM and info["tela"] == 10)
    ][:5]
    for (stem, recorte, x, midi, tipo), info in escolhidas:
        print(
            f"  {CURTO[stem]}|{info['tela']}|{recorte}|{x}|{midi}|{_nome(midi)}|compasso {info['compasso']}"
        )


if __name__ == "__main__":
    main()
