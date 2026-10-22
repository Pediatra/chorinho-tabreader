"""Gabarito dos dedos (M2): amostra, registro e a ferramenta que grava a cada resposta.

Fase M2 da trilha das mãos. Para cada nota de tablatura tocada (``tab.mvp``), o dono diz
qual dedo da mão esquerda pisa e qual dedo da mão direita toca. A unidade de pergunta é o
ATAQUE: a nota sorteada mais as outras notas do mesmo acorde (mesma tela, coluna e
``t_ini``). Este módulo tem:

1. funções puras (amostra estratificada, caixa ampliada, escolha da caixa de cada mão,
   ataque e acorde, registro do gabarito, migração do formato 1 para o 2, validação de
   resposta), testadas no gate;
2. o subcomando ``servir``: servidor ``http.server`` que mostra um ataque por vez e grava
   cada resposta em disco (escrita atômica), no mesmo padrão de ``tab.ouro_video``.

O material (quadros e recortes) é gerado por ``tab.maos_gabarito_preparar``, que usa a GPU.
Este módulo só usa stdlib, numpy e cv2, para caber no gate (a imagem do gate não tem
rtmlib).

Uso::

    python -m tab.maos_gabarito servir --pasta data/saida/maos/m2/dedos \\
        --ouro data/gold/maos/dedos_retrato_brasileiro.json --porta 8098
"""

from __future__ import annotations

import argparse
import copy
import datetime
import http.server
import json
import math
import os
import random
import re
import sys
import threading
from pathlib import Path

import cv2
import numpy as np

from tab.comum.caminhos import GABARITO_DEDOS, MAOS_DEDOS

#: Retângulo ``(x0, y0, x1, y1)`` no espaço do QUADRO (pixels inteiros).
Retangulo = tuple[int, int, int, int]

#: Semente da amostra (a mesma do resto da trilha).
SEMENTE_PADRAO = 20261012

#: Formato do gabarito: 1 = uma nota por item; 2 = um ataque por item (nota sorteada mais
#: as do acorde); 3 = formato 2 mais a pestana de cada ataque (``ataques``). Só o formato
#: 3 é aceito pelo servidor.
FORMATO_GABARITO = 3

#: Tamanho do rótulo ``cN`` desenhado ao lado de cada retângulo do quadro.
FONTE_ROTULO = 0.45

#: Notas com casa > 0 e notas de corda solta (casa 0) na amostra.
N_COM_CASA = 32
N_CORDA_SOLTA = 8

#: Folga, como fração do tamanho da caixa, para cada lado da mão (esquerda e direita).
FOLGA_MAO = 0.40

#: Altura dos recortes (px). A esquerda é maior, para ver os dedos no braço.
ALTURA_ESQUERDA_PX = 700
ALTURA_DIREITA_PX = 450

#: Largura do quadro mostrado na página (px).
LARGURA_QUADRO_PX = 960

#: Retângulo da nota na tablatura, em múltiplos do passo (largura e altura).
CAIXA_NOTA_LARGURA = 1.4
CAIXA_NOTA_ALTURA = 1.1

#: Desvio máximo, como fração do espaçamento, para as 6 linhas detectadas valerem.
TOLERANCIA_PASSO = 0.25

#: Instantes da mão direita, em relação a t_ini (s): antes, no ataque e depois.
DESLOCAMENTOS_DIREITA_S = (-0.15, 0.0, 0.15)

#: Lado da mão no rótulo do MediaPipe (``L`` e ``R``) e nos nomes deste módulo.
LADO_MEDIAPIPE = {"esquerda": "L", "direita": "R"}

#: Respostas válidas por campo; ``None`` significa "ainda não respondido".
RESPOSTAS = {
    "esquerda": ("0", "1", "2", "3", "4", "?"),
    "direita": ("p", "i", "m", "a", "c", "?"),
}

#: Tamanho máximo da observação livre.
TAMANHO_OBS_MAXIMO = 500

#: Respostas válidas da pestana de um ataque (``None`` = não respondido).
RESPOSTAS_PESTANA = ("sim", "nao", "?")

#: Dedos que podem fazer a pestana (a mão esquerda, como as notas).
DEDOS_PESTANA = ("1", "2", "3", "4")

#: Cordas da tablatura (1 = mais aguda, 6 = mais grave).
CORDA_MINIMA = 1
CORDA_MAXIMA = 6

#: Campos de pestana de um ataque (além de ``respondido_em``).
CAMPOS_PESTANA = ("pestana_dedo", "pestana_casa", "pestana_de", "pestana_ate")

#: Origens possíveis de uma caixa de mão.
ORIGENS = ("mediapipe", "wholebody", "fallback")

#: Páginas servidas: só estes tipos saem da pasta (nada de listar diretório).
_TIPOS = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".json": "application/json; charset=utf-8",
}


# ---------------------------------------------------------------------------------
# Funções puras: amostra, caixas e imagens
# ---------------------------------------------------------------------------------


