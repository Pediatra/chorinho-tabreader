"""n4 passo 1: cache das telas conferidas dos 8 ouros (roi, grade, notas no roi).

Para cada tela conferida: quadro em quadro_ref_s -> escolher_ou_mascara (roi, x0)
-> segmentar(roi) (linhas_y, passo). Notas do ouro: x_roi = x_centro_quadro - x0.
Grava n4/cache/<slug>__t<id>.png e .json.

Uso (container, cwd /app):
    python /app/data/saida/n4/extrair.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app")

import cv2  # noqa: E402

import medir as M  # noqa: E402
from tab import leitor  # noqa: E402
from tab.painel import escolher_ou_mascara  # noqa: E402
from tab.tabseg import segmentar  # noqa: E402

CACHE = Path("/app/data/saida/n4/cache")
SLUGS = (
    "retrato_brasileiro_v2",
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
    "la_vie_en_rose_edith_piaf_tab",
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
    "tabroom_335_larry_carlton_fingerstyle_guitar",
)


def main() -> int:
    """Extrai o cache e imprime telas e notas por vídeo."""
    CACHE.mkdir(parents=True, exist_ok=True)
    videos = M.videos_do_run()
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    videos.setdefault(M.EXTRA_SLUG, "/acervo/" + extra["video"])
    for slug in SLUGS:
        ouro = json.loads((M.OURO / f"{slug}.json").read_text(encoding="utf-8"))
        telas = [t for t in ouro["telas"] if t.get("conferida")]
        video = videos[slug]
        n_ok = n_notas = 0
        casas: dict[str, int] = {}
        for t in telas:
            frame = leitor.quadro_em(video, float(t["quadro_ref_s"]))
            cand = escolher_ou_mascara(frame) if frame is not None else None
            grade = segmentar(cand.roi) if cand is not None else None
            if cand is None or grade is None or grade.passo <= 0:
                print(f"  SEM PAINEL/GRADE {slug} tela {t['id']}", flush=True)
                continue
            nome = f"{slug}__t{t['id']}"
            cv2.imwrite(str(CACHE / f"{nome}.png"), cand.roi)
            notas = []
            for n in t["notas"]:
                casa = str(int(n["casa"]))
                casas[casa] = casas.get(casa, 0) + 1
                notas.append(
                    {
                        "corda": int(n["corda"]),
                        "casa": int(n["casa"]),
                        "x_roi": float(n["x_centro_quadro"]) - float(cand.x0),
                    }
                )
            meta = {
                "slug": slug,
                "tela": t["id"],
                "quadro_ref_s": float(t["quadro_ref_s"]),
                "x0": int(cand.x0),
                "linhas_y": [float(v) for v in grade.linhas_y],
                "passo": float(grade.passo),
                "notas": notas,
                "png": f"{nome}.png",
            }
            (CACHE / f"{nome}.json").write_text(
                json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            n_ok += 1
            n_notas += len(notas)
        print(
            f"{slug}: telas conferidas={len(telas)} extraidas={n_ok} notas={n_notas} "
            f"casas={dict(sorted(casas.items()))}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
