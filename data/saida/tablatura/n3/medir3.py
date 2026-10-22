"""Medição n3 (pedido 3): inventadas do v2_s1 e pares de casa errada dos v2.

Reusa medir.py (base, geometria, casamento) e medir2.py (recorte, folha). Saídas em
data/saida/n3/: inv2_<vid>_t<tela>_x<x>_c<corda>.png, inv2_<vid>_mont.png,
inv2_indice.txt, casa2_gre_<semente>.txt e casa2_<semente>_t..png.

Uso (container, cwd /app):
    python /app/data/saida/n3/medir3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import medir as M  # noqa: E402
import medir2 as M2  # noqa: E402
from tab import detector_tab  # noqa: E402
from tab.avaliar_video import casar_notas  # noqa: E402
from tab.digito import carregar as carregar_discriminador  # noqa: E402
from tab.reconhecer import carregar_modelo  # noqa: E402

SAIDA = M.SAIDA
CHAVES = ("v2_s1", "v2_s2", "v2_s3")
VIDEOS_INV = {
    "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover": "tfp",
    "greensleeves_guia_de_estudio_partitura_tab_pdf": "gre",
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics": "eob",
}
COR_CASA = (0, 0, 255)


def inventadas(reg: dict, chave: str) -> list[tuple[int, int, float, float]]:
    """(corda, casa, x_frame, confiança) das previsões da chave que não casaram."""
    previstas = reg["det_prev"].get(chave, [])
    pares = casar_notas(reg["notas_ouro"], previstas, reg["meia"])
    usadas = {j for _, j in pares}
    raw = reg["det_raw"][chave]
    return [
        (p.corda, p.casa, p.x, float(raw[j]["confianca"]))
        for j, p in enumerate(previstas)
        if j not in usadas
    ]


def pares_casa(reg: dict, chave: str) -> list[tuple[int, int, int, float]]:
    """(corda, casa_ouro, casa_previsto, x_frame) dos casados com casa diferente."""
    previstas = reg["det_prev"].get(chave, [])
    out = []
    for i, j in casar_notas(reg["notas_ouro"], previstas, reg["meia"]):
        n = reg["notas_ouro"][i]
        if int(n["casa"]) != previstas[j].casa:
            out.append((int(n["corda"]), int(n["casa"]), previstas[j].casa,
                        float(n["x_centro_quadro"])))
    return out


def folha(itens: list[tuple], destino: Path) -> None:
    """Folha com os recortes numerados, 4 por linha."""
    celulas = []
    for idx, it in enumerate(itens):
        img = cv2.imread(str(it[-1]))
        esc = 300 / img.shape[0]
        img = cv2.resize(img, None, fx=esc, fy=esc)
        img = cv2.copyMakeBorder(img, 0, 0, 0, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(img, f"#{idx}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 128, 255), 2)
        celulas.append(img)
    while len(celulas) % 4:
        celulas.append(np.full_like(celulas[0], 255))
    larg = max(c.shape[1] for c in celulas)
    celulas = [
        cv2.copyMakeBorder(c, 0, 0, 0, larg - c.shape[1], cv2.BORDER_CONSTANT,
                           value=(255, 255, 255))
        for c in celulas
    ]
    linhas = [np.hstack(celulas[i:i + 4]) for i in range(0, len(celulas), 4)]
    cv2.imwrite(str(destino), np.vstack(linhas))


def main() -> int:
    """Carrega os v2, mede os 3 vídeos e grava recortes, folhas e pares de casa."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    detectores = {
        k: detector_tab.carregar(M.DETECTORES_CAMINHO[k]) for k in CHAVES
    }
    base = carregar_modelo(str(M.MODELO_BASE))
    disc = carregar_discriminador()
    videos = M.videos_do_run()
    por_video = {}
    for slug in list(VIDEOS_INV) + ["greensleeves_guia_de_estudio_partitura_tab_pdf"]:
        por_video[slug] = M.medir_video(slug, videos[slug], base, detectores, disc)

    indice: list[str] = []
    rel: list[str] = ["# Inventadas do v2_s1 (contagem)"]
    for slug, abrev in VIDEOS_INV.items():
        itens = []
        for reg in por_video[slug]:
            if reg["sem_painel"] or reg["cand"] is None:
                continue
            for corda, casa, x, conf in inventadas(reg, "v2_s1"):
                nome = SAIDA / f"inv2_{abrev}_t{reg['id']}_x{int(x)}_c{corda}.png"
                M2.recorte(reg, x, corda, nome, [(f"v2 {casa}", COR_CASA, x, 0.0)])
                itens.append((reg["id"], corda, x, casa, conf, nome))
        rel.append(f"{slug}: {len(itens)}")
        for idx, (tid, corda, x, casa, conf, nome) in enumerate(itens):
            indice.append(
                f"{abrev}\t{idx}\ttela={tid}\tcorda={corda}\tx={x:.1f}\t"
                f"rotulo={casa}\tconf={conf:.3f}\t{nome.name}"
            )
        if itens:
            folha([(*it[:5], it[5]) for it in itens], SAIDA / f"inv2_{abrev}_mont.png")
    (SAIDA / "inv2_indice.txt").write_text("\n".join(indice) + "\n", encoding="utf-8")

    rel.append("")
    rel.append("# Casa errada (casados com casa diferente), por semente")
    gre = "greensleeves_guia_de_estudio_partitura_tab_pdf"
    for chave in CHAVES:
        pares = []
        for reg in por_video[gre]:
            if reg["sem_painel"] or reg["cand"] is None:
                continue
            for corda, c_ouro, c_prev, x in pares_casa(reg, chave):
                pares.append((reg["id"], corda, c_ouro, c_prev, x))
                nome = SAIDA / f"casa2_{chave}_t{reg['id']}_x{int(x)}_c{corda}.png"
                M2.recorte(reg, x, corda, nome,
                           [(f"ouro {c_ouro}", (0, 200, 0), x, -0.3),
                            (f"{chave} {c_prev}", COR_CASA, x, 0.3)])
        rel.append(f"{chave}: {len(pares)} pares")
        for tid, corda, c_ouro, c_prev, x in pares:
            rel.append(f"  tela={tid} corda={corda} x={x:.1f} ouro={c_ouro} {chave}={c_prev}")
    (SAIDA / "inv2_e_casa2.txt").write_text("\n".join(rel) + "\n", encoding="utf-8")
    print("\n".join(rel), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
