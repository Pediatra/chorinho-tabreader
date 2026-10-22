"""Medição n3 (pedido 2): inventadas do s1, casa errada e curva de limiar.

Reusa medir.py (mesma base, mesma geometria, mesmo casamento). Saídas em data/saida/n3/:
  - inv_<vid>_t<tela>_x<x>_c<corda>.png : recorte ampliado de cada nota inventada do s1
  - inv_<vid>_mont.png + inv_indice.txt  : folhas para classificar (índice -> arquivo)
  - casa_<vid>_t<tela>_x<x>_c<corda>.png : pares ouro x s1 com casa diferente
  - limiar.txt : P/R do s1 por limiar de pico (0,5, 0,6, 0,7, 0,8)

Limiar: detector_tab._decodificar lê o global LIMIAR no momento da chamada; aqui o
valor do módulo é trocado em memória (tab/detector_tab.py não é editado).

Uso (container, cwd /app):
    python /app/data/saida/n3/medir2.py
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
from tab import detector_tab  # noqa: E402
from tab.avaliar_video import casar_notas  # noqa: E402
from tab.digito import carregar as carregar_discriminador  # noqa: E402
from tab.reconhecer import ALGARISMOS, carregar_modelo  # noqa: E402

SAIDA = M.SAIDA
VIDEOS_INV = {
    "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover": "tfp",
    "greensleeves_guia_de_estudio_partitura_tab_pdf": "gre",
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics": "eob",
}
LIMIARES = (0.5, 0.6, 0.7, 0.8)
COR_CINZA = (150, 150, 150)
COR_CASA = (0, 0, 255)
COR_OURO_BR = (0, 200, 0)


def recorte(reg: dict, x_frame: float, corda: int, destino: Path,
            rotulos: list[tuple[str, tuple[int, int, int], float, float]]) -> None:
    """Recorte ampliado do painel em volta de x_frame; cordas visíveis, marcas coloridas.

    rotulos: (texto, cor, x_frame, desloc_em_passos_da_corda) para cada marca.
    """
    cand = reg["cand"]
    passo = reg["passo"]
    linhas = reg["linhas"]
    xr = x_frame - cand.x0
    x0 = int(max(0, xr - 3 * passo))
    x1 = int(min(cand.roi.shape[1], xr + 3 * passo))
    y0 = int(max(0, linhas[0] - 1.5 * passo))
    y1 = int(min(cand.roi.shape[0], linhas[-1] + 1.5 * passo))
    esc = 4
    img = cv2.resize(cand.roi[y0:y1, x0:x1], None, fx=esc, fy=esc,
                     interpolation=cv2.INTER_CUBIC)
    for y in linhas:
        cv2.line(img, (0, int((y - y0) * esc)), (img.shape[1], int((y - y0) * esc)),
                 COR_CINZA, 1)
    for texto, cor, xf, desloc in rotulos:
        px = int((xf - cand.x0 - x0) * esc)
        py = int((linhas[corda - 1] + desloc * passo - y0) * esc)
        cv2.circle(img, (px, py), 9, cor, 2)
        cv2.putText(img, texto, (px + 12, py - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    cor, 1)
    cv2.imwrite(str(destino), img)


def inventadas_s1(reg: dict) -> list[tuple[int, int, float, float]]:
    """(corda, casa, x_frame, confianca) das previsões s1 que não casaram."""
    previstas = reg["det_prev"].get(1, [])
    if not previstas:
        return []
    pares = casar_notas(reg["notas_ouro"], previstas, reg["meia"])
    usadas = {j for _, j in pares}
    raw = reg["det_raw"][1]
    return [
        (p.corda, p.casa, p.x, float(raw[j]["confianca"]))
        for j, p in enumerate(previstas)
        if j not in usadas
    ]


def pares_casa_errada(reg: dict) -> list[tuple[int, int, int, float]]:
    """(corda, casa_ouro, casa_s1, x_frame) dos pares casados com casa diferente."""
    previstas = reg["det_prev"].get(1, [])
    if not previstas:
        return []
    out = []
    for i, j in casar_notas(reg["notas_ouro"], previstas, reg["meia"]):
        n = reg["notas_ouro"][i]
        if int(n["casa"]) != previstas[j].casa:
            out.append((int(n["corda"]), int(n["casa"]), previstas[j].casa,
                        float(n["x_centro_quadro"])))
    return out


def main() -> int:
    """Roda main() de medir.py (tabela principal), e depois as três medições."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    detectores = M.carregar_detectores()
    print("== tabela principal (medir.main)", flush=True)
    M.main()

    base = carregar_modelo(str(M.MODELO_BASE))
    disc = carregar_discriminador()
    videos = M.videos_do_run()
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    videos[M.EXTRA_SLUG] = "/acervo/" + extra["video"]
    por_video = {}
    for slug, video in videos.items():
        if (M.OURO / f"{slug}.json").exists():
            print(f"== medindo {slug}", flush=True)
            por_video[slug] = M.medir_video(slug, video, base, detectores, disc)

    if 1 not in detectores:
        print("s1 ausente; abortando partes 1-3", flush=True)
        return 1
    modelo_s1 = detectores[1]
    out: list[str] = []

    # ---- 1. inventadas do s1 ------------------------------------------------
    out.append("# 1. Inventadas do s1 (vídeos com mais inventadas)")
    indice: list[str] = []
    cont_total: dict[str, int] = {}
    for slug, abrev in VIDEOS_INV.items():
        regs = por_video[slug]
        itens = []
        for reg in regs:
            if reg["sem_painel"] or reg["cand"] is None:
                continue
            for corda, casa, x, conf in inventadas_s1(reg):
                nome = SAIDA / f"inv_{abrev}_t{reg['id']}_x{int(x)}_c{corda}.png"
                recorte(reg, x, corda, nome, [(f"s1 {casa}", COR_CASA, x, 0.0)])
                itens.append((reg["id"], corda, x, casa, conf, nome))
        cont_total[slug] = len(itens)
        out.append(f"{slug}: {len(itens)} inventadas")
        for idx, (tid, corda, x, casa, conf, nome) in enumerate(itens):
            indice.append(
                f"{abrev}\t{idx}\ttela={tid}\tcorda={corda}\tx={x:.1f}\t"
                f"rotulo={casa}\tconf={conf:.3f}\t{nome.name}"
            )
        # folha para classificação
        if itens:
            celulas = []
            for idx, it in enumerate(itens):
                img = cv2.imread(str(it[5]))
                h = 300
                esc_h = h / img.shape[0]
                img = cv2.resize(img, None, fx=esc_h, fy=esc_h)
                img = cv2.copyMakeBorder(img, 0, 0, 0, 2, cv2.BORDER_CONSTANT,
                                         value=(255, 255, 255))
                cv2.putText(img, f"#{idx}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 128, 255), 2)
                celulas.append(img)
            colunas = 4
            while len(celulas) % colunas:
                celulas.append(np.full_like(celulas[0], 255))
            larg = max(c.shape[1] for c in celulas)
            celulas = [cv2.copyMakeBorder(c, 0, 0, 0, larg - c.shape[1],
                                          cv2.BORDER_CONSTANT, value=(255, 255, 255))
                       for c in celulas]
            linhas_img = [np.hstack(celulas[i:i + colunas])
                          for i in range(0, len(celulas), colunas)]
            cv2.imwrite(str(SAIDA / f"inv_{abrev}_mont.png"), np.vstack(linhas_img))
    (SAIDA / "inv_indice.txt").write_text("\n".join(indice) + "\n", encoding="utf-8")

    # ---- 2. casa errada do s1 no greensleeves -------------------------------
    out.append("")
    out.append("# 2. Casa errada do s1 (pares casados com casa diferente)")
    gre = "greensleeves_guia_de_estudio_partitura_tab_pdf"
    for reg in por_video[gre]:
        if reg["sem_painel"] or reg["cand"] is None:
            continue
        for corda, c_ouro, c_s1, x in pares_casa_errada(reg):
            out.append(f"tela={reg['id']} corda={corda} x={x:.1f} ouro={c_ouro} s1={c_s1}")
            nome = SAIDA / f"casa_gre_t{reg['id']}_x{int(x)}_c{corda}.png"
            recorte(reg, x, corda, nome,
                    [(f"ouro {c_ouro}", COR_OURO_BR, x, -0.3),
                     (f"s1 {c_s1}", COR_CASA, x, 0.3)])
    # ---- 3. curva de limiar -------------------------------------------------
    out.append("")
    out.append("# 3. Curva de limiar do s1 (P e R por vídeo e total)")
    tot_por_t = {t: [] for t in LIMIARES}
    for slug, regs in por_video.items():
        ms_por_t = {t: [] for t in LIMIARES}
        for t in LIMIARES:
            detector_tab.LIMIAR = t
            for reg in regs:
                if reg["sem_painel"] or reg["cand"] is None:
                    ms_por_t[t].append(M._metricas_par(reg["notas_ouro"], [], 0.0))
                    continue
                cand = reg["cand"]
                notas = detector_tab.detectar(modelo_s1, cand.roi, reg["linhas"],
                                              reg["passo"])
                prev = [
                    M.NotaPrevista(int(n["corda"]), int(n["rotulo"]),
                                   cand.x0 + float(n["x"]), None)
                    for n in notas if n["rotulo"] in ALGARISMOS
                ]
                ms_por_t[t].append(M._metricas_par(reg["notas_ouro"], prev, reg["meia"]))
        detector_tab.LIMIAR = 0.5
        out.append(slug)
        for t in LIMIARES:
            r = M.resumo(ms_por_t[t])
            tot_por_t[t].extend(ms_por_t[t])
            out.append(f"  limiar {t:.1f}: P={M.fmt(r['P'])} R={M.fmt(r['R'])} "
                       f"casadas={r['casadas']} entregues={r['entregues']} "
                       f"ouro={r['notas_ouro']}")
    out.append("TOTAL")
    for t in LIMIARES:
        r = M.resumo(tot_por_t[t])
        out.append(f"  limiar {t:.1f}: P={M.fmt(r['P'])} R={M.fmt(r['R'])} "
                   f"casadas={r['casadas']} entregues={r['entregues']} "
                   f"ouro={r['notas_ouro']}")

    (SAIDA / "limiar_e_inventadas.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("gravado limiar_e_inventadas.txt", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
