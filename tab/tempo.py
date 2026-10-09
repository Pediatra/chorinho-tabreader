"""Tempo por travessia do marcador — quando o cursor cruza o x da nota.

Medido nesta noite no `iwaki/henze` (t=116–120,5 s): o marcador é uma banda de **6 px**,
matiz **102**, que **desliza** ~16 px a cada 0,25 s (**≈65 px/s**) sem saltos. Nesse
caso o onset é invertível: a nota começa quando o marcador cruza o `x` dela.

O outro comportamento medido no acervo é o marcador **parado** (o "cursor" do
`sky guitar` #4, parado em x=0–99 por 5 s): ali a série não descreve travessia nenhuma,
e este módulo não inventa tempo — devolve None.

Por que não usar o `tempos_do_cursor` antigo: ele devolvia o **mesmo instante** para
notas diferentes (3 instantes para 36 notas, 1 para 3), porque tratava a janela com
cursor como um bloco em vez de usar o `x(t)` medido.
"""

from __future__ import annotations

import itertools

#: Salto por amostra acima disto não é o mesmo trecho de execução (troca de sistema,
#: troca de tela, erro de detecção). Medido: ~16 px por 0,25 s no caso bom, e saltos
#: de +42 px já aparecem numa quebra de compasso do mesmo vídeo.
SALTO_MAX_PX = 60.0

#: Degrau de quantização do x ao julgar sentido (trepidação some, salto fica).
QUANTIZACAO_PX = 10

#: Abaixo disto o marcador não acompanha nota por nota (medido: 0,6 px/s no
#: `asturias`; um playhead por nota anda na casa de dezenas de px/s).
VELOCIDADE_MINIMA_PX_S = 5.0


def tempo_de_x(serie: list[tuple[float, int]], x: float) -> float | None:
    """Quando o marcador cruzou a posição ``x``, pela primeira vez.

    Args:
        serie: pontos ``(t, x0)`` do marcador, em ordem de tempo.
        x: posição horizontal do token.

    Returns:
        O instante da primeira travessia, ou None se a série não cobre esse x.
    """
    for (t1, x1), (t2, x2) in itertools.pairwise(serie):
        if abs(x2 - x1) > SALTO_MAX_PX:
            continue  # troca de trecho: não interpolar por cima
        if x2 == x1:
            if x == x1:
                return t1
            continue
        baixo, alto = (x1, x2) if x1 < x2 else (x2, x1)
        if baixo <= x <= alto:
            fracao = (x - x1) / (x2 - x1)
            return round(t1 + fracao * (t2 - t1), 3)
    return None


def atribuir_tempos(
    tokens_x: list[float], serie: list[tuple[float, int]]
) -> list[float | None]:
    """Instante de cada token, pela travessia do marcador.

    Args:
        tokens_x: posição horizontal de cada token, na ordem das notas.
        serie: pontos ``(t, x0)`` do marcador.

    Returns:
        Um instante por token (None onde não houve travessia).
    """
    return [tempo_de_x(serie, x) for x in tokens_x]


def duracoes_por_onset(tempos: list[float | None]) -> list[float | None]:
    """Duração de cada nota como o intervalo até o próximo onset (inferida).

    Args:
        tempos: onsets em segundos, na ordem das notas.

    Returns:
        Uma duração por nota; a última recebe None (não há próximo onset).
    """
    duracoes: list[float | None] = []
    for atual, seguinte in itertools.pairwise(tempos):
        if atual is None or seguinte is None or seguinte <= atual:
            duracoes.append(None)
        else:
            duracoes.append(round(seguinte - atual, 3))
    duracoes.append(None)
    return duracoes


def patamares(
    serie: list[tuple[float, int]], tolerancia_px: int = 6, minimo_amostras: int = 2
) -> list[tuple[float, float, int]]:
    """Agrupa a série em PATAMARES: o marcador parado no mesmo x por várias amostras.

    O outro comportamento medido no acervo (rodada 1, `skyguitar`): o cursor **salta de
    nota em nota** e fica parado durante a nota — 100 saltos em 80 s, salto mediano de
    109 px, patamar de ~1 s. Nesse caso o onset é o **início do patamar**; entre os saltos
    não há travessia contínua para inverter.

    Args:
        serie: pontos ``(t, x)`` em ordem de tempo.
        tolerancia_px: quanto o x pode variar e ainda ser o mesmo patamar.
        minimo_amostras: quantas amostras seguidas formam um patamar.

    Returns:
        Lista de ``(t_inicio, t_fim, x_medio)``.
    """
    if not serie:
        return []
    grupos: list[list[tuple[float, int]]] = [[serie[0]]]
    for t, x in serie[1:]:
        if abs(x - grupos[-1][-1][1]) <= tolerancia_px:
            grupos[-1].append((t, x))
        else:
            grupos.append([(t, x)])
    return [
        (g[0][0], g[-1][0], int(sum(x for _, x in g) / len(g)))
        for g in grupos
        if len(g) >= minimo_amostras
    ]


