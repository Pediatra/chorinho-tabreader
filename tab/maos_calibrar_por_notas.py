"""Calibração do braço pelas notas da tablatura, sem olhar as linhas (M3c).

Ideia: a tablatura do produto diz, para cada nota, a corda, a casa e o instante
``t_ini``. O detector de mãos (passo ``tab.maos_pontas_notas``) diz onde estão as
pontas dos dedos da mão esquerda nesse instante. A nota pisada está debaixo de uma das
pontas. Centenas de notas dão centenas de correspondências "(corda, casa) <-> ponta",
e disso sai a homografia H que leva as coordenadas do braço para pixels.

Coordenadas do braço, no plano do braço:

- ``u``: posição física na casa ``k``, a ``FRACAO_PISADA`` (70 %) do caminho do traste
  ``k-1`` ao traste ``k``. Traste ``n`` em ``1 - 2^(-n/12)``, nut em 0;
- ``v = (corda - 1) / 5``: corda 1 (mi agudo) em 0, corda 6 (mi grave) em 1.

Ponto da nota em pixel: ``H . (u, v, 1)``. H é ajustada por RANSAC: amostra 4 notas
em posição geral, uma ponta candidata para cada, DLT normalizada (Hartley). Uma nota é
inlier se alguma ponta candidata está a menos de ``FATOR_TOLERANCIA`` vezes a largura
prevista da casa naquele ponto (medida pela própria H). Depois, refino por mínimos
quadrados (DLT) nos inliers, cada um com a ponta mais perto.

Só numpy e stdlib: o módulo não importa cv2, rtmlib nem o detector, para que os
testes do gate rodem sem GPU e sem acervo. O CLI (``main``) é que lê o vídeo e grava.

Uso::

    python -m tab.maos_calibrar_por_notas
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import GABARITO_DEDOS, MAOS_M3, MVP, acervo
from .maos_avaliar_dedos import carregar_json, montar_predicao
from .maos_braco import (
    FRACAO_PISADA,
    N_TRASTES,
    alvo_da_nota,
    dedo_mais_perto,
    escolher_mao_esquerda,
    pontas_da_mao,
    votar,
)

#: Pasta do passo 1 e do passo 2 (visível no host).
PASTA = MAOS_M3.parent / "m3c"

#: Pontas por instante (quadro em ``t_ini``), das notas pisadas do MVP.
PONTAS = PASTA / "pontas_mvp.json"

#: Pontas do quadro em ``t_ini - 0,1`` e ``t_ini + 0,1`` (o voto do M3).
PONTAS_ANT = PASTA / "pontas_mvp_ant.json"
PONTAS_DEP = PASTA / "pontas_mvp_dep.json"

#: Calibração fixa do M3 (feita à mão sobre a imagem), para comparar.
BRACO_FIXO = MAOS_M3 / "braco.json"

#: Vídeo do M3 dentro do acervo montado.
VIDEO = acervo() / "sky guitar" / "retrato brasileiro - tab & lesson.mp4"

#: Semente oficial do projeto; é a que produz as tabelas do relatório.
SEMENTE_OFICIAL = 20261012

#: Três sementes para medir a estabilidade do RANSAC.
SEMENTES = (SEMENTE_OFICIAL, 7, 31337)

#: Iterações do RANSAC (amostras de 4 notas).
ITERACOES = 20000

#: Quantas vezes refazer o ajuste nos inliers.
REFINOS = 3

#: Tolerância: fração da largura prevista da casa que conta como acerto.
FATOR_TOLERANCIA = 0.5

#: Deslocamento, em segundos, dos quadros do voto.
DESLOCAMENTO_VOTO = 0.1

#: Área mínima (em u, v) de um triângulo de 3 notas; abaixo disso há colinearidade.
TOLERANCIA_AREA = 1e-4


def s_traste(n: int) -> float:
    """Posição, no plano do braço, do traste ``n`` (nut em 0).

    Args:
        n: número do traste, de 0 (nut) para cima.

    Returns:
        ``1 - 2^(-n/12)``, com o comprimento do braço igual a 1.
    """
    return 1.0 - 2.0 ** (-n / 12.0)


#: Posição de cada traste de 0 a ``N_TRASTES`` no plano do braço.
S_TRASTES = np.array([s_traste(n) for n in range(N_TRASTES + 1)])


def u_casa(casa: int, frac: float = FRACAO_PISADA) -> float:
    """Coordenada ``u`` onde o dedo pisa a casa: ``frac`` do caminho até o traste.

    Args:
        casa: casa da nota, de 1 em diante (a casa 0 é corda solta, sem ponto).
        frac: fração do caminho, do traste ``casa-1`` ao traste ``casa``.

    Returns:
        ``s(casa-1) + frac * (s(casa) - s(casa-1))``.

    Raises:
        ValueError: se a casa é menor que 1 ou maior que ``N_TRASTES``.
    """
    if casa < 1 or casa > N_TRASTES:
        raise ValueError(f"casa {casa} fora de 1..{N_TRASTES}")
    antes = s_traste(casa - 1)
    depois = s_traste(casa)
    return antes + frac * (depois - antes)


def v_corda(corda: int) -> float:
    """Coordenada ``v`` da corda: 0 para a corda 1 (aguda), 1 para a corda 6.

    Args:
        corda: número da corda, de 1 a 6.

    Returns:
        ``(corda - 1) / 5``.

    Raises:
        ValueError: se a corda não está em 1..6.
    """
    if not 1 <= corda <= 6:
        raise ValueError(f"corda {corda} fora de 1..6")
    return (corda - 1) / 5.0


def coordenadas_do_braco(corda: int, casa: int) -> tuple[float, float]:
    """Coordenadas ``(u, v)`` no plano do braço de uma nota pisada.

    Args:
        corda: número da corda, de 1 a 6.
        casa: casa da nota, de 1 a ``N_TRASTES``.

    Returns:
        ``(u, v)``.
    """
    return u_casa(casa), v_corda(corda)


def aplicar_homografia(H: np.ndarray, pontos: np.ndarray) -> np.ndarray:
    """Leva pontos ``(N, 2)`` pela homografia ``H`` (3 x 3).

    Args:
        H: homografia que leva o plano do braço para pixels.
        pontos: ``(N, 2)`` de coordenadas no plano.

    Returns:
        ``(N, 2)`` de pixels. Pode ter ``inf`` ou ``nan`` onde o denominador é zero.
    """
    pontos = np.asarray(pontos, dtype=float).reshape(-1, 2)
    homog = np.column_stack([pontos, np.ones(len(pontos))])
    with np.errstate(divide="ignore", invalid="ignore"):
        proj = homog @ H.T
        return proj[:, :2] / proj[:, 2:3]


def _normalizacao(pontos: np.ndarray) -> np.ndarray:
    """Matriz de normalização de Hartley: centróide na origem, distância média sqrt(2).

    Args:
        pontos: ``(N, 2)`` com ``N >= 1``.

    Returns:
        Matriz 3 x 3 ``T`` tal que ``T @ [x, y, 1]`` tem a escala de Hartley.
    """
    centro = pontos.mean(axis=0)
    media = float(np.mean(np.linalg.norm(pontos - centro, axis=1)))
    escala = np.sqrt(2.0) / media if media > 0 else 1.0
    return np.array(
        [
            [escala, 0.0, -escala * centro[0]],
            [0.0, escala, -escala * centro[1]],
            [0.0, 0.0, 1.0],
        ]
    )


def dlt_homografia(origem: np.ndarray, destino: np.ndarray) -> np.ndarray:
    """Homografia por DLT normalizada (Hartley), com ``N >= 4`` correspondências.

    Args:
        origem: ``(N, 2)`` pontos no plano do braço.
        destino: ``(N, 2)`` pontos correspondentes em pixels.

    Returns:
        Homografia 3 x 3 com ``H[2, 2] = 1`` (ou normalizada pela norma se ``H[2, 2]``
        é quase zero).

    Raises:
        ValueError: se há menos de 4 correspondências.
    """
    origem = np.asarray(origem, dtype=float)
    destino = np.asarray(destino, dtype=float)
    if len(origem) < 4 or len(origem) != len(destino):
        raise ValueError("DLT precisa de pelo menos 4 correspondências pareadas")
    t1 = _normalizacao(origem)
    t2 = _normalizacao(destino)
    o = (t1 @ np.column_stack([origem, np.ones(len(origem))]).T).T
    d = (t2 @ np.column_stack([destino, np.ones(len(destino))]).T).T
    linhas = []
    for (x, y, _), (xp, yp, _) in zip(o, d, strict=True):
        linhas.append([-x, -y, -1.0, 0.0, 0.0, 0.0, xp * x, xp * y, xp])
        linhas.append([0.0, 0.0, 0.0, -x, -y, -1.0, yp * x, yp * y, yp])
    _, _, vt = np.linalg.svd(np.asarray(linhas))
    h = vt[-1].reshape(3, 3)
    H = np.linalg.inv(t2) @ h @ t1
    if abs(H[2, 2]) > 1e-12:
        return H / H[2, 2]
    return H / np.linalg.norm(H)


@dataclass(frozen=True)
class Conjunto:
    """Notas com as pontas candidatas do seu instante, em arrays.

    Attributes:
        indices: ``indice_mvp`` de cada nota.
        corda: número da corda de cada nota.
        casa: casa de cada nota (sempre maior que 0).
        t: instante ``t_ini`` de cada nota.
        uv: ``(N, 2)`` coordenadas no plano do braço.
        cand: ``(N, P, 2)`` pontas candidatas (preenchidas com 0 onde não há).
        mascara: ``(N, P)`` bool, ``True`` onde a ponta candidata existe.
    """

    indices: np.ndarray
    corda: np.ndarray
    casa: np.ndarray
    t: np.ndarray
    uv: np.ndarray
    cand: np.ndarray
    mascara: np.ndarray

    @property
    def tem_candidato(self) -> np.ndarray:
        """``(N,)`` bool: a nota tem pelo menos uma ponta candidata no instante.

        Returns:
            Máscara das notas que podem ser inliers.
        """
        return self.mascara.any(axis=1)


def pontas_esquerdas(maos: list[dict[str, Any]]) -> np.ndarray:
    """Pontas dos dedos 1 a 4 de todas as mãos esquerdas de um quadro.

    Args:
        maos: mãos do quadro (registros de ``tab.maos_pontas_notas``), com ``lado`` e
            ``pts``.

    Returns:
        ``(P, 2)`` de pontas; ``(0, 2)`` se não há mão esquerda.
    """
    pontos = [
        ponto
        for mao in maos
        if mao["lado"] == "esquerda"
        for ponto in pontas_da_mao(mao).values()
    ]
    return np.asarray(pontos, dtype=float).reshape(-1, 2)


def montar_conjunto(
    mvp: list[dict[str, Any]],
    maos_por_t: dict[float, list[dict[str, Any]]],
    excluir: frozenset[float] = frozenset(),
) -> Conjunto:
    """Notas pisadas do MVP com as pontas do seu instante, para o RANSAC.

    Usa só as notas com ``casa > 0`` e ``t_ini`` presente no mapa de pontas. Instantes
    em ``excluir`` (arredondados a 3 casas) saem: é o teste de honestidade com os
    instantes do gabarito fora da calibração.

    Args:
        mvp: lista ``notas`` do MVP.
        maos_por_t: ``t_ini`` (3 casas) -> mãos do quadro daquele instante.
        excluir: instantes que não entram na calibração.

    Returns:
        O :class:`Conjunto`. Notas sem mão esquerda ficam, com máscara vazia.

    Raises:
        ValueError: se o conjunto fica vazio.
    """
    linhas: list[tuple[int, int, int, float, np.ndarray]] = []
    for indice, nota in enumerate(mvp):
        t = nota.get("t_ini")
        if t is None or nota["casa"] <= 0:
            continue
        chave = round(float(t), 3)
        if chave in excluir or chave not in maos_por_t:
            continue
        pontas = pontas_esquerdas(maos_por_t[chave])
        linhas.append((indice, nota["corda"], nota["casa"], chave, pontas))
    if not linhas:
        raise ValueError("nenhuma nota pisada com pontas para calibrar")
    p_max = max(max(len(p) for *_, p in linhas), 1)
    n = len(linhas)
    cand = np.zeros((n, p_max, 2))
    mascara = np.zeros((n, p_max), dtype=bool)
    for i, (_, _, _, _, pontas) in enumerate(linhas):
        cand[i, : len(pontas)] = pontas
        mascara[i, : len(pontas)] = True
    corda = np.array([x[1] for x in linhas])
    casa = np.array([x[2] for x in linhas])
    uv = np.array(
        [coordenadas_do_braco(c, k) for c, k in zip(corda, casa, strict=True)]
    )
    return Conjunto(
        indices=np.array([x[0] for x in linhas]),
        corda=corda,
        casa=casa,
        t=np.array([x[3] for x in linhas]),
        uv=uv,
        cand=cand,
        mascara=mascara,
    )


def largura_casa(H: np.ndarray, casa: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Largura prevista, em px, de cada casa na altura ``v`` da nota (medida pela H).

    Args:
        H: homografia calibrada.
        casa: ``(N,)`` casas.
        v: ``(N,)`` coordenadas ``v`` das notas.

    Returns:
        ``(N,)`` distâncias, em px, entre o traste ``casa-1`` e o traste ``casa``.
    """
    a = aplicar_homografia(H, np.column_stack([S_TRASTES[casa - 1], v]))
    b = aplicar_homografia(H, np.column_stack([S_TRASTES[casa], v]))
    return np.linalg.norm(b - a, axis=1)


