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


def resumo(serie: list[tuple[float, int]]) -> dict:
    """O que a série do marcador mostra: desliza, fica parado, ou nada.

    Args:
        serie: pontos ``(t, x0)`` do marcador.

    Returns:
        Dicionário com número de pontos, deslocamento total, velocidade mediana e o
        veredito (`desliza`, `parado`, `sem_marcador`).
    """
    if len(serie) < 3:
        return {"pontos": len(serie), "veredito": "sem_marcador"}
    deslocamentos = [
        abs(x2 - x1)
        for (_, x1), (_, x2) in itertools.pairwise(serie)
        if abs(x2 - x1) <= SALTO_MAX_PX
    ]
    if not deslocamentos:
        return {"pontos": len(serie), "veredito": "sem_marcador"}
    ordenados = sorted(deslocamentos)
    mediana = ordenados[len(ordenados) // 2]
    total = max(x for _, x in serie) - min(x for _, x in serie)
    veredito = "desliza" if mediana >= 3 else "parado"
    return {
        "pontos": len(serie),
        "deslocamento_total_px": int(total),
        "passo_mediano_px": int(mediana),
        "veredito": veredito,
    }