def _sortear_faixas(
    notas: list[dict], indices: list[int], n: int, rng: random.Random
) -> list[int]:
    """Uma nota por faixa de contagem igual, na ordem de ``t_ini``.

    Args:
        notas: notas do mvp.
        indices: índices (em ``notas``) das notas candidatas deste grupo.
        n: quantas faixas (e quantas notas sorteadas).
        rng: gerador já semeado.

    Returns:
        Os índices sorteados, uma por faixa.

    Raises:
        ValueError: se há menos candidatas do que faixas.
    """
    if len(indices) < n:
        raise ValueError(f"{len(indices)} notas candidatas para {n} faixas")
    ordenados = sorted(indices, key=lambda i: (notas[i]["t_ini"], i))
    total = len(ordenados)
    escolhidos = []
    for k in range(n):
        faixa = ordenados[k * total // n : (k + 1) * total // n]
        escolhidos.append(rng.choice(faixa))
    return escolhidos


def amostrar_notas(
    notas: list[dict],
    semente: int = SEMENTE_PADRAO,
    n_com_casa: int = N_COM_CASA,
    n_corda_solta: int = N_CORDA_SOLTA,
) -> list[dict]:
    """Amostra estratificada de notas com ``t_ini``, com ``n_com_casa + n_corda_solta`` itens.

    As notas com casa > 0 e as de corda solta (casa 0) são sorteadas em grupos separados.
    Dentro de cada grupo, as notas são ordenadas por ``t_ini`` e divididas em faixas de
    contagem igual; sorteia-se uma por faixa com ``random.Random(semente)``. A lista final
    está em ordem de ``t_ini`` e cada item ganha o id estável ``n01``..``nNN``.

    Args:
        notas: notas do ``mvp.json`` (``t_ini``, ``corda``, ``casa``, ``tela``...).
        semente: semente do sorteio.
        n_com_casa: quantas notas com casa > 0.
        n_corda_solta: quantas notas com casa 0.

    Returns:
        Uma entrada por nota sorteada: ``id``, ``indice_mvp``, ``corda``, ``casa``,
        ``t_ini``, ``tela``, ``coluna``, ``x_quadro`` e ``x_centro_quadro``.

    Raises:
        ValueError: se algum grupo tem menos notas do que faixas pedidas.
    """
    com_tempo = [i for i, n in enumerate(notas) if n.get("t_ini") is not None]
    solta = [i for i in com_tempo if str(notas[i]["casa"]) == "0"]
    com_casa = [i for i in com_tempo if str(notas[i]["casa"]) != "0"]
    rng = random.Random(semente)
    sorteados = _sortear_faixas(notas, com_casa, n_com_casa, rng)
    sorteados += _sortear_faixas(notas, solta, n_corda_solta, rng)
    sorteados.sort(key=lambda i: (notas[i]["t_ini"], i))
    amostra = []
    for k, idx in enumerate(sorteados, start=1):
        n = notas[idx]
        amostra.append(
            {
                "id": f"n{k:02d}",
                "indice_mvp": idx,
                "corda": n["corda"],
                "casa": n["casa"],
                "t_ini": n["t_ini"],
                "tela": n.get("tela"),
                "coluna": n.get("coluna"),
                "x_quadro": n.get("x_quadro"),
                "x_centro_quadro": n.get("x_centro_quadro"),
            }
        )
    return amostra


def ampliar_caixa(
    caixa: list[float] | tuple[float, ...], fator: float, forma: tuple[int, ...]
) -> Retangulo:
    """Caixa ampliada em ``fator`` do seu tamanho para cada lado, limitada ao quadro.

    Args:
        caixa: ``(x0, y0, x1, y1)`` no quadro.
        fator: folga por lado, como fração da largura (x) e da altura (y) da caixa.
        forma: ``shape`` do quadro (``altura, largura, ...``).

    Returns:
        A caixa ampliada, em inteiros, dentro dos limites do quadro.

    Raises:
        ValueError: se a caixa fica fora do quadro (resultado vazio).
    """
    x0, y0, x1, y1 = (float(v) for v in caixa)
    margem_x = fator * (x1 - x0)
    margem_y = fator * (y1 - y0)
    altura, largura = int(forma[0]), int(forma[1])
    rect = (
        max(0, math.floor(x0 - margem_x)),
        max(0, math.floor(y0 - margem_y)),
        min(largura, math.ceil(x1 + margem_x)),
        min(altura, math.ceil(y1 + margem_y)),
    )
    if rect[2] <= rect[0] or rect[3] <= rect[1]:
        raise ValueError(f"caixa {caixa} fora do quadro {largura}x{altura}")
    return rect


def escolher_caixa(
    lado: str, maos_mp: list[dict], pessoas_wb: list[dict], forma: tuple[int, ...]
) -> dict:
    """Caixa de uma mão (``esquerda`` ou ``direita``), com a origem.

    Ordem: a mão do MediaPipe desse lado com maior score (fora da tablatura); se não há,
    a do Wholebody desse lado com maior média; se não há, a metade inferior inteira do
    quadro (``fallback``).

    Args:
        lado: ``esquerda`` ou ``direita``.
        maos_mp: mãos do MediaPipe do quadro (``lado`` L/R, ``caixa``, ``score``,
            ``na_tab``).
        pessoas_wb: pessoas do Wholebody (``esquerda`` e ``direita``, cada uma com
            ``caixa`` e ``media``).
        forma: ``shape`` do quadro.

    Returns:
        ``{"origem": ..., "caixa": [x0, y0, x1, y1], "score": float ou None}``, a caixa
        ainda SEM a folga (a folga é aplicada por ``caixa_final``).

    Raises:
        ValueError: se ``lado`` não é ``esquerda`` nem ``direita``.
    """
    if lado not in LADO_MEDIAPIPE:
        raise ValueError(f"lado desconhecido: {lado!r}")
    mp = [
        m
        for m in maos_mp
        if m.get("lado") == LADO_MEDIAPIPE[lado] and not m.get("na_tab")
    ]
    if mp:
        melhor = max(mp, key=lambda m: float(m["score"]))
        return {
            "origem": "mediapipe",
            "caixa": [float(v) for v in melhor["caixa"]],
            "score": float(melhor["score"]),
        }
    wb = [p[lado] for p in pessoas_wb if p.get(lado)]
    if wb:
        melhor = max(wb, key=lambda m: float(m["media"]))
        return {
            "origem": "wholebody",
            "caixa": [float(v) for v in melhor["caixa"]],
            "score": float(melhor["media"]),
        }
    altura, largura = int(forma[0]), int(forma[1])
    return {
        "origem": "fallback",
        "caixa": [0.0, float(altura // 2), float(largura), float(altura)],
        "score": None,
    }


def caixa_final(escolha: dict, forma: tuple[int, ...]) -> Retangulo:
    """Caixa usada no recorte: a escolhida, ampliada em ``FOLGA_MAO`` (exceto fallback).

    Args:
        escolha: saída de ``escolher_caixa``.
        forma: ``shape`` do quadro.

    Returns:
        ``(x0, y0, x1, y1)`` em inteiros, dentro do quadro.
    """
    if escolha["origem"] == "fallback":
        x0, y0, x1, y1 = escolha["caixa"]
        return int(x0), int(y0), int(x1), int(y1)
    return ampliar_caixa(escolha["caixa"], FOLGA_MAO, forma)


def recortar_caixa(quadro: np.ndarray, caixa: Retangulo) -> np.ndarray:
    """Recorte do quadro (cópia), com a caixa dentro dos limites.

    Args:
        quadro: imagem BGR.
        caixa: ``(x0, y0, x1, y1)``.

    Returns:
        Cópia do recorte.

    Raises:
        ValueError: se o recorte sai vazio.
    """
    x0, y0, x1, y1 = caixa
    recorte = quadro[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)].copy()
    if recorte.size == 0:
        raise ValueError(f"recorte vazio para a caixa {caixa}")
    return recorte


def redimensionar_altura(bgr: np.ndarray, altura: int) -> np.ndarray:
    """Redimensiona mantendo a proporção, para a altura pedida (interpolação cúbica).

    Args:
        bgr: imagem BGR.
        altura: altura de saída, em px.

    Returns:
        A imagem redimensionada.
    """
    fator = altura / bgr.shape[0]
    largura = max(1, round(bgr.shape[1] * fator))
    return cv2.resize(bgr, (largura, altura), interpolation=cv2.INTER_CUBIC)


# ---------------------------------------------------------------------------------
# Linhas das cordas, acorde e caixa da nota
# ---------------------------------------------------------------------------------


def acorde_da_coluna(notas: list[dict], indice: int) -> list[dict]:
    """Notas que soam JUNTO com a nota ``indice``: mesma tela, coluna e ``t_ini``.

    A coluna sozinha não basta: no ``mvp.json`` a mesma ``coluna`` se repete em outros
    instantes (outra passagem), e isso juntaria notas que não tocam juntas.

    Args:
        notas: notas do ``mvp.json``.
        indice: índice da nota em ``notas``.

    Returns:
        Uma entrada por nota do acorde (``indice_mvp``, ``corda``, ``casa``), em ordem
        crescente de corda, incluindo a própria nota.
    """
    alvo = notas[indice]
    acorde = [
        {"indice_mvp": i, "corda": n["corda"], "casa": n["casa"]}
        for i, n in enumerate(notas)
        if n.get("t_ini") is not None
        and n.get("tela") == alvo.get("tela")
        and n.get("coluna") == alvo.get("coluna")
        and n["t_ini"] == alvo["t_ini"]
    ]
    return sorted(acorde, key=lambda a: (a["corda"], a["indice_mvp"]))


def texto_acorde(acorde: list[dict]) -> str:
    """Texto do acorde para o cabeçalho do quadro, sem marcar nenhuma nota.

    Args:
        acorde: notas do ataque (``corda`` e ``casa``), em ordem de corda.

    Returns:
        Texto no formato ``acorde: c1 casa 4 | c2 casa 5``.
    """
    return "acorde: " + " | ".join(f"c{a['corda']} casa {a['casa']}" for a in acorde)


def ataque_de(id_item: str) -> str:
    """Id do ataque de uma nota da amostra: ``n02`` vira ``a02``.

    Args:
        id_item: id da nota sorteada (``nNN``).

    Returns:
        O id do ataque (``aNN``), com o mesmo número.
    """
    return "a" + id_item[1:]


def notas_do_ataque(item: dict, notas: list[dict]) -> list[dict]:
    """Notas do ataque de ``item``: a sorteada e as outras do mesmo acorde.

    A sorteada mantém o id da amostra (``n02``); as acrescentadas ganham ``n02_c<corda>``.
    A ordem é a de corda (1 = aguda, 6 = grave).

    Args:
        item: nota da amostra (``id`` e ``indice_mvp``).
        notas: notas do ``mvp.json``.

    Returns:
        Uma entrada por nota do ataque, com ``id``, ``ataque``, ``sorteada``,
        ``indice_mvp``, ``corda``, ``casa``, ``t_ini``, ``tela`` e ``x_centro_quadro``.

    Raises:
        ValueError: se duas notas do acorde caem na mesma corda.
    """
    ataque = ataque_de(item["id"])
    entradas = []
    for a in acorde_da_coluna(notas, item["indice_mvp"]):
        nota = notas[a["indice_mvp"]]
        sorteada = a["indice_mvp"] == item["indice_mvp"]
        id_nota = item["id"] if sorteada else f"{item['id']}_c{a['corda']}"
        entradas.append(
            {
                "id": id_nota,
                "ataque": ataque,
                "sorteada": sorteada,
                "indice_mvp": a["indice_mvp"],
                "corda": a["corda"],
                "casa": a["casa"],
                "t_ini": nota["t_ini"],
                "tela": nota.get("tela"),
                "x_centro_quadro": nota.get("x_centro_quadro"),
            }
        )
    cordas = [e["corda"] for e in entradas]
    if len(set(cordas)) != len(cordas):
        raise ValueError(f"{item['id']}: duas notas do acorde na mesma corda: {cordas}")
    return entradas


def linhas_confiaveis(linhas_y: list[float] | None, passo: float) -> bool:
    """As linhas detectadas são as 6 cordas da tablatura?

    Args:
        linhas_y: y das linhas detectadas no quadro, ou ``None``.
        passo: passo do painel no ``mvp.json``, em px.

    Returns:
        ``True`` se há exatamente 6 linhas, com espaçamento regular (desvio até
        ``TOLERANCIA_PASSO``) e média igual ao ``passo`` (mesma tolerância).
    """
    if not linhas_y or len(linhas_y) != 6 or passo <= 0:
        return False
    ys = sorted(float(v) for v in linhas_y)
    difs = [ys[k + 1] - ys[k] for k in range(5)]
    media = sum(difs) / len(difs)
    if media <= 0:
        return False
    if any(abs(d - media) > TOLERANCIA_PASSO * media for d in difs):
        return False
    return abs(media - passo) <= TOLERANCIA_PASSO * passo


def y_da_corda(
    corda: int, linhas_y: list[float] | None, painel: list[float], passo: float
) -> tuple[float, str]:
    """Altura, no quadro, da linha da ``corda``, e de onde ela veio.

    Usa as linhas detectadas (origem ``segmentacao``) se ``linhas_confiaveis``; senão,
    a reserva ``y0 do painel + (corda - 1) * passo`` (origem ``reserva``). A reserva
    ignora a margem do painel, por isso é contada à parte.

    Args:
        corda: 1 (linha de cima, a mais aguda) a 6 (a de baixo).
        linhas_y: y das linhas detectadas no quadro, ou ``None``.
        painel: ``[x0, y0, x1, y1]`` do painel no quadro 1920x1080.
        passo: passo do painel, em px.

    Returns:
        ``(y, origem)``, com origem ``segmentacao`` ou ``reserva``.

    Raises:
        ValueError: se ``corda`` não está entre 1 e 6.
    """
    if not 1 <= corda <= 6:
        raise ValueError(f"corda fora de 1..6: {corda}")
    if linhas_confiaveis(linhas_y, passo):
        ys = sorted(float(v) for v in linhas_y or [])
        return ys[corda - 1], "segmentacao"
    return float(painel[1]) + (corda - 1) * passo, "reserva"


def caixa_da_nota(x_centro: float, y_corda: float, passo: float) -> Retangulo:
    """Retângulo pequeno em volta do algarismo da nota, no quadro 1920x1080.

    Args:
        x_centro: ``x_centro_quadro`` da nota.
        y_corda: altura da linha da corda (``y_da_corda``).
        passo: passo do painel, em px.

    Returns:
        ``(x0, y0, x1, y1)`` em inteiros, centrado na nota, com
        ``CAIXA_NOTA_LARGURA * passo`` de largura e ``CAIXA_NOTA_ALTURA * passo`` de altura.
    """
    meia_x = CAIXA_NOTA_LARGURA * passo / 2
    meia_y = CAIXA_NOTA_ALTURA * passo / 2
    return (
        round(x_centro - meia_x),
        round(y_corda - meia_y),
        round(x_centro + meia_x),
        round(y_corda + meia_y),
    )


# ---------------------------------------------------------------------------------
# Registro do gabarito
# ---------------------------------------------------------------------------------


def _nota_em_branco(entrada: dict) -> dict:
    """Registro de uma nota do gabarito (formato 2), sem resposta.

    Args:
        entrada: saída de ``notas_do_ataque``.

    Returns:
        O registro com ``esquerda``, ``direita``, ``obs`` e ``respondido_em`` vazios.
    """
    return {
        "id": entrada["id"],
        "ataque": entrada["ataque"],
        "sorteada": entrada["sorteada"],
        "indice_mvp": entrada["indice_mvp"],
        "corda": entrada["corda"],
        "casa": entrada["casa"],
        "t_ini": entrada["t_ini"],
        "esquerda": None,
        "direita": None,
        "obs": "",
        "respondido_em": None,
    }


def gabarito_novo(
    video: str, amostra: list[dict], semente: int, notas: list[dict]
) -> dict:
    """Registro do gabarito (formato 3) com todas as respostas em branco.

    Args:
        video: chave do vídeo no acervo (ex.: ``sky guitar/retrato....mp4``).
        amostra: saída de ``amostrar_notas``.
        semente: semente usada na amostra.
        notas: notas do ``mvp.json``, para montar o acorde de cada ataque.

    Returns:
        O dicionário do gabarito, com uma entrada por nota de cada ataque e uma pestana
        em branco por ataque.
    """
    gabarito = {
        "formato": FORMATO_GABARITO,
        "ataques": {},
        "video": video,
        "como_foi_rotulado": "dono, ferramenta tab.maos_gabarito, um ataque por vez",
        "semente": semente,
        "ferramenta": "tab.maos_gabarito",
        "notas": [
            _nota_em_branco(e) for item in amostra for e in notas_do_ataque(item, notas)
        ],
    }
    return migrar_pestanas(gabarito)


def _pestana_em_branco() -> dict:
    """Registro de pestana de um ataque, sem resposta.

    Returns:
        ``pestana`` e os campos de pestana com ``None``, e ``respondido_em`` vazio.
    """
    return {
        "pestana": None,
        "pestana_dedo": None,
        "pestana_casa": None,
        "pestana_de": None,
        "pestana_ate": None,
        "respondido_em": None,
    }


def migrar_pestanas(gabarito: dict) -> dict:
    """Converte o gabarito do formato 2 para o 3: acrescenta a pestana em branco de cada ataque.

    Pura e idempotente: não usa o ``mvp.json`` e não toca em nenhuma nota. Cada ataque
    presente nas notas ganha uma entrada em ``ataques``; uma entrada que já existe (com ou
    sem resposta) é mantida como está. Um gabarito já no formato 3 volta igual.

    Args:
        gabarito: gabarito nos formatos 2 ou 3 (não é alterado).

    Returns:
        Um gabarito novo, no formato 3, com as notas idênticas às de entrada.

    Raises:
        ValueError: se o formato não é 2 nem 3.
    """
    formato = gabarito.get("formato")
    if formato not in (2, FORMATO_GABARITO):
        raise ValueError(f"migrar_pestanas espera o formato 2 ou 3, veio {formato!r}")
    existentes = gabarito.get("ataques", {})
    ids = list(dict.fromkeys(n["ataque"] for n in gabarito["notas"]))
    ids += [a for a in existentes if a not in ids]
    ataques = {a: copy.deepcopy(existentes.get(a, _pestana_em_branco())) for a in ids}
    resto = {k: v for k, v in gabarito.items() if k not in ("formato", "ataques")}
    return {
        "formato": FORMATO_GABARITO,
        "ataques": ataques,
        **copy.deepcopy(resto),
    }


def migrar_arquivo(ouro: Path) -> int:
    """Migra o gabarito em disco do formato 2 para o 3 (grava de forma atômica).

    Args:
        ouro: arquivo do gabarito.

    Returns:
        Quantos ataques o gabarito tem no formato 3.

    Raises:
        ValueError: se o formato não é 2 nem 3.
    """
    antigo = json.loads(ouro.read_text(encoding="utf-8"))
    novo = migrar_pestanas(antigo)
    if novo != antigo:
        gravar_atomico(ouro, novo)
    return len(novo["ataques"])


def migrar_gabarito(antigo: dict, notas: list[dict]) -> dict:
    """Converte o gabarito do formato 1 (uma nota por item) para o 3 (um ataque por item, com pestana).

    Cada nota antiga ``nNN`` vira o ataque ``aNN`` e MANTÉM o id e as respostas (``esquerda``,
    ``direita``, ``obs``, ``respondido_em``) exatamente como estavam. As outras notas do
    acorde entram como novas, em branco, com id ``nNN_c<corda>``. Um gabarito já nos formatos
    2 ou 3 é só completado com ``migrar_pestanas`` (rodar de novo não duplica nada). O
    gabarito de entrada não é alterado.

    Args:
        antigo: gabarito como está em disco (formato 1, ou 2 e 3).
        notas: notas do ``mvp.json``.

    Returns:
        Um gabarito novo, no formato 3.

    Raises:
        ValueError: se corda, casa ou ``t_ini`` de uma nota antiga não batem com o mvp.
    """
    if antigo.get("formato", 1) != 1:
        return migrar_pestanas(antigo)
    novas = []
    for velha in antigo["notas"]:
        mvp = notas[velha["indice_mvp"]]
        if (
            str(mvp["corda"]) != str(velha["corda"])
            or str(mvp["casa"]) != str(velha["casa"])
            or mvp["t_ini"] != velha["t_ini"]
        ):
            raise ValueError(f"{velha['id']}: corda/casa/t_ini não batem com o mvp")
        item = {"id": velha["id"], "indice_mvp": velha["indice_mvp"]}
        for entrada in notas_do_ataque(item, notas):
            nova = _nota_em_branco(entrada)
            if entrada["sorteada"]:
                for campo in ("esquerda", "direita", "obs", "respondido_em"):
                    nova[campo] = velha.get(campo, nova[campo])
            novas.append(nova)
    resto = {k: v for k, v in antigo.items() if k not in ("formato", "notas")}
    return migrar_pestanas({"formato": 2, **resto, "notas": novas})


def _tem_resposta(nota: dict) -> bool:
    """Há alguma resposta (esquerda, direita ou observação) nesta nota?

    Args:
        nota: nota do gabarito.

    Returns:
        ``True`` se a nota já foi respondida em algum campo.
    """
    return (
        nota.get("esquerda") is not None
        or nota.get("direita") is not None
        or bool(nota.get("obs"))
    )


def mesclar_gabarito(novo: dict, existente: dict | None) -> dict:
    """Copia para o gabarito novo as respostas do existente, sem perder nenhuma.

    Uma resposta cuja nota não existe mais na amostra nova (ou com outro ``indice_mvp``)
    faz a função recusar: o dono não perde resposta em silêncio.

    Args:
        novo: gabarito recém-montado (``gabarito_novo``).
        existente: gabarito já gravado em disco, ou ``None``.

    Returns:
        O gabarito novo, com as respostas do existente copiadas.

    Raises:
        ValueError: se o vídeo é outro, ou se há resposta órfã.
    """
    if existente is None:
        return novo
    if existente.get("video") != novo["video"]:
        raise ValueError(
            f"o gabarito é de {existente.get('video')!r}, não de {novo['video']!r}"
        )
    por_id = {n["id"]: n for n in novo["notas"]}
    orfas = []
    for antiga in existente.get("notas", []):
        if not _tem_resposta(antiga):
            continue
        nova = por_id.get(antiga["id"])
        if nova is None or nova["indice_mvp"] != antiga["indice_mvp"]:
            orfas.append(antiga["id"])
            continue
        for campo in ("esquerda", "direita", "obs", "respondido_em"):
            nova[campo] = antiga.get(campo, nova[campo])
    for id_ataque, antiga_pestana in existente.get("ataques", {}).items():
        if not pestana_respondida(antiga_pestana):
            continue
        if id_ataque not in novo["ataques"]:
            orfas.append(id_ataque)
            continue
        novo["ataques"][id_ataque] = copy.deepcopy(antiga_pestana)
    if orfas:
        raise ValueError(f"respostas sem nota na amostra nova: {orfas}")
    return novo


def _inteiro(valor: object) -> bool:
    """É um inteiro de verdade (``bool`` não conta)?

    Args:
        valor: o valor recebido.

    Returns:
        ``True`` se ``valor`` é ``int`` e não é ``bool``.
    """
    return isinstance(valor, int) and not isinstance(valor, bool)


def pestana_respondida(ataque: dict) -> bool:
    """A pestana do ataque já tem resposta (``sim``, ``nao`` ou ``?``)?

    Args:
        ataque: registro de pestana do ataque (``ataques[aNN]``).

    Returns:
        ``True`` se ``pestana`` não é ``None``.
    """
    return ataque.get("pestana") is not None


def validar_pestana(campos: dict) -> dict:
    """Confere a pestana de um ataque e devolve o registro a gravar (sem ``respondido_em``).

    ``nao`` e ``?`` limpam os campos de pestana. ``sim`` exige a casa (inteiro >= 1), as
    cordas ``pestana_de`` e ``pestana_ate`` (inteiros de 1 a 6, com ``de`` < ``ate``, ou
    seja, pelo menos duas cordas) e o dedo (``1`` a ``4``; sem o campo, ``1``).

    Args:
        campos: ``pestana`` e, se ``sim``, ``pestana_dedo``, ``pestana_casa``,
            ``pestana_de`` e ``pestana_ate``.

    Returns:
        O registro de pestana, com ``respondido_em`` ``None``.

    Raises:
        ValueError: se um campo não existe, o valor é inválido ou as cordas se contradizem.
    """
    desconhecidos = set(campos) - {"pestana", *CAMPOS_PESTANA}
    if desconhecidos:
        raise ValueError(f"campos de pestana desconhecidos: {sorted(desconhecidos)}")
    pestana = campos.get("pestana")
    if pestana not in RESPOSTAS_PESTANA:
        raise ValueError(f"pestana: valor {pestana!r} não existe")
    if pestana != "sim":
        return {**_pestana_em_branco(), "pestana": pestana}
    dedo = campos.get("pestana_dedo") or "1"
    if dedo not in DEDOS_PESTANA:
        raise ValueError(f"pestana_dedo: valor {dedo!r} não existe")
    casa = campos.get("pestana_casa")
    if not _inteiro(casa) or casa < 1:
        raise ValueError(f"pestana_casa: inteiro >= 1, veio {casa!r}")
    de, ate = campos.get("pestana_de"), campos.get("pestana_ate")
    for nome, corda in (("pestana_de", de), ("pestana_ate", ate)):
        if not _inteiro(corda) or not CORDA_MINIMA <= corda <= CORDA_MAXIMA:
            raise ValueError(
                f"{nome}: corda de {CORDA_MINIMA} a {CORDA_MAXIMA}, veio {corda!r}"
            )
    if de >= ate:
        raise ValueError(f"pestana_de ({de}) deve ser menor que pestana_ate ({ate})")
    return {
        **_pestana_em_branco(),
        "pestana": "sim",
        "pestana_dedo": dedo,
        "pestana_casa": casa,
        "pestana_de": de,
        "pestana_ate": ate,
    }


def atualizar_pestana(gabarito: dict, id_ataque: str, campos: dict, agora: str) -> dict:
    """Aplica a pestana de um ataque (in place) e devolve o registro gravado.

    Args:
        gabarito: o registro em memória (formato 3).
        id_ataque: id do ataque (``aNN``).
        campos: o que ``validar_pestana`` aceita.
        agora: carimbo ISO-8601 da resposta.

    Returns:
        O registro de pestana do ataque, já com ``respondido_em``.

    Raises:
        ValueError: se o ataque não existe ou algum campo é inválido.
    """
    if id_ataque not in gabarito["ataques"]:
        raise ValueError(f"ataque {id_ataque!r} não existe")
    registro = validar_pestana(campos)
    registro["respondido_em"] = agora
    gabarito["ataques"][id_ataque] = registro
    return registro


def validar_resposta(campo: str, valor: object) -> None:
    """Confere um valor de resposta; ``None`` (limpar) é aceito em esquerda e direita.

    Args:
        campo: ``esquerda``, ``direita`` ou ``obs``.
        valor: o valor enviado pela página.

    Raises:
        ValueError: se o campo ou o valor não existem.
    """
    if campo == "obs":
        if not isinstance(valor, str) or len(valor) > TAMANHO_OBS_MAXIMO:
            raise ValueError(f"obs: texto de até {TAMANHO_OBS_MAXIMO} caracteres")
        return
    if campo not in RESPOSTAS:
        raise ValueError(f"campo desconhecido: {campo!r}")
    if valor is None:
        return
    if not isinstance(valor, str) or valor not in RESPOSTAS[campo]:
        raise ValueError(f"{campo}: valor {valor!r} não existe")


def atualizar_resposta(gabarito: dict, id_nota: str, campos: dict, agora: str) -> dict:
    """Aplica as respostas de uma nota (in place) e devolve a nota.

    Args:
        gabarito: o registro em memória.
        id_nota: id da nota (``n01``...).
        campos: subconjunto de ``esquerda``, ``direita`` e ``obs``.
        agora: carimbo ISO-8601 da resposta.

    Returns:
        A nota atualizada.

    Raises:
        ValueError: se a nota não existe, o campo é desconhecido ou o valor é inválido.
    """
    nota = next((n for n in gabarito["notas"] if n["id"] == id_nota), None)
    if nota is None:
        raise ValueError(f"nota {id_nota!r} não existe")
    desconhecidos = set(campos) - {"esquerda", "direita", "obs"}
    if desconhecidos:
        raise ValueError(f"campos desconhecidos: {sorted(desconhecidos)}")
    for campo, valor in campos.items():
        validar_resposta(campo, valor)
    for campo, valor in campos.items():
        nota[campo] = valor
    nota["respondido_em"] = agora
    return nota


def completa_nota(nota: dict) -> bool:
    """A nota tem as DUAS respostas (esquerda e direita)?

    Args:
        nota: nota do gabarito.

    Returns:
        ``True`` se ``esquerda`` e ``direita`` estão respondidas.
    """
    return nota["esquerda"] is not None and nota["direita"] is not None


def completas(gabarito: dict) -> int:
    """Quantas notas têm as DUAS respostas (esquerda e direita).

    Args:
        gabarito: o registro.

    Returns:
        Contagem de notas completas.
    """
    return sum(1 for n in gabarito["notas"] if completa_nota(n))


def ataque_completo(gabarito: dict, id_ataque: str) -> bool:
    """O ataque está completo: todas as notas com as duas respostas E a pestana respondida.

    Args:
        gabarito: o registro no formato 3.
        id_ataque: id do ataque (``aNN``).

    Returns:
        ``True`` se o ataque tem notas, todas completas, e a pestana não é ``None``.
    """
    notas = [n for n in gabarito["notas"] if n["ataque"] == id_ataque]
    return (
        bool(notas)
        and all(completa_nota(n) for n in notas)
        and pestana_respondida(gabarito["ataques"].get(id_ataque, {}))
    )


def progresso_ataques(gabarito: dict) -> tuple[int, int]:
    """Quantos ataques estão completos (ver ``ataque_completo``).

    Args:
        gabarito: o registro no formato 3.

    Returns:
        ``(ataques completos, total de ataques)``.
    """
    ids = list(dict.fromkeys(n["ataque"] for n in gabarito["notas"]))
    feitos = sum(1 for a in ids if ataque_completo(gabarito, a))
    return feitos, len(ids)


def gravar_atomico(destino: Path, conteudo: dict) -> None:
    """Grava JSON de forma atômica: temporário no mesmo diretório + ``os.replace``.

    Args:
        destino: arquivo final.
        conteudo: dicionário serializável.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, destino)


# ---------------------------------------------------------------------------------
# Servidor e página
# ---------------------------------------------------------------------------------


def criar_servidor(
    pasta: Path, ouro: Path, porta: int = 8098, host: str = "127.0.0.1"
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor (não o inicia). Por padrão escuta SOMENTE em 127.0.0.1.

    Args:
        pasta: pasta do ``preparar`` (``indice.json``, ``<id>/*.jpg``).
        ouro: arquivo do gabarito; é carregado agora e gravado a cada resposta.
        porta: porta TCP (0 = uma livre).
        host: endereço de escuta (``0.0.0.0`` só dentro de container).

    Returns:
        O servidor; ``servidor.server_address[1]`` é a porta real.
    """
    pasta = pasta.resolve()
    estado = json.loads(ouro.read_text(encoding="utf-8"))
    trava = threading.Lock()

    class Manipulador(http.server.BaseHTTPRequestHandler):
        """Serve a página e as imagens, e grava cada resposta em ``POST /responder``."""

        server_version = "maos_gabarito"

        def log_message(self, formato: str, *args: object) -> None:
            """Silencia o log por requisição (cada clique faria uma linha)."""

        def _responder(self, codigo: int, tipo: str, corpo: bytes) -> None:
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, codigo: int, dados: dict) -> None:
            corpo = json.dumps(dados, ensure_ascii=False).encode()
            self._responder(codigo, _TIPOS[".json"], corpo)

        def _host_ok(self) -> bool:
            """Recusa Host/Origin que não sejam a máquina local (rebinding, CSRF)."""
            local = {"127.0.0.1", "localhost"}
            host_cabecalho = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            origem = self.headers.get("Origin")
            if host_cabecalho not in local:
                return False
            if origem is None:
                return True
            return (
                re.fullmatch(r"http://(127\.0\.0\.1|localhost)(:\d+)?", origem)
                is not None
            )

        def do_GET(self) -> None:
            """Página, gabarito atual e arquivos da pasta (imagens e ``indice.json``)."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            caminho = self.path.split("?", 1)[0]
            if caminho in {"/", "/index.html"}:
                self._responder(200, "text/html; charset=utf-8", PAGINA.encode())
                return
            if caminho == "/gabarito.json":
                with trava:
                    corpo = json.dumps(estado, ensure_ascii=False).encode()
                self._responder(200, _TIPOS[".json"], corpo)
                return
            alvo = (pasta / caminho.lstrip("/")).resolve()
            if alvo.suffix in _TIPOS and alvo.is_relative_to(pasta) and alvo.is_file():
                self._responder(200, _TIPOS[alvo.suffix], alvo.read_bytes())
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def do_POST(self) -> None:
            """``/responder`` (uma nota) e ``/pestana`` (um ataque): grava o gabarito."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            if self.path not in {"/responder", "/pestana"}:
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= 16_000:
                    raise ValueError("corpo ausente ou grande demais")
                dados = json.loads(self.rfile.read(tamanho))
                if not isinstance(dados, dict):
                    raise ValueError("o corpo deve ser um objeto JSON")
                agora = datetime.datetime.now().isoformat(timespec="seconds")
                with trava:
                    anterior = copy.deepcopy(estado)
                    try:
                        if self.path == "/pestana":
                            id_ataque = dados.pop("ataque")
                            resposta = {
                                "ataque": id_ataque,
                                "pestana": atualizar_pestana(
                                    estado, id_ataque, dados, agora
                                ),
                            }
                        else:
                            id_nota = dados.pop("id")
                            resposta = {
                                "nota": atualizar_resposta(
                                    estado, id_nota, dados, agora
                                )
                            }
                        gravar_atomico(ouro, estado)
                    except OSError:
                        estado.clear()
                        estado.update(anterior)
                        raise
                    feitas = completas(estado)
                    total = len(estado["notas"])
                    ataques_feitos, ataques_total = progresso_ataques(estado)
            except (ValueError, KeyError, TypeError) as erro:
                self._json(400, {"ok": False, "erro": f"{type(erro).__name__}: {erro}"})
                return
            except OSError as erro:
                self._json(500, {"ok": False, "erro": f"não gravou em disco: {erro}"})
                return
            self._json(
                200,
                {
                    "ok": True,
                    **resposta,
                    "completas": feitas,
                    "total": total,
                    "ataques_completos": ataques_feitos,
                    "total_ataques": ataques_total,
                    "salvo_em": agora,
                },
            )

    return http.server.ThreadingHTTPServer((host, porta), Manipulador)


PAGINA = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dedos do gabarito</title>
<style>
:root{--fundo:#fff;--texto:#1b1b1b;--suave:#666;--borda:#c9c9c9;--acento:#0b6bcb;--ok:#1a7f37;--ruim:#c62828;--painel:#f4f4f4;--aviso:#9a5b00}
@media (prefers-color-scheme:dark){:root{--fundo:#161616;--texto:#e8e8e8;--suave:#999;--borda:#444;--acento:#5aa9ff;--ok:#4cc26a;--ruim:#ff6b6b;--painel:#222;--aviso:#f0b050}}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;padding:0 16px 32px;background:var(--fundo);color:var(--texto);font:15px/1.4 system-ui,sans-serif}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid var(--borda);position:sticky;top:0;background:var(--fundo);z-index:5}
button,input,select{font:inherit;color:inherit;background:var(--painel);border:1px solid var(--borda);border-radius:6px;padding:6px 10px}
button{cursor:pointer}
button.on{background:var(--acento);color:#fff;border-color:var(--acento)}
button.ok{border-left:5px solid var(--ok)}
progress{width:180px;height:14px}
#status{margin-left:auto;font-weight:600}#status.ruim{color:var(--ruim)}#status.ok{color:var(--ok)}
.suave{color:var(--suave)}
.linha{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}
#lista{display:flex;gap:4px;flex-wrap:wrap;margin:8px 0}
#lista button{padding:2px 6px;font-size:13px}
#lista button.ok{border-left-width:3px}
.aviso{color:var(--aviso);font-weight:600;margin:4px 0}
#titulo{font-weight:600;margin:4px 0}
h3{font-size:15px;margin:14px 0 6px}
img{max-width:100%;height:auto;display:block;border:1px solid var(--borda)}
.quadro{max-width:960px}
.par{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
.esq{flex:1 1 300px;min-width:0}
.resp{flex:1 1 380px;min-width:0}
.tres{display:flex;gap:8px;flex-wrap:wrap}
.tres figure{margin:0;flex:1 1 180px;min-width:0}
.tres figcaption{font-size:13px;color:var(--suave);margin-top:2px}
.nota{display:flex;gap:6px 10px;flex-wrap:wrap;align-items:center;border:1px solid var(--borda);border-radius:6px;padding:6px 8px;margin:6px 0;cursor:pointer}
.nota.ativa{border:2px solid var(--acento);background:var(--painel)}
.nota .rotulo{font-weight:600;min-width:130px}
.nota.ok .rotulo::after{content:" ✓";color:var(--ok)}
.grupo{display:flex;gap:4px;align-items:center;flex-wrap:wrap}
.grupo button{padding:3px 7px;font-size:14px}
.legenda{font-size:13px;color:var(--suave);margin:4px 0}
.bloco-pestana{border:1px dashed var(--borda);border-radius:6px;padding:6px 8px;margin:6px 0;cursor:pointer}
.bloco-pestana.ativa{border:2px solid var(--acento);background:var(--painel)}
.bloco-pestana.ok{border-left:5px solid var(--ok)}
.bloco-pestana b{font-weight:600}
.linha-pest{display:flex;gap:6px 10px;flex-wrap:wrap;align-items:center;margin:4px 0}
.linha-pest input[type=number]{width:72px}
input[type=text]{width:100%;max-width:420px}
label{display:block;margin-top:10px}
</style></head><body>
<header>
  <b>Dedos do gabarito</b><span id="video" class="suave"></span>
  <progress id="barra" max="1" value="0"></progress>
  <span id="progresso" class="suave"></span>
  <span id="status">carregando…</span>
</header>
<div class="linha">
  <button id="ant">← ataque anterior</button>
  <span id="posicao"></span>
  <button id="prox">próximo ataque →</button>
  <span class="suave">← → mudam de ataque · ↑ ↓ mudam de linha (e chegam à pestana) · teclas de nota respondem a linha ativa · b alterna pestana não/sim · n = pestana não</span>
</div>
<div id="lista"></div>
<div id="titulo"></div>
<div id="info" class="suave"></div>
<div id="avisos"></div>

<h3>Quadro (um retângulo vermelho por nota do acorde, com a corda ao lado)</h3>
<img id="img-quadro" class="quadro" alt="quadro do vídeo">

<div class="par">
  <div class="esq">
    <h3>Mão esquerda (no braço)</h3>
    <img id="img-esq" alt="mão esquerda">
  </div>
  <div class="resp">
    <h3>Pestana e notas do ataque (a linha destacada é a ativa)</h3>
    <div id="pestana" class="bloco-pestana">
      <div class="linha-pest">
        <b>Pestana</b>
        <span id="pest-resp" class="grupo"></span>
        <span id="pest-resumo" class="suave"></span>
      </div>
      <div id="pest-campos" class="linha-pest" hidden>
        <span class="grupo"><span class="suave">dedo</span><span id="pest-dedo" class="grupo"></span></span>
        <span class="grupo"><span class="suave">casa</span><input id="pest-casa" type="number" min="1" step="1" aria-label="casa da pestana"></span>
        <span class="grupo"><span class="suave">da corda</span><select id="pest-de" aria-label="pestana: da corda"></select></span>
        <span class="grupo"><span class="suave">até a corda</span><select id="pest-ate" aria-label="pestana: até a corda"></select></span>
      </div>
      <div class="legenda">não = sem pestana · sim = pestana (dedo, casa e cordas) · ? = não dá para ver</div>
    </div>
    <div id="linhas"></div>
    <div class="legenda">esquerda: 1 indicador · 2 médio · 3 anelar · 4 mínimo · 0 corda solta · x ou ? não dá para ver</div>
    <div class="legenda">direita: p polegar · i indicador · m médio · a anelar · c mínimo (raro) · z ou ? não dá para ver</div>
    <label>Observação da nota ativa (opcional)
      <input id="obs" type="text" maxlength="500">
    </label>
  </div>
</div>

<h3>Mão direita: t − 0,15 s · t · t + 0,15 s (mesma caixa)</h3>
<div class="tres">
  <figure><img id="dir-m" alt="mão direita, antes"><figcaption>t − 0,15 s</figcaption></figure>
  <figure><img id="dir-0" alt="mão direita, no instante"><figcaption>t</figcaption></figure>
  <figure><img id="dir-p" alt="mão direita, depois"><figcaption>t + 0,15 s</figcaption></figure>
</div>

<script>
"use strict";
const ESQUERDA = [["1","indicador"],["2","médio"],["3","anelar"],["4","mínimo"],["0","corda solta / nenhum"],["?","não dá para ver"]];
const DIREITA = [["p","polegar"],["i","indicador"],["m","médio"],["a","anelar"],["c","mínimo (raro)"],["?","não dá para ver"]];
const TECLAS_ESQ = {"1":"1","2":"2","3":"3","4":"4","0":"0","x":"?"};
const TECLAS_DIR = {"p":"p","i":"i","m":"m","a":"a","c":"c","z":"?"};
const PESTANA_OPCOES = [["nao","não"],["sim","sim"],["?","?"]];
const SEM_PESTANA = {pestana_dedo: null, pestana_casa: null, pestana_de: null, pestana_ate: null};
let INDICE = null, G = null;
let ATAQUES = [];   // [{id: "a02", ks: [indices em G.notas, por corda]}]
let A = 0, L = 0;   // ataque ativo e linha ativa dentro dele
let PEST_ATIVA = false; // o bloco da pestana é a linha ativa (teclas de nota não respondem)

const $ = id => document.getElementById(id);
function completa(n) { return n.esquerda != null && n.direita != null; }
function setStatus(t, c) { const s = $("status"); s.textContent = t; s.className = c || ""; }
function pestanaDe(a) { return G.ataques[a.id] || {pestana: null}; }
function pestanaOk(a) { return pestanaDe(a).pestana != null; }
function ataqueCompleto(a) { return a.ks.every(k => completa(G.notas[k])) && pestanaOk(a); }

function montarAtaques() {
  ATAQUES = [];
  const pos = new Map();
  G.notas.forEach((n, k) => {
    if (!pos.has(n.ataque)) { pos.set(n.ataque, ATAQUES.length); ATAQUES.push({id: n.ataque, ks: []}); }
    ATAQUES[pos.get(n.ataque)].ks.push(k);
  });
  ATAQUES.forEach(a => a.ks.sort((x, y) => G.notas[x].corda - G.notas[y].corda));
}

// Próxima linha sem as duas respostas, a partir de 'de' (inclusive) e dando a volta.
function primeiraIncompleta(a, de) {
  const m = a.ks.length;
  for (let j = 0; j < m; j++) {
    const l = (de + j) % m;
    if (!completa(G.notas[a.ks[l]])) return l;
  }
  return -1;
}

// Onde o foco cai ao abrir um ataque: a primeira nota incompleta; se todas as notas
// estão prontas e falta a pestana, o foco vai para o bloco da pestana.
function posInicial(a) {
  const at = ATAQUES[a], l = primeiraIncompleta(at, 0);
  if (l >= 0) return {L: l, P: false};
  return {L: 0, P: !pestanaOk(at)};
}

function progresso() {
  const notasFeitas = G.notas.filter(completa).length;
  const ataquesFeitos = ATAQUES.filter(ataqueCompleto).length;
  $("progresso").textContent = ataquesFeitos + "/" + ATAQUES.length + " ataques completos (" + notasFeitas + "/" + G.notas.length + " notas)";
  $("barra").max = ATAQUES.length;
  $("barra").value = ataquesFeitos;
}

function listaAtaques() {
  const l = $("lista"); l.replaceChildren();
  ATAQUES.forEach((a, j) => {
    const b = document.createElement("button");
    const feito = ataqueCompleto(a);
    const parcial = pestanaOk(a) || a.ks.some(k => G.notas[k].esquerda != null || G.notas[k].direita != null);
    b.textContent = a.id.slice(1) + (feito ? " ✓" : parcial ? " ·" : "");
    b.className = (j === A ? "on " : "") + (feito ? "ok" : "");
    b.onclick = () => irAtaque(j);
    l.append(b);
  });
}

function botoesDaLinha(l, campo, opcoes, n) {
  const g = document.createElement("span");
  g.className = "grupo";
  for (const [tecla, nome] of opcoes) {
    const b = document.createElement("button");
    b.textContent = tecla;
    b.title = nome;
    b.className = n[campo] === tecla ? "on" : "";
    b.onclick = ev => { ev.stopPropagation(); responder(l, campo, tecla); };
    g.append(b);
  }
  return g;
}

function texto(t) { return document.createTextNode(t); }

function renderLinhas() {
  const a = ATAQUES[A], l = $("linhas"); l.replaceChildren();
  a.ks.forEach((k, j) => {
    const n = G.notas[k];
    const div = document.createElement("div");
    div.className = "nota" + (j === L && !PEST_ATIVA ? " ativa" : "") + (completa(n) ? " ok" : "");
    div.onclick = () => { L = j; PEST_ATIVA = false; mostrar(); };
    const rot = document.createElement("span");
    rot.className = "rotulo";
    rot.textContent = "c" + n.corda + " casa " + n.casa;
    div.append(rot, texto("— esquerda "), botoesDaLinha(j, "esquerda", ESQUERDA, n), texto("direita "), botoesDaLinha(j, "direita", DIREITA, n));
    l.append(div);
  });
}

// Casa da pestana padrão: a menor casa > 0 entre as notas do ataque (1 se não há).
function casaPadrao(a) {
  const casas = a.ks.map(k => Number(G.notas[k].casa)).filter(c => c > 0);
  return casas.length ? Math.min(...casas) : 1;
}

// Pestana "sim" inicial: casa padrão; cordas de menor a maior nota dessa casa (se houver
// ao menos duas cordas); senão, da corda 1 até a 6.
function pestanaPadrao(a) {
  const casa = casaPadrao(a);
  const cordas = a.ks.map(k => G.notas[k]).filter(n => Number(n.casa) === casa).map(n => Number(n.corda));
  let de = 1, ate = 6;
  if (cordas.length && Math.min(...cordas) < Math.max(...cordas)) { de = Math.min(...cordas); ate = Math.max(...cordas); }
  return {pestana: "sim", pestana_dedo: "1", pestana_casa: casa, pestana_de: de, pestana_ate: ate};
}

function resumoPestana(p) {
  if (p.pestana === "nao") return "sem pestana";
  if (p.pestana === "?") return "não dá para ver";
  if (p.pestana !== "sim") return "pestana ainda não respondida";
  const n = p.pestana_ate - p.pestana_de + 1;
  return "pestana de " + n + " cordas" + (n === 6 ? " (inteira)" : "");
}

function renderPestana() {
  const at = ATAQUES[A], p = pestanaDe(at), bloco = $("pestana");
  bloco.className = "bloco-pestana" + (PEST_ATIVA ? " ativa" : "") + (pestanaOk(at) ? " ok" : "");
  const g = $("pest-resp"); g.replaceChildren();
  for (const [valor, rotulo] of PESTANA_OPCOES) {
    const b = document.createElement("button");
    b.textContent = rotulo;
    b.className = p.pestana === valor ? "on" : "";
    b.onclick = ev => { ev.stopPropagation(); escolherPestana(valor); };
    g.append(b);
  }
  $("pest-resumo").textContent = resumoPestana(p);
  const sim = p.pestana === "sim";
  $("pest-campos").hidden = !sim;
  if (!sim) return;
  const d = $("pest-dedo"); d.replaceChildren();
  for (const dedo of ["1", "2", "3", "4"]) {
    const b = document.createElement("button");
    b.textContent = dedo;
    b.className = (p.pestana_dedo || "1") === dedo ? "on" : "";
    b.onclick = ev => { ev.stopPropagation(); mudarPestana({pestana_dedo: dedo}); };
    d.append(b);
  }
  $("pest-casa").value = p.pestana_casa;
  $("pest-de").value = p.pestana_de;
  $("pest-ate").value = p.pestana_ate;
}

function mostrar() {
  const a = ATAQUES[A];
  const i = INDICE.notas.find(x => x.ataque === a.id);
  const base = "/" + i.pasta + "/";
  const ativa = G.notas[a.ks[L]];
  $("posicao").textContent = "ataque " + (A + 1) + " / " + ATAQUES.length;
  $("titulo").textContent = a.id + " · t=" + Number(i.t_ini).toFixed(2) + " s · " + i.texto_acorde;
  $("info").textContent = a.ks.length + (a.ks.length === 1 ? " nota" : " notas") + " no ataque · " + (PEST_ATIVA ? "pestana ativa" : "linha ativa: c" + ativa.corda + " casa " + ativa.casa);
  $("avisos").replaceChildren(...i.avisos.map(t => { const d = document.createElement("div"); d.className = "aviso"; d.textContent = t; return d; }));
  $("img-quadro").src = base + "quadro.jpg";
  $("img-esq").src = base + "esq.jpg";
  $("dir-m").src = base + "dir_m.jpg";
  $("dir-0").src = base + "dir_0.jpg";
  $("dir-p").src = base + "dir_p.jpg";
  renderLinhas();
  renderPestana();
  $("obs").value = ativa.obs || "";
  listaAtaques(); progresso();
}

// Grava um campo de uma nota e, se a linha ficou com as duas respostas, avança.
async function gravar(k, campo, valor, avancar, a, l) {
  const n = G.notas[k], antes = completa(n), anterior = n[campo];
  n[campo] = valor;
  A = a; L = l; PEST_ATIVA = false;
  mostrar();
  setStatus("gravando…", "");
  try {
    const r = await fetch("/responder", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id: n.id, [campo]: valor})});
    const j = await r.json();
    if (!j.ok) throw new Error(j.erro);
    setStatus("salvo em disco " + j.salvo_em.slice(11) + " (" + j.ataques_completos + "/" + j.total_ataques + " ataques, " + j.completas + "/" + j.total + " notas)", "ok");
  } catch (e) {
    n[campo] = anterior;
    mostrar();
    setStatus("NÃO SALVO (" + e.message + "): tente de novo", "ruim");
    return;
  }
  if (avancar && !antes && completa(n) && A === a && L === l) avancarAposCompletar(a, l);
  mostrar();
}

// Ataque completo (notas e pestana) vai para o próximo, na primeira nota sem resposta.
function avancarAtaque(a) {
  if (a >= ATAQUES.length - 1) return;
  A = a + 1;
  const pos = posInicial(A);
  L = pos.L; PEST_ATIVA = pos.P;
}

// Depois de uma nota ficar completa: próxima nota incompleta; se todas estão prontas e
// falta a pestana, a linha ativa vira o bloco da pestana.
function avancarAposCompletar(a, l) {
  const at = ATAQUES[a];
  if (ataqueCompleto(at)) { avancarAtaque(a); return; }
  const prox = primeiraIncompleta(at, (l + 1) % at.ks.length);
  if (prox >= 0) L = prox;
  else PEST_ATIVA = !pestanaOk(at);
}

// Resposta a uma linha do ataque atual (tecla ou clique). Clicar de novo na mesma tecla limpa.
function responder(l, campo, valor) {
  const a = A;
  const k = ATAQUES[a].ks[l];
  const n = G.notas[k];
  gravar(k, campo, n[campo] === valor ? null : valor, true, a, l);
}

// Grava a pestana do ataque atual e avança se o ataque ficou completo com ela.
async function gravarPestana(a, campos, avancar) {
  const at = ATAQUES[a], id = at.id;
  const anterior = G.ataques[id], antes = ataqueCompleto(at);
  G.ataques[id] = {...anterior, ...SEM_PESTANA, ...campos, respondido_em: null};
  A = a; PEST_ATIVA = false;
  mostrar();
  setStatus("gravando…", "");
  try {
    const r = await fetch("/pestana", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ataque: id, ...campos})});
    const j = await r.json();
    if (!j.ok) throw new Error(j.erro);
    G.ataques[id] = j.pestana;
    setStatus("salvo em disco " + j.salvo_em.slice(11) + " (" + j.ataques_completos + "/" + j.total_ataques + " ataques, " + j.completas + "/" + j.total + " notas)", "ok");
  } catch (e) {
    G.ataques[id] = anterior;
    mostrar();
    setStatus("NÃO SALVO (" + e.message + "): tente de novo", "ruim");
    return;
  }
  if (G.ataques[id].pestana === "sim") await preencherPestana(a);
  if (avancar && !antes && ataqueCompleto(at) && A === a) avancarAtaque(a);
  mostrar();
}