def avaliar(H: np.ndarray, c: Conjunto) -> dict[str, Any]:
    """Inliers de uma homografia e a ponta candidata mais perto de cada nota.

    Uma nota é inlier se a ponta candidata mais perto do ponto previsto está a menos
    de ``FATOR_TOLERANCIA`` vezes a largura prevista da casa naquele ponto. Uma H que
    manda notas para os dois lados do plano (denominador de sinal trocado) não conta.

    Args:
        H: homografia a avaliar.
        c: conjunto de notas.

    Returns:
        ``n`` (quantos inliers), ``inliers`` (``(N,)`` bool) e ``perto`` (``(N,)`` índice
        da ponta candidata mais perto).
    """
    n = len(c.indices)
    vazio = {"n": 0, "inliers": np.zeros(n, dtype=bool), "perto": np.zeros(n, int)}
    if not np.all(np.isfinite(H)):
        return vazio
    w = np.column_stack([c.uv, np.ones(n)]) @ H[2]
    if not (np.all(w > 0) or np.all(w < 0)):
        return vazio
    pred = aplicar_homografia(H, c.uv)
    dist = np.linalg.norm(c.cand - pred[:, None, :], axis=2)
    dist = np.where(c.mascara, dist, np.inf)
    perto = np.argmin(dist, axis=1)
    dmin = dist[np.arange(n), perto]
    tau = FATOR_TOLERANCIA * largura_casa(H, c.casa, c.uv[:, 1])
    inliers = np.isfinite(dmin) & (dmin < tau) & c.tem_candidato
    return {"n": int(inliers.sum()), "inliers": inliers, "perto": perto}


