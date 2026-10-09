"""Rastreio do cursor de execução (o "marcador que passa sobre a nota").

O usuário descreveu exatamente isto: um marcador vertical que percorre a partitura/
tablatura durante a execução. É ele que dá o TEMPO de cada nota sem precisar de
áudio: x do cursor(t) -> coluna da grade -> (corda, casa) -> t.

Método (determinístico, sem modelo):
  1. Restringe a faixa da partitura (ROI), excluindo o vídeo do braço.
  2. Acha a coluna cromática: pixels com saturação alta numa faixa de matiz.
  3. O cursor é uma banda vertical CONTÍNUA e alta (cobre a ROI quase toda).
  4. x(t) = centro da banda; valida monotonicidade (o cursor não volta).

Uso:
    python tools/cursor.py VIDEO [--roi 0 300] [--passo 1] [--debug dir]
"""
from __future__ import annotations

import argparse
import json
import sys

import cv2
import numpy as np


def detectar_cursor(frame_bgr: np.ndarray, altura_min_frac: float = 0.5,
                    largura_max_frac: float = 0.06,
                    matizes: tuple[int, int] = (85, 140)) -> tuple[int, int, tuple[int, int]] | None:
    """Devolve (x0, x1, (matiz, sat)) da banda do cursor, ou None.

    Duas travas aprendidas na marra: a "banda" tem de ser ESTREITA (<= 6 % da largura) e
    ter matiz de banda de playback (azul/pálido). Sem elas o detector achava o corpo do
    violão (medido: 149 px de largura, matiz 16 = laranja) e chamava aquilo de cursor,
    contaminando toda a medição de cobertura de tempo."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    h, w = frame_bgr.shape[:2]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    # cor de verdade (não preto/branco/cinza da partitura)
    crom = (sat > 60) & (val > 90)
    if crom.sum() < 50:
        return None
    contagem = crom.sum(axis=0)
    # a banda do cursor é a coluna cromática mais "cheia"
    limite = altura_min_frac * h
    cand = contagem > limite
    if not cand.any():
        # banda estreita em imagem baixa: relaxa para o topo da distribuição
        limite = max(3, 0.6 * contagem.max())
        cand = contagem > limite
        if not cand.any():
            return None
    xs = np.flatnonzero(cand)
    # maior grupo contíguo
    grupos, ini = [], xs[0]
    for a, b in zip(xs[:-1], xs[1:]):
        if b - a > 3:
            grupos.append((ini, a))
            ini = b
    grupos.append((ini, xs[-1]))
    x0, x1 = max(grupos, key=lambda g: (g[1] - g[0], contagem[g[0]:g[1] + 1].sum()))
    faixa = crom[:, x0:x1 + 1]
    if faixa.sum() == 0:
        return None
    matiz = hsv[:, x0:x1 + 1, 0][faixa]
    s = hsv[:, x0:x1 + 1, 1][faixa]
    m_med, s_med = int(np.median(matiz)), int(np.median(s))
    largura = x1 - x0 + 1
    if largura > largura_max_frac * w:            # largo demais: é madeira/objeto, não banda
        return None
    if not (matizes[0] <= m_med <= matizes[1]):   # matiz fora do azul de playback
        return None
    return int(x0), int(x1), (m_med, s_med)


def rastrear(caminho: str, roi: tuple[int, int] | None = None, passo: int = 1,
             debug_dir: str | None = None) -> dict:
    cap = cv2.VideoCapture(caminho)
    if not cap.isOpened():
        raise SystemExit(f"não abri {caminho}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    y0, y1 = roi if roi else (0, 0)

    amostras = []
    i = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % passo == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            if y1 > y0:
                frame = frame[y0:y1, :]
            det = detectar_cursor(frame)
            if det:
                x0, x1, (matiz, s) = det
                amostras.append({"frame": i, "t": i / fps, "x": (x0 + x1) / 2.0,
                                 "x0": x0, "x1": x1, "largura": x1 - x0 + 1,
                                 "matiz": matiz, "sat": s})
            if debug_dir and len(amostras) <= 3:
                vis = frame.copy()
                if det:
                    cv2.rectangle(vis, (det[0], 0), (det[1], vis.shape[0] - 1), (0, 0, 255), 2)
                cv2.imwrite(f"{debug_dir}/cursor_f{i:06d}.png", vis)
        i += 1

    cap.release()
    xs = np.array([a["x"] for a in amostras])
    ts = np.array([a["t"] for a in amostras])
    # O cursor NÃO desliza: ele salta de nota em nota e fica parado enquanto a nota
    # dura (medido: x constante por ~1 s, salto de ~1 passo de nota). Por isso a
    # estatística útil é a de SALTOS, não de velocidade.
    saltos = np.array([], dtype=float)
    instantes = np.array([], dtype=float)
    retrocessos = 0
    if len(xs) > 1:
        dx = np.diff(xs)
        mask = np.abs(dx) > 5.0
        saltos = np.abs(dx[mask])
        instantes = ts[1:][mask]
        retrocessos = int((dx < -5.0).sum())
    intervalos = np.diff(instantes) if len(instantes) > 1 else np.array([])
    larguras = [a["largura"] for a in amostras]
    resumo = {
        "fps": fps,
        "frames_totais": n,
        "amostras_com_cursor": len(amostras),
        "cobertura": (len(amostras) / max(1, n / passo)),
        "x_min": float(xs.min()) if len(xs) else None,
        "x_max": float(xs.max()) if len(xs) else None,
        "largura_nucleo_mediana": float(np.median(larguras)) if larguras else None,
        "largura_nucleo_p90": float(np.percentile(larguras, 90)) if larguras else None,
        "matiz_mediana": float(np.median([a["matiz"] for a in amostras])) if amostras else None,
        "posicoes_x_distintas": int(len(np.unique(np.round(xs)))),
        "n_saltos": int(len(saltos)),
        "salto_mediano_px": float(np.median(saltos)) if len(saltos) else None,
        "retrocessos": retrocessos,
        "intervalo_mediano_entre_saltos_s": float(np.median(intervalos)) if len(intervalos) else None,
    }
    return {"resumo": resumo, "amostras": amostras}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--roi", type=int, nargs=2, default=[0, 300])
    ap.add_argument("--passo", type=int, default=1)
    ap.add_argument("--debug")
    ap.add_argument("--json")
    args = ap.parse_args()
    r = rastrear(args.video, (args.roi[0], args.roi[1]), args.passo, args.debug)
    print(json.dumps(r["resumo"], indent=1, ensure_ascii=False))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(r, fh, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