// Nota sob a pestana (casa da pestana, corda entre de e até) sem dedo da esquerda
// recebe o dedo da pestana. Nunca sobrescreve um dedo já respondido.
async function preencherPestana(a) {
  const at = ATAQUES[a], p = G.ataques[at.id];
  for (const k of at.ks) {
    const n = G.notas[k];
    if (n.esquerda != null || n.casa !== p.pestana_casa) continue;
    if (n.corda < p.pestana_de || n.corda > p.pestana_ate) continue;
    try {
      const r = await fetch("/responder", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id: n.id, esquerda: p.pestana_dedo})});
      const j = await r.json();
      if (!j.ok) throw new Error(j.erro);
      n.esquerda = p.pestana_dedo;
    } catch (e) {
      setStatus("NÃO SALVO o dedo da pestana em c" + n.corda + " (" + e.message + ")", "ruim");
      return;
    }
  }
}

// Botões não / sim / ? e teclas n e b. Com sim, as notas sob a pestana recebem o dedo
// dela e o ataque completo avança; para corrigir dedo, casa ou cordas, volte com ←.
// Clicar em sim de novo reaplica o preenchimento e avança se o ataque ficou completo.
async function escolherPestana(valor) {
  const at = ATAQUES[A];
  if (pestanaDe(at).pestana === valor) {
    if (valor !== "sim") return;
    const a = A;
    await preencherPestana(a);
    if (ataqueCompleto(at) && A === a) avancarAtaque(a);
    mostrar();
    return;
  }
  if (valor === "sim") gravarPestana(A, pestanaPadrao(at), true);
  else gravarPestana(A, {pestana: valor}, true);
}