def _posicao_geral(c: Conjunto, amostra: list[int]) -> bool:
    """A amostra de 4 notas serve para uma homografia: duas cordas, duas casas, sem
    três colineares no plano do braço.

    Args:
        c: conjunto de notas.
        amostra: 4 índices de nota.

    Returns:
        ``True`` se a amostra está em posição geral.
    """
    if len(set(c.corda[amostra])) < 2 or len(set(c.casa[amostra])) < 2:
        return False
    uv = c.uv[amostra]
    for a, b, d in itertools.combinations(range(4), 3):
        ux, uy = uv[b] - uv[a]
        vx, vy = uv[d] - uv[a]
        if abs(ux * vy - uy * vx) < TOLERANCIA_AREA:
            return False
    return True


def ransac(
    c: Conjunto,
    semente: int,
    iteracoes: int = ITERACOES,
    refinos: int = REFINOS,
) -> dict[str, Any]:
    """Homografia por RANSAC, com refino nos inliers. Determinístico pela semente.

    Args:
        c: conjunto de notas com pelo menos 4 notas que têm ponta candidata.
        semente: semente do ``random.Random`` injetado.
        iteracoes: amostras de 4 notas a tentar.
        refinos: quantas vezes refazer a DLT sobre os inliers.

    Returns:
        ``H`` (3 x 3), ``inliers`` (quantos), ``mascara`` (``(N,)`` bool), ``descartadas``
        (amostras sem posição geral), ``semente``, ``iteracoes``, ``elegiveis``.

    Raises:
        ValueError: se há menos de 4 notas com ponta candidata.
        RuntimeError: se nenhuma hipótese foi montada.
    """
    rng = random.Random(semente)
    elegiveis = [int(i) for i in np.flatnonzero(c.tem_candidato)]
    if len(elegiveis) < 4:
        raise ValueError(f"{len(elegiveis)} notas com ponta; precisa de 4")
    melhor_n = -1
    melhor_H: np.ndarray | None = None
    descartadas = 0
    for _ in range(iteracoes):
        amostra = rng.sample(elegiveis, 4)
        if not _posicao_geral(c, amostra):
            descartadas += 1
            continue
        escolhas = [
            int(rng.choice(list(np.flatnonzero(c.mascara[i])))) for i in amostra
        ]
        destinos = c.cand[amostra, escolhas]
        H = dlt_homografia(c.uv[amostra], destinos)
        n = avaliar(H, c)["n"]
        if n > melhor_n:
            melhor_n, melhor_H = n, H
    if melhor_H is None:
        raise RuntimeError("RANSAC: nenhuma amostra em posição geral")
    H = melhor_H
    for _ in range(refinos):
        resultado = avaliar(H, c)
        inl = resultado["inliers"]
        if int(inl.sum()) < 4:
            break
        destinos = c.cand[np.flatnonzero(inl), resultado["perto"][inl]]
        H = dlt_homografia(c.uv[inl], destinos)
    final = avaliar(H, c)
    return {
        "H": H,
        "inliers": final["n"],
        "mascara": final["inliers"],
        "descartadas": descartadas,
        "semente": semente,
        "iteracoes": iteracoes,
        "elegiveis": len(elegiveis),
    }


