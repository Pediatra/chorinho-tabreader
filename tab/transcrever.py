"""VÍDEO -> JSON: o produto do goal, em um comando.

painel (3 faixas) -> grade de 6 cordas -> tokens -> classificador sintético
-> compasso (barlines) -> tempo de cada nota (cursor) -> JSON.

Uso:
    python -m tab.transcrever VIDEO [--inicio 0.4] [--janela 30] [--json saida.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

from .caminhos import MODELO_PADRAO
from .cursor import detectar_cursor
from .inventario import FAIXAS, ler_quadro
from .reconhecer import carregar_modelo, completar, reconhecer_linha
from .tabseg import segmentar


def achar_painel(frame):
    melhor = None
    for nome, y0, y1 in FAIXAS:
        y1 = min(y1, frame.shape[0])
        roi = frame[y0:y1, :]
        g = segmentar(roi)
        if len(g.linhas_y) == 6 and g.glifos:
            chave = (g.glifos_centrados, len(g.glifos))
            if melhor is None or chave > melhor[0]:
                melhor = (chave, nome, roi, g)
    return melhor


def varrer_cursor(video, roi_abs, passo_s=0.5, t_max=180.0):
    """Varre o vídeo e devolve as JANELAS em que o cursor está ativo.

    O cursor é INTERMITENTE (medido: 95 % dos vídeos têm cursor em algum quadro, mas só
    50 % o mantêm por 12 s contínuos). Assumir cursor no vídeo inteiro faz o produto
    devolver tempo vazio; procurar as janelas é o que torna o anexo de tempo confiável.
    """
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    marcas = []
    t = 0.0
    prox = 0.0
    while t < t_max:
        if not cap.grab():
            break
        if t >= prox:
            ok, fr = cap.retrieve()
            if ok:
                det = detectar_cursor(fr[roi_abs[0] : roi_abs[1], :])
                marcas.append((t, bool(det)))
            prox += passo_s
        t += 1.0 / fps
    cap.release()
    janelas, ini = [], None
    for t, d in marcas:
        if d and ini is None:
            ini = t
        elif not d and ini is not None:
            if t - ini >= 2.0:
                janelas.append((round(ini, 1), round(t, 1)))
            ini = None
    if ini is not None and marcas:
        janelas.append((round(ini, 1), round(marcas[-1][0], 1)))
    return janelas


def tempos_do_cursor(video, roi_abs, tokens, t0, janela, passo_s=0.15):
    """Segue a banda colorida e devolve o instante em que ela para em cada coluna."""
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
    marcador = []
    t = t0
    while t < t0 + janela:
        ok = cap.grab()
        if not ok:
            break
        if round((t - t0) / passo_s) != round((t - passo_s - t0) / passo_s):
            ok, fr = cap.retrieve()
            if ok:
                det = detectar_cursor(fr[roi_abs[0] : roi_abs[1], :])
                if det:
                    marcador.append(((det[0] + det[1]) / 2.0, t))
        t += 1.0 / fps
    cap.release()
    if not marcador:
        return [None] * len(tokens)
    # patamares: x constante por >= 3 amostras
    patamares, ini = [], 0
    for i in range(1, len(marcador)):
        if abs(marcador[i][0] - marcador[ini][0]) > 4:
            if i - ini >= 3:
                patamares.append(
                    (
                        float(np.median([m[0] for m in marcador[ini:i]])),
                        marcador[ini][1],
                        marcador[i - 1][1],
                    )
                )
            ini = i
    if len(marcador) - ini >= 3:
        patamares.append(
            (
                float(np.median([m[0] for m in marcador[ini:]])),
                marcador[ini][1],
                marcador[-1][1],
            )
        )
    saida = []
    for tk in tokens:
        if not patamares:
            saida.append((None, None))
            continue
        p = min(patamares, key=lambda q: abs(q[0] - tk.cx))
        saida.append((round(p[1], 2), round(p[2], 2)))
    return saida


def serie_cursor(video, roi_abs, t0, janela, passo_s=0.1):
    """Série x(t) do cursor, SEM exigir patamar (o cursor que desliza nunca para)."""
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
    amostras, t, prox = [], t0, t0
    while t < t0 + janela:
        if not cap.grab():
            break
        if t >= prox:
            ok, fr = cap.retrieve()
            if ok:
                det = detectar_cursor(fr[roi_abs[0] : roi_abs[1], :])
                if det:
                    amostras.append(((det[0] + det[1]) / 2.0, t))
            prox += passo_s
        t += 1.0 / fps
    cap.release()
    return amostras


def passagens(amostras, folga=30.0):
    """Divide x(t) em PASSAGENS: o cursor entra pela margem esquerda e sai pela direita.

    É a unidade natural da música — um sistema. Transcrever uma janela arbitrária dava
    tempo para poucas notas (medido: 4 s de cursor para 36 notas); transcrever por
    passagem dá a travessia de cada coluna daquele sistema.
    """
    if not amostras:
        return []
    xs = [a[0] for a in amostras]
    x_min = min(xs)
    limite_esq = x_min + folga
    listas, atual, dentro = [], [], False
    for x, t in amostras:
        if not dentro and x <= limite_esq:
            dentro, atual = True, [(x, t)]
            continue
        if dentro:
            atual.append((x, t))
            if x < atual[-2][0] - 60:  # retrocesso forte = fim de passagem
                listas.append(atual[:-1])
                atual, dentro = [(x, t)], True
    if atual:
        listas.append(atual)
    saida = []
    for p in listas:
        if len(p) < 5:
            continue
        xs_p = [a[0] for a in p]
        saida.append(
            {
                "t_ini": round(p[0][1], 2),
                "t_fim": round(p[-1][1], 2),
                "x_min": round(min(xs_p)),
                "x_max": round(max(xs_p)),
                "n_amostras": len(p),
                "_amostras": p,
            }
        )
    return saida


def tempos_por_travessia(amostras, tokens):
    """Instante = quando x(t) CRUZA o x da coluna da nota (interpolado).

    Vale para cursor que desliza (medido: 67-166 px/s, ~3 px por quadro, nunca forma
    patamar). Para cursor que salta, o patamar é a leitura certa — as duas convivem.
    """
    saida = []
    for tk in tokens:
        t_cruza = None
        for i in range(1, len(amostras)):
            x0, t0 = amostras[i - 1]
            x1, t1 = amostras[i]
            if x1 != x0 and (x0 - tk.cx) * (x1 - tk.cx) <= 0:
                t_cruza = t0 + (tk.cx - x0) / (x1 - x0) * (t1 - t0)
                break
        saida.append((round(t_cruza, 2) if t_cruza is not None else None, None))
    for i in range(len(saida) - 1):
        if saida[i][1] is None and saida[i + 1][0] is not None:
            saida[i] = (saida[i][0], saida[i + 1][0])
    return saida


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--inicio", type=float, default=0.4, help="fração do vídeo")
    ap.add_argument("--janela", type=float, default=30.0, help="segundos a transcrever")
    ap.add_argument(
        "--varredura",
        type=float,
        default=180.0,
        help="segundos a varrer atrás do cursor",
    )
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    ap.add_argument("--json")
    args = ap.parse_args()

    # duração para converter a fração em segundos
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    t0 = (n / fps) * args.inicio if n else 0.0

    frame, via = ler_quadro(args.video, args.inicio)
    if frame is None:
        print("não consegui ler quadro", file=sys.stderr)
        return 2
    m = achar_painel(frame)
    if m is None:
        print("nenhuma pauta de tablatura encontrada", file=sys.stderr)
        return 3
    _, nome, roi, g0 = m
    limites = {f[0]: (f[1], f[2]) for f in FAIXAS}
    y0 = limites[nome][0]
    y1 = min(limites[nome][1], frame.shape[0])

    modelo, rotulos, dev = carregar_modelo(args.modelo)
    r = reconhecer_linha(roi, modelo, rotulos, dev)
    tokens = sorted(g0.glifos, key=lambda x: (x.coluna, x.corda))
    janelas = varrer_cursor(args.video, (y0, y1), t_max=args.varredura)
    t_ini = janelas[0][0] if janelas else t0
    tempos = tempos_do_cursor(args.video, (y0, y1), tokens, t_ini, args.janela)
    r = completar(r, tempos)
    r.update(
        {
            "video": os.path.basename(args.video),
            "painel": nome,
            "quadro_em_s": round(t0, 1),
            "lido_via": via,
            "janelas_com_cursor": janelas,
            "segundos_com_cursor": round(sum(b - a for a, b in janelas), 1),
        }
    )
    print(json.dumps({k: v for k, v in r.items() if k != "notas"}, ensure_ascii=False))
    print("primeiras 3 notas:", json.dumps(r["notas"][:3], ensure_ascii=False))
    if args.json:
        with open(args.json, "w") as destino:
            json.dump(r, destino, ensure_ascii=False, indent=1)
        print("salvo em", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
