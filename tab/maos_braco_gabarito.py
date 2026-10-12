"""Gabarito da geometria do braço do violão (M3b): amostra, registro e a ferramenta.

Fase M3b da trilha das mãos (``docs/decisoes/1003-fases-das-maos.md``). O dono marca,
em ~20 quadros de canais e layouts diferentes, as cordas 1 e 6, o nut (a pestana) e os
trastes. Serve para medir e desenvolver um detector de braço que funcione em qualquer
vídeo, no lugar das coordenadas fixas do vídeo do MVP.

Este módulo tem:

1. funções puras (amostra, conversão de clique, trastes, numeração, completo,
   mesclagem do gabarito, validação de resposta), testadas no gate;
2. ``preparar``: copia os quadros da amostra do cache do censo para ``m3b/quadros``,
   grava ``indice.json`` e cria o gabarito (mesclado com o que já existe);
3. ``servir``: servidor ``http.server`` que mostra um quadro por vez e grava cada
   mudança em disco (escrita atômica);
4. ``folha``: folha numerada com as miniaturas da amostra, para conferência.

Coordenadas são guardadas SEMPRE no espaço do quadro original. A página manda o clique
na imagem escalada e a escala; o servidor converte (``x_quadro = x_img / escala``).

Uso::

    python -m tab.maos_braco_gabarito preparar
    python -m tab.maos_braco_gabarito servir --porta 8098 --host 0.0.0.0
    python -m tab.maos_braco_gabarito folha
"""

from __future__ import annotations

import argparse
import copy
import datetime
import http.server
import itertools
import json
import math
import random
import re
import shutil
import sys
import threading
from pathlib import Path

import cv2
import numpy as np

from .cache import ModoCache, caminho_do_quadro, pasta_do_video
from .caminhos import CENSO_MAOS, GABARITO_BRACO, MAOS_M3B, cache_quadros
from .maos_gabarito import gravar_atomico

#: Ponto ``[x, y]`` no espaço do quadro original.
Ponto = list[float]

#: Semente da amostra (a mesma da trilha das mãos).
SEMENTE_PADRAO = 20261012

#: Formato do gabarito do braço. O servidor só aceita este.
FORMATO_GABARITO = 1

#: Canais da amostra (os que têm mais vídeos com quadro elegível no censo).
N_CANAIS = 8

#: Quadros por canal, de vídeos diferentes; os ``EXTRA_MAIORES`` canais mais numerosos
#: ganham um quadro a mais (8 x 2 + 4 = 20).
POR_CANAL = 2
EXTRA_MAIORES = 4

#: Vídeo do MVP. Entra na amostra como controle, com um quadro em que a tab aparece.
ARQUIVO_MVP = "sky guitar/retrato brasileiro - tab & lesson.mp4"
CANAL_MVP = "sky guitar"

#: Valores de ``braco``. ``None`` = ainda não respondido.
BRACOS = ("sim", "parcial", "nao", "?")

#: Modos de clique da página (a tecla ``f`` do nut fora não é um modo de clique).
MODOS_CLIQUE = ("corda1", "corda6", "nut", "trastes")

#: Campos de resposta do quadro (o que o desfazer restaura e o gabarito guarda).
CAMPOS_RESPOSTA = (
    "braco",
    "corda1",
    "corda6",
    "nut",
    "trastes",
    "traste_referencia",
    "obs",
)

#: Campos que o desfazer restaura (a observação fica de fora de propósito).
CAMPOS_DESFAZER = ("braco", "corda1", "corda6", "nut", "trastes", "traste_referencia")

#: Campos de geometria: some quando o braço é "nao" ou "?".
CAMPOS_GEOMETRIA = ("corda1", "corda6", "nut", "trastes", "traste_referencia")

#: Raio para remover um traste clicado de novo, como fração da largura do quadro.
FRACAO_RAIO_TRASTE = 0.012

#: Numeração de traste aceita na referência (cordas e trastes de violão: 1 a 30).
NUMERO_TRASTE_MAXIMO = 30

#: Tamanho máximo da observação e da pilha de desfazer por quadro.
TAMANHO_OBS_MAXIMO = 500
MAX_HISTORICO = 200

#: Escala aceita para o clique (a imagem da página nunca passa disso).
ESCALA_MAXIMA = 20.0

#: Tamanho máximo do corpo de um POST.
TAMANHO_CORPO_MAXIMO = 16_000

_TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
}


# ---------------------------------------------------------------------------------
# Amostra
# ---------------------------------------------------------------------------------


def _quadros_elegiveis(video: dict) -> list[dict]:
    """Quadros do vídeo com pelo menos uma mão detectada.

    Args:
        video: linha do censo (``quadros`` com ``maos``).

    Returns:
        Os quadros com ao menos uma mão, na ordem do censo.
    """
    return [q for q in video["quadros"] if len(q.get("maos") or []) >= 1]


def _escolher_quadro(quadros: list[dict], rng: random.Random) -> dict:
    """Sorteia um quadro, preferindo os que têm 2 ou mais mãos.

    Args:
        quadros: quadros elegíveis de um vídeo (com pelo menos uma mão).
        rng: gerador da amostra (o mesmo para todo o sorteio).

    Returns:
        O quadro sorteado.
    """
    preferidos = [q for q in quadros if len(q["maos"]) >= 2] or quadros
    return rng.choice(sorted(preferidos, key=lambda q: q["i"]))