def grade_do_braco(H: np.ndarray) -> np.ndarray:
    """Pontos de uma grade do braço (cordas e trastes 0 a 12) em pixels.

    Args:
        H: homografia calibrada.

    Returns:
        ``(N, 2)`` de pixels, em amostras ao longo de cada corda e traste.
    """
    us = np.linspace(0.0, S_TRASTES[12], 13)
    vs = np.linspace(0.0, 1.0, 6)
    pontos = np.array([(u, v) for u in us for v in vs])
    return aplicar_homografia(H, pontos)


def diferenca_entre_h(h1: np.ndarray, h2: np.ndarray) -> dict[str, float]:
    """Diferença, em px, que duas homografias dão sobre a grade do braço.

    Args:
        h1: primeira homografia.
        h2: segunda homografia.

    Returns:
        ``mediana_px`` e ``maximo_px`` da distância entre as duas projeções.
    """
    d = np.linalg.norm(grade_do_braco(h1) - grade_do_braco(h2), axis=1)
    return {"mediana_px": float(np.median(d)), "maximo_px": float(np.max(d))}


def estatisticas(valores: list[float]) -> dict[str, float]:
    """Mediana, percentil 90 e máximo de uma lista de números.

    Args:
        valores: números, não vazios.

    Returns:
        Dicionário com ``mediana``, ``p90`` e ``maximo``, arredondados a 4 casas.
    """
    v = np.asarray(valores, dtype=float)
    return {
        "mediana": round(float(np.median(v)), 4),
        "p90": round(float(np.percentile(v, 90)), 4),
        "maximo": round(float(np.max(v)), 4),
    }


