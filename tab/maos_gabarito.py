"""Gabarito dos dedos (M2): amostra, registro e a ferramenta que grava a cada resposta.

Fase M2 da trilha das mãos. Para cada nota de tablatura tocada (``tab.mvp``), o dono diz
qual dedo da mão esquerda pisa e qual dedo da mão direita toca. Este módulo tem:

1. funções puras (amostra estratificada, caixa ampliada, escolha da caixa de cada mão,
   registro do gabarito, validação de resposta), testadas no gate;
2. o subcomando ``servir``: servidor ``http.server`` que mostra uma nota por vez e grava
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

from .caminhos import GABARITO_DEDOS, MAOS_DEDOS

#: Retângulo ``(x0, y0, x1, y1)`` no espaço do QUADRO (pixels inteiros).
Retangulo = tuple[int, int, int, int]

#: Semente da amostra (a mesma do resto da trilha).
SEMENTE_PADRAO = 20261012

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


def texto_acorde(acorde: list[dict], indice: int) -> str:
    """Linha do acorde para o cabeçalho e a página, com a nota pedida marcada.

    Args:
        acorde: saída de ``acorde_da_coluna``.
        indice: ``indice_mvp`` da nota pedida.

    Returns:
        Texto no formato ``acorde: c1 casa 0 | c3 casa 2 <- ESTA | c5 casa 3``.
    """
    partes = []
    for a in acorde:
        marca = " <- ESTA" if a["indice_mvp"] == indice else ""
        partes.append(f"c{a['corda']} casa {a['casa']}{marca}")
    return "acorde: " + " | ".join(partes)


def perguntas(corda: int, casa: int | str) -> tuple[str, str]:
    """Pergunta de cada mão, citando a corda e a casa da nota.

    Args:
        corda: corda da nota (1 = aguda, 6 = grave).
        casa: casa da nota (0 = corda solta).

    Returns:
        ``(pergunta da mão esquerda, pergunta da mão direita)``.
    """
    esquerda = f"Mão esquerda: que dedo pisa a corda {corda} (casa {casa})?"
    direita = f"Mão direita: que dedo toca a corda {corda}?"
    return esquerda, direita


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


def gabarito_novo(video: str, amostra: list[dict], semente: int) -> dict:
    """Registro do gabarito com todas as respostas em branco (``None``).

    Args:
        video: chave do vídeo no acervo (ex.: ``sky guitar/retrato....mp4``).
        amostra: saída de ``amostrar_notas``.
        semente: semente usada na amostra.

    Returns:
        O dicionário do gabarito no formato do plano.
    """
    notas = [
        {
            "id": n["id"],
            "indice_mvp": n["indice_mvp"],
            "corda": n["corda"],
            "casa": n["casa"],
            "t_ini": n["t_ini"],
            "esquerda": None,
            "direita": None,
            "obs": "",
            "respondido_em": None,
        }
        for n in amostra
    ]
    return {
        "video": video,
        "como_foi_rotulado": "dono, ferramenta tab.maos_gabarito, uma nota por vez",
        "semente": semente,
        "ferramenta": "tab.maos_gabarito",
        "notas": notas,
    }


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
    if orfas:
        raise ValueError(f"respostas sem nota na amostra nova: {orfas}")
    return novo


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


def completas(gabarito: dict) -> int:
    """Quantas notas têm as DUAS respostas (esquerda e direita).

    Args:
        gabarito: o registro.

    Returns:
        Contagem de notas completas.
    """
    return sum(
        1
        for n in gabarito["notas"]
        if n["esquerda"] is not None and n["direita"] is not None
    )


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
            """``/responder``: aplica uma resposta de uma nota e grava o gabarito."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            if self.path != "/responder":
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= 16_000:
                    raise ValueError("corpo ausente ou grande demais")
                dados = json.loads(self.rfile.read(tamanho))
                id_nota = dados.pop("id")
                agora = datetime.datetime.now().isoformat(timespec="seconds")
                with trava:
                    nota = atualizar_resposta(estado, id_nota, dados, agora)
                    gravar_atomico(ouro, estado)
                    feitas = completas(estado)
                    total = len(estado["notas"])
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
                    "nota": nota,
                    "completas": feitas,
                    "total": total,
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
body{margin:0;padding:0 16px 32px;background:var(--fundo);color:var(--texto);font:15px/1.4 system-ui,sans-serif}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid var(--borda);position:sticky;top:0;background:var(--fundo);z-index:5}
button,input{font:inherit;color:inherit;background:var(--painel);border:1px solid var(--borda);border-radius:6px;padding:6px 10px}
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
#acorde{font-weight:600;margin:4px 0}
h3{font-size:15px;margin:14px 0 6px}
img{max-width:100%;height:auto;display:block;border:1px solid var(--borda)}
.quadro{max-width:960px}
.par{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
.esq{flex:1 1 300px;min-width:0}
.resp{flex:1 1 300px;min-width:0}
.botoes{display:flex;gap:6px;flex-wrap:wrap}
.tres{display:flex;gap:8px;flex-wrap:wrap}
.tres figure{margin:0;flex:1 1 180px;min-width:0}
.tres figcaption{font-size:13px;color:var(--suave);margin-top:2px}
input[type=text]{width:100%;max-width:420px}
label{display:block;margin-top:10px}
</style></head><body>
<header>
  <b>Dedos do gabarito</b><span id="video" class="suave"></span>
  <progress id="barra" max="40" value="0"></progress>
  <span id="progresso" class="suave"></span>
  <span id="status">carregando…</span>
</header>
<div class="linha">
  <button id="ant">← anterior</button>
  <span id="posicao"></span>
  <button id="prox">próxima →</button>
  <span class="suave">setas ← → mudam de nota</span>
</div>
<div id="lista"></div>
<div id="info" class="linha"><b></b></div>
<div id="acorde"></div>
<div id="avisos"></div>

<h3>Quadro (a nota está no retângulo vermelho; as outras da coluna são as do acorde)</h3>
<img id="img-quadro" class="quadro" alt="quadro do vídeo">

<div class="par">
  <div class="esq">
    <h3>Mão esquerda (no braço)</h3>
    <img id="img-esq" alt="mão esquerda">
  </div>
  <div class="resp">
    <h3 id="pergunta-esq">Mão esquerda: que dedo pisa esta nota?</h3>
    <div id="btn-esq" class="botoes"></div>
    <div class="suave">teclas 1 2 3 4 0 · x = não dá para ver</div>
    <h3 id="pergunta-dir">Mão direita: que dedo toca esta nota?</h3>
    <div id="btn-dir" class="botoes"></div>
    <div class="suave">teclas p i m a c · z = não dá para ver</div>
    <label>Observação (opcional)
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
let INDICE = null, G = null, atual = 0;

const $ = id => document.getElementById(id);
function completa(n) { return n.esquerda != null && n.direita != null; }
function infoDe(n) { return INDICE.notas.find(x => x.id === n.id); }
function setStatus(t, c) { const s = $("status"); s.textContent = t; s.className = c || ""; }

function progresso() {
  const f = G.notas.filter(completa).length;
  $("progresso").textContent = f + "/" + G.notas.length + " completas";
  $("barra").value = f;
}

function botoes(id, opcoes, campo, n) {
  const c = $(id); c.replaceChildren();
  for (const [tecla, nome] of opcoes) {
    const b = document.createElement("button");
    b.textContent = tecla + " · " + nome;
    b.className = n[campo] === tecla ? "on" : "";
    b.onclick = () => escolher(campo, tecla);
    c.append(b);
  }
}

function lista() {
  const l = $("lista"); l.replaceChildren();
  G.notas.forEach((n, k) => {
    const b = document.createElement("button");
    const parcial = n.esquerda != null || n.direita != null;
    b.textContent = String(k + 1).padStart(2, "0") + (completa(n) ? " ✓" : parcial ? " ·" : "");
    b.className = (k === atual ? "on " : "") + (completa(n) ? "ok" : "");
    b.onclick = () => { atual = k; mostrar(); };
    l.append(b);
  });
}

function mostrar() {
  const n = G.notas[atual], i = infoDe(n), base = "/" + i.pasta + "/";
  $("posicao").textContent = (atual + 1) + " / " + G.notas.length;
  $("info").firstChild.textContent = n.id + " · t=" + n.t_ini + " s · corda " + n.corda + " · casa " + n.casa + " · tela " + i.tela;
  $("acorde").textContent = i.texto_acorde ?? "";
  if (i.pergunta_esquerda) $("pergunta-esq").textContent = i.pergunta_esquerda;
  if (i.pergunta_direita) $("pergunta-dir").textContent = i.pergunta_direita;
  $("avisos").replaceChildren(...i.avisos.map(a => { const d = document.createElement("div"); d.className = "aviso"; d.textContent = a; return d; }));
  $("img-quadro").src = base + "quadro.jpg";
  $("img-esq").src = base + "esq.jpg";
  $("dir-m").src = base + "dir_m.jpg";
  $("dir-0").src = base + "dir_0.jpg";
  $("dir-p").src = base + "dir_p.jpg";
  botoes("btn-esq", ESQUERDA, "esquerda", n);
  botoes("btn-dir", DIREITA, "direita", n);
  $("obs").value = n.obs || "";
  lista(); progresso();
}

async function gravar(campo, valor, avancar) {
  const k = atual, n = G.notas[k], antes = completa(n), anterior = n[campo];
  n[campo] = valor;
  mostrar();
  setStatus("gravando…", "");
  try {
    const r = await fetch("/responder", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id: n.id, [campo]: valor})});
    const j = await r.json();
    if (!j.ok) throw new Error(j.erro);
    setStatus("salvo em disco " + j.salvo_em.slice(11) + " (" + j.completas + "/" + j.total + " completas)", "ok");
  } catch (e) {
    n[campo] = anterior;
    mostrar();
    setStatus("NÃO SALVO (" + e.message + "): tente de novo", "ruim");
    return;
  }
  if (avancar && !antes && completa(n) && atual === k && k < G.notas.length - 1) atual = k + 1;
  mostrar();
}

