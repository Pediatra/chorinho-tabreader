"""Rodada 1030 (só desenvolvimento): consenso com o vídeo inteiro e nut fora da imagem.

Pré-registro: ``docs/rodadas/1030-video-inteiro-e-nut-fora.md`` (commit 7332f4d8). Nada
daqui entra num ciclo sem rodada própria.

Parte A: os 16 vídeos revisados (8 da 1026 e 8 da 1027), lidos a 2 quadros por segundo com
o detector dos ciclos (``L2_todos_s1`` + ``A3_100_todos_s1``, sem retreino). Cada quadro é
previsto sozinho; depois vêm o consenso denso por vídeo (tomadas e sinal S4) e o modo
corrige (renumera pelo deslocamento k). Os quadros não vão para o disco: o ``ler_trecho``
do ``tab.maos_braco_cadeia`` os entrega por um fluxo do ffmpeg. Grava ``video_<nn>.jsonl``
por vídeo e ``parte_a.json``.

Parte B: numeração do primeiro traste visível quando o nut está fora da imagem. Quatro
métodos: 1 nut ausente (só sinaliza), 2 ajuste com b livre, 3 ajuste com a hipótese de fim
do braço, 4 tomada (a numeração de outro quadro da mesma tomada que viu o nut). Grava
``parte_b.json``.

CLI: ``python -m tab.maos_braco_video {parte-a,parte-b}`` (GPU, com a trava da GPU).
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import os
import random
import statistics
import sys
from pathlib import Path

import numpy as np
import torch.nn as nn

from .caminhos import (
    GABARITO_BRACO_M11B,
    GABARITO_BRACO_M25_PROVA,
    GABARITO_BRACO_M25_TREINO,
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    MAOS_M11B,
    MAOS_M25,
    MAOS_M26,
    MAOS_M27,
    MAOS_M30,
    acervo,
)
from .maos_braco_cadeia import ler_trecho
from .maos_braco_ciclo import (
    ARQUIVO_INDICE,
    ARQUIVO_SORTEIO,
    ESTAGIO1,
    ESTAGIO2,
    _ler_json,
    aplicar_consenso,
    medir_quadros,
    previsto_do_resultado,
)
from .maos_braco_consenso import (
    _curva_da_referencia,
    _meio_geral,
    mesma_tomada,
    tomadas,
)
from .maos_braco_detector import (
    CANAL_CORDA1,
    CANAL_CORDA6,
    CANAL_NUT,
    CANAL_TRASTES,
    LIMITE_CRISTA,
    LIMITE_NUT,
    N_MAX_V2,
    PASSOS,
    TOLERANCIA_V2,
    _ajustar_corda,
    _carregar_pesos,
    _imagem,
    _perfil_entre_cordas,
    _picos,
    _trava_gpu,
    prever_mapas,
)
from .maos_braco_faixa import (
    LARGURA_FAIXA,
    matriz_da_faixa,
    perturbar,
    recortar,
    voltar,
)
from .maos_braco_gabarito import numerar_trastes
from .maos_braco_localizador import _carregar_localizador, cadeia, sinalizado
from .maos_braco_regra import s_do_traste
from .maos_gabarito import gravar_atomico

#: Parte A: quadros por segundo do vídeo inteiro (passo de 0,5 s).
QUADROS_POR_SEGUNDO = 2
PASSO_S = 1.0 / QUADROS_POR_SEGUNDO
#: Parte A: um quadro revisado recebe o quadro denso mais próximo, a até este tempo.
TOLERANCIA_REVISADO_S = 0.25

#: Parte A: rodadas revisadas (gabarito do dono e pasta com ``sorteio.json``/``indice.json``).
RODADAS_REVISADAS = {
    "1026": (GABARITO_BRACO_M26, MAOS_M26),
    "1027": (GABARITO_BRACO_M27, MAOS_M27),
}

#: Parte B: o nut é dado como ausente quando a ponta das cordas do lado do nut está a até
#: esta fração da borda menor da imagem (o método 1, da pré-registração de 1030).
FRACAO_BORDA = 0.02
#: Parte B: número do primeiro traste visível testado nos métodos 2 e 3, de 1 a 5.
PRIMEIRO_MINIMO = 1
PRIMEIRO_MAXIMO = 5
#: Parte B: hipóteses de fim do braço (última casa visível), de aço ou clássico.
FIM_DO_BRACO = (18, 19, 20)
#: Parte B: iterações do ajuste com b livre (reatribui os picos até estabilizar).
ITERACOES_AJUSTE = 8
#: Parte B: mínimo de picos para um ajuste (3 parâmetros e 1 de folga).
MIN_PICOS_AJUSTE = 4
#: Parte B: diferença de resíduo (em fração do espaço local) abaixo da qual duas hipóteses
#: empatam. Empate entre hipóteses com números diferentes é recusa: a numeração é ambígua.
EMPATE_RESIDUO = 1e-3
#: Parte B: semente da perturbação do eixo de cada caso (como na 1022).
SEMENTE_CASO = "20261030:B:{}"

#: Fontes de quadros com nut fora e referência de traste (dados de desenvolvimento).
FONTES_B = (
    ("C", GABARITO_BRACO_M25_TREINO, MAOS_M25 / "treino"),
    ("N", GABARITO_BRACO_M25_PROVA, MAOS_M25 / "prova"),
    ("1026", GABARITO_BRACO_M26, MAOS_M26),
    ("1027", GABARITO_BRACO_M27, MAOS_M27),
    ("M11B", GABARITO_BRACO_M11B, MAOS_M11B),
)

ARQUIVO_PARTE_A = MAOS_M30 / "parte_a.json"
ARQUIVO_PARTE_B = MAOS_M30 / "parte_b.json"

#: Critério do modo corrige (pré-registro 1030, parte A).
CRITERIO_CORRIGE = (
    "o modo corrige não pode transformar nenhum certo em errado nos quadros revisados, e "
    "precisa transformar ao menos 1 errado em certo; se os dois, o consenso denso vai a um "
    "ciclo seguinte; senão fica só o S4"
)


# ---------------------------------------------------------------------------------
# Parte A: vídeo inteiro
# ---------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class VideoRevisado:
    """Um dos 16 vídeos revisados: rodada de origem, caminho no acervo e duração.

    Attributes:
        numero: posição de 1 a 16 (nome do ``video_<nn>.jsonl``).
        rodada: ``"1026"`` ou ``"1027"``.
        arquivo: caminho relativo ao acervo.
        duracao_s: duração do vídeo, em segundos.
    """

    numero: int
    rodada: str
    arquivo: str
    duracao_s: float


def videos_revisados() -> list[VideoRevisado]:
    """Os vídeos dos sorteios da 1026 e da 1027, na ordem de cada sorteio.

    Returns:
        16 vídeos (8 de cada rodada), numerados de 1 a 16.
    """
    saida: list[VideoRevisado] = []
    for rodada, (_, pasta) in RODADAS_REVISADAS.items():
        for video in _ler_json(pasta / ARQUIVO_SORTEIO)["videos"]:
            saida.append(
                VideoRevisado(
                    numero=len(saida) + 1,
                    rodada=rodada,
                    arquivo=video["arquivo"],
                    duracao_s=float(video["duracao_s"]),
                )
            )
    return saida


def nome_jsonl(numero: int) -> str:
    """Nome do arquivo com os quadros de um vídeo.

    Args:
        numero: posição do vídeo (1 a 16).

    Returns:
        ``video_<nn>.jsonl``.
    """
    return f"video_{numero:02d}.jsonl"


def corrigir_pela_tomada(quadros: dict[str, dict]) -> dict[str, dict | None]:
    """Modo corrige: renumera pelo k cada quadro com S4, e o nut vem da referência.

    Um quadro com deslocamento k ≠ 0 em relação à referência da tomada recebe cada número
    de traste somado a k. Se a referência viu o nut, o nut do quadro passa a ser o dela.
    Quadro sem S4 fica sem correção (``None``).

    Args:
        quadros: ``{id: entrada de previsto.json}`` já com ``S4`` (``aplicar_consenso``).

    Returns:
        ``{id: entrada corrigida ou None}``, com as mesmas chaves de ``quadros``.
    """
    saida: dict[str, dict | None] = {}
    for id_q, quadro in quadros.items():
        sinal = quadro.get("S4")
        if not quadro["achou"] or not sinal or not sinal.get("S4"):
            saida[id_q] = None
            continue
        corrigido = copy.deepcopy(quadro)
        corrigido.pop("S4", None)
        k = int(sinal["k"])
        for item in corrigido["trastes"]:
            item["numero"] = int(item["numero"]) + k
        referencia = quadros[sinal["referencia"]]
        if referencia.get("nut") is not None:
            corrigido["nut"] = copy.deepcopy(referencia["nut"])
        saida[id_q] = corrigido
    return saida


def processar_video(
    video: VideoRevisado, loc: nn.Module, dois: nn.Module
) -> list[dict]:
    """Roda a cadeia em todos os quadros a 2 fps do vídeo e aplica o consenso denso (GPU).

    Args:
        video: vídeo a processar.
        loc: estágio 1 (``L2_todos_s1``).
        dois: estágio 2 (``A3_100_todos_s1``).

    Returns:
        Um registro por quadro, na ordem do tempo: ``id``, ``t``, ``previsto`` (sozinho),
        ``S4`` (sinal do consenso ou None), ``sinalizado_s4`` (depois do S4) e
        ``corrigido`` (modo corrige ou None).
    """
    previstos: dict[str, dict] = {}
    dimensoes: dict[str, tuple[int, int]] = {}
    tempos: dict[str, float] = {}
    ordem: list[str] = []
    fluxo = ler_trecho(acervo() / video.arquivo, 0.0, video.duracao_s, PASSO_S)
    for k, (t, imagem) in enumerate(fluxo):
        id_q = f"v{video.numero:02d}_{k:05d}"
        resultado = cadeia(loc, dois, imagem, id_q, conjunta=True)
        previstos[id_q] = previsto_do_resultado(
            {"arquivo": video.arquivo}, resultado, sinalizado(resultado)
        )
        dimensoes[id_q] = (imagem.shape[1], imagem.shape[0])
        tempos[id_q] = t
        ordem.append(id_q)
        if k % 200 == 0:
            print(f"{video.arquivo}: {k} quadros (t={t:.1f} s)", flush=True)
    novos = aplicar_consenso({"ordem": ordem, "quadros": previstos}, dimensoes)[
        "quadros"
    ]
    corrigidos = corrigir_pela_tomada(novos)
    return [
        {
            "id": id_q,
            "t": round(tempos[id_q], 3),
            "previsto": previstos[id_q],
            "S4": novos[id_q].get("S4"),
            "sinalizado_s4": bool(novos[id_q]["sinalizado"]),
            "corrigido": corrigidos[id_q],
        }
        for id_q in ordem
    ]


def gravar_jsonl(destino: Path, registros: list[dict]) -> None:
    """Grava uma linha JSON por registro, de forma atômica.

    Args:
        destino: arquivo final (``video_<nn>.jsonl``).
        registros: registros do ``processar_video``.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".tmp")
    with temporario.open("w", encoding="utf-8") as saida:
        for registro in registros:
            saida.write(json.dumps(registro, ensure_ascii=False) + "\n")
    os.replace(temporario, destino)