def resumo(serie: list[tuple[float, int]]) -> dict:
    """O que a série do marcador mostra: desliza, fica parado, ou nada.

    Args:
        serie: pontos ``(t, x0)`` do marcador.

    Returns:
        Dicionário com número de pontos, deslocamento total, passo mediano e o veredito:
        `desliza` (anda sempre para o mesmo lado), `parado` (fica no mesmo x),
        `erratico` (aparece em lugares sem relação — artefato) ou `sem_marcador`.
    """
    if len(serie) < 3:
        return {"pontos": len(serie), "veredito": "sem_marcador"}
    # Quantizar o x antes de julgar o sentido: trepidação de ±2 px some (fica no mesmo
    # degrau de QUANTIZACAO_PX) e salto de centenas de px permanece. Mediana móvel não
    # serve aqui — medida e descartada: ela achatava justamente os saltos grandes que
    # caracterizam o artefato, e a série errática do `iwaki/henze` passava a "parado".
    # round() de float já devolve int neste Python (medido — regra 8 do AGENTS.md).
    quant = [(t_, round(x / QUANTIZACAO_PX) * QUANTIZACAO_PX) for t_, x in serie]
    todos = [x2 - x1 for (_, x1), (_, x2) in itertools.pairwise(quant)]
    passos = [p for p in todos if abs(p) <= SALTO_MAX_PX]
    grandes = [p for p in todos if abs(p) > SALTO_MAX_PX]
    if not passos:
        # Só saltos grandes: a "detecção" aparece em pontos sem relação entre si. Medido
        # no `iwaki/henze` ao longo dos 342 s: x = 230, 285, 341, 548, 638, 690, 844,
        # 1184, 1491, 1527... — um movimento suave de 4 s dentro disso me fez concluir
        # "o marcador desliza" quando era coincidência.
        return {
            "pontos": len(serie),
            "saltos_grandes": len(grandes),
            "veredito": "erratico" if len(grandes) >= 2 else "sem_marcador",
        }
    ordenados = sorted(abs(p) for p in passos)
    mediana = ordenados[len(ordenados) // 2]
    total = max(x for _, x in quant) - min(x for _, x in quant)
    # Marcador de execução anda para UM lado; série que troca de sentido é artefato.
    sinais = [1 if p > 0 else -1 for p in passos if p != 0]
    trocas = sum(1 for a, b in itertools.pairwise(sinais) if a != b)
    if sinais and trocas / len(sinais) > 0.3:
        veredito = "erratico"
    elif mediana >= 3:
        veredito = "desliza"
    else:
        # x praticamente parado entre amostras: ou é patamar de cursor que salta, ou é
        # ruído parado. Patamares com avanço em UM sentido = cursor que salta.
        degraus = patamares(quant)
        avancos = [
            x2 - x1
            for (_, _, x1), (_, _, x2) in itertools.pairwise(degraus)
            if x2 != x1
        ]
        sentido = [1 if d > 0 else -1 for d in avancos]
        troca_sentido = sum(1 for a, b in itertools.pairwise(sentido) if a != b)
        avanca = bool(sentido) and troca_sentido / len(sentido) <= 0.3
        veredito = "salta" if (len(degraus) >= 3 and avanca) else "parado"
    # Velocidade: um marcador que acompanha NOTA POR NOTA anda, no mínimo, uma fração do
    # passo por nota. Medido no `asturias`, a banda laranja anda 10 px em 17 s (0,6 px/s):
    # mesmo sendo a favor de um sentido, não serve para dar onset de nota.
    intervalo = serie[-1][0] - serie[0][0]
    velocidade = (total / intervalo) if intervalo > 0 else 0.0
    if veredito in {"desliza", "salta"} and velocidade < VELOCIDADE_MINIMA_PX_S:
        veredito = "lento"
    return {
        "pontos": len(serie),
        "deslocamento_total_px": int(total),
        "passo_mediano_px": int(mediana),
        "velocidade_px_s": round(velocidade, 1),
        "veredito": veredito,
    }