function escolher(campo, valor) {
  const n = G.notas[atual];
  gravar(campo, n[campo] === valor ? null : valor, true);
}

function anterior() { if (atual > 0) { atual--; mostrar(); } }
function proxima() { if (atual < G.notas.length - 1) { atual++; mostrar(); } }
$("ant").onclick = anterior;
$("prox").onclick = proxima;
$("obs").addEventListener("change", ev => gravar("obs", ev.target.value, false));

document.addEventListener("keydown", ev => {
  if (ev.ctrlKey || ev.metaKey || ev.altKey || !G) return;
  const t = ev.target.tagName;
  if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return;
  const k = ev.key.toLowerCase();
  if (ev.key === "ArrowRight") proxima();
  else if (ev.key === "ArrowLeft") anterior();
  else if (Object.hasOwn(TECLAS_ESQ, k)) escolher("esquerda", TECLAS_ESQ[k]);
  else if (Object.hasOwn(TECLAS_DIR, k)) escolher("direita", TECLAS_DIR[k]);
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
  $("video").textContent = G.video;
  atual = Math.max(0, G.notas.findIndex(n => !completa(n)));
  setStatus("carregado: " + (G.notas.some(n => n.esquerda != null || n.direita != null) ? "retomando" : "gabarito novo"), "ok");
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
    """Ponto de entrada: ``servir`` (o ``preparar`` está em ``tab.maos_gabarito_preparar``).

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
    args = ap.parse_args()
    return servir(args.pasta, args.ouro, args.porta, args.host)


if __name__ == "__main__":
    sys.exit(main())