def amostrar_quadros(
    censo: list[dict],
    semente: int = SEMENTE_PADRAO,
    n_canais: int = N_CANAIS,
    por_canal: int = POR_CANAL,
    extra_maiores: int = EXTRA_MAIORES,
    arquivo_mvp: str = ARQUIVO_MVP,
) -> list[dict]:
    """Sorteia os quadros da ferramenta do braço, reproduzível pela semente.

    Escolhe os ``n_canais`` canais com mais vídeos que têm quadro elegível. De cada
    canal sorteia ``por_canal`` quadros de vídeos DIFERENTES; os ``extra_maiores``
    canais mais numerosos ganham um quadro a mais. O vídeo do MVP entra com um quadro
    em que a tab aparece (``tab`` verdadeiro). No fim a lista é embaralhada e recebe
    os ids ``q01``..``qNN``.

    Args:
        censo: linhas do censo de mãos (uma por vídeo, com ``quadros``).
        semente: semente do sorteio.
        n_canais: quantos canais entram.
        por_canal: quadros por canal.
        extra_maiores: canais que ganham um quadro a mais.
        arquivo_mvp: ``arquivo`` do vídeo do MVP (controle).

    Returns:
        Lista de dicionários com ``id``, ``chave``, ``arquivo``, ``canal``, ``indice``
        (índice do quadro no vídeo), ``t``, ``tab``, ``n_maos`` e ``mvp``.

    Raises:
        ValueError: se faltar vídeo ou canal para a amostra (ex.: o MVP sem quadro com
            tab ou um canal com menos vídeos do que quadros pedidos).
    """
    por_canal_lista: dict[str, list[dict]] = {}
    for video in sorted(censo, key=lambda v: (v["canal"], v["arquivo"])):
        if _quadros_elegiveis(video):
            por_canal_lista.setdefault(video["canal"], []).append(video)
    ordem = sorted(por_canal_lista, key=lambda c: (-len(por_canal_lista[c]), c))
    ordem = ordem[:n_canais]
    if CANAL_MVP not in ordem:
        raise ValueError(f"o canal do MVP ({CANAL_MVP}) ficou fora dos {n_canais}")

    rng = random.Random(semente)
    escolhidos: list[tuple[dict, dict, bool]] = []
    for posicao, canal in enumerate(ordem):
        n = por_canal + (1 if posicao < extra_maiores else 0)
        videos = list(por_canal_lista[canal])
        if canal == CANAL_MVP:
            mvp = [v for v in videos if v["arquivo"] == arquivo_mvp]
            if not mvp:
                raise ValueError(f"o vídeo do MVP não está no censo: {arquivo_mvp}")
            com_tab = [q for q in _quadros_elegiveis(mvp[0]) if q.get("tab")]
            if not com_tab:
                raise ValueError("o MVP não tem quadro elegível com tab")
            escolhidos.append((mvp[0], _escolher_quadro(com_tab, rng), True))
            videos = [v for v in videos if v is not mvp[0]]
            n -= 1
        if len(videos) < n:
            raise ValueError(f"{canal}: {len(videos)} vídeos para {n} quadros")
        rng.shuffle(videos)
        for video in videos[:n]:
            quadro = _escolher_quadro(_quadros_elegiveis(video), rng)
            escolhidos.append((video, quadro, False))

    rng.shuffle(escolhidos)
    amostra = []
    for k, (video, quadro, mvp_controle) in enumerate(escolhidos, start=1):
        amostra.append(
            {
                "id": f"q{k:02d}",
                "chave": video["chave"],
                "arquivo": video["arquivo"],
                "canal": video["canal"],
                "indice": quadro["i"],
                "t": quadro["t"],
                "tab": bool(quadro.get("tab")),
                "n_maos": len(quadro["maos"]),
                "mvp": mvp_controle,
            }
        )
    return amostra


# ---------------------------------------------------------------------------------
# Coordenadas
# ---------------------------------------------------------------------------------


def _ponto_numerico(valor: object) -> Ponto:
    """Valida ``[x, y]`` com números finitos (sem booleanos).

    Args:
        valor: o que chegou no JSON.

    Returns:
        ``[x, y]`` como float.

    Raises:
        ValueError: se não for um par de números finitos.
    """
    if not isinstance(valor, list) or len(valor) != 2:
        raise ValueError("ponto deve ser [x, y]")
    for v in valor:
        if isinstance(v, bool) or not isinstance(v, int | float):
            raise ValueError("coordenadas devem ser números")
        if not math.isfinite(v):
            raise ValueError("coordenadas devem ser finitas")
    return [float(valor[0]), float(valor[1])]


def converter_clique(ponto_img: object, escala: object) -> Ponto:
    """Converte um clique na imagem escalada para o espaço do quadro original.

    A página mede a imagem na tela. ``escala`` é largura mostrada / largura original,
    então ``x_quadro = x_img / escala`` (o mesmo para y).

    Args:
        ponto_img: ``[x, y]`` em pixels da imagem mostrada na tela.
        escala: largura mostrada dividida pela largura do quadro original (> 0).

    Returns:
        ``[x, y]`` no espaço do quadro, com 1 casa decimal.

    Raises:
        ValueError: se a escala não for um número entre 0 (exclusive) e ``ESCALA_MAXIMA``,
            ou se o ponto não for um par de números.
    """
    if isinstance(escala, bool) or not isinstance(escala, int | float):
        raise ValueError("escala deve ser número")
    if not (math.isfinite(escala) and 0 < escala <= ESCALA_MAXIMA):
        raise ValueError(f"escala fora do intervalo (0, {ESCALA_MAXIMA}]")
    x, y = _ponto_numerico(ponto_img)
    return [round(x / escala, 1), round(y / escala, 1)]


def validar_no_quadro(ponto: Ponto, dimensoes: tuple[int, int]) -> None:
    """Recusa ponto fora do quadro original.

    Args:
        ponto: ``[x, y]`` no espaço do quadro.
        dimensoes: ``(largura, altura)`` do quadro original.

    Raises:
        ValueError: se o ponto estiver fora do retângulo do quadro.
    """
    largura, altura = dimensoes
    x, y = ponto
    if not (0 <= x <= largura and 0 <= y <= altura):
        raise ValueError(f"clique fora do quadro ({x:.0f}, {y:.0f})")


# ---------------------------------------------------------------------------------
# Trastes, cordas e numeração
# ---------------------------------------------------------------------------------


def aplicar_par(par: list[Ponto] | None, ponto: Ponto) -> list[Ponto]:
    """Acrescenta um clique a um par de cordas (corda 1 ou 6).

    Um par tem 2 pontos. Com o par cheio, o clique novo começa outro par.

    Args:
        par: pontos já marcados (0 a 2) ou ``None``.
        ponto: o clique novo.

    Returns:
        A nova lista de pontos (1 ou 2).
    """
    if par is None or len(par) >= 2:
        return [ponto]
    return [*par, ponto]


def aplicar_traste(
    trastes: list[Ponto] | None, ponto: Ponto, raio: float
) -> list[Ponto]:
    """Adiciona um traste, ou remove o mais próximo se o clique cair perto de um.

    Args:
        trastes: trastes já marcados ou ``None``.
        ponto: o clique novo.
        raio: distância (no quadro) em que o clique remove um traste marcado.

    Returns:
        A nova lista de trastes.
    """
    atuais = [list(t) for t in (trastes or [])]
    perto = [i for i, t in enumerate(atuais) if math.dist(t, ponto) <= raio]
    if perto:
        mais_perto = min(perto, key=lambda i: math.dist(atuais[i], ponto))
        del atuais[mais_perto]
        return atuais
    return [*atuais, ponto]