def comparar_com_fixa(H: np.ndarray, braco: dict[str, Any]) -> list[dict[str, Any]]:
    """Ponto previsto por H e pela calibração fixa, para cada corda 1-6 e casa 1-12.

    O ponto fixo é o de :func:`tab.maos_braco.alvo_da_nota` com ``braco.json``, a mesma
    convenção (70 % do caminho). A largura de referência é a da calibração fixa.

    Args:
        H: homografia calibrada.
        braco: conteúdo de ``braco.json`` (``cordas`` e ``trastes``).

    Returns:
        Uma linha por (corda, casa): ``corda``, ``casa``, ``erro_px`` (distância entre os
        dois pontos) e ``fracao`` (erro dividido pela largura fixa da casa).
    """
    cordas = {c["corda"]: {"a": c["a"], "b": c["b"]} for c in braco["cordas"]}
    trastes = {int(k): v for k, v in braco["trastes"].items()}
    linhas = []
    for corda in range(1, 7):
        for casa in range(1, 13):
            fixo = np.asarray(alvo_da_nota(corda, casa, cordas, trastes))
            previsto = aplicar_homografia(
                H, np.array([coordenadas_do_braco(corda, casa)])
            )[0]
            largura = abs(trastes[casa - 1]["x"] - trastes[casa]["x"])
            erro = float(np.linalg.norm(previsto - fixo))
            linhas.append(
                {
                    "corda": corda,
                    "casa": casa,
                    "erro_px": erro,
                    "fracao": erro / largura,
                }
            )
    return linhas


