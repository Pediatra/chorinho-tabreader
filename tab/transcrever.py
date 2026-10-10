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

from .caminhos import MODELO_PADRAO, SAIDA
from .cursor import detectar_cursor
from .digito import carregar
from .inventario import ler_quadro
from .painel import escolher
from .pipeline import roi_das_cordas
from .reconhecer import carregar_modelo, completar, reconhecer_linha
from .tempo import atribuir_tempos, resumo, tempos_por_patamar


def achar_painel(frame):
    """Painel de tablatura do quadro — delega para a implementação única.

    Havia três cópias desta escolha no projeto, todas ordenando por glifos centrados,
    e esse critério escolhe o **braço do violão** (medido num quadro do `sky guitar`).
    Agora é `tab.painel`, com a uniformidade do fundo como primeiro critério.

    Args:
        frame: quadro inteiro.

    Returns:
        O candidato escolhido (com `.nome`, `.roi`, `.grade`) ou None.
    """
    return escolher(frame)


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
    ap.add_argument(
        "--simbolos",
        default=str(SAIDA / "simbolos"),
        help="diretório dos recortes crus de símbolo ('' desliga)",
    )
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
    # A FAIXA VEM DO PRÓPRIO PAINEL, não de nomes fixos. O `achar_painel` evoluiu: ele devolve um
    # `Candidato` cujo nome é a COORDENADA (ex.: `y929`), e a busca em `FAIXAS` (nomes fixos de banda,
    # de quando o painel era escolhido entre 3 faixas) quebrava com `KeyError: 'y929'` — a cadeia
    # ponta a ponta ficava inteira parada. `roi_das_cordas` dá a faixa das cordas no quadro, que é o
    # que o cursor precisa varrer.
    nome, roi = m.nome, m.roi
    y0, y1 = roi_das_cordas(m)
    y1 = min(y1, frame.shape[0])

    modelo, rotulos, dev = carregar_modelo(args.modelo)
    # Símbolo não se descarta: o ponta a ponta também grava o recorte cru.
    r = reconhecer_linha(
        roi,
        modelo,
        rotulos,
        dev,
        dir_simbolos=args.simbolos or None,
        prefixo=os.path.basename(os.path.dirname(os.path.abspath(args.video))),
        discriminador=carregar(),
    )
    janelas = varrer_cursor(args.video, (y0, y1), t_max=args.varredura)
    # TEMPO POR TRAVESSIA. Medido no `iwaki/henze`: o marcador desliza ~65 px/s, então o
    # onset da nota é quando ele cruza o x dela — invertível. O `tempos_do_cursor`
    # antigo devolvia o MESMO instante para notas diferentes (3 instantes para 36 notas,
    # 1 para 3), que é a classe do erro histórico "323 notas com tempo" (eram 3).
    # A janela de tempo tem de ser onde o marcador ESTÁ ativo, não onde o
    # `--inicio` caiu: medido no `iwaki/henze`, as janelas ativas estavam em
    # 113,5–143 s e o `--inicio 0.48` apontava para 164 s, onde ele está parado.
    if janelas:
        t0 = janelas[0][0]
    serie = serie_cursor(args.video, (y0, y1), t0, args.janela, passo_s=0.25)
    veredito = resumo(serie)
    if veredito["veredito"] in {"desliza", "salta"}:
        if veredito["veredito"] == "desliza":
            onsets = atribuir_tempos([n["x"] for n in r["notas"]], serie)
        else:
            # marcador que SALTA: o onset é o início do patamar, não uma travessia
            onsets = tempos_por_patamar([n["x"] for n in r["notas"]], serie)
        r = completar(r, [(t, None) if t is not None else None for t in onsets])
        r["tempo"] = {
            "medido": True,
            "mecanismo": "travessia do marcador (banda que desliza)",
            "onset": "instante em que o marcador cruza o x da nota",
            "duracoes": "inferidas (intervalo até o próximo onset)",
            "serie": veredito,
        }
    else:
        # NÃO atribuir tempo sem travessia. Nota sem tempo é dívida; nota com tempo
        # falso é mentira.
        r["tempo"] = {
            "medido": False,
            "motivo": f"marcador {veredito['veredito']} na janela varrida",
            "serie": veredito,
        }
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