def ler_jsonl(caminho: Path) -> list[dict]:
    """Lê um arquivo com uma linha JSON por registro.

    Args:
        caminho: arquivo ``.jsonl``.

    Returns:
        Os registros, na ordem do arquivo.
    """
    with caminho.open(encoding="utf-8") as entrada:
        return [json.loads(linha) for linha in entrada if linha.strip()]


def estatisticas_sem_rotulo(registros: list[dict]) -> dict:
    """Estatísticas do vídeo sem rótulo: tomadas, tamanho e discordância da tomada.

    Args:
        registros: registros de um vídeo (``processar_video``).

    Returns:
        Quadros, quadros com braço, tomadas, tamanho das tomadas, fração de quadros em
        tomada de 2 ou mais, e fração dos quadros com referência que discordam (S4).
    """
    com_braco = [
        {
            "id": r["id"],
            "arquivo": r["previsto"]["arquivo"],
            "corda1": r["previsto"]["corda1"],
            "corda6": r["previsto"]["corda6"],
        }
        for r in registros
        if r["previsto"]["achou"]
    ]
    grupos = tomadas(com_braco) if com_braco else []
    tamanhos = [len(g) for g in grupos]
    com_referencia = [
        r for r in registros if r["S4"] is not None and r["S4"].get("referencia")
    ]
    discordam = [r for r in com_referencia if r["S4"]["S4"]]
    return {
        "quadros": len(registros),
        "com_braco": len(com_braco),
        "tomadas": len(grupos),
        "tamanho_medio": statistics.fmean(tamanhos) if tamanhos else None,
        "tamanho_mediano": statistics.median(tamanhos) if tamanhos else None,
        "tamanho_maximo": max(tamanhos) if tamanhos else None,
        "fracao_em_tomada_de_2_ou_mais": (
            sum(t for t in tamanhos if t >= 2) / len(com_braco) if com_braco else None
        ),
        "quadros_com_referencia": len(com_referencia),
        "fracao_discordam_da_tomada": (
            len(discordam) / len(com_referencia) if com_referencia else None
        ),
    }