function alternarPestana() {
  escolherPestana(pestanaDe(ATAQUES[A]).pestana === "sim" ? "nao" : "sim");
}

// Muda um campo de uma pestana já "sim" (dedo, casa, corda de ou até), com o resto igual.
function mudarPestana(mudanca) {
  const at = ATAQUES[A], p = pestanaDe(at);
  const campos = {
    pestana: "sim",
    pestana_dedo: p.pestana_dedo || "1",
    pestana_casa: p.pestana_casa,
    pestana_de: p.pestana_de,
    pestana_ate: p.pestana_ate,
    ...mudanca,
  };
  gravarPestana(A, campos, false);
}

function mudarCorda(campo, valor) {
  const p = pestanaDe(ATAQUES[A]);
  const de = campo === "pestana_de" ? valor : p.pestana_de;
  const ate = campo === "pestana_ate" ? valor : p.pestana_ate;
  if (de >= ate) {
    setStatus("a corda de cima (" + de + ") tem que ser menor que a de baixo (" + ate + ")", "ruim");
    mostrar();
    return;
  }
  mudarPestana({[campo]: valor});
}

function mudarCasa(texto) {
  const v = Number(texto);
  if (!Number.isInteger(v) || v < 1) {
    setStatus("casa da pestana: número inteiro maior que 0", "ruim");
    mostrar();
    return;
  }
  mudarPestana({pestana_casa: v});
}

