"""VÍDEO -> JSON: o produto do goal, em um comando.

painel (3 faixas) -> grade de 6 cordas -> tokens -> classificador sintético
-> compasso (barlines) -> tempo de cada nota (cursor) -> JSON.

Pela CLI, ``python -m tab.transcrever VIDEO --json saida.json`` lê o vídeo inteiro e
grava o JSON ``chorinho/video@1`` (ver ``tab.esquema``). Os auxiliares de tempo abaixo
são do ramo antigo (um quadro, ``janela``) e saem em commit separado do MVP.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from tab.comum import leitor
from tab.comum.caminhos import DETECTOR_PADRAO, MODELO_PADRAO
from tab.tablatura.leitura.cursor import detectar_cursor
from tab.tablatura.leitura.painel import escolher
from tab.tablatura.produto.esquema import validar
from tab.tablatura.produto.video import (
    IMAGEM_PADRAO,
    IMAGENS,
    LEITOR_PADRAO,
    LEITORES,
    _json_seguro,
    transcrever_video,
)


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
    marcas = []
    for t, fr in leitor.quadros(video, 0.0, t_max, 1.0 / passo_s, recorte_y=roi_abs):
        det = detectar_cursor(fr)
        marcas.append((t, bool(det)))
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
    marcador = []
    for t, fr in leitor.quadros(
        video, t0, t0 + janela, 1.0 / passo_s, recorte_y=roi_abs
    ):
        det = detectar_cursor(fr)
        if det:
            marcador.append(((det[0] + det[1]) / 2.0, t))
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
    amostras = []
    for t, fr in leitor.quadros(
        video, t0, t0 + janela, 1.0 / passo_s, recorte_y=roi_abs
    ):
        det = detectar_cursor(fr)
        if det:
            amostras.append(((det[0] + det[1]) / 2.0, t))
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


def janela_serie(t0: float, janela: float, dur: float) -> tuple[float, float]:
    """Intervalo de vídeo que a série de tempo varre: ``[t0, t0 + janela]``.

    Args:
        t0: início da varredura, em segundos.
        janela: duração pedida, em segundos.
        dur: duração do vídeo, em segundos (``0`` se desconhecida: sem corte).

    Returns:
        ``(t_inicio, t_fim)``, com ``t_fim`` limitado à duração do vídeo quando ela é conhecida.
    """
    fim = t0 + janela
    if dur > 0:
        fim = min(fim, dur)
    return (t0, fim)


def main() -> int:
    """CLI fina: ``python -m tab.transcrever VIDEO --json saida.json``.

    Lê o vídeo inteiro com ``tab.video.transcrever_video``, valida o resultado com
    ``tab.esquema.validar`` e só então grava o JSON. Erro de esquema é falha alta: nada
    é gravado e o processo termina com código 1.

    Returns:
        ``0`` ao gravar um JSON válido; ``1`` se o esquema recusar a saída.
    """
    ap = argparse.ArgumentParser(description="VÍDEO -> JSON chorinho/video@1.")
    ap.add_argument("video")
    ap.add_argument("--json", required=True, help="onde gravar o JSON v1")
    ap.add_argument("--leitor", choices=LEITORES, default=LEITOR_PADRAO)
    ap.add_argument("--modelo", default=str(MODELO_PADRAO), help="leitor glifos")
    ap.add_argument("--detector", default=str(DETECTOR_PADRAO), help="leitor rede")
    ap.add_argument("--imagem", choices=IMAGENS, default=IMAGEM_PADRAO)
    args = ap.parse_args()
    dados = transcrever_video(
        args.video,
        modelo=args.modelo,
        imagem=args.imagem,
        leitor_notas=args.leitor,
        detector=args.detector,
    )
    erros = validar(dados)
    if erros:
        for erro in erros[:20]:
            print(f"ERRO DE ESQUEMA: {erro}", file=sys.stderr)
        print(
            f"{len(erros)} erro(s) de esquema: JSON NAO gravado em {args.json}",
            file=sys.stderr,
        )
        return 1
    destino = Path(args.json)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1, default=_json_seguro),
        encoding="utf-8",
    )
    r = dados["resumo"]
    print(
        f"{r['telas']} telas, {r['exibicoes']} exibicoes, {r['notas']} notas, "
        f"{r['nao_notas']} nao-notas -> {destino}"
    )
    print(
        f"tempo: {r['notas_com_tempo']} notas com t_ini, {r['instantes_distintos']} "
        f"instantes, telas sem tempo {r['telas_sem_tempo']} | esquema: ok"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