def _direcao_principal(pontos: list[Ponto]) -> tuple[float, float]:
    """Direção do eixo principal de uma nuvem de pontos (PCA em 2D).

    Args:
        pontos: pelo menos um ponto.

    Returns:
        Vetor unitário ``(dx, dy)`` da direção de maior variância.
    """
    n = len(pontos)
    mx = sum(p[0] for p in pontos) / n
    my = sum(p[1] for p in pontos) / n
    sxx = sum((p[0] - mx) ** 2 for p in pontos)
    syy = sum((p[1] - my) ** 2 for p in pontos)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pontos)
    angulo = 0.5 * math.atan2(2 * sxy, sxx - syy)
    return math.cos(angulo), math.sin(angulo)


def ordenar_trastes(trastes: list[Ponto], nut: Ponto | None) -> list[Ponto]:
    """Ordena os trastes do nut para fora (o mais perto do nut vem primeiro).

    Com o nut visível, a ordem é a distância ao nut. Sem o nut, os trastes são
    colocados no eixo do braço (PCA dos cliques) e o sentido vem da espaçamento: os
    trastes ficam mais juntos para o corpo, então o lado do nut é o de intervalos
    maiores. Com menos de 3 trastes não há espaçamento que decida o sentido, e o
    eixo sai na ordem crescente.

    Args:
        trastes: trastes marcados.
        nut: ponto do nut, ou ``None`` se estiver fora.

    Returns:
        Os trastes na ordem do nut para fora.
    """
    if not trastes:
        return []
    if nut is not None:
        return sorted(trastes, key=lambda t: math.dist(t, nut))
    if len(trastes) == 1:
        return [list(trastes[0])]
    dx, dy = _direcao_principal(trastes)
    ordenados = sorted(trastes, key=lambda t: t[0] * dx + t[1] * dy)
    intervalos = [math.dist(a, b) for a, b in itertools.pairwise(ordenados)]
    meio = len(intervalos) // 2
    if meio and sum(intervalos[:meio]) < sum(intervalos[-meio:]):
        ordenados.reverse()
    return ordenados


def numerar_trastes(registro: dict) -> list[dict]:
    """Numera os trastes marcados, na ordem do nut para fora.

    Com o nut visível, o traste mais perto do nut é o 1. Com o nut fora e um traste
    de referência (o dono disse que este clique é o traste ``numero``), os outros
    trastes ganham número pela posição relativa a ele. Números abaixo de 1 não existem
    (são o nut) e saem como ``None``.

    Args:
        registro: resposta de um quadro (``nut``, ``trastes``, ``traste_referencia``).

    Returns:
        Lista de ``{"numero": int | None, "ponto": [x, y]}`` na ordem do nut.
    """
    trastes = [list(t) for t in (registro.get("trastes") or [])]
    nut = registro.get("nut")
    referencia = registro.get("traste_referencia")
    nut_ponto = nut if isinstance(nut, list) else None
    ordenados = ordenar_trastes(trastes, nut_ponto)
    numeros: list[int | None] = [None] * len(ordenados)
    if nut_ponto is not None:
        numeros = list(range(1, len(ordenados) + 1))
    elif (
        nut == "fora"
        and isinstance(referencia, dict)
        and referencia["ponto"] in (ordenados)
    ):
        r = ordenados.index(referencia["ponto"])
        numeros = [
            referencia["numero"] + (j - r)
            if referencia["numero"] + (j - r) >= 1
            else None
            for j in range(len(ordenados))
        ]
    return [{"numero": n, "ponto": p} for n, p in zip(numeros, ordenados, strict=True)]


# ---------------------------------------------------------------------------------
# Registro do gabarito
# ---------------------------------------------------------------------------------


def registro_em_branco(chave: str) -> dict:
    """Resposta de um quadro, sem nada marcado.

    Args:
        chave: chave do vídeo de origem (para conferir a mesclagem).

    Returns:
        Registro com todos os campos em ``None`` (``trastes`` e ``historico`` vazios).
    """
    return {
        "chave": chave,
        "braco": None,
        "corda1": None,
        "corda6": None,
        "nut": None,
        "trastes": None,
        "traste_referencia": None,
        "obs": None,
        "respondido_em": None,
        "historico": [],
    }


def gabarito_novo(indice: list[dict], semente: int) -> dict:
    """Gabarito sem respostas para a amostra dada.

    Args:
        indice: itens da amostra (com ``id`` e ``chave``).
        semente: semente usada no sorteio.

    Returns:
        Dicionário no formato do gabarito, com um registro por quadro.
    """
    return {
        "formato": FORMATO_GABARITO,
        "como_foi_rotulado": (
            "dono, por quadro, na ferramenta tab.maos_braco_gabarito; coordenadas "
            "no espaço do quadro original (x_quadro = x_img / escala)"
        ),
        "semente": semente,
        "ferramenta": "tab.maos_braco_gabarito",
        "quadros": {q["id"]: registro_em_branco(q["chave"]) for q in indice},
    }


def tem_resposta(registro: dict) -> bool:
    """Se o quadro já foi respondido (alguma vez, mesmo que tenha sido apagado depois).

    Args:
        registro: resposta de um quadro.

    Returns:
        True quando ``respondido_em`` está preenchido.
    """
    return registro.get("respondido_em") is not None


def _par_completo(valor: object) -> bool:
    """Se uma corda tem exatamente os 2 pontos.

    Args:
        valor: ``corda1`` ou ``corda6``.

    Returns:
        True com 2 pontos.
    """
    return isinstance(valor, list) and len(valor) == 2


def registro_completo(registro: dict) -> bool:
    """Se o quadro está pronto para o gabarito.

    Pronto é: ``braco`` respondido; se for ``nao`` ou ``?``, basta isso. Se for ``sim``
    ou ``parcial``, precisa das duas cordas (2 pontos cada), do nut (ponto, ou ``fora``
    com ``traste_referencia``) e de pelo menos 2 trastes.

    Args:
        registro: resposta de um quadro.

    Returns:
        True se o quadro está completo.
    """
    braco = registro.get("braco")
    if braco is None:
        return False
    if braco in ("nao", "?"):
        return True
    if not (
        _par_completo(registro.get("corda1")) and _par_completo(registro.get("corda6"))
    ):
        return False
    nut = registro.get("nut")
    if nut == "fora":
        nut_ok = registro.get("traste_referencia") is not None
    else:
        nut_ok = isinstance(nut, list)
    return nut_ok and len(registro.get("trastes") or []) >= 2


def completos(gabarito: dict) -> list[str]:
    """Ids dos quadros completos, na ordem do gabarito.

    Args:
        gabarito: gabarito com ``quadros``.

    Returns:
        Lista de ids completos.
    """
    return [id_q for id_q, reg in gabarito["quadros"].items() if registro_completo(reg)]


