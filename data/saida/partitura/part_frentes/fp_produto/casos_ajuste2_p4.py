"""Ajuste 2 (P4): recortes ampliados das 5 notas de acorde que voltaram a entrar (fora da tela 10).

Só lê; grava PNG em fp_produto/casos_ajuste2. Cada recorte: 120 px de largura em volta do x do
evento, ampliado 3x, com uma linha vermelha no x.

Uso (dentro do container, em /app): python casos_ajuste2_p4.py
"""

import json
from pathlib import Path

import cv2

NOVO = Path("/app/data/saida/part_frentes/fp_produto/video")
SAIDA = Path("/app/data/saida/part_frentes/fp_produto/casos_ajuste2")
GYM = "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"
CURTO = {GYM: "gym"}
ALVOS = [
    # (stem, recorte, x do evento, altura escrita)
    (GYM, "T01", 1448.5, 82),
    (GYM, "T02", 478.5, 57),
    (GYM, "T02", 1679.0, 52),
    (GYM, "T03", 1224.5, 85),
    (GYM, "T04", 985.5, 52),
]


def achar(doc, recorte, x, midi):
    for pauta in doc["pautas"]:
        if pauta["recorte"] != recorte:
            continue
        for evento in pauta["eventos"]:
            if evento["x_quadro"] is None or abs(evento["x_quadro"] - x) > 0.6:
                continue
            for simbolo in evento["simbolos"]:
                if simbolo["origem"] == "tab_completada" and simbolo["midi_escrito"] == midi:
                    return pauta, evento, simbolo
    raise LookupError(f"{recorte} x {x} midi {midi} não achado")


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    for stem, recorte, x, midi in ALVOS:
        pasta = NOVO / stem
        doc = json.loads((pasta / f"{stem}.partitura.json").read_text(encoding="utf-8"))
        pauta, evento, simbolo = achar(doc, recorte, x, midi)
        imagem = cv2.imread(str(pasta / "recortes" / f"{recorte}.png"))
        xr = int(round(evento["x_quadro"] - pauta["caixa_quadro"][0]))
        xa = max(0, xr - 60)
        xb = min(imagem.shape[1], xr + 60)
        corte = cv2.resize(imagem[:, xa:xb], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        cv2.line(corte, ((xr - xa) * 3, 0), ((xr - xa) * 3, corte.shape[0]), (0, 0, 255), 1)
        nome = (
            f"{CURTO[stem]}_{recorte}_c{evento['compasso']}_m{midi}"
            f"_x{round(evento['x_quadro'])}_acorde_voz{simbolo['voz']}.png"
        )
        cv2.imwrite(str(SAIDA / nome), corte)
        print(
            f"{nome}: tela {pauta['tela']} compasso {evento['compasso']} x {evento['x_quadro']}"
            f" nota {simbolo['nome']} voz {simbolo['voz']}"
        )


if __name__ == "__main__":
    main()