def contar_transicoes(antes: list[dict], depois: list[dict]) -> dict:
    """Quadros que mudam de certo para errado (e o contrário) entre dois modos.

    Args:
        antes: linhas da medida no modo de referência (``sozinho``).
        depois: linhas da medida no modo comparado (``corrige``).

    Returns:
        Listas de ids e contagens, e se o consenso denso passa para um ciclo seguinte.
    """
    certo_antes = {linha["id"]: linha["correto"] for linha in antes}
    certo_depois = {linha["id"]: linha["correto"] for linha in depois}
    comuns = certo_antes.keys() & certo_depois.keys()
    perdeu = sorted(i for i in comuns if certo_antes[i] and not certo_depois[i])
    ganhou = sorted(i for i in comuns if not certo_antes[i] and certo_depois[i])
    return {
        "certo_para_errado": perdeu,
        "errado_para_certo": ganhou,
        "n_certo_para_errado": len(perdeu),
        "n_errado_para_certo": len(ganhou),
        "passa_para_ciclo": not perdeu and bool(ganhou),
    }


def medir_parte_a(videos: list[VideoRevisado]) -> dict:
    """Mede a parte A nos quadros revisados (±0,25 s do quadro denso), três modos.

    Modos: ``sozinho`` (a previsão do quadro), ``s4`` (com o sinal do consenso denso) e
    ``corrige`` (com a renumeração pelo k). A marca do dono é a do gabarito da rodada.

    Args:
        videos: os 16 vídeos revisados.

    Returns:
        Totais por modo, transições ``sozinho`` -> ``corrige``, estatísticas sem rótulo por
        vídeo e os quadros excluídos, com o motivo.
    """
    ordem: list[str] = []
    gabarito: dict[str, dict] = {}
    modos: dict[str, dict[str, dict]] = {"sozinho": {}, "s4": {}, "corrige": {}}
    excluidos: list[dict] = []
    sem_rotulo: dict[str, dict] = {}
    for video in videos:
        registros = ler_jsonl(MAOS_M30 / nome_jsonl(video.numero))
        chave_video = f"v{video.numero:02d}"
        sem_rotulo[chave_video] = {
            "rodada": video.rodada,
            "arquivo": video.arquivo,
            **estatisticas_sem_rotulo(registros),
        }
        denso = {round(r["t"] * QUADROS_POR_SEGUNDO): r for r in registros}
        gabarito_rodada, pasta = RODADAS_REVISADAS[video.rodada]
        registros_dono = _ler_json(gabarito_rodada)["quadros"]
        indice = _ler_json(pasta / ARQUIVO_INDICE)["quadros"]
        for item in indice:
            if item["arquivo"] != video.arquivo:
                continue
            chave = f"{video.rodada}:{item['id']}"
            rec = denso.get(round(float(item["t"]) * QUADROS_POR_SEGUNDO))
            if rec is None or abs(rec["t"] - float(item["t"])) > TOLERANCIA_REVISADO_S:
                excluidos.append({"chave": chave, "motivo": "sem quadro denso"})
                continue
            if item["id"] not in registros_dono:
                excluidos.append({"chave": chave, "motivo": "sem registro no gabarito"})
                continue
            ordem.append(chave)
            gabarito[chave] = registros_dono[item["id"]]
            modos["sozinho"][chave] = rec["previsto"]
            modos["s4"][chave] = {**rec["previsto"], "sinalizado": rec["sinalizado_s4"]}
            corrigido = rec["corrigido"] or rec["previsto"]
            modos["corrige"][chave] = {**corrigido, "sinalizado": rec["sinalizado_s4"]}
    medidas = {
        modo: medir_quadros(
            {"ordem": ordem, "quadros": previstos},
            {"quadros": gabarito},
            "a próxima rodada",
        )
        for modo, previstos in modos.items()
    }
    excluidos += medidas["sozinho"]["excluidos"]
    return {
        "rodada": 1030,
        "parte": "A",
        "videos": [
            {"numero": v.numero, "rodada": v.rodada, "arquivo": v.arquivo}
            for v in videos
        ],
        "quadros_medidos": len(ordem),
        "excluidos": excluidos,
        "modos": {modo: medida["totais"] for modo, medida in medidas.items()},
        "transicoes_sozinho_para_corrige": contar_transicoes(
            medidas["sozinho"]["linhas"], medidas["corrige"]["linhas"]
        ),
        "linhas": {modo: medida["linhas"] for modo, medida in medidas.items()},
        "sem_rotulo": sem_rotulo,
        "criterio": CRITERIO_CORRIGE,
    }


