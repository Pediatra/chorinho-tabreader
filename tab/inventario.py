"""Inventário do acervo real: que famílias de tablatura existem e em que proporção.

Para cada vídeo amostrado: procura a pauta de tablatura em 3 faixas do quadro
(topo/meio/base), mede a grade e tenta achar o cursor. Agrega por canal.

Uso:
    python tools/inventario.py --raiz "/run/media/.../chorinho" --por-canal 25 --saida /tmp/inv.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
import time
import collections

import subprocess
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tabseg import segmentar  # noqa: E402
from cursor import detectar_cursor  # noqa: E402

FAIXAS = [("topo", 0, 400), ("meio", 300, 750), ("base", 620, 1080)]


def ler_quadro(caminho: str, frac: float = 0.35) -> tuple[np.ndarray | None, str]:
    """Lê um quadro. Tenta o OpenCV e, se falhar (AV1 sem decodificação no cv2),
    cai para o ffmpeg em software. Devolve (quadro, via)."""
    cap = cv2.VideoCapture(caminho)
    if cap.isOpened():
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if n > 10:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * frac))
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None and frame.size:
            return frame, "cv2"
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", caminho],
            capture_output=True, text=True, timeout=30)
        dur = float(proc.stdout.strip() or 0)
    except Exception:
        dur = 0.0
    ss = max(0.0, dur * frac)
    try:
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{ss:.2f}", "-i", caminho,
             "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True, timeout=90)
        if proc.stdout:
            arr = np.frombuffer(proc.stdout, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None and frame.size:
                return frame, "ffmpeg"
    except Exception:
        pass
    return None, "falhou"


def analisar_quadro(frame: np.ndarray) -> dict:
    """Procura a melhor faixa de tablatura e o cursor no quadro inteiro."""
    melhor = None
    cursor_faixa = None
    for nome, y0, y1 in FAIXAS:
        if y1 > frame.shape[0]:
            y1 = frame.shape[0]
        if y1 - y0 < 60:
            continue
        roi = frame[y0:y1, :]
        try:
            g = segmentar(roi)
        except Exception as exc:                       # nunca derrubar o inventário
            continue
        if len(g.linhas_y) != 6 or not g.glifos:
            continue
        score = (g.glifos_centrados, len(g.glifos))
        if melhor is None or score > melhor[0]:
            melhor = (score, nome, g)
        if cursor_faixa is None:
            det = detectar_cursor(roi)
            if det:
                cursor_faixa = (nome, det[0], det[1], det[2])
    out: dict = {"tab": False}
    if melhor is not None:
        score, nome, g = melhor
        frac = g.glifos_centrados / max(1, len(g.glifos))
        out = {
            "tab": True, "faixa": nome, "passo": round(g.passo, 1),
            "mascara": g.avisos[0].replace("mascara=", ""),
            "glifos": len(g.glifos), "centrados": g.glifos_centrados,
            "frac_centrados": round(frac, 2),
            "colunas": len({x.coluna for x in g.glifos}),
            "cordas_com_nota": len({x.corda for x in g.glifos}),
            "y_linhas": g.linhas_y,
        }
    out["cursor"] = bool(cursor_faixa)
    if cursor_faixa:
        out["cursor_faixa"] = cursor_faixa[0]
        out["cursor_largura"] = cursor_faixa[2] - cursor_faixa[1] + 1
    return out


def amostrar(raiz: str, por_canal: int, seed: int = 0) -> dict[str, list[str]]:
    rng = random.Random(seed)
    canais: dict[str, list[str]] = {}
    for d in sorted(glob.glob(os.path.join(raiz, "*"))):
        if not os.path.isdir(d) or os.path.basename(d) == "derived":
            continue
        vids = sorted(glob.glob(os.path.join(d, "**", "*.mp4"), recursive=True))
        if not vids:
            continue
        if len(vids) > por_canal:
            vids = sorted(rng.sample(vids, por_canal))
        canais[os.path.basename(d)] = vids
    return canais


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", required=True)
    ap.add_argument("--por-canal", type=int, default=25)
    ap.add_argument("--saida", default="/tmp/inventario.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--frame-frac", type=float, default=0.35)
    args = ap.parse_args()

    canais = amostrar(args.raiz, args.por_canal, args.seed)
    resultados = []
    t0 = time.time()
    for canal, vids in canais.items():
        for i, v in enumerate(vids):
            frame, via = ler_quadro(v, args.frame_frac)
            if frame is None:
                resultados.append({"canal": canal,
                                   "arquivo": os.path.relpath(v, args.raiz),
                                   "tab": False, "cursor": False, "erro": "decodificacao",
                                   "via": via})
                print(f"[{time.time()-t0:7.1f}s] {canal[:18]:<18} "
                      f"{os.path.basename(v)[:34]:<34} FALHA DE DECODIFICACAO", flush=True)
                continue
            r = analisar_quadro(frame)
            r["via"] = via
            r.update({"canal": canal, "arquivo": os.path.relpath(v, args.raiz),
                      "segundos": round(time.time() - t0, 1)})
            resultados.append(r)
            print(f"[{time.time()-t0:7.1f}s] {canal[:18]:<18} {os.path.basename(v)[:38]:<38} "
                  f"tab={r['tab']} cursor={r['cursor']} passo={r.get('passo')} "
                  f"glifos={r.get('glifos')} frac={r.get('frac_centrados')}", flush=True)

    with open(args.saida, "w") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=1)

    print("\n=== RESUMO POR CANAL ===")
    print(f"{'canal':<24}{'n':>4}{'tab':>8}{'cursor':>9}{'faixa(top/meio/base)':>24}{'mascara':>22}{'passo med':>10}")
    for canal in canais:
        rs = [r for r in resultados if r["canal"] == canal]
        if not rs:
            continue
        tab = [r for r in rs if r["tab"]]
        cur = [r for r in rs if r["cursor"]]
        faixas = collections.Counter(r["faixa"] for r in tab)
        masc = collections.Counter(r["mascara"].split("_")[0] for r in tab)
        passos = [r["passo"] for r in tab]
        print(f"{canal[:23]:<24}{len(rs):>4}{len(tab)/len(rs):>8.0%}{len(cur)/len(rs):>9.0%}"
              f"{str(dict(faixas)):>24}{str(dict(masc)):>22}"
              f"{(round(float(np.median(passos)),1) if passos else 0):>10}")
    falhas = sum(1 for r in resultados if r.get("erro"))
    vias = collections.Counter(r.get("via") for r in resultados)
    print(f"\nleitura de quadro: {dict(vias)} | falhas de decodificação: {falhas}")
    total = len(resultados)
    print(f"TOTAL amostrado: {total} vídeos | com tablatura: "
          f"{sum(1 for r in resultados if r['tab'])/max(1,total):.0%} | com cursor: "
          f"{sum(1 for r in resultados if r['cursor'])/max(1,total):.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