def mesclar_gabarito(novo: dict, existente: dict | None) -> dict:
    """Mescla o gabarito recém-sorteado com o que já estava no disco.

    As respostas do arquivo existente são mantidas. Um quadro respondido só é aceito
    se a chave do vídeo bate com a da amostra nova: caso contrário as respostas
    apontariam para outro vídeo, e a mesclagem recusa.

    Args:
        novo: gabarito gerado pela amostra atual.
        existente: gabarito do disco, ou ``None`` se não houver.

    Returns:
        O gabarito novo, com as respostas do existente.

    Raises:
        ValueError: se o existente tiver formato antigo, ou se uma resposta não couber
            na amostra nova (outro vídeo ou quadro que sumiu).
    """
    if existente is None:
        return novo
    if existente.get("formato") != FORMATO_GABARITO:
        raise ValueError(
            f"gabarito existente tem formato {existente.get('formato')}, "
            f"esperado {FORMATO_GABARITO}"
        )
    for id_q, antigo in existente.get("quadros", {}).items():
        if not tem_resposta(antigo):
            continue
        if id_q not in novo["quadros"]:
            raise ValueError(f"{id_q} tem resposta mas não está na amostra nova")
        atual = novo["quadros"][id_q]
        if antigo.get("chave") != atual["chave"]:
            raise ValueError(f"{id_q} tem resposta de outro vídeo; não mesclou")
        for campo in (*CAMPOS_RESPOSTA, "respondido_em", "historico"):
            atual[campo] = copy.deepcopy(antigo.get(campo, atual[campo]))
    return novo


def visao_quadro(gabarito: dict, id_quadro: str) -> dict:
    """O que a página mostra de um quadro: registro, numeração e se está completo.

    Args:
        gabarito: gabarito com ``quadros``.
        id_quadro: id do quadro (``qNN``).

    Returns:
        ``registro`` (sem o histórico, só com ``desfazer_disponivel``), ``numeracao``
        dos trastes e ``completo``.
    """
    reg = gabarito["quadros"][id_quadro]
    registro = {k: copy.deepcopy(v) for k, v in reg.items() if k != "historico"}
    registro["desfazer_disponivel"] = bool(reg.get("historico"))
    return {
        "registro": registro,
        "numeracao": numerar_trastes(reg),
        "completo": registro_completo(reg),
    }


def resumo(gabarito: dict, indice: list[dict]) -> dict:
    """Estado inteiro para a página: uma visão por quadro e o progresso.

    Args:
        gabarito: gabarito com ``quadros``.
        indice: itens da amostra, na ordem de exibição.

    Returns:
        ``quadros`` (id -> visão), ``completos`` (ids), ``concluidos`` e ``total``.
    """
    visoes = {q["id"]: visao_quadro(gabarito, q["id"]) for q in indice}
    feitos = [q["id"] for q in indice if visoes[q["id"]]["completo"]]
    return {
        "quadros": visoes,
        "completos": feitos,
        "concluidos": len(feitos),
        "total": len(indice),
    }


# ---------------------------------------------------------------------------------
# Respostas
# ---------------------------------------------------------------------------------


def _empilhar(registro: dict) -> None:
    """Guarda o estado atual dos campos que o desfazer restaura (pilha limitada).

    Args:
        registro: resposta do quadro, alterada em lugar.
    """
    foto = {c: copy.deepcopy(registro[c]) for c in CAMPOS_DESFAZER}
    registro["historico"] = [*registro.get("historico", []), foto][-MAX_HISTORICO:]


def _limpar_referencia_orfa(registro: dict) -> None:
    """Tira a referência de traste se o traste dela foi removido.

    Args:
        registro: resposta do quadro, alterada em lugar.
    """
    ref = registro.get("traste_referencia")
    if ref and ref["ponto"] not in (registro.get("trastes") or []):
        registro["traste_referencia"] = None


def _validar_referencia(valor: object, registro: dict) -> dict:
    """Valida ``{"ponto", "numero"}`` da referência de traste.

    Args:
        valor: o que chegou no JSON.
        registro: resposta do quadro (o ponto tem que ser um traste marcado).

    Returns:
        A referência com ``ponto`` como lista de float e ``numero`` como int.

    Raises:
        ValueError: se o formato for outro, o número estiver fora de 1..30, ou o ponto
            não for um traste marcado.
    """
    if not isinstance(valor, dict) or set(valor) != {"ponto", "numero"}:
        raise ValueError("traste_referencia deve ser {ponto, numero}")
    numero = valor["numero"]
    if isinstance(numero, bool) or not isinstance(numero, int):
        raise ValueError("numero do traste deve ser inteiro")
    if not 1 <= numero <= NUMERO_TRASTE_MAXIMO:
        raise ValueError(f"numero do traste fora de 1..{NUMERO_TRASTE_MAXIMO}")
    ponto = _ponto_numerico(valor["ponto"])
    if ponto not in (registro.get("trastes") or []):
        raise ValueError("a referência precisa ser um traste já marcado")
    return {"ponto": ponto, "numero": numero}


def _clicar(
    registro: dict, dados: dict, dimensoes: tuple[int, int], agora: str
) -> None:
    """Aplica um clique no modo pedido (corda 1, corda 6, nut ou traste).

    Args:
        registro: resposta do quadro, alterada em lugar.
        dados: ``modo``, ``ponto_img`` e ``escala``.
        dimensoes: ``(largura, altura)`` do quadro original.
        agora: carimbo de data/hora da resposta.

    Raises:
        ValueError: se o modo for desconhecido, a escala ou o ponto forem inválidos,
            ou o clique cair fora do quadro.
    """
    modo = dados.get("modo")
    if modo not in MODOS_CLIQUE:
        raise ValueError(f"modo de clique desconhecido: {modo}")
    ponto = converter_clique(dados.get("ponto_img"), dados.get("escala"))
    validar_no_quadro(ponto, dimensoes)
    _empilhar(registro)
    if modo in ("corda1", "corda6"):
        registro[modo] = aplicar_par(registro[modo], ponto)
    elif modo == "nut":
        registro["nut"] = ponto
    else:
        raio = FRACAO_RAIO_TRASTE * dimensoes[0]
        registro["trastes"] = aplicar_traste(registro["trastes"], ponto, raio)
        _limpar_referencia_orfa(registro)
    registro["respondido_em"] = agora