def decidir_dedo(
    H: np.ndarray, corda: int, casa: int, maos: list[dict[str, Any]]
) -> str | None:
    """Dedo da esquerda pela calibração: a ponta mais perto do ponto previsto por H.

    Segue o M3: corda solta é ``"0"``; senão, a mão esquerda da câmera do braço
    (:func:`tab.maos_braco.escolher_mao_esquerda`) e a ponta mais perto do alvo.

    Args:
        H: homografia calibrada.
        corda: número da corda, de 1 a 6.
        casa: casa da nota (0 é corda solta).
        maos: mãos do quadro em ``t_ini``.

    Returns:
        ``"0"`` a ``"4"``, ou ``None`` se não há mão esquerda na câmera do braço.
    """
    if casa == 0:
        return "0"
    mao = escolher_mao_esquerda(maos)
    if mao is None:
        return None
    alvo = aplicar_homografia(H, np.array([coordenadas_do_braco(corda, casa)]))[0]
    dedo, _, _ = dedo_mais_perto((float(alvo[0]), float(alvo[1])), pontas_da_mao(mao))
    return dedo


def decidir_voto(
    H: np.ndarray,
    corda: int,
    casa: int,
    maos_ant: list[dict[str, Any]],
    maos_meio: list[dict[str, Any]],
    maos_dep: list[dict[str, Any]],
) -> str | None:
    """Voto de ``decidir_dedo`` em ``t - 0,1``, ``t`` e ``t + 0,1``, como no M3.

    Args:
        H: homografia calibrada.
        corda: número da corda.
        casa: casa da nota.
        maos_ant: mãos no quadro de ``t - 0,1``.
        maos_meio: mãos no quadro de ``t``.
        maos_dep: mãos no quadro de ``t + 0,1``.

    Returns:
        A maioria; empate fica com o quadro central.
    """
    centro = decidir_dedo(H, corda, casa, maos_meio)
    if casa == 0:
        return "0"
    decisoes = [
        decidir_dedo(H, corda, casa, maos_ant),
        centro,
        decidir_dedo(H, corda, casa, maos_dep),
    ]
    return votar(decisoes, padrao=centro)


def mapa_de_maos(instantes: list[dict[str, Any]]) -> dict[float, list[dict[str, Any]]]:
    """Mãos por instante, a partir do JSON de pontas (chave ``t_ini`` arredondada).

    Args:
        instantes: lista ``instantes`` do JSON de pontas.

    Returns:
        ``t_ini`` (3 casas) -> lista de mãos.
    """
    return {round(float(r["t_ini"]), 3): r["maos"] for r in instantes}


