"""Inventário do acervo real: que famílias de tablatura existem e em que proporção.

Para cada vídeo amostrado: procura a pauta de tablatura em 3 faixas do quadro
(topo/meio/base), mede a grade e tenta achar o cursor. Agrega por canal.

Uso:
    python -m tab.inventario --raiz "/run/media/.../chorinho" --por-canal 25 --saida /tmp/inv.json
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import random
import subprocess
import time

import cv2
import numpy as np

from .caminhos import SAIDA
from .cursor import detectar_cursor
from .painel import FAIXAS, escolher  # noqa: F401  (re-export)

# FAIXAS vem de tab.painel: uma fonte só para as faixas candidatas.


def duracao(caminho: str) -> float:
    """Duração do vídeo em segundos, por ffprobe.

    Existe porque o observador de **cor** do marcador devolve onsets em **fração** e o JSON precisa de
    **segundos**. O `ler_quadro` já faz esta chamada de ffprobe para o fallback de AV1, mas **não devolve**
    a duração — devolver mudaria uma assinatura usada em todo o projeto, então o helper fica separado.

    Args:
        caminho: caminho do vídeo.

    Returns:
        Duração em segundos, ou ``0.0`` se o ffprobe não responder.
    """
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                caminho,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(proc.stdout.strip() or 0)
    except Exception:
        return 0.0


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
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                caminho,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        dur = float(proc.stdout.strip() or 0)
    except Exception:
        dur = 0.0
    ss = max(0.0, dur * frac)
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                f"{ss:.2f}",
                "-i",
                caminho,
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ],
            capture_output=True,
            timeout=90,
        )
        if proc.stdout:
            arr = np.frombuffer(proc.stdout, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None and frame.size:
                return frame, "ffmpeg"
    except Exception:
        pass
    return None, "falhou"


def analisar_quadro(frame: np.ndarray) -> dict:
    """Procura o painel de tablatura e o cursor no quadro.

    Delega a escolha para `tab.painel` (implementação única). Aqui só se monta o
    registro com o que o inventário precisa.

    Args:
        frame: quadro inteiro.

    Returns:
        Dicionário com `tab`, a faixa, o passo, os glifos e o cursor.
    """
    escolhido = escolher(frame)
    out: dict = {"tab": False}
    if escolhido is not None:
        g = escolhido.grade
        out = {
            "tab": True,
            "faixa": escolhido.nome,
            "uniformidade": round(escolhido.uniformidade, 3),
            "passo": round(g.passo, 1),
            "mascara": g.avisos[0].replace("mascara=", "") if g.avisos else None,
            "glifos": len(g.glifos),
            "centrados": g.glifos_centrados,
            "frac_centrados": round(g.glifos_centrados / max(1, len(g.glifos)), 2),
            "colunas": len({x.coluna for x in g.glifos}),
            "cordas_com_nota": len({x.corda for x in g.glifos}),
            "y_linhas": g.linhas_y,
        }
        det = detectar_cursor(escolhido.roi)
        out["cursor"] = bool(det)
        if det:
            out["cursor_faixa"] = escolhido.nome
            out["cursor_largura"] = int(det[1] - det[0] + 1)
    else:
        out["cursor"] = False
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
    ap.add_argument("--saida", default=str(SAIDA / "inventario.json"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--frame-frac", type=float, default=0.35)
    args = ap.parse_args()

    canais = amostrar(args.raiz, args.por_canal, args.seed)
    resultados = []
    t0 = time.time()
    for canal, vids in canais.items():
        for v in vids:
            frame, via = ler_quadro(v, args.frame_frac)
            if frame is None:
                resultados.append(
                    {
                        "canal": canal,
                        "arquivo": os.path.relpath(v, args.raiz),
                        "tab": False,
                        "cursor": False,
                        "erro": "decodificacao",
                        "via": via,
                    }
                )
                print(
                    f"[{time.time() - t0:7.1f}s] {canal[:18]:<18} "
                    f"{os.path.basename(v)[:34]:<34} FALHA DE DECODIFICACAO",
                    flush=True,
                )
                continue
            r = analisar_quadro(frame)
            r["via"] = via
            r.update(
                {
                    "canal": canal,
                    "arquivo": os.path.relpath(v, args.raiz),
                    "segundos": round(time.time() - t0, 1),
                }
            )
            resultados.append(r)
            print(
                f"[{time.time() - t0:7.1f}s] {canal[:18]:<18} {os.path.basename(v)[:38]:<38} "
                f"tab={r['tab']} cursor={r['cursor']} passo={r.get('passo')} "
                f"glifos={r.get('glifos')} frac={r.get('frac_centrados')}",
                flush=True,
            )

    with open(args.saida, "w") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=1)

    print("\n=== RESUMO POR CANAL ===")
    print(
        f"{'canal':<24}{'n':>4}{'tab':>8}{'cursor':>9}{'faixa(top/meio/base)':>24}{'mascara':>22}{'passo med':>10}"
    )
    for canal in canais:
        rs = [r for r in resultados if r["canal"] == canal]
        if not rs:
            continue
        tab = [r for r in rs if r["tab"]]
        cur = [r for r in rs if r["cursor"]]
        faixas = collections.Counter(r["faixa"] for r in tab)
        masc = collections.Counter(r["mascara"].split("_")[0] for r in tab)
        passos = [r["passo"] for r in tab]
        print(
            f"{canal[:23]:<24}{len(rs):>4}{len(tab) / len(rs):>8.0%}{len(cur) / len(rs):>9.0%}"
            f"{dict(faixas)!s:>24}{dict(masc)!s:>22}"
            f"{(round(float(np.median(passos)), 1) if passos else 0):>10}"
        )
    falhas = sum(1 for r in resultados if r.get("erro"))
    vias = collections.Counter(r.get("via") for r in resultados)
    print(f"\nleitura de quadro: {dict(vias)} | falhas de decodificação: {falhas}")
    total = len(resultados)
    print(
        f"TOTAL amostrado: {total} vídeos | com tablatura: "
        f"{sum(1 for r in resultados if r['tab']) / max(1, total):.0%} | com cursor: "
        f"{sum(1 for r in resultados if r['cursor']) / max(1, total):.0%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