def _mudar_campo(registro: dict, dados: dict, agora: str) -> None:
    """Muda um campo de resposta (braço, nut, referência ou observação).

    Args:
        registro: resposta do quadro, alterada em lugar.
        dados: ``campo`` e ``valor``.
        agora: carimbo de data/hora da resposta.

    Raises:
        ValueError: se o campo ou o valor não forem válidos.
    """
    campo = dados.get("campo")
    valor = dados.get("valor")
    if campo == "braco":
        if valor is not None and valor not in BRACOS:
            raise ValueError(f"braco deve ser um de {BRACOS} ou null")
        _empilhar(registro)
        registro["braco"] = valor
        if valor in ("nao", "?"):
            for c in CAMPOS_GEOMETRIA:
                registro[c] = None
    elif campo == "nut":
        if valor not in ("fora", None):
            raise ValueError("nut aceita 'fora' ou null (o ponto vem do clique)")
        _empilhar(registro)
        registro["nut"] = valor
    elif campo == "traste_referencia":
        ref = None if valor is None else _validar_referencia(valor, registro)
        _empilhar(registro)
        registro["traste_referencia"] = ref
    elif campo == "obs":
        if valor is not None and not isinstance(valor, str):
            raise ValueError("obs deve ser texto")
        texto = (valor or "").strip()
        if len(texto) > TAMANHO_OBS_MAXIMO:
            raise ValueError(f"obs com mais de {TAMANHO_OBS_MAXIMO} caracteres")
        registro["obs"] = texto or None
    else:
        raise ValueError(f"campo desconhecido: {campo}")
    registro["respondido_em"] = agora


def aplicar_acao(
    gabarito: dict,
    id_quadro: str,
    dados: dict,
    dimensoes: tuple[int, int],
    agora: str,
) -> None:
    """Aplica uma ação da página a um quadro: clique, mudança de campo ou desfazer.

    Args:
        gabarito: gabarito, alterado em lugar.
        id_quadro: id do quadro (``qNN``).
        dados: ``acao`` (``clique`` ou ``desfazer``) com ``modo``/``ponto_img``/``escala``,
            ou ``campo``/``valor``.
        dimensoes: ``(largura, altura)`` do quadro original.
        agora: carimbo de data/hora da resposta.

    Raises:
        KeyError: se o quadro não existe no gabarito.
        ValueError: se a ação, o campo, o valor ou o clique forem inválidos.
    """
    registro = gabarito["quadros"][id_quadro]
    acao = dados.get("acao")
    if acao == "desfazer":
        if not registro.get("historico"):
            raise ValueError("nada para desfazer neste quadro")
        foto = registro["historico"][-1]
        for c in CAMPOS_DESFAZER:
            registro[c] = copy.deepcopy(foto[c])
        registro["historico"] = registro["historico"][:-1]
        registro["respondido_em"] = agora
    elif acao == "clique":
        _clicar(registro, dados, dimensoes, agora)
    elif "campo" in dados:
        _mudar_campo(registro, dados, agora)
    else:
        raise ValueError("ação desconhecida (use clique, desfazer ou campo)")


# ---------------------------------------------------------------------------------
# Preparar (cópia dos quadros e gabarito)
# ---------------------------------------------------------------------------------


def preparar(
    censo: Path,
    cache: Path,
    pasta: Path,
    ouro: Path,
    semente: int = SEMENTE_PADRAO,
) -> int:
    """Sorteia a amostra, copia os quadros e grava ``indice.json`` e o gabarito.

    Os quadros vêm do cache do censo (somente leitura). O gabarito que já existe no
    disco é mesclado: as respostas ficam.

    Args:
        censo: ``censo_maos.jsonl``.
        cache: raiz do cache de quadros (``/cache`` no container).
        pasta: destino (``m3b``); recebe ``quadros/qNN.png`` e ``indice.json``.
        ouro: arquivo do gabarito (``data/gold/maos/braco.json``).
        semente: semente do sorteio.

    Returns:
        Quantos quadros entraram na amostra.

    Raises:
        FileNotFoundError: se um quadro sorteado não estiver no cache.
        ValueError: se a mesclagem recusar (ver ``mesclar_gabarito``).
    """
    linhas = [
        json.loads(linha) for linha in censo.read_text(encoding="utf-8").splitlines()
    ]
    amostra = amostrar_quadros(linhas, semente)
    modo = ModoCache(raiz=cache)
    (pasta / "quadros").mkdir(parents=True, exist_ok=True)
    indice = []
    for q in amostra:
        origem = caminho_do_quadro(
            pasta_do_video(q["chave"], modo),
            f"presenca_{q['indice']:02d}",
            modo.formato,
        )
        if not origem.is_file():
            raise FileNotFoundError(f"quadro fora do cache: {origem}")
        destino = pasta / "quadros" / f"{q['id']}.png"
        shutil.copyfile(origem, destino)
        imagem = cv2.imread(str(destino))
        if imagem is None:
            raise ValueError(f"imagem ilegível: {destino}")
        altura, largura = imagem.shape[:2]
        indice.append(
            {
                **q,
                "png": f"quadros/{q['id']}.png",
                "largura": int(largura),
                "altura": int(altura),
            }
        )
    gravar_atomico(pasta / "indice.json", {"semente": semente, "quadros": indice})
    existente = json.loads(ouro.read_text(encoding="utf-8")) if ouro.exists() else None
    final = mesclar_gabarito(gabarito_novo(indice, semente), existente)
    gravar_atomico(ouro, final)
    return len(indice)


# ---------------------------------------------------------------------------------
# Servidor e página
# ---------------------------------------------------------------------------------


