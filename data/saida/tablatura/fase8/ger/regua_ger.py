"""Fase 8: CA-2/3/5/6/7 por vídeo nos 8 ouros, leitor rede, modelo da dobra que não viu o vídeo.

Uso (container): python /app/data/saida/fase8/rede/regua.py
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/app")
from tab.esquema import validar  # noqa: E402

SAIDA = Path(sys.argv[1])
SUF = sys.argv[2] if len(sys.argv) > 2 else ""
SAIDA.mkdir(parents=True, exist_ok=True)
DOBRA = {
    "greensleeves_guia_de_estudio_partitura_tab_pdf": 2,
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar": 2,
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab": 3,
    "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover": 3,
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics": 4,
    "tabroom_335_larry_carlton_fingerstyle_guitar": 4,
}


def main() -> int:
    """Produto + régua + esquema para cada ouro."""
    for slug, dobra in DOBRA.items():
        ouro = f"/app/data/gold/ouro_video/{slug}.json"
        video = "/acervo/" + json.loads(Path(ouro).read_text(encoding="utf-8"))["video"]
        pred = SAIDA / f"{slug}.json"
        if not pred.exists():
            subprocess.run(
                [sys.executable, "-m", "tab.video", video, "--json", str(pred),
                 "--detector", f"/app/artefatos/detector_tab_v3ft_d{dobra}{SUF}/modelo.pt"],
                check=True, cwd="/app",
            )
        rel = SAIDA / f"{slug}.regua.txt"
        with rel.open("w", encoding="utf-8") as f:
            subprocess.run(
                [sys.executable, "-m", "tab.avaliar_video", "--ouro", ouro, "--pred",
                 str(pred), "--json", str(rel.with_suffix(".json"))],
                check=True, cwd="/app", stdout=f,
            )
        erros = validar(json.loads(pred.read_text(encoding="utf-8")))
        print("==", slug, flush=True)
        print(rel.read_text(encoding="utf-8"), flush=True)
        print("esquema:", len(erros), "erros", erros[:3], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
