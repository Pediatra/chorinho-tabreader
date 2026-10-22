"""n4 passo 4-5: avaliação em vídeo DEIXADO DE FORA, por dobra (validação cruzada).

Para cada dobra d: carrega artefatos/detector_tab_v3ft_d<d>/modelo.pt e roda
medir.medir_video NOS dois vídeos da dobra (fora do treino dessa dobra), com a base
(oficial_3) e o v3_s1 e o ft no mesmo quadro. Métricas: tab.avaliar_video._metricas_par
(via medir). Casa errada: medir3.pares_casa (ouro -> lido).

Saídas: data/saida/n4/avaliacao.txt e avaliacao.json.

Uso (container, cwd /app):
    python /app/data/saida/n4/avaliar_n4.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app")

import medir as M  # noqa: E402
import medir3 as M3  # noqa: E402
from tab import detector_tab  # noqa: E402
from tab.digito import carregar as carregar_discriminador  # noqa: E402
from tab.reconhecer import carregar_modelo  # noqa: E402

SAIDA = Path("/app/data/saida/n4")
ARTEFATOS = Path("/app/artefatos")
PARTIDA = "v3_s1"
DOBRAS = {
    1: ("retrato_brasileiro_v2", "la_vie_en_rose_edith_piaf_tab"),
    2: (
        "greensleeves_guia_de_estudio_partitura_tab_pdf",
        "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
    ),
    3: (
        "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
        "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
    ),
    4: (
        "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
        "tabroom_335_larry_carlton_fingerstyle_guitar",
    ),
}


def main() -> int:
    """Roda cada dobra nos seus dois vídeos deixados de fora e grava o relatório."""
    videos = M.videos_do_run()
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    videos.setdefault(M.EXTRA_SLUG, "/acervo/" + extra["video"])
    base = carregar_modelo(str(M.MODELO_BASE))
    disc = carregar_discriminador()
    v3 = detector_tab.carregar(ARTEFATOS / "detector_tab_v3_s1" / "modelo.pt")

    linhas: list[str] = [
        "Avaliação n4: ajuste fino com validação cruzada por vídeo (4 dobras).",
        "Cada vídeo é medido SOMENTE pelo modelo da dobra em que ele ficou de fora.",
        "BASE = oficial_3; v3_s1 = partida sem ajuste; ft = modelo da dobra.",
        "",
    ]
    json_saida: dict = {"videos": {}, "dobras": {}}
    total: dict[str, list[dict]] = {"base": [], "v3_s1": [], "ft": []}
    casa_total: dict[str, Counter] = {"v3_s1": Counter(), "ft": Counter()}
    casa_video: dict[str, dict[str, Counter]] = {}

    for d, fora in DOBRAS.items():
        ft = detector_tab.carregar(ARTEFATOS / f"detector_tab_v3ft_d{d}" / "modelo.pt")
        for slug in fora:
            linhas.append(f"## dobra {d}: {slug}")
            regs = M.medir_video(slug, videos[slug], base, {"v3_s1": v3, "ft": ft}, disc)
            m_base = [r["m_base"] for r in regs]
            m_v3 = [r["m_det"]["v3_s1"] for r in regs]
            m_ft = [r["m_det"]["ft"] for r in regs]
            total["base"] += m_base
            total["v3_s1"] += m_v3
            total["ft"] += m_ft
            res = {
                "base": M.resumo(m_base),
                "v3_s1": M.resumo(m_v3),
                "ft": M.resumo(m_ft),
            }
            linhas.append(M.linha_resumo("BASE", res["base"]))
            linhas.append(M.linha_resumo("v3_s1", res["v3_s1"]))
            linhas.append(M.linha_resumo(f"ft_d{d}", res["ft"]))
            json_saida["videos"][slug] = {"dobra": d, **res}
            casa_video[slug] = {}
            for chave in ("v3_s1", "ft"):
                pares = Counter()
                for reg in regs:
                    if reg["sem_painel"] or reg["cand"] is None:
                        continue
                    for _corda, c_ouro, c_lido, _x in M3.pares_casa(reg, chave):
                        pares[(c_ouro, c_lido)] += 1
                casa_total[chave] += pares
                casa_video[slug][chave] = pares
            linhas.append(
                f"  telas={len(regs)} sem_painel={sum(r['sem_painel'] for r in regs)}"
            )
            linhas.append("")
        json_saida["dobras"][d] = list(fora)

    linhas.append("## TOTAL (8 vídeos, cada um medido pelo modelo que não o viu)")
    res_total = {k: M.resumo(v) for k, v in total.items()}
    linhas.append(M.linha_resumo("BASE", res_total["base"]))
    linhas.append(M.linha_resumo("v3_s1", res_total["v3_s1"]))
    linhas.append(M.linha_resumo("ft_cv", res_total["ft"]))
    json_saida["total"] = res_total
    linhas.append("")
    linhas.append("## Casa errada (ouro -> lido), ft_cv vs v3_s1, total")
    for chave in ("v3_s1", "ft"):
        linhas.append(f"  {chave}: {sum(casa_total[chave].values())} pares com casa errada")
        for (o, lido), n in casa_total[chave].most_common(20):
            linhas.append(f"    ouro {o} -> lido {lido}: {n}")
    json_saida["casa_errada"] = {
        chave: {f"{o}->{lido}": n for (o, lido), n in casa_total[chave].items()}
        for chave in casa_total
    }
    json_saida["casa_errada_por_video"] = {
        slug: {c: {f"{o}->{l}": n for (o, l), n in p.items()} for c, p in v.items()}
        for slug, v in casa_video.items()
    }
    (SAIDA / "avaliacao.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (SAIDA / "avaliacao.json").write_text(
        json.dumps(json_saida, indent=1, ensure_ascii=False, default=float) + "\n",
        encoding="utf-8",
    )
    print("\n".join(linhas), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