def criar_servidor(
    pasta: Path, ouro: Path, porta: int = 8098, host: str = "127.0.0.1"
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor (não o inicia). Por padrão escuta SOMENTE em 127.0.0.1.

    Args:
        pasta: pasta do ``preparar`` (``indice.json`` e ``quadros/``).
        ouro: gabarito; é carregado agora e gravado a cada resposta.
        porta: porta TCP (0 = uma livre).
        host: endereço de escuta (``0.0.0.0`` só dentro de container).

    Returns:
        O servidor; ``servidor.server_address[1]`` é a porta real.
    """
    pasta = pasta.resolve()
    indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
    itens = indice["quadros"]
    dimensoes = {q["id"]: (q["largura"], q["altura"]) for q in itens}
    estado = json.loads(ouro.read_text(encoding="utf-8"))
    trava = threading.Lock()

    class Manipulador(http.server.BaseHTTPRequestHandler):
        """Serve a página e as imagens, e grava cada ação em ``POST /responder``."""

        server_version = "maos_braco_gabarito"

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
            """Página, estado atual e arquivos da pasta (imagens e ``indice.json``)."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            caminho = self.path.split("?", 1)[0]
            if caminho in {"/", "/index.html"}:
                self._responder(200, _TIPOS[".html"], PAGINA.encode())
                return
            if caminho == "/estado.json":
                with trava:
                    dados = {"indice": itens, **resumo(estado, itens)}
                self._json(200, dados)
                return
            alvo = (pasta / caminho.lstrip("/")).resolve()
            if alvo.suffix in _TIPOS and alvo.is_relative_to(pasta) and alvo.is_file():
                self._responder(200, _TIPOS[alvo.suffix], alvo.read_bytes())
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def do_POST(self) -> None:
            """``/responder``: aplica uma ação a um quadro e grava o gabarito."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            if self.path != "/responder":
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= TAMANHO_CORPO_MAXIMO:
                    raise ValueError("corpo ausente ou grande demais")
                dados = json.loads(self.rfile.read(tamanho))
                if not isinstance(dados, dict):
                    raise ValueError("o corpo deve ser um objeto JSON")
                id_quadro = dados.pop("quadro", None)
                if id_quadro not in dimensoes:
                    raise ValueError(f"quadro desconhecido: {id_quadro}")
                agora = datetime.datetime.now().isoformat(timespec="seconds")
                with trava:
                    anterior = copy.deepcopy(estado)
                    try:
                        aplicar_acao(
                            estado, id_quadro, dados, dimensoes[id_quadro], agora
                        )
                        gravar_atomico(ouro, estado)
                    except Exception:
                        estado.clear()
                        estado.update(anterior)
                        raise
                    resposta = resumo(estado, itens)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as erro:
                self._json(400, {"ok": False, "erro": f"{type(erro).__name__}: {erro}"})
                return
            except OSError as erro:
                self._json(500, {"ok": False, "erro": f"não gravou em disco: {erro}"})
                return
            self._json(
                200, {"ok": True, "quadro": id_quadro, "salvo_em": agora, **resposta}
            )

    return http.server.ThreadingHTTPServer((host, porta), Manipulador)


PAGINA = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gabarito do braço (M3b)</title>
<style>
:root { color-scheme: dark; }
body { margin: 0; font-family: system-ui, sans-serif; background: #1b1d22; color: #eee; }
header { position: sticky; top: 0; z-index: 5; background: #24272e; padding: 10px 16px; }
h1 { font-size: 17px; margin: 0 0 6px; }
.instr { font-size: 13px; color: #c4c8d0; line-height: 1.45; }
.barra { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 8px; }
button { background: #3a3f49; color: #eee; border: 1px solid #5a606c; border-radius: 6px;
  padding: 6px 10px; cursor: pointer; font-size: 14px; }
button:hover { border-color: #8a93a3; }
button.ativo { background: #2f7d4f; border-color: #6fcf97; }
button:disabled { opacity: .4; cursor: default; }
.prog { margin-left: auto; font-weight: 600; }
main { padding: 10px 16px 24px; }
.quadro { position: relative; width: 100%; }
.quadro img { width: 100%; display: block; cursor: crosshair; user-select: none; }
.quadro svg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; pointer-events: none; }
.lista { display: flex; flex-wrap: wrap; gap: 4px; margin: 8px 0; }
.lista button { padding: 3px 7px; font-size: 12px; }
.lista button.feito::after { content: " \2713"; color: #6fcf97; }
.grupo { margin-top: 10px; font-size: 14px; }
.msg { font-size: 13px; color: #9fe3b8; }
.msg.erro { color: #ff9b9b; }
input[type=text], input[type=number], select { background: #111; color: #eee;
  border: 1px solid #5a606c; border-radius: 6px; padding: 5px 7px; font-size: 14px; }
input[type=text] { width: 100%; max-width: 560px; box-sizing: border-box; }
input[type=number] { width: 72px; }
.trastes li { margin: 2px 0; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<header>
  <h1>Gabarito do braço do violão (M3b): quadro <span id="pos"></span></h1>
  <div class="instr">
    Modo: <b>1</b> corda 1 (2 cliques, um em cada extremo, o mais afastado possível);
    <b>6</b> corda 6 (idem); <b>n</b> nut (1 clique no centro da pestana);
    <b>t</b> trastes (um clique no meio de cada traste visível; clicar perto de um marcado
    o remove); <b>f</b> nut fora da imagem. Braço: sim, parcial, não, ?.
    Setas &larr; &rarr; trocam de quadro. Nada avança sozinho.
  </div>
  <div class="barra">
    <button id="ant">&larr; anterior</button>
    <button id="prox">próximo &rarr;</button>
    <button data-modo="corda1">1 corda 1</button>
    <button data-modo="corda6">6 corda 6</button>
    <button data-modo="nut">n nut</button>
    <button data-modo="trastes">t trastes</button>
    <button id="fora">f nut fora</button>
    <button id="desfazer">desfazer último clique</button>
    <span class="prog" id="prog"></span>
  </div>
  <div class="barra">
    braço:
    <button data-braco="sim">sim</button>
    <button data-braco="parcial">parcial</button>
    <button data-braco="nao">não</button>
    <button data-braco="?">?</button>
    <span class="msg" id="msg"></span>
  </div>
</header>
<main>
  <div class="lista" id="lista"></div>
  <div class="quadro" id="quadro"><img id="img" alt="quadro"><svg id="svg"></svg></div>
  <div class="grupo" id="bloco-trastes"></div>
  <div class="grupo">
    <label>observação<br><input type="text" id="obs" maxlength="500"></label>
  </div>
</main>
<script>
let estado = null;
let idx = 0;
let modo = null;
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";

function atual() { return estado.indice[idx]; }
function visao() { return estado.quadros[atual().id]; }

function msg(texto, erro) {
  const el = $("msg");
  el.textContent = texto;
  el.className = erro ? "msg erro" : "msg";
}

async function carregar() {
  try {
    const r = await fetch("/estado.json");
    estado = await r.json();
    render();
  } catch (e) {
    msg("não consegui ler o estado: " + e, true);
  }
}

async function enviar(corpo) {
  try {
    const r = await fetch("/responder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    const d = await r.json();
    if (!d.ok) { msg(d.erro, true); return; }
    estado.quadros = d.quadros;
    estado.completos = d.completos;
    estado.concluidos = d.concluidos;
    msg("gravado às " + d.salvo_em, false);
    render();
  } catch (e) {
    msg("falha ao gravar: " + e, true);
  }
}

function linha(x1, y1, x2, y2, cor, largura) {
  const l = document.createElementNS(NS, "line");
  l.setAttribute("x1", x1); l.setAttribute("y1", y1);
  l.setAttribute("x2", x2); l.setAttribute("y2", y2);
  l.setAttribute("stroke", cor); l.setAttribute("stroke-width", largura);
  return l;
}

function ponto(x, y, raio, cor, borda) {
  const c = document.createElementNS(NS, "circle");
  c.setAttribute("cx", x); c.setAttribute("cy", y); c.setAttribute("r", raio);
  c.setAttribute("fill", cor); c.setAttribute("stroke", borda || "none");
  c.setAttribute("stroke-width", raio * 0.3);
  return c;
}

function texto(x, y, conteudo, tamanho, cor) {
  const t = document.createElementNS(NS, "text");
  t.setAttribute("x", x); t.setAttribute("y", y);
  t.setAttribute("font-size", tamanho); t.setAttribute("fill", cor);
  t.setAttribute("stroke", "#000"); t.setAttribute("stroke-width", tamanho * 0.12);
  t.setAttribute("paint-order", "stroke");
  t.textContent = conteudo;
  return t;
}

function desenhar() {
  const q = atual();
  const r = visao().registro;
  const svg = $("svg");
  svg.innerHTML = "";
  svg.setAttribute("viewBox", "0 0 " + q.largura + " " + q.altura);
  const w = q.largura;
  const espessura = w * 0.0035;
  const raio = w * 0.006;
  const fonte = w * 0.02;
  const c1 = r.corda1 || [];
  const c6 = r.corda6 || [];
  if (c1.length === 2) svg.appendChild(linha(c1[0][0], c1[0][1], c1[1][0], c1[1][1], "#2ecc71", espessura));
  if (c6.length === 2) svg.appendChild(linha(c6[0][0], c6[0][1], c6[1][0], c6[1][1], "#ff8c1a", espessura));
  c1.forEach((p) => svg.appendChild(ponto(p[0], p[1], raio, "#2ecc71", "#000")));
  c6.forEach((p) => svg.appendChild(ponto(p[0], p[1], raio, "#ff8c1a", "#000")));
  let ux = 1, uy = 0;
  if (c1.length === 2) {
    const dx = c1[1][0] - c1[0][0], dy = c1[1][1] - c1[0][1];
    const n = Math.hypot(dx, dy);
    if (n > 0) { ux = dx / n; uy = dy / n; }
  }
  const px = -uy, py = ux;
  const meio = w * 0.03;
  visao().numeracao.forEach((item) => {
    const [x, y] = item.ponto;
    if (c1.length === 2) {
      svg.appendChild(linha(x + px * meio, y + py * meio, x - px * meio, y - py * meio, "#ffe066", espessura * 0.7));
    }
    svg.appendChild(ponto(x, y, raio * 0.6, "#ffe066", "#000"));
    const rotulo = item.numero === null ? "?" : String(item.numero);
    svg.appendChild(texto(x + meio * 0.5, y - meio * 0.5, rotulo, fonte, "#ffe066"));
  });
  if (Array.isArray(r.nut)) {
    const [x, y] = r.nut;
    svg.appendChild(ponto(x, y, raio * 1.6, "#ffffff", "#000"));
    svg.appendChild(texto(x + raio * 2, y - raio * 2, "nut", fonte, "#ffffff"));
  } else if (r.nut === "fora") {
    svg.appendChild(texto(w * 0.01, w * 0.03, "nut fora", fonte, "#ffffff"));
  }
}

function blocoTrastes() {
  const box = $("bloco-trastes");
  box.innerHTML = "";
  const v = visao();
  const r = v.registro;
  const lista = document.createElement("ol");
  lista.className = "trastes";
  v.numeracao.forEach((item) => {
    const li = document.createElement("li");
    const n = item.numero === null ? "sem número" : "traste " + item.numero;
    li.textContent = n + " em (" + item.ponto[0] + ", " + item.ponto[1] + ")";
    lista.appendChild(li);
  });
  box.appendChild(lista);
  if (r.nut === "fora" && v.numeracao.length) {
    const seletor = document.createElement("select");
    v.numeracao.forEach((item, k) => {
      const op = document.createElement("option");
      op.value = String(k);
      op.textContent = "clique " + (k + 1) + " (" + item.ponto[0] + ", " + item.ponto[1] + ")";
      seletor.appendChild(op);
    });
    const numero = document.createElement("input");
    numero.type = "number"; numero.min = "1"; numero.max = "30"; numero.value = "1";
    const botao = document.createElement("button");
    botao.textContent = "definir como traste de referência";
    botao.addEventListener("click", () => {
      const k = Number(seletor.value);
      const n = Number(numero.value);
      enviar({ quadro: atual().id, campo: "traste_referencia",
               valor: { ponto: v.numeracao[k].ponto, numero: n } });
    });
    const limpar = document.createElement("button");
    limpar.textContent = "tirar referência";
    limpar.addEventListener("click", () => {
      enviar({ quadro: atual().id, campo: "traste_referencia", valor: null });
    });
    const p = document.createElement("p");
    const ref = r.traste_referencia;
    p.textContent = ref ? "referência atual: traste " + ref.numero + " em (" + ref.ponto[0] + ", " + ref.ponto[1] + ")" : "sem referência de traste";
    box.appendChild(p);
    box.appendChild(seletor);
    box.appendChild(document.createTextNode(" é o traste "));
    box.appendChild(numero);
    box.appendChild(document.createTextNode(" "));
    box.appendChild(botao);
    box.appendChild(document.createTextNode(" "));
    box.appendChild(limpar);
  }
}

function render() {
  if (!estado || !estado.indice.length) return;
  const q = atual();
  $("pos").textContent = (idx + 1) + "/" + estado.indice.length + " (" + q.id + ", " + q.canal + ")";
  $("prog").textContent = estado.concluidos + "/" + estado.total + " completos";
  const img = $("img");
  const destino = "/" + q.png;
  if (img.getAttribute("src") !== destino) {
    // Até a imagem nova carregar, a antiga some e o clique é recusado: senão o ponto
    // cairia no quadro anterior com a escala errada.
    img.style.visibility = "hidden";
    img.setAttribute("src", destino);
  }
  const lista = $("lista");
  lista.innerHTML = "";
  estado.indice.forEach((item, k) => {
    const b = document.createElement("button");
    b.textContent = item.id;
    if (estado.completos.indexOf(item.id) >= 0) b.classList.add("feito");
    if (k === idx) b.classList.add("ativo");
    b.addEventListener("click", () => { idx = k; render(); });
    lista.appendChild(b);
  });
  document.querySelectorAll("[data-modo]").forEach((b) => {
    b.classList.toggle("ativo", b.dataset.modo === modo);
  });
  const r = visao().registro;
  document.querySelectorAll("[data-braco]").forEach((b) => {
    b.classList.toggle("ativo", b.dataset.braco === r.braco);
  });
  $("ant").disabled = idx === 0;
  $("prox").disabled = idx === estado.indice.length - 1;
  $("desfazer").disabled = !r.desfazer_disponivel;
  const obs = $("obs");
  if (document.activeElement !== obs) obs.value = r.obs || "";
  desenhar();
  blocoTrastes();
}

function trocar(delta) {
  const novo = idx + delta;
  if (novo < 0 || novo >= estado.indice.length) return;
  idx = novo;
  render();
}

function definirModo(m) {
  modo = modo === m ? null : m;
  msg(modo ? "modo: " + modo + " (clique na imagem)" : "sem modo de clique", false);
  render();
}

$("img").addEventListener("load", () => { $("img").style.visibility = "visible"; });

$("img").addEventListener("click", (ev) => {
  if (!estado) return;
  const img = $("img");
  if (!img.complete || img.style.visibility === "hidden") {
    msg("a imagem ainda está carregando; clique de novo em seguida", true);
    return;
  }
  const bb = img.getBoundingClientRect();
  const x = ev.clientX - bb.left;
  const y = ev.clientY - bb.top;
  if (x < 0 || y < 0 || x > bb.width || y > bb.height) return;
  if (!modo) { msg("escolha um modo (1, 6, n ou t) antes de clicar", true); return; }
  const escala = bb.width / img.naturalWidth;
  enviar({ quadro: atual().id, acao: "clique", modo: modo, ponto_img: [x, y], escala: escala });
});

document.querySelectorAll("[data-modo]").forEach((b) => {
  b.addEventListener("click", () => definirModo(b.dataset.modo));
});
document.querySelectorAll("[data-braco]").forEach((b) => {
  b.addEventListener("click", () => {
    enviar({ quadro: atual().id, campo: "braco", valor: b.dataset.braco });
  });
});
$("fora").addEventListener("click", () => {
  enviar({ quadro: atual().id, campo: "nut", valor: "fora" });
});
$("desfazer").addEventListener("click", () => {
  enviar({ quadro: atual().id, acao: "desfazer" });
});
$("ant").addEventListener("click", () => trocar(-1));
$("prox").addEventListener("click", () => trocar(1));
$("obs").addEventListener("change", (ev) => {
  enviar({ quadro: atual().id, campo: "obs", valor: ev.target.value });
});

document.addEventListener("keydown", (ev) => {
  const alvo = ev.target.tagName;
  if (alvo === "INPUT" || alvo === "SELECT" || alvo === "TEXTAREA") return;
  if (ev.key === "ArrowLeft") trocar(-1);
  else if (ev.key === "ArrowRight") trocar(1);
  else if (ev.key === "1") definirModo("corda1");
  else if (ev.key === "6") definirModo("corda6");
  else if (ev.key === "n") definirModo("nut");
  else if (ev.key === "t") definirModo("trastes");
  else if (ev.key === "f") enviar({ quadro: atual().id, campo: "nut", valor: "fora" });
});

carregar();
</script>
</body>
</html>
"""


def servir(pasta: Path, ouro: Path, porta: int, host: str) -> int:
    """Sobe o servidor e fica nele até Ctrl+C.

    Args:
        pasta: pasta do ``preparar`` (``indice.json`` e ``quadros/``).
        ouro: gabarito do braço (já criado pelo ``preparar``).
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
        print(f"{ouro} não está no formato {FORMATO_GABARITO}", file=sys.stderr)
        return 2
    servidor = criar_servidor(pasta, ouro, porta, host)
    print(f"ferramenta do braço: http://127.0.0.1:{servidor.server_address[1]}/")
    print(f"escutando em {host}; cada resposta é gravada em: {ouro}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


# ---------------------------------------------------------------------------------
# Folha de conferência
# ---------------------------------------------------------------------------------


def montar_folha(pasta: Path, saida: Path, colunas: int = 5) -> int:
    """Folha numerada com as miniaturas da amostra, para conferência a olho.

    Args:
        pasta: pasta do ``preparar`` (``indice.json`` e ``quadros/``).
        saida: arquivo JPEG de saída.
        colunas: miniaturas por linha.

    Returns:
        Quantas miniaturas entraram na folha.
    """
    itens = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))["quadros"]
    celula_w, celula_h = 384, 216
    linhas = math.ceil(len(itens) / colunas)
    folha = np.zeros((linhas * celula_h, colunas * celula_w, 3), dtype=np.uint8)
    for k, item in enumerate(itens):
        imagem = cv2.imread(str(pasta / item["png"]))
        if imagem is None:
            raise ValueError(f"imagem ilegível: {item['png']}")
        escala = min(celula_w / imagem.shape[1], celula_h / imagem.shape[0])
        miniatura = cv2.resize(
            imagem, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA
        )
        y0 = (k // colunas) * celula_h
        x0 = (k % colunas) * celula_w
        h, w = miniatura.shape[:2]
        folha[y0 : y0 + h, x0 : x0 + w] = miniatura
        rotulo = f"{item['id']} {'MVP' if item['mvp'] else ''}".strip()
        cv2.rectangle(folha, (x0, y0), (x0 + 74, y0 + 26), (0, 0, 0), -1)
        cv2.putText(
            folha,
            rotulo,
            (x0 + 6, y0 + 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )
    saida.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(saida), folha, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return len(itens)


def main() -> int:
    """Ponto de entrada: ``preparar``, ``servir`` e ``folha``.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    p = sub.add_parser(
        "preparar", help="sorteia a amostra, copia os quadros e o gabarito"
    )
    p.add_argument("--censo", type=Path, default=CENSO_MAOS)
    p.add_argument("--cache", type=Path, default=cache_quadros())
    p.add_argument("--pasta", type=Path, default=MAOS_M3B)
    p.add_argument("--ouro", type=Path, default=GABARITO_BRACO)
    p.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    s = sub.add_parser("servir", help="serve a ferramenta (grava a cada clique)")
    s.add_argument("--pasta", type=Path, default=MAOS_M3B)
    s.add_argument("--ouro", type=Path, default=GABARITO_BRACO)
    s.add_argument("--porta", type=int, default=8098)
    s.add_argument("--host", default="127.0.0.1")
    f = sub.add_parser("folha", help="folha numerada com as miniaturas")
    f.add_argument("--pasta", type=Path, default=MAOS_M3B)
    f.add_argument("--saida", type=Path, default=MAOS_M3B / "folha.jpg")
    args = ap.parse_args()
    if args.comando == "preparar":
        try:
            total = preparar(
                args.censo, args.cache, args.pasta, args.ouro, args.semente
            )
        except (ValueError, FileNotFoundError) as erro:
            print(f"não preparou: {erro}", file=sys.stderr)
            return 2
        print(f"{total} quadros em {args.pasta}; gabarito em {args.ouro}")
        return 0
    if args.comando == "folha":
        total = montar_folha(args.pasta, args.saida)
        print(f"folha com {total} miniaturas em {args.saida}")
        return 0
    return servir(args.pasta, args.ouro, args.porta, args.host)


if __name__ == "__main__":
    sys.exit(main())