def quadro_bgr(video: Path, instante: float) -> np.ndarray:
    """Um quadro do vídeo em BGR, lido pelo ffmpeg (AV1 não decodifica no OpenCV).

    Mesma leitura de ``tab.maos_visao_dedos.quadro_bgr``; repetida aqui para que este
    módulo não importe o detector (e o rtmlib).

    Args:
        video: arquivo de vídeo.
        instante: segundo do quadro.

    Returns:
        Quadro ``uint8`` em BGR.

    Raises:
        RuntimeError: se o quadro não decodifica.
    """
    bruto = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{max(instante, 0.0):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    quadro = cv2.imdecode(np.frombuffer(bruto, dtype=np.uint8), cv2.IMREAD_COLOR)
    if quadro is None:
        raise RuntimeError(f"quadro não decodificado em t={instante:.3f}")
    return quadro


def desenhar_grade(
    quadro: np.ndarray, H: np.ndarray, braco: dict[str, Any], pontas: np.ndarray
) -> np.ndarray:
    """Grade prevista por H (vermelho) e pela calibração fixa (verde), mais as pontas.

    Args:
        quadro: quadro BGR inteiro.
        H: homografia calibrada.
        braco: conteúdo de ``braco.json``.
        pontas: ``(P, 2)`` pontas das mãos esquerdas no quadro (azul).

    Returns:
        Cópia do quadro com as linhas e os pontos desenhados.
    """
    img = quadro.copy()
    vermelho, verde, azul = (0, 0, 255), (0, 255, 0), (255, 200, 0)
    us = np.linspace(0.0, S_TRASTES[12], 40)
    vs = np.linspace(0.0, 1.0, 40)
    for corda in range(1, 7):
        pts = aplicar_homografia(
            H, np.column_stack([us, np.full_like(us, v_corda(corda))])
        )
        cv2.polylines(img, [pts.astype(np.int32)], False, vermelho, 2)
    for k in range(0, 13):
        pts = aplicar_homografia(
            H, np.column_stack([np.full_like(vs, S_TRASTES[k]), vs])
        )
        cv2.polylines(img, [pts.astype(np.int32)], False, vermelho, 1)
    cordas = {c["corda"]: c for c in braco["cordas"]}
    xs = np.linspace(0, img.shape[1] - 1, 200)
    for corda in cordas.values():
        ys = corda["a"] + corda["b"] * xs
        cv2.polylines(
            img,
            [np.column_stack([xs, ys]).astype(np.int32)],
            False,
            verde,
            1,
        )
    for x, y in pontas:
        cv2.circle(img, (int(x), int(y)), 6, azul, -1)
    return img


def _decidir_gabarito(
    mvp: list[dict[str, Any]],
    gabarito: dict[str, Any],
    H: np.ndarray,
    maos_meio: dict[float, list[dict[str, Any]]],
    maos_ant: dict[float, list[dict[str, Any]]],
    maos_dep: dict[float, list[dict[str, Any]]],
) -> tuple[dict[int, tuple[str | None, None]], dict[int, tuple[str | None, None]]]:
    """Decisões de ponta e de voto para as notas do gabarito, uma por nota física.

    Args:
        mvp: lista ``notas`` do MVP.
        gabarito: JSON do gabarito de dedos.
        H: homografia calibrada.
        maos_meio: mãos em ``t_ini``.
        maos_ant: mãos em ``t_ini - 0,1``.
        maos_dep: mãos em ``t_ini + 0,1``.

    Returns:
        ``(ponta, voto)``: ``indice_mvp`` -> ``(esquerda, None)`` para cada método.
    """
    ponta: dict[int, tuple[str | None, None]] = {}
    voto: dict[int, tuple[str | None, None]] = {}
    for gnota in gabarito["notas"]:
        indice = gnota["indice_mvp"]
        if indice in ponta:
            continue
        nota = mvp[indice]
        corda, casa, t = nota["corda"], nota["casa"], round(float(nota["t_ini"]), 3)
        maos = maos_meio.get(t, [])
        ponta[indice] = (decidir_dedo(H, corda, casa, maos), None)
        voto[indice] = (
            decidir_voto(
                H,
                corda,
                casa,
                maos_ant.get(t, []),
                maos,
                maos_dep.get(t, []),
            ),
            None,
        )
    return ponta, voto


def _imprimir_estabilidade(resultados: list[dict[str, Any]]) -> None:
    """Imprime inliers por semente e a diferença das homografias entre sementes.

    Args:
        resultados: saída de :func:`ransac`, uma por semente.
    """
    for r in resultados:
        print(
            f"semente {r['semente']}: inliers {r['inliers']}/{r['elegiveis']}, "
            f"amostras descartadas {r['descartadas']}/{r['iteracoes']}"
        )
    for r in resultados[1:]:
        dif = diferenca_entre_h(resultados[0]["H"], r["H"])
        print(
            f"diferença H (semente {resultados[0]['semente']} vs {r['semente']}): "
            f"mediana {dif['mediana_px']:.2f} px, máxima {dif['maximo_px']:.2f} px"
        )


def main() -> None:
    """Calibra H pelas notas, mede contra o braço fixo e grava as predições do M3c."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mvp", type=Path, default=MVP)
    parser.add_argument("--gabarito", type=Path, default=GABARITO_DEDOS)
    parser.add_argument("--pasta", type=Path, default=PASTA)
    parser.add_argument("--sem-imagem", action="store_true")
    args = parser.parse_args()

    mvp = carregar_json(args.mvp)["notas"]
    gabarito = carregar_json(args.gabarito)
    braco = carregar_json(BRACO_FIXO)
    maos_meio = mapa_de_maos(carregar_json(PONTAS)["instantes"])
    maos_ant = mapa_de_maos(carregar_json(PONTAS_ANT)["instantes"])
    maos_dep = mapa_de_maos(carregar_json(PONTAS_DEP)["instantes"])
    gold_t = frozenset(round(float(n["t_ini"]), 3) for n in gabarito["notas"])

    conj = montar_conjunto(mvp, maos_meio)
    conj_excl = montar_conjunto(mvp, maos_meio, excluir=gold_t)
    pisadas = sum(1 for n in mvp if n.get("t_ini") is not None and n["casa"] > 0)
    instantes = len({round(float(t), 3) for t in conj.t})
    print(
        f"pisadas com tempo: {pisadas}; com pontas no instante: {len(conj.indices)} "
        f"({instantes} instantes)"
    )

    resultados = [ransac(conj, s) for s in SEMENTES]
    _imprimir_estabilidade(resultados)
    principal = resultados[0]
    H = principal["H"]
    com_mao = int(conj.tem_candidato.sum())
    print(
        f"inliers (semente oficial): {principal['inliers']}/{com_mao} notas com mão "
        f"esquerda; {principal['inliers']}/{pisadas} pisadas no MVP"
    )

    excl = ransac(conj_excl, SEMENTE_OFICIAL)
    print(
        f"sem os {len(gold_t)} instantes do gabarito: inliers {excl['inliers']}/"
        f"{len(conj_excl.indices)} notas; diferença H vs principal "
        f"{diferenca_entre_h(H, excl['H'])}"
    )

    ponta, voto = _decidir_gabarito(mvp, gabarito, H, maos_meio, maos_ant, maos_dep)
    ponta_x, voto_x = _decidir_gabarito(
        mvp, gabarito, excl["H"], maos_meio, maos_ant, maos_dep
    )
    args.pasta.mkdir(parents=True, exist_ok=True)
    predicoes = {
        "calib_notas_ponta": ponta,
        "calib_notas_voto": voto,
        "calib_notas_ponta_excl": ponta_x,
        "calib_notas_voto_excl": voto_x,
    }
    for nome, decisoes in predicoes.items():
        pred = montar_predicao(nome, decisoes)
        (args.pasta / f"pred_{nome}.json").write_text(
            json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    comparacao = comparar_com_fixa(H, braco)
    resumo = {
        "erro_px": estatisticas([c["erro_px"] for c in comparacao]),
        "fracao": estatisticas([c["fracao"] for c in comparacao]),
    }
    calibracao = {
        "convencao": "u = posicao dos 70 % da casa; v = (corda-1)/5",
        "H": H.tolist(),
        "H_sem_gabarito": excl["H"].tolist(),
        "inliers": principal["inliers"],
        "notas_com_pontas": len(conj.indices),
        "pisadas": pisadas,
        "estabilidade": [
            {"semente": r["semente"], "inliers": r["inliers"]} for r in resultados
        ],
        "contra_fixa": resumo,
        "contra_fixa_por_nota": comparacao,
    }
    (args.pasta / "calibracao.json").write_text(
        json.dumps(calibracao, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"contra a calibração fixa: erro {resumo['erro_px']} px; fração {resumo['fracao']}"
    )

    if not args.sem_imagem:
        por_instante: dict[float, int] = {}
        for t in conj.t.tolist():
            por_instante[t] = por_instante.get(t, 0) + 1
        t_img = max(por_instante, key=lambda t: (por_instante[t], -t))
        quadro = quadro_bgr(VIDEO, t_img)
        pontas = pontas_esquerdas(maos_meio.get(t_img, []))
        cv2.imwrite(
            str(args.pasta / "calibracao_mvp.jpg"),
            desenhar_grade(quadro, H, braco, pontas),
            [cv2.IMWRITE_JPEG_QUALITY, 90],
        )
        print(f"imagem em t={t_img}: {args.pasta / 'calibracao_mvp.jpg'}")


if __name__ == "__main__":
    main()
