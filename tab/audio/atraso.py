"""Atraso entre o marcador da tela e o ataque da nota no áudio (trilha A1).

Para cada EVENTO de coluna com ``t_ini`` (um acorde é um evento), mede ``Δ = t_som - t_ini``,
onde ``t_som`` é o ataque achado no áudio por dois métodos (``fluxo`` e ``alturas``, ver
``tab.audio_onsets``), em duas passadas: a 1ª com a janela centrada em ``t_ini``; a 2ª com a
janela centrada em ``t_ini + mediana(Δ da 1ª passada, método fluxo)``. Só MEDE e RESUME: não
conclui sobre causas.

Uso::

    python -m tab.audio_atraso --produto data/saida/conserto_v2/mvp.json \\
        --video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" \\
        --saida data/saida/audio/a1/atraso_mvp.json

Eventos: notas agrupadas por ``(tela, exibicao, passagem, coluna)``. Janela de cada evento:
meia-distância até o vizinho em cada lado (na ordem de tempo global), com teto de
``TETO_JANELA_S``. Escolha do pico do método ``fluxo``: o mais próximo do centro da janela
dentro dela. ``na_borda``: o pico está a menos de 1 quadro de uma borda da janela.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

import numpy as np

from tab.audio.extrair import garantir, ler
from tab.audio.onsets import (
    DELTA_PICO,
    GAMA_LOG,
    N_FFT,
    PASSO,
    espectrograma,
    fluxo_espectral,
    fluxo_nas_alturas,
    mascara_alturas,
    midi_da_nota,
    picos,
)

#: Teto da meia-janela de cada evento, em segundos.
TETO_JANELA_S = 0.30

#: Janela, após ``t_ini``, em que se soma a energia para estimar a transposição, em segundos.
JANELA_TRANSPOSICAO_S = 0.150

#: Transposições testadas (semitons), de ``-3`` a ``+7``.
K_TRANSPOSICAO = tuple(range(-3, 8))

#: Meia-largura do contexto usado na força do método ``alturas``, em segundos.
CONTEXTO_ALTURAS_S = 1.0


@dataclass(frozen=True)
class Evento:
    """Um evento de coluna: um acorde (todas as notas de uma coluna num mesmo instante).

    Attributes:
        tela: id da tela.
        exibicao: índice da exibição dentro da tela (0 é a 1ª).
        passagem: índice da passagem dentro da exibição.
        coluna: coluna do evento.
        t_ini: instante do marcador, em segundos do vídeo.
        notas: pares ``(corda, casa)`` do acorde.
    """

    tela: int
    exibicao: int
    passagem: int
    coluna: int
    t_ini: float
    notas: tuple[tuple[int, int], ...]


@dataclass
class Contexto:
    """Resultados do vídeo que são comuns a todas as medições.

    Attributes:
        mag: magnitude ``[quadros, bins]`` do vídeo inteiro.
        freqs: frequências dos bins, em Hz.
        tempos: instante de cada quadro, na linha do vídeo.
        fluxo: fluxo espectral do vídeo inteiro.
        picos_idx: índices dos picos de ``fluxo`` (``tab.audio_onsets.picos``).
        mediana_fluxo: mediana de ``fluxo``, usada na força do método ``fluxo``.
    """

    mag: np.ndarray
    freqs: np.ndarray
    tempos: np.ndarray
    fluxo: np.ndarray
    picos_idx: list[int]
    mediana_fluxo: float


def _r(valor: float | None, casas: int = 4) -> float | None:
    """Arredonda para escrever no JSON de forma estável (sha256 repetível).

    Args:
        valor: número ou ``None``.
        casas: casas decimais.

    Returns:
        ``round(valor, casas)`` como ``float``, ou ``None``.
    """
    if valor is None:
        return None
    return round(float(valor), casas)


def agrupar_eventos(notas: list[dict]) -> list[Evento]:
    """Agrupa as notas com ``t_ini`` em eventos de coluna, ordenados por tempo.

    Args:
        notas: lista ``notas`` do produto (``tab.esquema``). Notas com ``t_ini`` ``None`` são
            ignoradas.

    Returns:
        Eventos ordenados por ``t_ini`` (desempate por tela, exibição, passagem e coluna).

    Raises:
        ValueError: se as notas de um mesmo acorde tiverem ``t_ini`` diferentes.
    """
    grupos: dict[tuple[int, int, int, int], list[dict]] = {}
    for nota in notas:
        if nota.get("t_ini") is None:
            continue
        chave = (
            int(nota["tela"]),
            int(nota["exibicao"]),
            int(nota["passagem"]),
            int(nota["coluna"]),
        )
        grupos.setdefault(chave, []).append(nota)
    eventos = []
    for chave, grupo in grupos.items():
        instantes = {float(n["t_ini"]) for n in grupo}
        if len(instantes) != 1:
            raise ValueError(f"acorde com t_ini diferentes: {chave} -> {instantes}")
        pares = tuple(sorted((int(n["corda"]), int(n["casa"])) for n in grupo))
        eventos.append(Evento(*chave, t_ini=instantes.pop(), notas=pares))
    eventos.sort(key=lambda e: (e.t_ini, e.tela, e.exibicao, e.passagem, e.coluna))
    return eventos


def janelas(
    tempos: list[float], teto: float = TETO_JANELA_S
) -> list[tuple[float, float]]:
    """Meia-distância até o vizinho de cada lado, limitada pelo teto.

    ``w_esq = min(teto, (t_i - t_{i-1}) / 2)``; idem ``w_dir``; sem vizinho, ``teto``.

    Args:
        tempos: instantes dos eventos, em ordem crescente.
        teto: limite de cada meia-janela, em segundos.

    Returns:
        Lista de ``(w_esq, w_dir)``, uma por evento.
    """
    saida = []
    ultimo = len(tempos) - 1
    for i, t in enumerate(tempos):
        esq = min(teto, (t - tempos[i - 1]) / 2.0) if i > 0 else teto
        dir_ = min(teto, (tempos[i + 1] - t) / 2.0) if i < ultimo else teto
        saida.append((esq, dir_))
    return saida


def pico_mais_proximo(
    tempos_picos: np.ndarray, a: float, b: float, centro: float
) -> int | None:
    """Índice do pico dentro de ``[a, b]`` mais próximo de ``centro``.

    Args:
        tempos_picos: instantes dos picos, em segundos.
        a: início da janela.
        b: fim da janela.
        centro: referência (``t_ini`` na 1ª passada; ``t_ini + mediana`` na 2ª).

    Returns:
        Posição do pico em ``tempos_picos``, ou ``None`` se nenhum cair na janela.
    """
    dentro = np.flatnonzero((tempos_picos >= a) & (tempos_picos <= b))
    if dentro.size == 0:
        return None
    return int(dentro[np.argmin(np.abs(tempos_picos[dentro] - centro))])


def na_borda(t_pico: float, a: float, b: float, quadro: float) -> bool:
    """Se o pico está a menos de um quadro de uma das bordas da janela.

    Args:
        t_pico: instante do pico, em segundos.
        a: início da janela.
        b: fim da janela.
        quadro: duração de um quadro, em segundos (``PASSO / taxa``).

    Returns:
        ``True`` se ``t_pico - a < quadro`` ou ``b - t_pico < quadro``.
    """
    return (t_pico - a) < quadro or (b - t_pico) < quadro


def estimar_transposicao(
    mag: np.ndarray,
    freqs: np.ndarray,
    tempos: np.ndarray,
    eventos: list[Evento],
) -> tuple[int, dict[int, float], float]:
    """Escolhe a transposição (semitons) pela energia nos harmônicos esperados.

    Para cada ``k``, soma a magnitude nos bins dos harmônicos das alturas transpostas por
    ``k``, nos quadros de ``[t_ini, t_ini + JANELA_TRANSPOSICAO_S]``, sobre todos os eventos.

    Args:
        mag: magnitude do vídeo inteiro.
        freqs: frequências dos bins, em Hz.
        tempos: instantes dos quadros.
        eventos: eventos com notas.

    Returns:
        ``(k_escolhido, energia_por_k, razao_melhor_sobre_segundo)``.
    """
    energia: dict[int, float] = {}
    for k in K_TRANSPOSICAO:
        total = 0.0
        for ev in eventos:
            midis = [midi_da_nota(c, s, k) for c, s in ev.notas]
            mascara = mascara_alturas(freqs, midis)
            i0 = int(np.searchsorted(tempos, ev.t_ini, side="left"))
            i1 = int(np.searchsorted(tempos, ev.t_ini + JANELA_TRANSPOSICAO_S, "right"))
            if i1 > i0:
                total += float(mag[i0:i1][:, mascara].sum())
        energia[k] = total
    ordenados = sorted(energia.items(), key=lambda kv: (-kv[1], kv[0]))
    melhor_k, melhor_v = ordenados[0]
    segundo_v = ordenados[1][1] if len(ordenados) > 1 else 0.0
    razao = melhor_v / segundo_v if segundo_v > 0 else float("inf")
    return melhor_k, energia, razao


def _sem_ataque() -> dict:
    """Resultado de um método que não achou ataque na janela.

    Returns:
        Dicionário com ``t_som``, ``delta_ms``, ``forca`` e ``na_borda`` vazios.
    """
    return {"t_som": None, "delta_ms": None, "forca": None, "na_borda": False}


def _ataque_fluxo(
    ctx: Contexto, t_ini: float, a: float, b: float, centro: float
) -> dict:
    """Ataque pelo método ``fluxo``: pico de ``picos`` mais próximo do centro da janela.

    Args:
        ctx: resultados do vídeo.
        t_ini: marcador do evento.
        a: início da janela.
        b: fim da janela.
        centro: referência para escolher o pico.

    Returns:
        Dicionário com ``t_som``, ``delta_ms``, ``forca`` (valor do pico / mediana do fluxo do
        vídeo) e ``na_borda``.
    """
    if not ctx.picos_idx:
        return _sem_ataque()
    idx = np.asarray(ctx.picos_idx, dtype=np.int64)
    tempos_picos = ctx.tempos[idx]
    j = pico_mais_proximo(tempos_picos, a, b, centro)
    if j is None:
        return _sem_ataque()
    k = int(idx[j])
    t_som = float(ctx.tempos[k])
    forca = float(ctx.fluxo[k]) / max(ctx.mediana_fluxo, 1e-12)
    dt = float(ctx.tempos[1] - ctx.tempos[0])
    return {
        "t_som": _r(t_som, 6),
        "delta_ms": _r((t_som - t_ini) * 1000.0, 3),
        "forca": _r(forca, 3),
        "na_borda": na_borda(t_som, a, b, dt),
    }


def _ataque_alturas(
    ctx: Contexto,
    midis: list[int],
    t_ini: float,
    a: float,
    b: float,
) -> dict:
    """Ataque pelo método ``alturas``: máximo do fluxo nos harmônicos do evento.

    Só vale se o máximo dentro da janela for um pico local da curva (maior que os dois
    quadros vizinhos, que podem estar fora da janela).

    Args:
        ctx: resultados do vídeo.
        midis: MIDI das notas do evento (já transpostas).
        t_ini: marcador do evento.
        a: início da janela.
        b: fim da janela.

    Returns:
        Dicionário com ``t_som``, ``delta_ms``, ``forca`` (máximo / mediana da curva em
        ``CONTEXTO_ALTURAS_S`` ao redor do evento) e ``na_borda``.
    """
    tempos = ctx.tempos
    dt = float(tempos[1] - tempos[0]) if len(tempos) > 1 else 1.0
    k_a = int(np.searchsorted(tempos, a, side="left"))
    k_b = int(np.searchsorted(tempos, b, side="right")) - 1
    if k_b < k_a:
        return _sem_ataque()
    ini = max(0, k_a - 1)
    fim = min(len(tempos), k_b + 2)
    curva = fluxo_nas_alturas(ctx.mag[ini:fim], ctx.freqs, midis)
    seg = curva[k_a - ini : k_b - ini + 1]
    j_rel = int(np.argmax(seg))
    j = k_a - ini + j_rel
    if j < 1 or j + 1 >= len(curva):
        return _sem_ataque()
    if not (curva[j] > curva[j - 1] and curva[j] > curva[j + 1]):
        return _sem_ataque()
    k = k_a + j_rel
    n_ctx = max(1, round(CONTEXTO_ALTURAS_S / dt))
    ctx_ini = max(0, k - n_ctx)
    ctx_fim = min(len(tempos), k + n_ctx + 1)
    contexto = fluxo_nas_alturas(ctx.mag[ctx_ini:ctx_fim], ctx.freqs, midis)
    mediana_ctx = max(float(np.median(contexto)), 1e-12)
    t_som = float(tempos[k])
    return {
        "t_som": _r(t_som, 6),
        "delta_ms": _r((t_som - t_ini) * 1000.0, 3),
        "forca": _r(float(curva[j]) / mediana_ctx, 3),
        "na_borda": na_borda(t_som, a, b, dt),
    }


def medir_passada(
    eventos: list[Evento],
    larguras: list[tuple[float, float]],
    centros: list[float],
    ctx: Contexto,
    transposicao: int,
) -> list[dict]:
    """Mede os dois métodos em todos os eventos, numa passada.

    Args:
        eventos: eventos ordenados.
        larguras: ``(w_esq, w_dir)`` de cada evento.
        centros: centro da janela de cada evento (``t_ini`` ou ``t_ini + mediana``).
        ctx: resultados do vídeo.
        transposicao: semitons escolhidos por ``estimar_transposicao``.

    Returns:
        Uma entrada por evento: ``{"janela": [a, b], "fluxo": {...}, "alturas": {...}}``.
    """
    saida = []
    for ev, (w_esq, w_dir), centro in zip(eventos, larguras, centros, strict=True):
        a = centro - w_esq
        b = centro + w_dir
        midis = [midi_da_nota(c, s, transposicao) for c, s in ev.notas]
        saida.append(
            {
                "janela": [_r(a, 6), _r(b, 6)],
                "fluxo": _ataque_fluxo(ctx, ev.t_ini, a, b, centro),
                "alturas": _ataque_alturas(ctx, midis, ev.t_ini, a, b),
            }
        )
    return saida


def _estat(valores: list[float]) -> dict:
    """Mediana, percentis e MAD de uma lista de números (vazia: campos ``None``).

    Args:
        valores: Δ em ms.

    Returns:
        ``n``, ``mediana``, ``p10``, ``p25``, ``p75``, ``p90`` e ``mad`` (mediana de
        ``|x - mediana|``, sem escala).
    """
    if not valores:
        return {
            "n": 0,
            "mediana": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "mad": None,
        }
    v = np.asarray(valores, dtype=np.float64)
    med = float(np.median(v))
    return {
        "n": int(v.size),
        "mediana": _r(med, 3),
        "p10": _r(np.percentile(v, 10), 3),
        "p25": _r(np.percentile(v, 25), 3),
        "p75": _r(np.percentile(v, 75), 3),
        "p90": _r(np.percentile(v, 90), 3),
        "mad": _r(np.median(np.abs(v - med)), 3),
    }


def resumir(
    eventos: list[Evento],
    resultados: list[dict],
    metodo: str,
) -> dict:
    """Resumo de um método numa passada: contagens, Δ, borda, telas, exibições, deriva.

    Args:
        eventos: eventos (mesma ordem de ``resultados``).
        resultados: saída de ``medir_passada``.
        metodo: ``"fluxo"`` ou ``"alturas"``.

    Returns:
        Dicionário com ``com_ataque``, ``total``, ``delta_ms``, ``na_borda``, ``por_tela``,
        ``por_exibicao``, ``deriva`` e ``exib2_menos_exib1_ms`` (por tela).
    """
    com = [(ev, r[metodo]) for ev, r in zip(eventos, resultados, strict=True)]
    ok = [(ev, m) for ev, m in com if m["t_som"] is not None]
    deltas = [m["delta_ms"] for _, m in ok]

    por_tela: dict[str, dict] = {}
    for tela in sorted({ev.tela for ev in eventos}):
        sub = [(ev, m) for ev, m in com if ev.tela == tela]
        d = [m["delta_ms"] for _, m in sub if m["t_som"] is not None]
        por_tela[str(tela)] = {
            "n_com_ataque": len(d),
            "n_total": len(sub),
            **_resumo_mediana(d),
        }

    por_exibicao: dict[str, dict] = {}
    for exib in sorted({ev.exibicao for ev in eventos}):
        sub = [(ev, m) for ev, m in com if ev.exibicao == exib]
        d = [m["delta_ms"] for _, m in sub if m["t_som"] is not None]
        por_exibicao[str(exib)] = {
            "n_com_ataque": len(d),
            "n_total": len(sub),
            **_resumo_mediana(d),
        }

    diferenca: dict[str, float | None] = {}
    for tela in sorted({ev.tela for ev in eventos}):
        d1 = [m["delta_ms"] for ev, m in ok if ev.tela == tela and ev.exibicao == 0]
        d2 = [m["delta_ms"] for ev, m in ok if ev.tela == tela and ev.exibicao == 1]
        if d1 and d2:
            diferenca[str(tela)] = _r(float(np.median(d2) - np.median(d1)), 3)

    return {
        "com_ataque": len(ok),
        "total": len(com),
        "delta_ms": _estat(deltas),
        "na_borda": sum(1 for _, m in ok if m["na_borda"]),
        "por_tela": por_tela,
        "por_exibicao": por_exibicao,
        "deriva": _deriva(eventos, ok),
        "exib2_menos_exib1_ms": diferenca,
    }


def _resumo_mediana(valores: list[float]) -> dict:
    """Mediana e percentis 10 e 90 (para os cortes por tela e por exibição).

    Args:
        valores: Δ em ms.

    Returns:
        ``mediana``, ``p10`` e ``p90`` (``None`` se vazia).
    """
    if not valores:
        return {"mediana": None, "p10": None, "p90": None}
    v = np.asarray(valores, dtype=np.float64)
    return {
        "mediana": _r(float(np.median(v)), 3),
        "p10": _r(float(np.percentile(v, 10)), 3),
        "p90": _r(float(np.percentile(v, 90)), 3),
    }


def _deriva(
    todos: list[Evento],
    ok: list[tuple[Evento, dict]],
) -> dict:
    """Deriva de Δ no tempo: reta de mínimos quadrados e medianas em 4 quartos de tempo.

    Os quartos dividem o intervalo ``[primeiro t_ini, último t_ini]`` em 4 partes IGUAIS em
    tempo (não por número de eventos).

    Args:
        todos: todos os eventos (define o intervalo de tempo).
        ok: pares ``(evento, método)`` com ataque.

    Returns:
        ``inclinacao_ms_por_min`` (``None`` se houver menos de 2 pontos) e ``quartos``.
    """
    if len(ok) >= 2:
        t = np.asarray([ev.t_ini for ev, _ in ok], dtype=np.float64)
        d = np.asarray([m["delta_ms"] for _, m in ok], dtype=np.float64)
        inclinacao = _r(float(np.polyfit(t, d, 1)[0]) * 60.0, 4)
    else:
        inclinacao = None
    quartos = []
    if todos:
        t_min = min(ev.t_ini for ev in todos)
        t_max = max(ev.t_ini for ev in todos)
        bordas = np.linspace(t_min, t_max, 5)
        for q in range(4):
            a, b = float(bordas[q]), float(bordas[q + 1])
            sel = [
                m["delta_ms"]
                for ev, m in ok
                if (a <= ev.t_ini < b) or (q == 3 and ev.t_ini == b)
            ]
            quartos.append(
                {
                    "inicio_s": _r(a, 3),
                    "fim_s": _r(b, 3),
                    "com_ataque": len(sel),
                    "mediana_ms": _r(float(np.median(sel)), 3) if sel else None,
                }
            )
    return {"inclinacao_ms_por_min": inclinacao, "quartos": quartos}


def preparar(video: str) -> tuple[Contexto, dict]:
    """Áudio do vídeo: FLAC em cache (ou extraído), espectrograma, fluxo e picos.

    Args:
        video: caminho absoluto do vídeo (somente leitura).

    Returns:
        ``(contexto, meta)``: ``meta`` é o meta do A0 (``t_amostra0``, ``taxa``, ``cache``...).
    """
    flac, meta = garantir(video)
    amostras, taxa = ler(flac)
    mag, tempos, freqs = espectrograma(amostras, taxa, float(meta["t_amostra0"]))
    fluxo = fluxo_espectral(mag)
    pk = picos(fluxo, tempos)
    contexto = Contexto(
        mag=mag,
        freqs=freqs,
        tempos=tempos,
        fluxo=fluxo,
        picos_idx=pk,
        mediana_fluxo=float(np.median(fluxo)),
    )
    return contexto, meta


def analisar(eventos: list[Evento], ctx: Contexto, transposicao: int) -> dict:
    """Roda as duas passadas e monta a saída completa (eventos e resumos).

    Args:
        eventos: eventos ordenados por tempo.
        ctx: resultados do vídeo.
        transposicao: semitons escolhidos.

    Returns:
        Dicionário com ``mediana_delta_fluxo_passada1_s``, ``eventos`` e ``resumo``.
    """
    larguras = janelas([ev.t_ini for ev in eventos])
    t_ini = [ev.t_ini for ev in eventos]
    passada1 = medir_passada(eventos, larguras, t_ini, ctx, transposicao)

    deltas1 = [
        r["fluxo"]["delta_ms"] for r in passada1 if r["fluxo"]["delta_ms"] is not None
    ]
    mediana_s = float(np.median(deltas1)) / 1000.0 if deltas1 else 0.0
    centros2 = [t + mediana_s for t in t_ini]
    passada2 = medir_passada(eventos, larguras, centros2, ctx, transposicao)

    linhas = []
    for ev, (w_esq, w_dir), r1, r2 in zip(
        eventos, larguras, passada1, passada2, strict=True
    ):
        linhas.append(
            {
                "tela": ev.tela,
                "exibicao": ev.exibicao,
                "passagem": ev.passagem,
                "coluna": ev.coluna,
                "t_ini": _r(ev.t_ini, 6),
                "notas": [list(p) for p in ev.notas],
                "alturas_midi": [midi_da_nota(c, s, transposicao) for c, s in ev.notas],
                "w_esq": _r(w_esq, 6),
                "w_dir": _r(w_dir, 6),
                "passada1": r1,
                "passada2": r2,
            }
        )

    resumo = {}
    for nome, res in (("passada1", passada1), ("passada2", passada2)):
        resumo[nome] = {
            metodo: resumir(eventos, res, metodo) for metodo in ("fluxo", "alturas")
        }
    return {
        "mediana_delta_fluxo_passada1_s": _r(mediana_s, 6),
        "eventos": linhas,
        "resumo": resumo,
    }


def _imprimir_resumo(saida: dict) -> None:
    """Imprime o resumo de cada método e passada, com denominadores.

    Args:
        saida: dicionário de ``analisar``.
    """
    print(
        f"mediana de Δ (fluxo, passada 1): {saida['mediana_delta_fluxo_passada1_s']} s"
    )
    for passada, por_metodo in saida["resumo"].items():
        for metodo, r in por_metodo.items():
            d = r["delta_ms"]
            print(
                f"{passada} {metodo}: {r['com_ataque']} de {r['total']} eventos com ataque"
                f" | Δ ms mediana={d['mediana']} p10={d['p10']} p25={d['p25']}"
                f" p75={d['p75']} p90={d['p90']} MAD={d['mad']}"
                f" | na_borda={r['na_borda']}"
            )
            dr = r["deriva"]
            quartos = [q["mediana_ms"] for q in dr["quartos"]]
            print(
                f"    deriva {dr['inclinacao_ms_por_min']} ms/min | "
                f"medianas por quarto de tempo (ms): {quartos}"
            )


def main() -> int:
    """Ponto de entrada da CLI: mede o atraso de todos os eventos de um produto.

    Returns:
        Código de saída (0 se deu certo).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--produto", required=True, help="JSON do produto (mvp.json)")
    parser.add_argument(
        "--video", required=True, help="vídeo de origem (somente leitura)"
    )
    parser.add_argument("--saida", required=True, help="JSON de saída")
    args = parser.parse_args()

    with open(args.produto, encoding="utf-8") as f:
        produto = json.load(f)
    notas = produto["notas"]
    eventos = agrupar_eventos(notas)
    print(
        f"notas: {len(notas)} | com t_ini: {sum(1 for n in notas if n.get('t_ini') is not None)}"
        f" | eventos: {len(eventos)} | instantes distintos: "
        f"{len({ev.t_ini for ev in eventos})}"
    )

    ctx, meta = preparar(os.path.abspath(args.video))
    print(
        f"cache={meta['cache']} t_amostra0={meta['t_amostra0']} taxa={meta['taxa']} "
        f"quadros={ctx.mag.shape[0]} picos={len(ctx.picos_idx)} "
        f"mediana_fluxo={ctx.mediana_fluxo:.4f}"
    )

    k, energia, razao = estimar_transposicao(ctx.mag, ctx.freqs, ctx.tempos, eventos)
    maximo = max(energia.values()) or 1.0
    tabela = {
        str(kk): {
            "energia": _r(energia[kk], 3),
            "normalizada": _r(energia[kk] / maximo, 6),
        }
        for kk in K_TRANSPOSICAO
    }
    print("transposicao (k: energia normalizada):")
    for kk in K_TRANSPOSICAO:
        print(f"  {kk:+d}: {energia[kk] / maximo:.6f}")
    print(f"k escolhido: {k} | razao melhor/segundo: {_r(razao, 4)}")

    saida = analisar(eventos, ctx, k)
    saida["video"] = {
        "arquivo": os.path.abspath(args.video),
        "t_amostra0": meta["t_amostra0"],
        "taxa": meta["taxa"],
        "n_quadros": int(ctx.mag.shape[0]),
    }
    saida["parametros"] = {
        "N_FFT": N_FFT,
        "PASSO": PASSO,
        "GAMA_LOG": GAMA_LOG,
        "DELTA_PICO": DELTA_PICO,
        "TETO_JANELA_S": TETO_JANELA_S,
        "JANELA_TRANSPOSICAO_S": JANELA_TRANSPOSICAO_S,
        "CONTEXTO_ALTURAS_S": CONTEXTO_ALTURAS_S,
    }
    saida["transposicao"] = {
        "k": k,
        "tabela": tabela,
        "razao_melhor_sobre_segundo": _r(razao, 4),
    }
    saida["contagens"] = {
        "notas": len(notas),
        "notas_com_t_ini": sum(1 for n in notas if n.get("t_ini") is not None),
        "eventos": len(eventos),
        "instantes_distintos": len({ev.t_ini for ev in eventos}),
    }
    _imprimir_resumo(saida)

    destino = args.saida
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    texto = json.dumps(saida, ensure_ascii=False, indent=1, sort_keys=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    print(f"gravado: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
