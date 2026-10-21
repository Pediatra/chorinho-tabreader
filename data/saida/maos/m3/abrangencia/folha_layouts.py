"""Folha de conferência: um quadro (presenca_06) de cada um dos 30 vídeos da amostra."""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

PASTA = Path("/app/data/saida/maos/m3/abrangencia")
CACHE = Path("/cache/png")
LARGURA, ALTURA = 480, 270
COLUNAS = 5


def main() -> None:
    amostra = json.loads((PASTA / "amostra.json").read_text(encoding="utf-8"))
    linhas = (len(amostra) + COLUNAS - 1) // COLUNAS
    folha = Image.new("RGB", (COLUNAS * LARGURA, linhas * (ALTURA + 22)), (30, 30, 30))
    desenho = ImageDraw.Draw(folha)
    for i, r in enumerate(amostra):
        x = (i % COLUNAS) * LARGURA
        y = (i // COLUNAS) * (ALTURA + 22)
        pasta = CACHE / Path(r["_pasta"]).name
        quadro = Image.open(pasta / "presenca_06.png").convert("RGB")
        quadro.thumbnail((LARGURA, ALTURA))
        folha.paste(quadro, (x, y + 22))
        desenho.text((x + 4, y + 4), f"#{i:02d} {r['canal'][:14]} | {r['arquivo'][:40]}", fill=(255, 255, 0))
    folha.save(PASTA / "folha_layouts.jpg", quality=85)
    print("ok", folha.size)


if __name__ == "__main__":
    sys.exit(main())
