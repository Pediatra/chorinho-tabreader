"""Casos olhados da P4 (rodada 3027): recorte ampliado de 5 notas completadas, e os candidatos
de harmônico que entraram completados. Só lê; grava PNG em fp_produto/casos.

Uso (dentro do container): python casos_p4.py
"""

import json
from pathlib import Path

import cv2

NOVO = Path("/app/data/saida/part_frentes/fp_produto/video")
E1 = Path("/app/data/saida/part_frentes/fp_produto/e1_passo2.json")
SAIDA = Path("/app/data/saida/part_frentes/fp_produto/casos")
CURTO = {
    "greensleeves_guia_de_estudio_partitura_tab_pdf": "greensleeves",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab": "south",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar": "gym",
}
ALVOS = [
    ("greensleeves_guia_de_estudio_partitura_tab_pdf", "isolado", None),
    ("south_american_music_easy_guitar_tutorial_with_sheet_and_tab", "acorde", None),
    ("south_american_music_easy_guitar_tutorial_with_sheet_and_tab", "isolado", None),
    ("gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar", "acorde", 4),
    ("gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar", "isolado", None),
]


def achar(doc, tipo, tela):
    """Primeira nota completada do tipo pedido (na tela, se houver)."""
    for pauta in doc["pautas"]:
        if tela is not None and pauta["tela"] != tela:
            continue
        for evento in pauta["eventos"]:
            isolado = evento["par"] is not None and evento["par"]["metodo"] == "tab"
            if (tipo == "isolado") != isolado:
                continue
            for simbolo in evento["simbolos"]:
                if simbolo["origem"] == "tab_completada":
                    return pauta, evento, simbolo
    raise LookupError(f"sem nota {tipo} na tela {tela}")


def recortar(stem, pauta, evento, simbolo):
    """PNG ampliado 3x, 120 px de largura em volta do x da nota, com uma linha vermelha."""
    x0 = pauta["caixa_quadro"][0]
    imagem = cv2.imread(str(NOVO / stem / "recortes" / f"{pauta['recorte']}.png"))
    xr = int(round(evento["x_quadro"] - x0))
    xa = max(0, xr - 60)
    xb = min(imagem.shape[1], xr + 60)
    corte = cv2.resize(imagem[:, xa:xb], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.line(corte, ((xr - xa) * 3, 0), ((xr - xa) * 3, corte.shape[0]), (0, 0, 255), 1)
    SAIDA.mkdir(parents=True, exist_ok=True)
    tipo = "isolado" if evento["par"]["metodo"] == "tab" else "acorde"
    nome = (
        f"{CURTO[stem]}_{pauta['recorte']}_c{evento['compasso']}"
        f"_m{simbolo['midi_escrito']}_{tipo}.png"
    )
    cv2.imwrite(str(SAIDA / nome), corte)
    return nome


def main():
    for stem, tipo, tela in ALVOS:
        doc = json.loads((NOVO / stem / f"{stem}.partitura.json").read_text(encoding="utf-8"))
        pauta, evento, simbolo = achar(doc, tipo, tela)
        nome = recortar(stem, pauta, evento, simbolo)
        print(
            f"{nome}: tela {pauta['tela']} recorte {pauta['recorte']} compasso"
            f" {evento['compasso']} x {evento['x_quadro']} nome {simbolo['nome']}"
            f" voz {simbolo['voz']} figura {simbolo['figura']} harmonico"
            f" {simbolo.get('harmonico', False)}"
        )
    e1 = json.loads(E1.read_text(encoding="utf-8"))
    candidatos = [n for n in e1["completadas"] if n["candidato_oitava"]]
    print(f"candidatos de oitava entre as contadas (E1): {len(candidatos)}")
    for n in candidatos:
        print(
            f"  {CURTO.get(n['video'], n['video'][:30])} tela {n['tela']} recorte {n['recorte']}"
            f" compasso {n['compasso']} midi {n['midi']} tipo {n['tipo']}"
        )


if __name__ == "__main__":
    main()