def parte_a() -> dict:
    """Parte A completa: roda os vídeos que faltam (GPU) e mede os 128 quadros revisados.

    Vídeo já feito (com o ``video_<nn>.jsonl``) é pulado. A trava da GPU é tomada por vídeo.

    Returns:
        O resultado gravado em ``parte_a.json``.
    """
    videos = videos_revisados()
    for video in videos:
        destino = MAOS_M30 / nome_jsonl(video.numero)
        if destino.exists():
            print(f"pulo {destino.name}: já feito", flush=True)
            continue
        with _trava_gpu():
            loc = _carregar_localizador(ESTAGIO1)
            dois, _ = _carregar_pesos(ESTAGIO2, PASSOS)
            registros = processar_video(video, loc, dois)
        gravar_jsonl(destino, registros)
        print(f"{destino.name}: {len(registros)} quadros", flush=True)
    resultado = medir_parte_a(videos)
    gravar_atomico(ARQUIVO_PARTE_A, resultado)
    return resultado


# ---------------------------------------------------------------------------------
# Parte B: nut fora da imagem (métodos de numeração)
# ---------------------------------------------------------------------------------


def eixo_sem_nut(
    corda1: list, corda6: list, largura: int, altura: int
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Eixo da faixa sem nut: a origem é a ponta das cordas mais perto de uma borda.

    Com o nut fora da imagem, o lado do nut é a ponta das cordas que fica mais perto da
    borda do quadro. O extremo é a outra ponta. Mesmo formato que ``eixo_da_faixa``.

    Args:
        corda1: dois pontos da corda 1, no quadro.
        corda6: dois pontos da corda 6, no quadro.
        largura: largura do quadro.
        altura: altura do quadro.

    Returns:
        ``(origem, direcao, comprimento, largura)``, no quadro.

    Raises:
        ValueError: se as cordas não têm dois pontos, ou o eixo é degenerado.
    """
    c1 = np.asarray(corda1, dtype=float)
    c6 = np.asarray(corda6, dtype=float)
    if c1.shape != (2, 2) or c6.shape != (2, 2):
        raise ValueError("as cordas 1 e 6 precisam de dois pontos cada")

    def distancia_a_borda(ponto: np.ndarray) -> float:
        """Menor distância de um ponto às quatro bordas do quadro."""
        return min(ponto[0], largura - ponto[0], ponto[1], altura - ponto[1])

    lado = min(
        (0, 1),
        key=lambda i: distancia_a_borda(c1[i]) + distancia_a_borda(c6[i]),
    )
    origem = (c1[lado] + c6[lado]) / 2.0
    vetor = (c1[1 - lado] + c6[1 - lado]) / 2.0 - origem
    comprimento = float(np.linalg.norm(vetor))
    if comprimento == 0.0:
        raise ValueError("eixo sem comprimento")
    u = vetor / comprimento
    normal = np.array([-u[1], u[0]])
    largura_eixo = max(abs(float(np.dot(c6[i] - c1[i], normal))) for i in (0, 1))
    if largura_eixo == 0.0:
        raise ValueError("cordas 1 e 6 coincidem")
    return origem, u, comprimento, largura_eixo


@dataclasses.dataclass(frozen=True)
class Geometria:
    """Cordas e picos de uma faixa, sem depender do nut.

    Attributes:
        xs: colunas da faixa (0 a 1023).
        y1: reta da corda 1 em cada coluna.
        y6: reta da corda 6 em cada coluna.
        picos: x dos picos do canal de trastes entre as cordas, em ordem.
        nut_max: maior valor do canal do nut entre as cordas.
        inicio: primeira coluna em que alguma corda aparece (None se nenhuma).
    """

    xs: np.ndarray
    y1: np.ndarray
    y6: np.ndarray
    picos: list[int]
    nut_max: float
    inicio: int | None


def geometria_sem_nut(mapas: np.ndarray) -> Geometria | None:
    """Cordas, picos e sinais do nut de uma faixa (sem exigir o pico do nut).

    Args:
        mapas: probabilidades ``(4, 192, 1024)`` do estágio 2.

    Returns:
        A ``Geometria``, ou None se alguma corda não tem reta.
    """
    reta1 = _ajustar_corda(mapas[CANAL_CORDA1])
    reta6 = _ajustar_corda(mapas[CANAL_CORDA6])
    if reta1 is None or reta6 is None:
        return None
    xs = np.arange(mapas.shape[2], dtype=float)
    y1 = reta1[0] * xs + reta1[1]
    y6 = reta6[0] * xs + reta6[1]
    perfil_nut = _perfil_entre_cordas(mapas[CANAL_NUT], y1, y6)
    picos = _picos(_perfil_entre_cordas(mapas[CANAL_TRASTES], y1, y6))
    presente = (
        np.maximum(mapas[CANAL_CORDA1].max(axis=0), mapas[CANAL_CORDA6].max(axis=0))
        > LIMITE_CRISTA
    )
    colunas = np.nonzero(presente)[0]
    return Geometria(
        xs=xs,
        y1=y1,
        y6=y6,
        picos=picos,
        nut_max=float(perfil_nut.max()),
        inicio=int(colunas.min()) if colunas.size else None,
    )


def nut_ausente(geo: Geometria, matriz: np.ndarray, dimensoes: tuple[int, int]) -> bool:
    """Método 1: o nut está fora da imagem (ausente) pelas duas provas do pré-registro.

    É ausente quando a ponta das cordas do lado do nut toca a borda do quadro (a até 2 %
    da borda menor), ou quando o canal do nut é fraco (abaixo de ``LIMITE_NUT``).

    Args:
        geo: geometria da faixa (``geometria_sem_nut``).
        matriz: afim da faixa (``matriz_da_faixa``).
        dimensoes: ``(largura, altura)`` do quadro original.

    Returns:
        True quando o nut deve ser tratado como ausente.
    """
    largura, altura = dimensoes
    if geo.inicio is None:
        return True
    x = float(geo.inicio)
    pontas_faixa = np.array(
        [[x, geo.y1[geo.inicio]], [x, geo.y6[geo.inicio]]], dtype=float
    )
    pontas = voltar(pontas_faixa, matriz)
    distancia = min(min(p[0], largura - p[0], p[1], altura - p[1]) for p in pontas)
    toca_borda = distancia <= FRACAO_BORDA * min(largura, altura)
    return bool(toca_borda or geo.nut_max < LIMITE_NUT)


def _posicoes(params: np.ndarray) -> np.ndarray | None:
    """Posições ``t(n)`` do modelo projetivo com b livre, para n de 0 a ``N_MAX_V2 + 1``.

    Args:
        params: ``[a, b, c]`` de ``t = (a s + b) / (c s + 1)``.

    Returns:
        O array de posições, ou None se o denominador não é positivo ou t não cresce.
    """
    a, b, c = (float(v) for v in params)
    s = np.array([s_do_traste(n) for n in range(N_MAX_V2 + 2)], dtype=float)
    den = c * s + 1.0
    if np.any(den[: N_MAX_V2 + 1] <= 1e-9):
        return None
    t = (a * s + b) / den
    if np.any(np.diff(t[: N_MAX_V2 + 1]) <= 0.0):
        return None
    return t


def _ajuste(pares: list[tuple[int, float]]) -> np.ndarray | None:
    """Mínimos quadrados de ``(a, b, c)`` nos pares (número, posição), com b livre.

    Args:
        pares: pares ``(n, x)`` do pico ``x`` atribuído ao traste ``n``.

    Returns:
        ``[a, b, c]``, ou None com menos de 3 números distintos.
    """
    if len({n for n, _ in pares}) < 3:
        return None
    s = np.array([s_do_traste(n) for n, _ in pares], dtype=float)
    t = np.array([x for _, x in pares], dtype=float)
    matriz = np.column_stack([s, np.ones_like(s), -t * s])
    solucao, *_ = np.linalg.lstsq(matriz, t, rcond=None)
    return solucao


def _inliers(picos: list[float], t: np.ndarray) -> list[tuple[int, float]]:
    """Atribui cada pico ao traste mais próximo, um para um, dentro da tolerância.

    Como no ``_numerar_v2``: o pico entra no traste ``n`` se está a até ``TOLERANCIA_V2``
    do espaço local, e cada pico serve a um número só.

    Args:
        picos: x dos picos, em ordem crescente.
        t: posições do modelo (``_posicoes``).

    Returns:
        Pares ``(n, x)`` em ordem de número (e de x).
    """
    usados: set[int] = set()
    pares: list[tuple[int, float]] = []
    for n in range(1, N_MAX_V2 + 1):
        if t[n] >= LARGURA_FAIXA:
            break
        espaco = float(t[n + 1] - t[n])
        candidatos = [
            (abs(p - t[n]), i)
            for i, p in enumerate(picos)
            if i not in usados and abs(p - t[n]) <= TOLERANCIA_V2 * espaco
        ]
        if not candidatos:
            continue
        _, i = min(candidatos)
        usados.add(i)
        pares.append((n, picos[i]))
    return pares


def _residuo(pares: list[tuple[int, float]], t: np.ndarray) -> float:
    """Soma dos erros de cada pico, em fração do espaço local (menor é melhor).

    Args:
        pares: pares ``(n, x)`` dos inliers.
        t: posições do modelo.

    Returns:
        A soma dos erros normalizados.
    """
    return float(sum(abs(x - t[n]) / float(t[n + 1] - t[n]) for n, x in pares))


def _ajustar_b_livre(
    picos: list[float], iniciais: list[tuple[int, float]]
) -> dict | None:
    """Ajuste com b livre a partir de uma numeração inicial (iterado até estabilizar).

    Args:
        picos: x dos picos, em ordem crescente.
        iniciais: numeração de partida ``(n, x)``.

    Returns:
        ``{"pares", "inliers", "residuo"}``, ou None se o ajuste falha ou há poucos inliers.
    """
    pares = iniciais
    for _ in range(ITERACOES_AJUSTE):
        params = _ajuste(pares)
        if params is None:
            return None
        t = _posicoes(params)
        if t is None:
            return None
        novos = _inliers(picos, t)
        if len(novos) < MIN_PICOS_AJUSTE:
            return None
        if novos == pares:
            break
        pares = novos
    return {"pares": pares, "inliers": len(pares), "residuo": _residuo(pares, t)}


def hipoteses(picos: list[float], com_fim: bool) -> list[dict]:
    """Ajustes com b livre para cada hipótese de numeração inicial.

    A hipótese do primeiro traste visível é 1 a 5 (o primeiro pico recebe esse número e os
    seguintes, em sequência). Com ``com_fim``, entram também as hipóteses em que o último
    pico é o traste 18, 19 ou 20 (fim do braço, uma hipótese a mais, nunca verdade).

    Args:
        picos: x dos picos, em ordem crescente.
        com_fim: se True, acrescenta as hipóteses de fim do braço (método 3).

    Returns:
        Os ajustes que convergiram, cada um com a ``origem`` da hipótese.
    """
    if len(picos) < MIN_PICOS_AJUSTE:
        return []
    saida: list[dict] = []
    for primeiro in range(PRIMEIRO_MINIMO, PRIMEIRO_MAXIMO + 1):
        iniciais = [
            (primeiro + i, x) for i, x in enumerate(picos) if primeiro + i <= N_MAX_V2
        ]
        resultado = _ajustar_b_livre(picos, iniciais)
        if resultado is not None:
            saida.append({**resultado, "origem": f"primeiro={primeiro}"})
    if com_fim:
        for fim in FIM_DO_BRACO:
            total = len(picos)
            iniciais = [
                (fim - (total - 1 - i), x)
                for i, x in enumerate(picos)
                if fim - (total - 1 - i) >= 1
            ]
            resultado = _ajustar_b_livre(picos, iniciais)
            if resultado is not None:
                saida.append({**resultado, "origem": f"fim={fim}"})
    return saida


def melhor_numeracao(picos: list[float], com_fim: bool) -> dict | None:
    """Melhor hipótese (mais inliers e, em empate, menor resíduo) e os empates.

    ``empatados`` lista os números do primeiro traste das hipóteses que empatam com a
    melhor (mesmo número de inliers e resíduo a até ``EMPATE_RESIDUO``). Se o empate tem
    números diferentes, a numeração é ambígua (ver ``numero_decidido``).

    Args:
        picos: x dos picos, em ordem crescente.
        com_fim: se True, entram as hipóteses de fim do braço (método 3).

    Returns:
        A melhor hipótese com ``empatados``, ou None (nenhuma hipótese converge).
    """
    candidatos = hipoteses(picos, com_fim)
    if not candidatos:
        return None
    melhor = max(candidatos, key=lambda h: (h["inliers"], -h["residuo"]))
    empatados = sorted(
        {
            numero_do_primeiro(h)
            for h in candidatos
            if h["inliers"] == melhor["inliers"]
            and h["residuo"] <= melhor["residuo"] + EMPATE_RESIDUO
        }
    )
    return {**melhor, "empatados": empatados}


def numero_do_primeiro(numeracao: dict | None) -> int | None:
    """Número do primeiro traste visível (o de menor x entre os inliers), sem regra de empate.

    Args:
        numeracao: resultado de ``melhor_numeracao``, ou None.

    Returns:
        O número da melhor hipótese, ou None se não há numeração.
    """
    if not numeracao or not numeracao["pares"]:
        return None
    return int(numeracao["pares"][0][0])


def numero_decidido(numeracao: dict | None) -> int | None:
    """Número do primeiro traste que o método afirma, ou None (recusa).

    Recusa quando não há numeração, ou quando as melhores hipóteses empatam em números
    diferentes: o resíduo não distingue o número do primeiro traste.

    Args:
        numeracao: resultado de ``melhor_numeracao``, ou None.

    Returns:
        O número decidido, ou None.
    """
    if not numeracao or len(numeracao["empatados"]) != 1:
        return None
    return int(numeracao["empatados"][0])


def numero_pela_tomada(ponto: np.ndarray, referencia: dict) -> int | None:
    """Método 4: número de um ponto do quadro, lido na curva de um quadro da mesma tomada.

    Args:
        ponto: ponto no quadro original (o primeiro traste visível detectado).
        referencia: quadro com nut visível, ``nut``, ``corda1``, ``corda6`` e ``trastes``
            numerados (``[{numero, ponto}]``).

    Returns:
        O número inteiro mais próximo, ou None se o ponto cai fora da curva da referência.
    """
    curva = _curva_da_referencia(referencia)
    if curva is None:
        return None
    numeros_ref, t_ref, origem, u = curva
    t = float(np.dot(np.asarray(ponto, dtype=float) - origem, u))
    if not (t_ref[0] <= t <= t_ref[-1]):
        return None
    return round(float(np.interp(t, t_ref, numeros_ref)))


def _referencia_de(registro: dict, arquivo: str) -> dict | None:
    """Quadro de referência (nut visível) de um registro do gabarito, ou None.

    Args:
        registro: resposta do dono com ``nut`` (lista), cordas e trastes.
        arquivo: vídeo do quadro (para a tomada).

    Returns:
        Quadro de referência no formato de ``numero_pela_tomada``, ou None.
    """
    if not isinstance(registro.get("nut"), list):
        return None
    if registro.get("corda1") is None or registro.get("corda6") is None:
        return None
    trastes = [
        {"numero": t["numero"], "ponto": t["ponto"]}
        for t in numerar_trastes(registro)
        if t["numero"] is not None
    ]
    if not trastes:
        return None
    return {
        "arquivo": arquivo,
        "nut": registro["nut"],
        "corda1": registro["corda1"],
        "corda6": registro["corda6"],
        "trastes": trastes,
    }


@dataclasses.dataclass(frozen=True)
class CasoB:
    """Quadro de desenvolvimento com nut fora e referência de traste (dono).

    Attributes:
        id: ``<fonte>:<id do quadro>``.
        fonte: origem do quadro (``C``, ``N``, ``1026``, ``1027`` ou ``M11B``).
        arquivo: vídeo no acervo.
        png: imagem do quadro.
        largura: largura do quadro original.
        altura: altura do quadro original.
        corda1: dois pontos da corda 1 (dono).
        corda6: dois pontos da corda 6 (dono).
        verdade: número do traste de referência, marcado pelo dono.
    """

    id: str
    fonte: str
    arquivo: str
    png: Path
    largura: int
    altura: int
    corda1: list
    corda6: list
    verdade: int


def carregar_casos() -> tuple[list[CasoB], dict[str, list[dict]]]:
    """Casos de desenvolvimento e as referências com nut visível de cada fonte.

    Um caso é um quadro com ``nut == "fora"``, ``traste_referencia`` e cordas. Fonte sem
    caso é pulada (é o que acontece com o C, que não tem referência).

    Returns:
        ``(casos, referencias)``: os casos, e ``{fonte: [referências]}``.
    """
    casos: list[CasoB] = []
    referencias: dict[str, list[dict]] = {}
    for fonte, gabarito, pasta in FONTES_B:
        quadros = _ler_json(gabarito)["quadros"]
        indice = {
            item["id"]: item for item in _ler_json(pasta / ARQUIVO_INDICE)["quadros"]
        }
        referencias[fonte] = []
        for id_q, registro in quadros.items():
            if id_q not in indice:
                continue
            item = indice[id_q]
            ref = _referencia_de(registro, item["arquivo"])
            if ref is not None:
                referencias[fonte].append(ref)
            if registro.get("nut") != "fora" or not registro.get("traste_referencia"):
                continue
            if registro.get("corda1") is None or registro.get("corda6") is None:
                continue
            casos.append(
                CasoB(
                    id=f"{fonte}:{id_q}",
                    fonte=fonte,
                    arquivo=item["arquivo"],
                    png=pasta / item["png"],
                    largura=int(item["largura"]),
                    altura=int(item["altura"]),
                    corda1=registro["corda1"],
                    corda6=registro["corda6"],
                    verdade=int(registro["traste_referencia"]["numero"]),
                )
            )
    return casos, referencias


def _quadro_do_primeiro(
    geo: Geometria, primeiro_x: float, matriz: np.ndarray
) -> np.ndarray:
    """Leva o primeiro pico (ponto médio das cordas nele) de volta ao quadro original.

    Args:
        geo: geometria da faixa.
        primeiro_x: x do primeiro pico na faixa.
        matriz: afim da faixa.

    Returns:
        O ponto ``(2,)`` no quadro original.
    """
    coluna = round(float(primeiro_x))
    y = (geo.y1[coluna] + geo.y6[coluna]) / 2.0
    return voltar(np.array([primeiro_x, y], dtype=float), matriz)


def analisar_caso(caso: CasoB, dois: nn.Module, referencias: list[dict]) -> dict:
    """Roda o estágio 2 na faixa do caso e aplica os métodos 1 a 4 (GPU).

    A faixa é recortada pelas cordas do dono, com a perturbação da 1022 (semente por caso).

    Args:
        caso: quadro de desenvolvimento.
        dois: estágio 2 (``A3_100_todos_s1``).
        referencias: quadros com nut visível da mesma fonte (método 4).

    Returns:
        O resultado do caso: o número verdadeiro, o método 1 e a previsão de cada método.
    """
    imagem = _imagem(caso.png)
    eixo = perturbar(
        eixo_sem_nut(caso.corda1, caso.corda6, caso.largura, caso.altura),
        random.Random(SEMENTE_CASO.format(caso.id)),
    )
    matriz = matriz_da_faixa(eixo)
    mapas = prever_mapas(dois, [recortar(imagem, matriz)])[0]
    geo = geometria_sem_nut(mapas)
    base = {
        "id": caso.id,
        "fonte": caso.fonte,
        "arquivo": caso.arquivo,
        "verdade": caso.verdade,
    }
    if geo is None:
        return {**base, "nut_ausente": None, "metodos": {}, "sem_faixa": True}
    dimensoes = (caso.largura, caso.altura)
    ausente = nut_ausente(geo, matriz, dimensoes)
    picos = [float(p) for p in geo.picos]
    metodos: dict[str, dict] = {}
    m2 = melhor_numeracao(picos, com_fim=False)
    metodos["2"] = _metodo_numeracao(m2)
    m3 = melhor_numeracao(picos, com_fim=True)
    metodos["3"] = _metodo_numeracao(m3)
    metodos["4"] = {"pred": None, "referencia": None}
    if picos:
        ponto = _quadro_do_primeiro(geo, picos[0], matriz)
        ref_tomada = _referencia_da_tomada(caso, referencias)
        if ref_tomada is not None:
            ref, _ = ref_tomada
            metodos["4"] = {
                "pred": numero_pela_tomada(ponto, ref),
                "referencia": ref["arquivo"],
            }
    return {**base, "nut_ausente": ausente, "metodos": metodos, "sem_faixa": False}


def _metodo_numeracao(numeracao: dict | None) -> dict:
    """Saída de um método de numeração: a previsão decidida e a bruta (argmax).

    Args:
        numeracao: resultado de ``melhor_numeracao``, ou None.

    Returns:
        ``pred`` (decidida, None é recusa), ``bruta`` (a melhor hipótese, sem regra de
        empate), ``empatados`` e ``origem``.
    """
    return {
        "pred": numero_decidido(numeracao),
        "bruta": numero_do_primeiro(numeracao) if numeracao else None,
        "empatados": numeracao["empatados"] if numeracao else [],
        "origem": numeracao["origem"] if numeracao else None,
    }


def _referencia_da_tomada(
    caso: CasoB, referencias: list[dict]
) -> tuple[dict, float] | None:
    """Referência mais próxima do caso que é da mesma tomada (regra do P3).

    Args:
        caso: quadro de desenvolvimento.
        referencias: quadros com nut visível da mesma fonte.

    Returns:
        ``(referencia, distância)``, ou None se nenhuma é da mesma tomada.
    """
    alvo = {"arquivo": caso.arquivo, "corda1": caso.corda1, "corda6": caso.corda6}
    candidatas = [r for r in referencias if mesma_tomada(alvo, r)]
    if not candidatas:
        return None
    meio = _meio_geral(alvo)
    mais_perto = min(
        candidatas, key=lambda r: float(np.linalg.norm(_meio_geral(r) - meio))
    )
    return mais_perto, float(np.linalg.norm(_meio_geral(mais_perto) - meio))


def medir_b(analisados: list[dict]) -> dict:
    """Totais por método: acertos, recusas e erros não sinalizados, contra o dono.

    Args:
        analisados: resultados de ``analisar_caso``.

    Returns:
        Totais por método, quantos casos têm faixa, e a conclusão do critério do pré-registro.
    """
    com_faixa = [a for a in analisados if not a["sem_faixa"]]
    totais: dict[str, dict] = {
        "1_nut_ausente": {
            "casos": len(com_faixa),
            "sinalizados": sum(1 for a in com_faixa if a["nut_ausente"]),
        }
    }
    for metodo, nome in (
        ("2", "2_b_livre"),
        ("3", "3_fim_do_braco"),
        ("4", "4_tomada"),
    ):
        acertos = recusas = erros = erros_brutos = 0
        for a in com_faixa:
            pred = a["metodos"][metodo]["pred"]
            bruta = a["metodos"][metodo].get("bruta", pred)
            if bruta is not None and bruta != a["verdade"]:
                erros_brutos += 1
            if pred is None:
                recusas += 1
            elif pred == a["verdade"]:
                acertos += 1
            else:
                erros += 1
        totais[nome] = {
            "casos": len(com_faixa),
            "acertos": acertos,
            "recusas": recusas,
            "erros_nao_sinalizados": erros,
            "erros_da_previsao_bruta": erros_brutos,
        }
    viaveis = [
        nome
        for nome in ("2_b_livre", "3_fim_do_braco", "4_tomada")
        if totais[nome]["erros_nao_sinalizados"] == 0 and totais[nome]["acertos"] > 0
    ]
    if viaveis:
        melhor = max(viaveis, key=lambda n: totais[n]["acertos"])
        conclusao = f"levar o método {melhor} a um ciclo"
    else:
        conclusao = "nenhum método vai ao ciclo: o nut ausente (método 1) passa a apenas sinalizar"
    totais["conclusao"] = conclusao
    return totais


def parte_b() -> dict:
    """Parte B completa: analisa os casos de desenvolvimento (GPU) e grava ``parte_b.json``.

    Returns:
        O resultado gravado: os casos (com a previsão de cada método) e os totais.
    """
    casos, referencias = carregar_casos()
    with _trava_gpu():
        dois, _ = _carregar_pesos(ESTAGIO2, PASSOS)
        analisados = [analisar_caso(c, dois, referencias[c.fonte]) for c in casos]
    resultado = {
        "rodada": 1030,
        "parte": "B",
        "casos": analisados,
        "totais": medir_b(analisados),
    }
    gravar_atomico(ARQUIVO_PARTE_B, resultado)
    return resultado


# ---------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------


def main() -> int:
    """Ponto de entrada: ``parte-a`` ou ``parte-b``.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="parte", required=True)
    sub.add_parser("parte-a", help="vídeo inteiro: roda os 16 vídeos (GPU) e mede")
    sub.add_parser("parte-b", help="nut fora: métodos de numeração (GPU)")
    args = ap.parse_args()
    try:
        if args.parte == "parte-a":
            resultado = parte_a()
            print(json.dumps(resultado["modos"], ensure_ascii=False, indent=1))
            print(
                json.dumps(
                    resultado["transicoes_sozinho_para_corrige"], ensure_ascii=False
                )
            )
            return 0
        resultado = parte_b()
        print(json.dumps(resultado["totais"], ensure_ascii=False, indent=1))
        return 0
    except (ValueError, FileNotFoundError, RuntimeError) as erro:
        print(f"não rodou: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