function irAtaque(a) {
  if (a < 0 || a >= ATAQUES.length) return;
  A = a;
  const pos = posInicial(a);
  L = pos.L; PEST_ATIVA = pos.P;
  mostrar();
}

function gravarObs(valor) {
  const a = A, l = L, k = ATAQUES[a].ks[l];
  gravar(k, "obs", valor, false, a, l);
}

function preencherCordas() {
  for (const id of ["pest-de", "pest-ate"]) {
    const s = $(id);
    for (let c = 1; c <= 6; c++) {
      const o = document.createElement("option");
      o.value = c; o.textContent = c;
      s.append(o);
    }
  }
}

$("ant").onclick = () => irAtaque(A - 1);
$("prox").onclick = () => irAtaque(A + 1);
$("obs").addEventListener("change", ev => gravarObs(ev.target.value));
$("pestana").addEventListener("click", () => { if (G && !PEST_ATIVA) { PEST_ATIVA = true; mostrar(); } });
$("pest-casa").addEventListener("change", ev => mudarCasa(ev.target.value));
$("pest-de").addEventListener("change", ev => mudarCorda("pestana_de", Number(ev.target.value)));
$("pest-ate").addEventListener("change", ev => mudarCorda("pestana_ate", Number(ev.target.value)));
preencherCordas();

