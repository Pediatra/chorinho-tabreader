"""Telas: segmenta o vídeo no TEMPO em páginas de tablatura (Fase 3 do plano do produto).

A tablatura de um vídeo-aula é uma sequência de **páginas** que troca (e repete) durante o
vídeo; uma página só não é a música. Este módulo devolve, para cada página distinta (``Tela``),
os trechos do vídeo em que ela está na tela (``exibicoes``) — é a base da leitura por tela
(Fase 4) e do tempo por exibição (Fase 5).

Cadeia (T3.1 a T3.6 do plano):

1. **presença grossa**: um quadro a cada 5 s, com painel de tablatura ou sem; as bordas de cada
   trecho com painel são refinadas por busca binária até ≤ 1 s;
2. **assinatura de tinta** a 2 quadros/s dentro da presença: pixels coloridos (o marcador)
   viram o fundo; o resto é binarizado, sem as cordas, e reduzido a ¼ de resolução;
3. **troca** quando ``1 − IoU`` da tinta entre amostras consecutivas passa de ``LIMIAR_TROCA``
   (escolhido no VALE do histograma medido; ver o ``ESTADO.md``);
4. **repetição**: página que reaparece é a MESMA ``id``, com nova exibição;
5. **rolagem**: só detectada (``cv2.phaseCorrelate``) e declarada em ``modo``.

Independente do ``tab.ouro_video`` (o ouro é régua; este módulo é o produto): as ideias e os
números medidos de lá foram reaproveitados, o código não é importado.

Todo vídeo é lido pelo ``tab.leitor`` (o gate proíbe ``cv2.VideoCapture`` fora dele).

Uso:
    python -m tab.telas VIDEO --json saida.json [--folha data/saida/telas/<slug>]
    python -m tab.telas --avaliar-ouro data/gold/ouro_video/<slug>.json --json telas.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

from tab.comum import leitor
from tab.tablatura.leitura.painel import (
    CONTRASTE_LINHA_MINIMO,
    FUNDO_ESCURO_MAXIMO,
    PASSO_MAXIMO_PX,
    PASSO_MINIMO_PX,
    _contraste_das_cordas,
    aparar_pauta,
    candidatos_claros_escuros,
    candidatos_por_mascara,
    escolher,
    refinar,
)

#: Retângulo ``(x0, y0, x1, y1)`` no espaço do QUADRO.
Retangulo = tuple[int, int, int, int]

#: Intervalo da presença grossa (T3.1), em segundos.
PASSO_PRESENCA_S = 5.0

#: Resolução máxima das bordas de presença depois da busca binária, em segundos.
RESOLUCAO_BORDA_S = 1.0

#: Quadros por segundo da amostragem dentro da presença (T3.2).
QPS_ASSINATURA = 2.0

#: Resolução da troca de página depois de afinada entre duas amostras, em segundos.
RESOLUCAO_TROCA_S = 0.1

#: Croma (``max − min`` dos canais B, G, R, 0-255) a partir do qual o pixel é "colorido" = marcador.
#: MEDIDO no `retrato brasileiro` (quadros de 305 s e 315 s): a faixa do marcador é azul PÁLIDA
#: (croma mediano 34, p10 16) e o fundo claro tem croma mediano 3. NÃO se usa a saturação HSV:
#: em pixel escuro um desvio de 2 níveis dá S > 25, e 64-68 % dos pixels de TINTA da tablatura
#: passavam por "coloridos" (a assinatura apagava os algarismos).
CROMA_MINIMO = 15

#: Pixels coloridos são alargados (antialiasing da borda do marcador).
DILATACAO_COLORIDO = 7

#: Portões contra o braço do violão e a tela preta, que o ``painel.escolher`` também aceita
#: (medidos no ``retrato brasileiro``): saturação mediana do recorte e cinza mediano.
SATURACAO_MEDIANA_MAXIMA = 25
CINZA_MEDIANO_MINIMO = 20

#: Corrida horizontal de tinta com pelo menos isto (px) é corda/pentagrama/barra de colcheia,
#: não algarismo (largura de algarismo: 7-22 px nos passos de 14-45 px do acervo).
COMPRIMENTO_LINHA_PX = 40

#: Fator de redução da máscara de tinta (¼ da resolução).
REDUCAO = 4

#: Abaixo desta fração de pixels não coloridos, o fundo todo é colorido e usa-se tudo.
FRACAO_MINIMA_VALIDOS = 0.2

#: Contraste mínimo (níveis de cinza) para um pixel ser tinta, mesmo que o Otsu proponha menos.
CONTRASTE_MINIMO = 40

#: Limiar de ``1 − IoU`` acima do qual a tinta mudou (troca de tela). MEDIDO (ESTADO.md,
#: Fase 3): no `retrato brasileiro` (869 amostras a 2 qps) as 868 distâncias consecutivas caem
#: em dois montes separados por um VALE VAZIO: 846 em [0, 0,02) e 22 em [0,5, 1,0]; no
#: `serge kottelat` (159 amostras) 150 em [0, 0,05), 1 em [0,15, 0,2) (o fade do início) e 7 em
#: [0,8, 1,0]. Nenhuma distância entre 0,2 e 0,5 em nenhum dos dois: o limiar fica no meio do vale.
LIMIAR_TROCA = 0.3

#: Limiar de ``1 − IoU`` abaixo do qual uma página é a MESMA que uma anterior (repetição).
#: MEDIDO no `retrato brasileiro`: dos 22 trechos depois do primeiro, 9 acharam uma página anterior
#: a <= 0,02 e 13 não tinham nenhuma a menos de 0,5 (vale vazio de 0,02 a 0,5).
LIMIAR_MESMA = 0.3

#: Trecho com menos amostras que isto (1,5 s a 2 qps) é transição (fade/wipe), não página:
#: é anexado à página vizinha mais parecida.
MIN_AMOSTRAS_TRECHO = 3

#: Oclusão (as mãos do vídeo por cima do lado da tablatura, ou a página ainda aparecendo):
#: duas páginas convergem se a tinta de um dos lados é igual (``1 − IoU`` <= este valor) por
#: ao menos ``FRACAO_OCLUSAO`` da largura. MEDIDO no `retrato brasileiro` 239-245 s: o prefixo
#: esquerdo (63 % da largura) dá 0,01 contra a página seguinte, e o total dá 0,63.
LIMIAR_OCLUSAO = 0.1
FRACAO_OCLUSAO = 0.4

#: Tinta mínima (px da máscara reduzida) na região comparada para valer o teste de oclusão.
TINTA_MINIMA_OCLUSAO = 150

#: Rolagem: fração mínima dos pares consecutivos com deslocamento e resposta altos.
RESPOSTA_ROLAGEM = 0.3
DESLOCAMENTO_ROLAGEM_PX = 0.5
FRACAO_ROLAGEM = 0.2


@dataclass
class Tela:
    """Uma página distinta de tablatura e os trechos do vídeo em que ela aparece."""

    id: int
    painel: Retangulo
    exibicoes: list[tuple[float, float]] = field(default_factory=list)
    quadro_ref_s: float = 0.0
    modo: str = "estatico"


# ---------------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------------


def mascara_colorida(bgr: np.ndarray) -> np.ndarray:
    """Pixels coloridos (croma alto = marcador), alargados em volta.

    Args:
        bgr: recorte BGR.

    Returns:
        Máscara booleana, ``True`` onde há cor.
    """
    canais = bgr.astype(np.int16)
    croma = canais.max(axis=2) - canais.min(axis=2)
    cor = (croma > CROMA_MINIMO).astype(np.uint8)
    kernel = np.ones((DILATACAO_COLORIDO, DILATACAO_COLORIDO), np.uint8)
    return cv2.dilate(cor, kernel) > 0


def assinatura(recorte: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Máscara de tinta do painel SEM o marcador (T3.2).

    Pixels coloridos viram o fundo (a mediana dos não coloridos); o resto é binarizado por
    Otsu sobre ``|cinza − fundo|`` (serve a tema claro e escuro), sem as cordas (corrida
    horizontal longa) e reduzido a ¼. Onde o
    marcador cobria, a tinta é desconhecida: a máscara ``valido`` diz onde se pode comparar
    (medido no ``serge kottelat``: sem ela a faixa que anda dava ``1 − IoU`` de 0,10-0,15 entre
    quadros da MESMA página).

    Args:
        recorte: painel em BGR.

    Returns:
        ``(tinta_reduzida_bool, valido_reduzido_bool, fracao_colorida)``.
    """
    colorido = mascara_colorida(recorte)
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    validos = ~colorido
    if validos.mean() < FRACAO_MINIMA_VALIDOS:
        validos = np.ones_like(validos)
    fundo = int(np.median(cinza[validos]))
    cinza = cinza.copy()
    cinza[colorido & validos] = fundo
    dif = np.abs(cinza.astype(np.int16) - fundo).astype(np.uint8)
    if dif.max() < CONTRASTE_MINIMO:
        tinta = np.zeros(dif.shape, np.uint8)
    else:
        limiar, _ = cv2.threshold(dif, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        tinta = (dif > max(limiar, CONTRASTE_MINIMO)).astype(np.uint8)
        # as cordas (e o pentagrama) são a mesma tinta em TODA página: sem tirá-las, a troca
        # entre duas páginas de mesmo leiaute dava 1 − IoU de 0,03-0,12, igual ao ruído
        linhas = cv2.morphologyEx(
            tinta, cv2.MORPH_OPEN, np.ones((1, COMPRIMENTO_LINHA_PX), np.uint8)
        )
        linhas = cv2.dilate(linhas, np.ones((3, 1), np.uint8))
        tinta = tinta & (1 - linhas)
    h, w = tinta.shape
    pequena = cv2.resize(
        tinta.astype(np.float32),
        (max(1, w // REDUCAO), max(1, h // REDUCAO)),
        interpolation=cv2.INTER_AREA,
    )
    nao_cor = cv2.resize(
        (~colorido).astype(np.float32),
        (pequena.shape[1], pequena.shape[0]),
        interpolation=cv2.INTER_AREA,
    )
    return pequena > 0.1, nao_cor > 0.99, float(colorido.mean())


def _reamostrar(mascara: np.ndarray, forma: tuple[int, ...]) -> np.ndarray:
    """Máscara booleana reamostrada (vizinho mais próximo) para ``forma``.

    Args:
        mascara: máscara booleana.
        forma: ``(altura, largura)`` de destino.

    Returns:
        A máscara no novo tamanho.
    """
    return (
        cv2.resize(
            mascara.astype(np.uint8),
            (forma[1], forma[0]),
            interpolation=cv2.INTER_NEAREST,
        )
        > 0
    )


def distancia_iou(
    a: np.ndarray,
    b: np.ndarray,
    valido_a: np.ndarray | None = None,
    valido_b: np.ndarray | None = None,
) -> float:
    """``1 − IoU`` entre duas máscaras de tinta (``b`` é reamostrada para o tamanho de ``a``).

    Args:
        a: máscara booleana.
        b: máscara booleana.
        valido_a: onde ``a`` é conhecida (fora do marcador); ``None`` = toda.
        valido_b: idem para ``b``.

    Returns:
        0 para tintas idênticas, 1 para disjuntas; 0 se as duas estão em branco.
    """
    if a.shape != b.shape:
        b = _reamostrar(b, a.shape)
        valido_b = None if valido_b is None else _reamostrar(valido_b, a.shape)
    if valido_a is not None or valido_b is not None:
        ok = np.ones(a.shape, bool)
        for v in (valido_a, valido_b):
            if v is not None:
                ok &= v
        if ok.mean() >= FRACAO_MINIMA_VALIDOS:
            a, b = a & ok, b & ok
    uniao = int(np.count_nonzero(a | b))
    if uniao == 0:
        return 0.0
    return 1.0 - int(np.count_nonzero(a & b)) / uniao


def recortar(quadro: np.ndarray, rect: Retangulo) -> np.ndarray:
    """Recorte do quadro, com o retângulo limitado às bordas.

    Args:
        quadro: imagem BGR.
        rect: ``(x0, y0, x1, y1)`` no espaço do quadro.

    Returns:
        O recorte (uma visão, não uma cópia).
    """
    x0, y0, x1, y1 = rect
    return quadro[max(0, y0) : y1, max(0, x0) : x1]


def painel_do_quadro(quadro: np.ndarray) -> Retangulo | None:
    """Retângulo do painel de tablatura no QUADRO, ou ``None`` se não há tablatura.

    Primeiro o caminho do HEAD (painel claro, inalterado). Se ele não achar nada, a TAB
    ESCURA (`_painel_escuro`): grupo de cordas claras sobre fundo escuro, na máscara de
    contraste claro. Se também não achar, o grupo forte por máscara (`_painel_por_mascara`),
    que cobre a TAB transparente sobre vídeo. Cada caminho só roda se os anteriores não
    acharam nada: quadro que o HEAD já lê fica como estava.

    Args:
        quadro: quadro BGR inteiro.

    Returns:
        ``(x0, y0, x1, y1)`` no espaço do quadro, ou ``None``.
    """
    rect = _painel_do_quadro_claro(quadro)
    if rect is not None:
        return rect
    rect = _painel_escuro(quadro)
    if rect is not None:
        return rect
    return _painel_por_mascara(quadro)


def _caixa_do_candidato(quadro: np.ndarray, cand) -> Retangulo | None:
    """Caixa aparada de um candidato, ou None se o portão de cor (fundo) reprova.

    Mesmas contas do `_painel_do_quadro_claro`, a partir do candidato já refinado.

    Args:
        quadro: quadro BGR inteiro.
        cand: candidato de ``tab.painel``.

    Returns:
        ``(x0, y0, x1, y1)`` aparado, ou None.
    """
    linhas = list(cand.grade.linhas_y)
    folga = round(1.5 * cand.passo)
    y0 = max(0, cand.y0 + min(linhas) - folga)
    y1 = min(quadro.shape[0], cand.y0 + max(linhas) + folga)
    x0 = cand.x0
    x1 = min(quadro.shape[1], x0 + cand.roi.shape[1])
    rect = aparar_pauta(quadro, (int(x0), int(y0), int(x1), int(y1)))
    miolo = recortar(quadro, rect)
    if miolo.size == 0:
        return None
    saturacao = cv2.cvtColor(miolo, cv2.COLOR_BGR2HSV)[:, :, 1]
    cinza = cv2.cvtColor(miolo, cv2.COLOR_BGR2GRAY)
    if (
        np.median(saturacao) > SATURACAO_MEDIANA_MAXIMA
        or np.median(cinza) < CINZA_MEDIANO_MINIMO
    ):
        return None
    return rect


def _painel_escuro(quadro: np.ndarray) -> Retangulo | None:
    """Caixa da TAB escura: o primeiro grupo escuro (por uniformidade) que passa no portão.

    Args:
        quadro: quadro BGR inteiro.

    Returns:
        A caixa aparada, ou None se nenhum grupo escuro passar.
    """
    for _uniform, cand in sorted(
        candidatos_claros_escuros(quadro), key=lambda t: t[0], reverse=True
    ):
        cand = refinar(cand)
        if not PASSO_MINIMO_PX <= cand.passo <= PASSO_MAXIMO_PX:
            continue
        rect = _caixa_do_candidato(quadro, cand)
        if rect is not None:
            return rect
    return None


def _caixa_escura_do_candidato(quadro: np.ndarray, cand) -> Retangulo | None:
    """Caixa aparada de um grupo sobre fundo ESCURO (o portão de `_painel_escuro`).

    Args:
        quadro: quadro BGR inteiro.
        cand: candidato de ``tab.painel`` já refinado.

    Returns:
        ``(x0, y0, x1, y1)`` aparado, ou None se o fundo não é escuro ou as cordas não
        são mais claras que o fundo acima delas.
    """
    cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY).astype(np.float32)
    faixa = cinza[cand.y0 : cand.y1, :]
    if float(np.median(faixa)) > FUNDO_ESCURO_MAXIMO:
        return None
    if _contraste_das_cordas(cinza, list(cand.grade.linhas_y), cand.y0) < (
        CONTRASTE_LINHA_MINIMO
    ):
        return None
    folga = round(1.5 * cand.passo)
    linhas = list(cand.grade.linhas_y)
    x0 = cand.x0
    x1 = min(quadro.shape[1], x0 + cand.roi.shape[1])
    y0 = max(0, cand.y0 + min(linhas) - folga)
    y1 = min(quadro.shape[0], cand.y0 + max(linhas) + folga)
    return aparar_pauta(quadro, (int(x0), int(y0), int(x1), int(y1)))


def _painel_por_mascara(quadro: np.ndarray) -> Retangulo | None:
    """Caixa do grupo forte por máscara, com o portão de papel OU o de fundo escuro.

    Só roda quando o HEAD, a TAB escura e o pool de `escolher` não acharam nada. Mede-se
    no caso TRANSPARENTE: os números são brancos sobre vídeo, e o fundo tem cor (o portão
    de papel do HEAD, saturação até 25, reprova); o portão escuro (fundo mediano <= 50 e
    cordas mais claras que o fundo) aceita.

    Args:
        quadro: quadro BGR inteiro.

    Returns:
        A caixa aparada da melhor faixa que passa no portão, ou None.
    """
    for _u, cand in sorted(
        candidatos_por_mascara(quadro), key=lambda t: t[0], reverse=True
    ):
        # refinar estreita em x à extensão das cordas: sem isto o destaque amarelo de um
        # acorde ao lado da TAB reprova o portão de papel (medido: caso 10, t=35)
        cand = refinar(cand)
        if not PASSO_MINIMO_PX <= cand.passo <= PASSO_MAXIMO_PX:
            continue
        rect = _caixa_do_candidato(quadro, cand)
        if rect is None:
            rect = _caixa_escura_do_candidato(quadro, cand)
        if rect is not None:
            return rect
    return None


def _painel_do_quadro_claro(quadro: np.ndarray) -> Retangulo | None:
    """Retângulo do painel de tablatura no QUADRO, ou ``None`` se não há tablatura.

    Usa o ``painel.escolher`` e os portões medidos contra o braço do violão e a tela preta:
    passo 14-45 px, saturação mediana do recorte <= 25 e cinza mediano >= 20.

    Args:
        quadro: quadro BGR inteiro.

    Returns:
        ``(x0, y0, x1, y1)`` no espaço do quadro (cordas com 1,5 passo de folga), ou ``None``.
    """
    cand = escolher(quadro)
    if cand is None or not PASSO_MINIMO_PX <= cand.passo <= PASSO_MAXIMO_PX:
        return None
    linhas = list(cand.grade.linhas_y)
    folga = round(1.5 * cand.passo)
    y0 = max(0, cand.y0 + min(linhas) - folga)
    y1 = min(quadro.shape[0], cand.y0 + max(linhas) + folga)
    x0 = cand.x0
    x1 = min(quadro.shape[1], x0 + cand.roi.shape[1])
    rect = aparar_pauta(quadro, (int(x0), int(y0), int(x1), int(y1)))
    miolo = recortar(quadro, rect)
    if miolo.size == 0:
        return None
    saturacao = cv2.cvtColor(miolo, cv2.COLOR_BGR2HSV)[:, :, 1]
    cinza = cv2.cvtColor(miolo, cv2.COLOR_BGR2GRAY)
    if (
        np.median(saturacao) > SATURACAO_MEDIANA_MAXIMA
        or np.median(cinza) < CINZA_MEDIANO_MINIMO
    ):
        return None
    return rect


# ---------------------------------------------------------------------------------
# T3.1: presença grossa
# ---------------------------------------------------------------------------------


@dataclass
class Trecho:
    """Um trecho contínuo do vídeo com painel de tablatura."""

    t0: float
    t1: float
    rect: Retangulo
    #: ``(t, retângulo)`` de cada amostra grossa com painel dentro do trecho.
    rects: list[tuple[float, Retangulo]] = field(default_factory=list)


def refinar_borda(
    tem: Callable[[float], bool],
    t_sem: float,
    t_com: float,
    resolucao: float = RESOLUCAO_BORDA_S,
) -> float:
    """Busca binária da borda entre um instante SEM painel e outro COM.

    Args:
        tem: ``t -> bool`` (há painel em ``t``?).
        t_sem: instante sem painel.
        t_com: instante com painel (pode ser antes ou depois de ``t_sem``).
        resolucao: largura máxima do intervalo final, em segundos.

    Returns:
        O primeiro instante com painel conhecido (lado "com" do intervalo final).
    """
    while abs(t_com - t_sem) > resolucao:
        meio = (t_com + t_sem) / 2.0
        if tem(meio):
            t_com = meio
        else:
            t_sem = meio
    return t_com


def uniao_retangulos(rects: list[Retangulo]) -> Retangulo:
    """Menor retângulo que contém todos (a página muda de altura: 286 e 329 px no MVP).

    Args:
        rects: ao menos um retângulo.

    Returns:
        ``(x0, y0, x1, y1)`` da união.
    """
    return (
        min(r[0] for r in rects),
        min(r[1] for r in rects),
        max(r[2] for r in rects),
        max(r[3] for r in rects),
    )


def presenca(
    video: str,
    duracao: float,
    passo: float = PASSO_PRESENCA_S,
    detectar: Callable[[np.ndarray], Retangulo | None] = painel_do_quadro,
) -> list[Trecho]:
    """Trechos do vídeo com tablatura: varredura grossa e bordas refinadas (T3.1).

    Args:
        video: caminho do vídeo.
        duracao: duração, em segundos.
        passo: intervalo da varredura grossa, em segundos.
        detectar: ``quadro -> retângulo | None``.

    Returns:
        Trechos em ordem de tempo, cada um com a união dos painéis das amostras.
    """
    amostras: list[tuple[float, Retangulo | None]] = [
        (t, detectar(q)) for t, q in leitor.quadros(video, 0.0, duracao, 1.0 / passo)
    ]

    def tem(t: float) -> bool:
        quadro = leitor.quadro_em(video, t)
        return quadro is not None and detectar(quadro) is not None

    trechos: list[Trecho] = []
    k = 0
    while k < len(amostras):
        if amostras[k][1] is None:
            k += 1
            continue
        j = k
        while j + 1 < len(amostras) and amostras[j + 1][1] is not None:
            j += 1
        rects = [(t, r) for t, r in amostras[k : j + 1] if r is not None]
        t_ini = refinar_borda(tem, amostras[k - 1][0], amostras[k][0]) if k > 0 else 0.0
        if j + 1 < len(amostras):
            t_fim = refinar_borda(tem, amostras[j + 1][0], amostras[j][0])
        else:
            t_fim = duracao
        trechos.append(
            Trecho(t_ini, t_fim, uniao_retangulos([r for _, r in rects]), rects)
        )
        k = j + 1
    return trechos


# ---------------------------------------------------------------------------------
# T3.2: amostras de tinta dentro de um trecho
# ---------------------------------------------------------------------------------


@dataclass
class Amostra:
    """Uma amostra a 2 qps: instante, tinta sem marcador e fração colorida."""

    t: float
    tinta: np.ndarray
    valido: np.ndarray
    colorido: float


def amostrar(video: str, trecho: Trecho, qps: float = QPS_ASSINATURA) -> list[Amostra]:
    """Amostras de tinta de um trecho, numa passada única do leitor.

    Args:
        video: caminho do vídeo.
        trecho: trecho com painel.
        qps: quadros por segundo.

    Returns:
        Uma ``Amostra`` por quadro lido.
    """
    saida = []
    for t, quadro in leitor.quadros(video, trecho.t0, trecho.t1, qps):
        tinta, valido, colorido = assinatura(recortar(quadro, trecho.rect))
        saida.append(Amostra(t, tinta, valido, colorido))
    return saida


# ---------------------------------------------------------------------------------
# T3.3 a T3.5: troca, repetição, rolagem (funções puras sobre máscaras)
# ---------------------------------------------------------------------------------


def deslocamento_rolagem(
    a: np.ndarray, b: np.ndarray, limiar: float = LIMIAR_TROCA
) -> tuple[float, float, float] | None:
    """Deslocamento de rolagem entre duas máscaras, se ele EXPLICA a diferença (T3.5).

    Correlação de fase (``cv2.phaseCorrelate``) com resposta alta e deslocamento horizontal
    não nulo; só vale se, depois de compensar o deslocamento, a distância cai a ``limiar``
    ou menos (pico alto entre duas páginas diferentes não é rolagem).

    Args:
        a: máscara anterior.
        b: máscara seguinte (mesmo tamanho).
        limiar: ``1 − IoU`` máximo depois de compensar.

    Returns:
        ``(dx, dy, resposta)`` em pixels da máscara reduzida, ou ``None``.
    """
    if a.shape != b.shape or not a.any() or not b.any():
        return None
    (dx, dy), resposta = cv2.phaseCorrelate(a.astype(np.float32), b.astype(np.float32))
    if resposta < RESPOSTA_ROLAGEM or abs(dx) < DESLOCAMENTO_ROLAGEM_PX:
        return None
    matriz = np.float32([[1, 0, -dx], [0, 1, -dy]])
    h, w = a.shape
    deslocada = cv2.warpAffine(b.astype(np.uint8), matriz, (w, h)) > 0
    if distancia_iou(a, deslocada) > limiar:
        return None
    return float(dx), float(dy), float(resposta)


def cortar_em_paginas(
    tintas: list[np.ndarray],
    limiar: float = LIMIAR_TROCA,
    min_amostras: int = MIN_AMOSTRAS_TRECHO,
    validos: list[np.ndarray] | None = None,
) -> tuple[list[tuple[int, int]], list[float], int]:
    """Corta a série de máscaras onde a tinta troca (T3.3).

    Quadros de transição (trecho curto entre duas trocas) são absorvidos pelo trecho anterior.
    Uma troca que a rolagem explica (``deslocamento_rolagem``) não corta.

    Args:
        tintas: máscaras de tinta, em ordem de tempo.
        limiar: ``1 − IoU`` acima do qual a tinta mudou.
        min_amostras: trecho com menos amostras que isto é transição.
        validos: máscaras de "tinta conhecida" de cada amostra (fora do marcador).

    Returns:
        ``(trechos, distancias, pares_rolando)``: índices ``(i0, i1)`` inclusivos de cada
        página, as ``n−1`` distâncias consecutivas e quantos pares tinham rolagem.
    """
    vs = validos if validos is not None else [None] * len(tintas)
    distancias = [
        distancia_iou(tintas[i], tintas[i + 1], vs[i], vs[i + 1])
        for i in range(len(tintas) - 1)
    ]
    cortes = [0]
    rolando = 0
    for i, d in enumerate(distancias):
        if d > limiar:
            if deslocamento_rolagem(tintas[i], tintas[i + 1], limiar) is not None:
                rolando += 1
                continue
            cortes.append(i + 1)
        elif d > 0.02 and deslocamento_rolagem(tintas[i], tintas[i + 1], limiar):
            rolando += 1
    cortes.append(len(tintas))
    trechos: list[list[int]] = [[a, b - 1] for a, b in itertools.pairwise(cortes)]
    unidos: list[list[int]] = []
    for trecho in trechos:
        if unidos and trecho[1] - trecho[0] + 1 < min_amostras:
            unidos[-1][1] = trecho[1]
        else:
            unidos.append(trecho)
    if len(unidos) > 1 and unidos[0][1] - unidos[0][0] + 1 < min_amostras:
        unidos[1][0] = unidos[0][0]
        unidos.pop(0)
    return [(a, b) for a, b in unidos], distancias, rolando


def _largura_igual(
    a: np.ndarray, b: np.ndarray, valido: np.ndarray, limiar: float
) -> float:
    """Fração da largura, a partir da esquerda, em que ``a`` e ``b`` têm a mesma tinta.

    Args:
        a: máscara de tinta.
        b: máscara de tinta do mesmo tamanho.
        valido: onde ambas são conhecidas.
        limiar: ``1 − IoU`` acumulado máximo.

    Returns:
        Largura (0 a 1) até a primeira coluna em que o ``1 − IoU`` acumulado passa de
        ``limiar`` (com ao menos ``TINTA_MINIMA_OCLUSAO`` de tinta já vista); 1 se nunca.
    """
    dif = ((a ^ b) & valido).sum(axis=0).cumsum()
    uniao = ((a | b) & valido).sum(axis=0).cumsum()
    ruim = np.flatnonzero((uniao >= TINTA_MINIMA_OCLUSAO) & (dif > limiar * uniao))
    return float(ruim[0] / a.shape[1]) if ruim.size else 1.0


def convergem(
    a: tuple[np.ndarray, np.ndarray],
    b: tuple[np.ndarray, np.ndarray],
    limiar: float = LIMIAR_OCLUSAO,
    fracao: float = FRACAO_OCLUSAO,
) -> bool:
    """Uma das páginas é a outra com algo por cima (mãos) ou ainda por aparecer?

    Args:
        a: ``(tinta, valido)``.
        b: ``(tinta, valido)``.
        limiar: ver ``LIMIAR_OCLUSAO``.
        fracao: ver ``FRACAO_OCLUSAO``.

    Returns:
        ``True`` se a tinta é igual em ``fracao`` da largura, pela esquerda ou pela direita.
    """
    ta, va = a
    tb, vb = b
    if ta.shape != tb.shape:
        tb, vb = _reamostrar(tb, ta.shape), _reamostrar(vb, ta.shape)
    ok = va & vb
    esquerda = _largura_igual(ta, tb, ok, limiar)
    direita = _largura_igual(ta[:, ::-1], tb[:, ::-1], ok[:, ::-1], limiar)
    return max(esquerda, direita) >= fracao


def absorver_transicoes(
    cortes: list[tuple[int, int]],
    reps: list[tuple[np.ndarray, np.ndarray]],
    min_amostras: int = MIN_AMOSTRAS_TRECHO,
    limiar_mesma: float = LIMIAR_MESMA,
) -> list[tuple[int, int, tuple[np.ndarray, np.ndarray]]]:
    """Anexa à vizinha os trechos que não são página: transição curta ou oclusão.

    Um trecho é anexado (ao vizinho mais parecido) se tem menos de ``min_amostras`` amostras
    ou se ``convergem`` com um vizinho (e nesse caso o MENOR dos dois é o anexado). A página
    que fica mantém a sua própria tinta (a limpa).

    Args:
        cortes: ``(i0, i1)`` inclusivos de cada trecho.
        reps: ``(tinta, valido)`` de cada trecho.
        min_amostras: trecho mais curto que isto é transição.
        limiar_mesma: ver ``LIMIAR_MESMA`` (não usado para decidir, só para desempate).

    Returns:
        ``(i0, i1, rep)`` dos trechos que ficaram.
    """
    runs = [(a, b, r) for (a, b), r in zip(cortes, reps, strict=True)]
    while len(runs) > 1:
        escolha = None
        for k, (a, b, rep) in enumerate(runs):
            viz = [j for j in (k - 1, k + 1) if 0 <= j < len(runs)]
            tam = b - a + 1
            dist = {
                j: distancia_iou(rep[0], runs[j][2][0], rep[1], runs[j][2][1])
                for j in viz
            }
            if tam < min_amostras:
                alvo = min(viz, key=lambda j: dist[j])
            else:
                conv = [
                    j
                    for j in viz
                    if convergem(rep, runs[j][2]) and tam <= runs[j][1] - runs[j][0] + 1
                ]
                if not conv:
                    continue
                alvo = min(conv, key=lambda j: dist[j])
            if escolha is None or tam < escolha[2]:
                escolha = (k, alvo, tam)
        if escolha is None:
            break
        k, alvo, _ = escolha
        a, b, _rep = runs[k]
        ia, ib, rep_alvo = runs[alvo]
        runs[alvo] = (min(a, ia), max(b, ib), rep_alvo)
        runs.pop(k)
    return runs


def tinta_majoritaria(
    tintas: list[np.ndarray], validos: list[np.ndarray] | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Tinta que vence o voto das amostras (e onde ela é conhecida).

    O pixel é tinta se for tinta em mais da metade das amostras em que é conhecido; o
    marcador anda, então quase todo pixel é conhecido em alguma amostra.

    Args:
        tintas: máscaras do mesmo tamanho.
        validos: máscaras de "conhecido" de cada amostra (``None`` = todas conhecidas).

    Returns:
        ``(tinta, valido)``.
    """
    pilha = np.stack(tintas).astype(np.float32)
    if validos is None:
        return pilha.mean(axis=0) > 0.5, np.ones(pilha.shape[1:], bool)
    conhecido = np.stack(validos).astype(np.float32)
    n = conhecido.sum(axis=0)
    voto = (pilha * conhecido).sum(axis=0) / np.maximum(n, 1)
    return voto > 0.5, n > 0


def histograma(valores: list[float]) -> dict[str, int]:
    """Histograma de distâncias ``1 − IoU`` em faixas fixas (para o vale do limiar).

    Args:
        valores: distâncias.

    Returns:
        ``{"[a,b)": contagem}`` na ordem das faixas.
    """
    bordas = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0001]
    contagens, _ = np.histogram(valores, bins=bordas)
    return {
        f"[{a:g},{min(b, 1.0):g})": int(c)
        for a, b, c in zip(bordas, bordas[1:], contagens, strict=False)
    }


# ---------------------------------------------------------------------------------
# T3.4 / T3.6: montagem das telas
# ---------------------------------------------------------------------------------


def quadro_de_referencia(
    exibicoes: list[tuple[float, float]], grupos: list[list[Amostra]]
) -> float:
    """Instante de leitura: dentro da MAIOR exibição, longe das fronteiras (transição).

    Entre as amostras da metade central da maior exibição, o de menos marcador (menor
    fração colorida); empate, o mais perto do meio.

    Args:
        exibicoes: ``(t0, t1)`` de cada exibição da tela.
        grupos: amostras de cada exibição, na mesma ordem.

    Returns:
        O instante, em segundos.
    """
    k = max(range(len(exibicoes)), key=lambda i: exibicoes[i][1] - exibicoes[i][0])
    t0, t1 = exibicoes[k]
    meio, quarto = (t0 + t1) / 2, (t1 - t0) / 4
    centrais = [a for a in grupos[k] if abs(a.t - meio) <= quarto] or grupos[k]
    if not centrais:
        return meio
    return min(centrais, key=lambda a: (round(a.colorido, 4), abs(a.t - meio))).t


def montar_telas(
    trechos: list[Trecho],
    amostras: list[list[Amostra]],
    limiar_troca: float = LIMIAR_TROCA,
    limiar_mesma: float = LIMIAR_MESMA,
    refinar: Callable[[Trecho, float, float, tuple, tuple], float] | None = None,
) -> tuple[list[Tela], dict]:
    """Corta cada trecho em páginas e junta as repetidas na mesma ``Tela`` (T3.3 e T3.4).

    Args:
        trechos: trechos com painel (T3.1).
        amostras: amostras de cada trecho (T3.2), na mesma ordem.
        limiar_troca: ``1 − IoU`` que separa páginas consecutivas.
        limiar_mesma: ``1 − IoU`` abaixo do qual uma página é uma tela já vista.
        refinar: ``(trecho, t_antes, t_depois, rep_antes, rep_depois) -> t`` (cada ``rep`` é
            ``(tinta, valido)``) que afina a
            troca entre duas amostras (sem ele, a troca fica na primeira amostra nova).

    Returns:
        ``(telas, medida)``; ``medida`` traz as distâncias consecutivas e o modo.
    """
    telas: list[Tela] = []
    representantes: list[tuple[np.ndarray, np.ndarray]] = []
    exib_amostras: list[list[list[Amostra]]] = []  # por tela, por exibição
    rects: list[list[Retangulo]] = []
    distancias: list[float] = []
    entre_paginas: list[float] = []
    pares = 0
    rolando = 0
    for trecho, amo in zip(trechos, amostras, strict=True):
        if not amo:
            continue
        cortes0, dist, roll = cortar_em_paginas(
            [a.tinta for a in amo],
            limiar_troca,
            min_amostras=1,
            validos=[a.valido for a in amo],
        )
        distancias += dist
        pares += len(dist)
        rolando += roll
        reps0 = [
            tinta_majoritaria(
                [a.tinta for a in amo[i0 : i1 + 1]],
                [a.valido for a in amo[i0 : i1 + 1]],
            )
            for i0, i1 in cortes0
        ]
        runs = absorver_transicoes(cortes0, reps0, limiar_mesma=limiar_mesma)
        cortes = [(a, b) for a, b, _ in runs]
        reps = [r for _, _, r in runs]
        instantes = [trecho.t0] + [amo[i0].t for i0, _ in cortes[1:]] + [trecho.t1]
        if refinar is not None:
            for k in range(1, len(cortes)):
                i0 = cortes[k][0]
                instantes[k] = refinar(
                    trecho, amo[i0 - 1].t, amo[i0].t, reps[k - 1], reps[k]
                )
        for k, (i0, i1) in enumerate(cortes):
            t0, t1 = instantes[k], instantes[k + 1]
            rep = reps[k]
            dists = [distancia_iou(r[0], rep[0], r[1], rep[1]) for r in representantes]
            alvo = int(np.argmin(dists)) if dists else -1
            if dists:
                entre_paginas.append(min(dists))
            if alvo < 0 or dists[alvo] > limiar_mesma:
                telas.append(Tela(len(telas) + 1, trecho.rect))
                representantes.append(rep)
                exib_amostras.append([])
                rects.append([])
                alvo = len(telas) - 1
            tela = telas[alvo]
            fatia = amo[i0 : i1 + 1]
            if tela.exibicoes and abs(tela.exibicoes[-1][1] - t0) < 1e-6:
                tela.exibicoes[-1] = (tela.exibicoes[-1][0], t1)
                exib_amostras[alvo][-1] += fatia
            else:
                tela.exibicoes.append((t0, t1))
                exib_amostras[alvo].append(list(fatia))
            rects[alvo] += [r for t, r in trecho.rects if t0 <= t < t1] or [trecho.rect]
    for tela, grupos, rs in zip(telas, exib_amostras, rects, strict=True):
        tela.quadro_ref_s = quadro_de_referencia(tela.exibicoes, grupos)
        tela.painel = uniao_retangulos(rs)
    rolante = pares > 0 and rolando / pares >= FRACAO_ROLAGEM
    modo = "rolante" if rolante else ("paginado" if len(telas) > 1 else "estatico")
    for tela in telas:
        tela.modo = modo
    medida = {
        "distancias": distancias,
        "entre_paginas": entre_paginas,
        "pares": pares,
        "pares_rolando": rolando,
        "modo": modo,
    }
    return telas, medida


def telas(
    video: str,
    medida: dict | None = None,
    detectar: Callable[[np.ndarray], Retangulo | None] = painel_do_quadro,
) -> list[Tela]:
    """Segmenta o vídeo em telas (páginas de tablatura) e suas exibições.

    Args:
        video: caminho do vídeo.
        medida: se dado, é preenchido com ``distancias``, ``histograma``, ``trechos`` e
            ``modo`` (para registrar o vale do limiar).
        detectar: ``quadro -> retângulo | None`` (os testes injetam um painel fixo).

    Returns:
        As telas, com ``id`` em ordem de primeira aparição.
    """
    duracao = float(leitor.info(video)["duracao_s"] or 0.0)
    trechos = presenca(video, duracao, detectar=detectar)
    amostras = [amostrar(video, t) for t in trechos]

    def refinar(
        trecho: Trecho, t_a: float, t_b: float, antes: tuple, depois: tuple
    ) -> float:
        def nova(t: float) -> bool:
            quadro = leitor.quadro_em(video, t)
            if quadro is None:
                return True
            tinta, valido, _ = assinatura(recortar(quadro, trecho.rect))
            return distancia_iou(tinta, depois[0], valido, depois[1]) < distancia_iou(
                tinta, antes[0], valido, antes[1]
            )

        return refinar_borda(nova, t_a, t_b, RESOLUCAO_TROCA_S)

    resultado, med = montar_telas(trechos, amostras, refinar=refinar)
    if medida is not None:
        medida.update(med)
        medida["histograma"] = histograma(med["distancias"])
        medida["histograma_entre_paginas"] = histograma(med["entre_paginas"])
        medida["trechos"] = [(t.t0, t.t1, t.rect) for t in trechos]
        medida["duracao_s"] = duracao
    return resultado


# ---------------------------------------------------------------------------------
# Critério de aceitação contra o ouro de vídeo
# ---------------------------------------------------------------------------------


def tela_em(resultado: list[Tela], t: float) -> int | None:
    """Id da tela cuja exibição contém ``t`` (``None`` se nenhuma).

    Args:
        resultado: telas previstas.
        t: instante, em segundos.

    Returns:
        O id, ou ``None``.
    """
    for tela in resultado:
        for t0, t1 in tela.exibicoes:
            if t0 <= t < t1:
                return tela.id
    return None


def avaliar_ouro(ouro: dict, resultado: list[Tela]) -> dict:
    """Mede as telas previstas contra o ouro de vídeo (CA da Fase 3).

    As ids diferem, então a tela prevista que corresponde a uma tela do ouro é a que contém o
    ``quadro_ref_s`` dela. Um instante está certo se a tela prevista em ``t`` é a
    correspondente da tela do ouro daquele instante.

    Args:
        ouro: conteúdo de ``data/gold/ouro_video/<slug>.json`` (não é alterado).
        resultado: telas previstas.

    Returns:
        Contagens e listas de erro, com os denominadores.
    """
    correspondente = {
        int(t["id"]): tela_em(resultado, float(t["quadro_ref_s"]))
        for t in ouro["telas"]
    }
    instantes = ouro["instantes"]
    certos = 0
    erros = []
    for i in instantes:
        prevista = tela_em(resultado, float(i["t"]))
        esperada = correspondente.get(int(i["tela"]))
        if prevista is not None and prevista == esperada:
            certos += 1
        else:
            erros.append(
                {
                    "t": i["t"],
                    "tela_ouro": i["tela"],
                    "prevista": prevista,
                    "esperada": esperada,
                }
            )
    paginas_do_ouro: dict[int, set[int | None]] = {}
    for i in instantes:
        paginas_do_ouro.setdefault(int(i["tela"]), set()).add(
            tela_em(resultado, float(i["t"]))
        )
    mistura = sorted(k for k, v in paginas_do_ouro.items() if len(v) > 1)
    for e in erros:
        e["ouro_mistura_paginas"] = int(e["tela_ouro"]) in mistura
    com_par = [k for k, v in correspondente.items() if v is not None]
    usadas = {v for v in correspondente.values() if v is not None}
    por_prevista: dict[int, list[int]] = {}
    for k, v in correspondente.items():
        if v is not None:
            por_prevista.setdefault(v, []).append(k)
    return {
        "instantes_certos": certos,
        "instantes": len(instantes),
        "telas_ouro": len(correspondente),
        "telas_ouro_com_prevista": len(com_par),
        "telas_previstas": len(resultado),
        "previstas_a_mais": len(resultado) - len(usadas),
        "correspondente": correspondente,
        "ouro_juntadas_pelo_produto": {
            str(k): v for k, v in por_prevista.items() if len(v) > 1
        },
        "telas_ouro_que_misturam_paginas": mistura,
        "erros_com_ouro_misturado": sum(1 for e in erros if e["ouro_mistura_paginas"]),
        "erros": erros,
    }


# ---------------------------------------------------------------------------------
# Folha de conferência e CLI
# ---------------------------------------------------------------------------------


def salvar_folha(video: str, resultado: list[Tela], pasta: Path) -> Path:
    """Grava uma imagem por tela (o ``quadro_ref_s`` recortado no painel) e a folha.

    Args:
        video: caminho do vídeo.
        resultado: telas previstas.
        pasta: pasta de saída (criada).

    Returns:
        O caminho da folha (``folha.png``).
    """
    pasta.mkdir(parents=True, exist_ok=True)
    largura = 960
    faixas = []
    for tela in resultado:
        quadro = leitor.quadro_em(video, tela.quadro_ref_s)
        if quadro is None:
            continue
        miolo = recortar(quadro, tela.painel)
        esc = largura / miolo.shape[1]
        miolo = cv2.resize(miolo, (largura, max(1, round(miolo.shape[0] * esc))))
        cv2.imwrite(str(pasta / f"tela_{tela.id:02d}.png"), miolo)
        exib = " ".join(f"{a:.0f}-{b:.0f}" for a, b in tela.exibicoes)
        rotulo = f"tela {tela.id} ref {tela.quadro_ref_s:.1f}s exib {exib}"
        faixa = cv2.copyMakeBorder(
            miolo, 28, 4, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)
        )
        cv2.putText(
            faixa, rotulo, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 0, 0), 1
        )
        faixas.append(faixa)
    folha = pasta / "folha.png"
    cv2.imwrite(
        str(folha), np.vstack(faixas) if faixas else np.zeros((8, 8, 3), np.uint8)
    )
    return folha


def main() -> int:
    """CLI: ``python -m tab.telas VIDEO --json saida.json [--folha PASTA] [--ouro OURO]``."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video")
    ap.add_argument("--json", required=True, help="onde gravar as telas")
    ap.add_argument("--folha", help="pasta das imagens de conferência")
    ap.add_argument("--ouro", help="ouro de vídeo para medir o CA da Fase 3")
    args = ap.parse_args()
    inicio = time.time()
    medida: dict = {}
    resultado = telas(args.video, medida)
    saida = {
        "video": args.video,
        "duracao_s": medida.get("duracao_s"),
        "modo": medida.get("modo"),
        "limiar_troca": LIMIAR_TROCA,
        "limiar_mesma": LIMIAR_MESMA,
        "trechos": medida.get("trechos"),
        "histograma": medida.get("histograma"),
        "histograma_entre_paginas": medida.get("histograma_entre_paginas"),
        "pares": medida.get("pares"),
        "pares_rolando": medida.get("pares_rolando"),
        "tempo_execucao_s": round(time.time() - inicio, 1),
        "telas": [asdict(t) for t in resultado],
    }
    if args.ouro:
        saida["ouro"] = avaliar_ouro(
            json.loads(Path(args.ouro).read_text(encoding="utf-8")), resultado
        )
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    if args.folha:
        salvar_folha(args.video, resultado, Path(args.folha))
    print(
        f"{len(resultado)} telas, modo {medida.get('modo')}, {saida['tempo_execucao_s']}s"
    )
    print(json.dumps(saida["histograma"], ensure_ascii=False))
    print(json.dumps(saida["histograma_entre_paginas"], ensure_ascii=False))
    for t in resultado:
        print(t.id, t.painel, f"ref {t.quadro_ref_s:.1f}", t.exibicoes)
    if args.ouro:
        o = {k: v for k, v in saida["ouro"].items() if k != "correspondente"}
        print(json.dumps(o, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
