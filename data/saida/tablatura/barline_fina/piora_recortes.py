"""Recorta, do quadro da tela, a primeira nota que a variante acrescenta em relação ao controle.

Uma nota é "nova" quando (tela, corda, x_quadro) existe na variante e não existe no controle.
O quadro é tirado no meio da primeira exibição da tela (ffmpeg), e o recorte mostra a faixa
do painel com uma linha vertical no x da nota.

Uso (dentro de /app): python data/saida/barline_fina/piora_recortes.py
"""

import json
import subprocess
from pathlib import Path

import cv2

D = Path("data/saida/barline_fina")
VIDEOS = {
    "retrato": "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4",
    "greensleeves": "/acervo/pablo romé/greensleeves 💚 guía de estudio 👌 partitura + tab + pdf.mp4",
    "gymnopedie": "/acervo/robert lunn/gymnopédie no.1 (erik satie) - includes sheet music⧸tab - classical guitar.mp4",
    "south_american": "/acervo/guitar dell ́arte/south american music (easy), guitar tutorial with sheet and tab.mp4",
    "tab_from_this_place": "/acervo/kimny's guitar/[ tab ] from this place - pat metheny ｜ fingerstyle guitar cover.mp4",
    "la_vie_en_rose": "/acervo/iwaki/la vie en rose - edith piaf ｜ tab.mp4",
    "end_of_beginning": "/acervo/kenneth acoustic/end of beginning - djo ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4",
}


def chave(n: dict) -> tuple:
    """Chave de identidade de uma nota para comparar controle e variante.

    Args:
        n: nota do JSON de transcrever.

    Returns:
        Tupla (tela, corda, x_quadro).
    """
    return (n["tela"], n["corda"], n["x_quadro"])


def main() -> int:
    """Gera um recorte por vídeo com a primeira nota nova da variante.

    Returns:
        Código de saída (0).
    """
    for nome, video in VIDEOS.items():
        var = json.loads((D / f"{nome}_variante.json").read_text(encoding="utf-8"))
        ctl = json.loads((D / f"{nome}_controle.json").read_text(encoding="utf-8"))
        base = {chave(n) for n in ctl["notas"]}
        novas = [n for n in var["notas"] if chave(n) not in base]
        if not novas:
            print(f"{nome}: sem nota nova")
            continue
        n = novas[0]
        tela = next(t for t in var["telas"] if t["id"] == n["tela"])
        ex = tela["exibicoes"][0]
        meio = (ex["t0"] + ex["t1"]) / 2
        quadro = D / f"piora_{nome}_quadro.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{meio:.3f}", "-i", video,
             "-frames:v", "1", str(quadro)],
            check=True,
        )
        img = cv2.imread(str(quadro))
        x = int(round(n["x_centro_quadro"]))
        px0, py0, px1, py1 = tela["painel"]
        x0, x1 = max(0, x - 90), min(img.shape[1], x + 90)
        y0, y1 = max(0, py0 - 10), min(img.shape[0], py1 + 10)
        recorte = img[y0:y1, x0:x1].copy()
        cv2.line(recorte, (x - x0, 0), (x - x0, recorte.shape[0] - 1), (0, 0, 255), 1)
        cv2.imwrite(str(D / f"piora_{nome}.png"), recorte)
        quadro.unlink()
        legenda = (
            f"{nome}: tela={n['tela']} corda={n['corda']} casa={n['casa']} "
            f"x_quadro={n['x_quadro']} x_centro={n['x_centro_quadro']} "
            f"t_meio_exibicao={meio:.3f}s painel={tela['painel']} "
            f"confianca={n['confianca']}"
        )
        (D / f"piora_{nome}.txt").write_text(legenda + "\n", encoding="utf-8")
        print(legenda)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