document.addEventListener("keydown", ev => {
  if (ev.ctrlKey || ev.metaKey || ev.altKey || !G) return;
  const t = ev.target.tagName;
  if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return;
  const k = ev.key.toLowerCase();
  const m = ATAQUES[A].ks.length;
  if (ev.key === "ArrowRight") irAtaque(A + 1);
  else if (ev.key === "ArrowLeft") irAtaque(A - 1);
  else if (ev.key === "ArrowDown") {
    ev.preventDefault();
    if (PEST_ATIVA) return;
    if (L < m - 1) L++; else PEST_ATIVA = true;
    mostrar();
  }
  else if (ev.key === "ArrowUp") {
    ev.preventDefault();
    if (PEST_ATIVA) { PEST_ATIVA = false; L = m - 1; }
    else if (L > 0) L--;
    else return;
    mostrar();
  }
  else if (k === "b") alternarPestana();
  else if (k === "n") escolherPestana("nao");
  else if (PEST_ATIVA) return;
  else if (Object.hasOwn(TECLAS_ESQ, k)) responder(L, "esquerda", TECLAS_ESQ[k]);
  else if (Object.hasOwn(TECLAS_DIR, k)) responder(L, "direita", TECLAS_DIR[k]);
});

(async function () {
  try {
    [INDICE, G] = await Promise.all([
      fetch("/indice.json").then(r => r.json()),
      fetch("/gabarito.json").then(r => r.json()),
    ]);
  } catch (e) {
    setStatus("erro ao carregar: " + e.message, "ruim");
    return;
  }
  if (G.formato !== 3) {
    setStatus("gabarito não está no formato 3: rode a migração (tab.maos_gabarito migrar)", "ruim");
    return;
  }
  $("video").textContent = G.video;
  montarAtaques();
  A = Math.max(0, ATAQUES.findIndex(a => !ataqueCompleto(a)));
  const pos = posInicial(A);
  L = pos.L; PEST_ATIVA = pos.P;
  const algumaResposta = G.notas.some(n => n.esquerda != null || n.direita != null) || Object.values(G.ataques).some(p => p.pestana != null);
  setStatus("carregado: " + (algumaResposta ? "retomando" : "gabarito novo"), "ok");
  mostrar();
})();
</script></body></html>
"""


def servir(pasta: Path, ouro: Path, porta: int, host: str) -> int:
    """Sobe o servidor e fica nele até Ctrl+C.

    Args:
        pasta: pasta do ``preparar`` (``indice.json`` e imagens).
        ouro: arquivo do gabarito (já criado pelo ``preparar``).
        porta: porta TCP.
        host: endereço de escuta.

    Returns:
        Código de saída.
    """
    if not (pasta / "indice.json").exists():
        print(f"sem indice.json em {pasta}; rode o preparar antes", file=sys.stderr)
        return 2
    if not ouro.exists():
        print(f"sem gabarito em {ouro}; rode o preparar antes", file=sys.stderr)
        return 2
    if json.loads(ouro.read_text(encoding="utf-8")).get("formato") != FORMATO_GABARITO:
        print(
            f"{ouro} não está no formato {FORMATO_GABARITO}; rode "
            "`python -m tab.maos_gabarito migrar --ouro ...` (ou o preparar)",
            file=sys.stderr,
        )
        return 2
    servidor = criar_servidor(pasta, ouro, porta, host)
    print(f"ferramenta dos dedos: http://127.0.0.1:{servidor.server_address[1]}/")
    print(f"escutando em {host}; cada resposta é gravada em: {ouro}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


def main() -> int:
    """Ponto de entrada: ``servir`` e ``migrar`` (o ``preparar`` está em ``tab.maos_gabarito_preparar``).

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    s = sub.add_parser(
        "servir", help="serve a ferramenta de rotular (grava a cada clique)"
    )
    s.add_argument("--pasta", type=Path, default=MAOS_DEDOS)
    s.add_argument("--ouro", type=Path, default=GABARITO_DEDOS)
    s.add_argument("--porta", type=int, default=8098)
    s.add_argument("--host", default="127.0.0.1")
    m = sub.add_parser(
        "migrar", help="converte o gabarito do formato 2 para o 3 (pestana), no disco"
    )
    m.add_argument("--ouro", type=Path, default=GABARITO_DEDOS)
    args = ap.parse_args()
    if args.comando == "migrar":
        try:
            total = migrar_arquivo(args.ouro)
        except ValueError as erro:
            print(f"não migrou {args.ouro}: {erro}", file=sys.stderr)
            return 2
        print(f"{args.ouro}: formato {FORMATO_GABARITO}, {total} ataques")
        return 0
    return servir(args.pasta, args.ouro, args.porta, args.host)


if __name__ == "__main__":
    sys.exit(main())
