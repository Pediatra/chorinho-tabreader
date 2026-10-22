"""Cortes de câmera no acervo: a medida (b) da decisão 1009.

A decisão 1009 pede que a impressão de "câmera parada" da maioria dos vídeos-aula seja
medida. Aqui, numa amostra do censo de mãos, conta-se quantas trocas de plano cada vídeo
tem e quantas por minuto.

Método:

- Só os quadros-chave de cada vídeo são decodificados (``-discard nokey``, no demuxer).
  Isso é rápido e cai nas trocas de cena, porque o codificador põe um quadro-chave no
  corte. É uma suposição: por vídeo, confere-se que o número de quadros decodificados
  bate com o número de pacotes marcados como chave (``ffprobe``), e falha alto se não
  bater. ``-skip_frame nokey`` não serve: no VP9 o decodificador ignora o pedido e
  entrega o vídeo inteiro (medido: 25.527 quadros para 223 chaves).
- A tablatura sai da comparação: a união das caixas do censo daquele vídeo é excluída.
  Sem caixa, o quadro inteiro entra.
- A distância entre quadros-chave consecutivos é a de Bhattacharyya do histograma HSV
  fora da máscara (16 x 8 x 8 faixas). A diferença média absoluta em cinza, fora da
  máscara, é a segunda medida.
- Corte é distância acima do limiar. O limiar não é escolhido às cegas: ``medir`` grava a
  distribuição de todas as distâncias e uma tabela de sensibilidade, e só conta cortes
  quando recebe um limiar (``--limiar``, ou ``LIMIAR_CORTE``).

Uso::

    python -m tab.maos_cortes medir                 # distribuição e sensibilidade
    python -m tab.maos_cortes medir --limiar 0.4    # também conta cortes e grava folhas
"""

from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import tempfile
import unicodedata
from collections.abc import Iterator, Sequence
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from tab.comum.caminhos import CENSO_MAOS, MAOS_M11, acervo

#: Resolução em que os quadros entram na comparação (largura, altura).
LARGURA_ANALISE = 192
ALTURA_ANALISE = 108
#: Resolução dos quadros nas folhas de conferência.
LARGURA_FOLHA = 384
ALTURA_FOLHA = 216
#: Faixas do histograma HSV (matiz, saturação, valor).
FAIXAS_HSV = (16, 8, 8)
#: Semente e tamanho da amostra (briefing da medida).
SEMENTE = 20261017
POR_CANAL = 3
#: Limiar de corte sobre a distância de Bhattacharyya.
#: Escolhido pela distribuição de 3.194 pares (53 vídeos, rodada 1009-b): o histograma tem
#: um modo de "mesma cena" entre 0,05 e 0,20 (1.170 pares em 0,10-0,15), e o primeiro
#: mínimo depois dele é em 0,30 (39 pares em 0,30-0,35, contra 65 em 0,25-0,30 e 46 em
#: 0,35-0,40). O vale é raso: a cauda de 0,35 a 1,0 é quase plana. Por isso a tabela de
#: sensibilidade (``sensibilidade.json``) e a conferência visual dizem o quanto a
#: contagem depende deste número.
LIMIAR_CORTE: float | None = 0.30
#: Limiares da tabela de sensibilidade.
GRADE_BHATTACHARYYA = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
GRADE_MAD = (10.0, 20.0, 30.0, 40.0, 60.0, 80.0)
#: Pares logo abaixo do limiar que entram na folha dos quase-cortes.
QUASE_CORTES = 20
#: Quantis gravados na distribuição.
QUANTIS = (0.5, 0.75, 0.9, 0.95, 0.99, 0.999)
#: Cor das caixas da tablatura nas folhas (BGR).
COR_CAIXA = (0, 255, 0)


class Quadro(NamedTuple):
    """Assinatura de um quadro-chave, já sem a tablatura.

    Attributes:
        t: instante do quadro, em segundos.
        hist: histograma HSV normalizado (soma 1), fora da máscara.
        cinza: tons de cinza dos pixels fora da máscara.
    """

    t: float
    hist: np.ndarray
    cinza: np.ndarray


class Par(NamedTuple):
    """Distância entre dois quadros-chave consecutivos de um vídeo.

    Attributes:
        i: índice do quadro-chave anterior (o posterior é ``i + 1``).
        t_a: instante do quadro anterior, em segundos.
        t_b: instante do quadro posterior, em segundos.
        bhattacharyya: distância de Bhattacharyya dos histogramas (0 igual, 1 disjunto).
        mad: diferença média absoluta em cinza, fora da máscara (0 a 255).
    """

    i: int
    t_a: float
    t_b: float
    bhattacharyya: float
    mad: float


def escala_do_rect(
    rect: Sequence[float],
    largura: int,
    altura: int,
    alvo: tuple[int, int] = (LARGURA_ANALISE, ALTURA_ANALISE),
) -> tuple[int, int, int, int]:
    """Leva a caixa do censo (pixels do vídeo) para a resolução ``alvo``.

    Args:
        rect: ``[x0, y0, x1, y1]`` em pixels do vídeo original.
        largura: largura do vídeo original, em pixels.
        altura: altura do vídeo original, em pixels.
        alvo: ``(largura, altura)`` da imagem de destino.

    Returns:
        ``(x0, y0, x1, y1)`` no destino, arredondado para fora e limitado à imagem.
    """
    largura_alvo, altura_alvo = alvo
    x0, y0, x1, y1 = (float(v) for v in rect)
    return (
        max(0, math.floor(x0 * largura_alvo / largura)),
        max(0, math.floor(y0 * altura_alvo / altura)),
        min(largura_alvo, math.ceil(x1 * largura_alvo / largura)),
        min(altura_alvo, math.ceil(y1 * altura_alvo / altura)),
    )


def mascara_da_tablatura(
    rects: Sequence[Sequence[float]], largura: int, altura: int
) -> np.ndarray:
    """Máscara da análise: 255 onde a comparação vale, 0 onde está a tablatura.

    Args:
        rects: caixas da tablatura do vídeo, em pixels do vídeo original (pode ser vazia).
        largura: largura do vídeo original, em pixels.
        altura: altura do vídeo original, em pixels.

    Returns:
        Array ``(ALTURA_ANALISE, LARGURA_ANALISE)`` uint8.
    """
    mascara = np.full((ALTURA_ANALISE, LARGURA_ANALISE), 255, dtype=np.uint8)
    for rect in rects:
        x0, y0, x1, y1 = escala_do_rect(rect, largura, altura)
        mascara[y0:y1, x0:x1] = 0
    return mascara


def assinatura(quadro: np.ndarray, t: float, mascara: np.ndarray) -> Quadro:
    """Histograma HSV e tons de cinza de um quadro, fora da máscara.

    Args:
        quadro: imagem BGR uint8 na resolução da análise.
        t: instante do quadro, em segundos.
        mascara: máscara de ``mascara_da_tablatura``.

    Returns:
        A assinatura do quadro.

    Raises:
        ValueError: se a máscara não deixa nenhum pixel de fora da tablatura.
    """
    util = mascara > 0
    if not util.any():
        raise ValueError("a tablatura cobre o quadro inteiro: nada para comparar")
    hsv = cv2.cvtColor(quadro, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist(
        [hsv], [0, 1, 2], mascara, list(FAIXAS_HSV), [0, 180, 0, 256, 0, 256]
    )
    hist = hist.ravel().astype(np.float32)
    hist /= hist.sum()
    cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)[util]
    return Quadro(t=t, hist=hist, cinza=cinza)


def distancia(a: Quadro, b: Quadro) -> tuple[float, float]:
    """Distância de Bhattacharyya dos histogramas e diferença média absoluta em cinza.

    Args:
        a: quadro anterior.
        b: quadro posterior (mesma máscara que ``a``).

    Returns:
        ``(bhattacharyya, mad)``.
    """
    bhatt = float(cv2.compareHist(a.hist, b.hist, cv2.HISTCMP_BHATTACHARYYA))
    mad = float(np.abs(a.cinza.astype(np.int16) - b.cinza.astype(np.int16)).mean())
    return bhatt, mad


def pares_consecutivos(quadros: Sequence[Quadro]) -> list[Par]:
    """Distâncias entre cada quadro-chave e o seguinte.

    Args:
        quadros: assinaturas em ordem de tempo, do mesmo vídeo.

    Returns:
        Um ``Par`` por par consecutivo (vazio se há menos de dois quadros).
    """
    pares = []
    for i, (a, b) in enumerate(pairwise(quadros)):
        bhatt, mad = distancia(a, b)
        pares.append(Par(i, a.t, b.t, bhatt, mad))
    return pares


def cortes(pares: Sequence[Par], limiar: float) -> list[Par]:
    """Pares cuja distância de Bhattacharyya passa do limiar.

    Args:
        pares: distâncias consecutivas de um vídeo.
        limiar: limiar de corte (corte é distância estritamente acima dele).

    Returns:
        Os pares que são cortes.
    """
    return [p for p in pares if p.bhattacharyya > limiar]


def sortear(
    linhas: Sequence[dict], semente: int = SEMENTE, por_canal: int = POR_CANAL
) -> list[dict]:
    """Sorteia até ``por_canal`` vídeos de cada canal, com semente fixa.

    Os canais são percorridos em ordem alfabética, e a lista de cada canal é ordenada por
    ``arquivo`` antes do sorteio, para o resultado não depender da ordem do censo. Canal
    com ``por_canal`` ou menos vídeos entra inteiro.

    Args:
        linhas: linhas do censo de mãos (uma por vídeo, com ``canal`` e ``arquivo``).
        semente: semente do ``random.Random`` do sorteio.
        por_canal: quantos vídeos sortear por canal.

    Returns:
        Os vídeos sorteados, agrupados por canal.
    """
    grupos: dict[str, list[dict]] = {}
    for linha in linhas:
        grupos.setdefault(linha["canal"], []).append(linha)
    rng = random.Random(semente)
    sorteados: list[dict] = []
    for canal in sorted(grupos):
        videos = sorted(grupos[canal], key=lambda linha: linha["arquivo"])
        if len(videos) > por_canal:
            videos = sorted(
                rng.sample(videos, por_canal), key=lambda linha: linha["arquivo"]
            )
        sorteados.extend(videos)
    return sorteados


def ler_censo(caminho: Path) -> list[dict]:
    """Lê o censo de mãos: uma linha JSON por vídeo.

    Args:
        caminho: arquivo ``.jsonl`` do censo.

    Returns:
        As linhas do censo, na ordem do arquivo.
    """
    with caminho.open(encoding="utf-8") as arquivo:
        return [json.loads(linha) for linha in arquivo if linha.strip()]


def _ffprobe(args: list[str]) -> str:
    """Roda o ffprobe e devolve a saída padrão.

    Args:
        args: argumentos depois de ``ffprobe -v error``.

    Returns:
        O texto que o ffprobe escreveu na saída padrão.

    Raises:
        RuntimeError: se o ffprobe falhar.
    """
    proc = subprocess.run(
        ["ffprobe", "-v", "error", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falhou: {proc.stderr.strip()}")
    return proc.stdout


def tempos_chave(video: Path) -> list[float]:
    """Instantes (em s) dos pacotes marcados como quadro-chave, em ordem de tempo.

    O ffprobe lê só os pacotes, sem decodificar. A ordem é a de apresentação (ordenada),
    que é a mesma em que o ffmpeg entrega os quadros.

    Args:
        video: caminho do vídeo (somente leitura).

    Returns:
        Os instantes dos quadros-chave.
    """
    saida = _ffprobe(
        [
            "-select_streams",
            "v:0",
            "-show_entries",
            "packet=pts_time,flags",
            "-of",
            "csv=p=0",
            str(video),
        ]
    )
    tempos = []
    for linha in saida.splitlines():
        pts, _, flags = linha.partition(",")
        if flags.startswith("K"):
            tempos.append(float(pts))
    return sorted(tempos)


def dimensoes_e_duracao(video: Path) -> tuple[int, int, float]:
    """Largura, altura (pixels) e duração (s) do primeiro fluxo de vídeo.

    Args:
        video: caminho do vídeo (somente leitura).

    Returns:
        ``(largura, altura, duracao)``.
    """
    saida = _ffprobe(
        [
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(video),
        ]
    )
    dados = json.loads(saida)
    fluxo = dados["streams"][0]
    return int(fluxo["width"]), int(fluxo["height"]), float(dados["format"]["duration"])


def _quadros_brutos(video: Path, largura: int, altura: int) -> Iterator[np.ndarray]:
    """Quadros-chave do vídeo em BGR, decodificados pelo ffmpeg.

    Só os quadros-chave saem (``-discard nokey``), na ordem do vídeo. Um quadro
    truncado ou um ffmpeg que falha levanta erro: nada é descartado em silêncio.

    Args:
        video: caminho do vídeo (somente leitura).
        largura: largura de saída, em pixels.
        altura: altura de saída, em pixels.

    Yields:
        Um array ``(altura, largura, 3)`` uint8 por quadro-chave. O array é só leitura.

    Raises:
        RuntimeError: se o ffmpeg falhar ou o último quadro vier truncado.
    """
    tamanho = largura * altura * 3
    comando = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-discard",
        "nokey",
        "-i",
        str(video),
        "-vf",
        f"scale={largura}:{altura}",
        "-fps_mode",
        "passthrough",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-",
    ]
    # O erro vai para um arquivo, não para um pipe: um pipe cheio travaria o ffmpeg.
    with tempfile.TemporaryFile() as erros:
        proc = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=erros)
        try:
            while True:
                bruto = proc.stdout.read(tamanho)
                if not bruto:
                    break
                if len(bruto) != tamanho:
                    raise RuntimeError(f"quadro truncado em {video.name}")
                yield np.frombuffer(bruto, dtype=np.uint8).reshape(altura, largura, 3)
            codigo = proc.wait()
            if codigo != 0:
                erros.seek(0)
                texto = erros.read().decode("utf-8", "replace").strip()
                raise RuntimeError(f"ffmpeg falhou em {video.name}: {texto}")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdout.close()


def _frames_em_escala(
    video: Path, indices: set[int], largura: int, altura: int
) -> dict[int, np.ndarray]:
    """Quadros-chave de índices pedidos (e os seguintes), na escala dada.

    Args:
        video: caminho do vídeo (somente leitura).
        indices: índices dos quadros-chave anteriores dos pares pedidos.
        largura: largura de saída, em pixels.
        altura: altura de saída, em pixels.

    Returns:
        Um quadro BGR (cópia) por índice pedido e por índice seguinte.

    Raises:
        RuntimeError: se algum quadro pedido não existir no vídeo.
    """
    alvo = set(indices) | {i + 1 for i in indices}
    achados: dict[int, np.ndarray] = {}
    gerador = _quadros_brutos(video, largura, altura)
    try:
        for n, quadro in enumerate(gerador):
            if n in alvo:
                achados[n] = quadro.copy()
            if len(achados) == len(alvo):
                break
    finally:
        gerador.close()
    if len(achados) != len(alvo):
        faltam = sorted(alvo - achados.keys())
        raise RuntimeError(f"faltam quadros em {video.name}: {faltam}")
    return achados


def medir_video(linha: dict, raiz: Path) -> tuple[dict, list[Par]]:
    """Mede um vídeo: estatísticas e distâncias entre quadros-chave consecutivos.

    Args:
        linha: linha do censo de mãos desse vídeo (``arquivo``, ``canal``, ``largura``,
            ``altura``, ``quadros`` com ``tab`` e ``rect``).
        raiz: pasta do acervo.

    Returns:
        ``(estatisticas, pares)``. As estatísticas não têm contagem de cortes: ela
        depende do limiar e é feita por ``contar``.

    Raises:
        ValueError: se as dimensões do censo não batem com as do vídeo, ou se a
            decodificação dá um número de quadros diferente do de pacotes-chave.
    """
    video = raiz / linha["arquivo"]
    largura, altura, duracao = dimensoes_e_duracao(video)
    if (largura, altura) != (linha["largura"], linha["altura"]):
        raise ValueError(
            f"dimensões do censo ({linha['largura']}x{linha['altura']}) diferentes "
            f"do vídeo ({largura}x{altura})"
        )
    rects = [q["rect"] for q in linha["quadros"] if q.get("rect")]
    mascara = mascara_da_tablatura(rects, largura, altura)
    tempos = tempos_chave(video)
    brutos = list(_quadros_brutos(video, LARGURA_ANALISE, ALTURA_ANALISE))
    if len(brutos) != len(tempos):
        raise ValueError(
            f"{len(brutos)} quadros decodificados para {len(tempos)} pacotes-chave"
        )
    quadros = [
        assinatura(quadro, t, mascara) for quadro, t in zip(brutos, tempos, strict=True)
    ]
    pares = pares_consecutivos(quadros)
    intervalo = round(float(np.median(np.diff(tempos))), 3) if len(tempos) > 1 else None
    estatisticas = {
        "arquivo": linha["arquivo"],
        "canal": linha["canal"],
        "duracao_s": round(duracao, 3),
        "quadros_chave": len(tempos),
        "intervalo_mediano_s": intervalo,
        "fracao_util": round(float(np.count_nonzero(mascara)) / mascara.size, 4),
        "tab_no_censo": any(q["tab"] for q in linha["quadros"]),
        "erro": None,
    }
    return estatisticas, pares


def contar(estatisticas: dict, pares: Sequence[Par], limiar: float) -> dict:
    """Número de cortes do vídeo e de cortes por minuto, para um limiar.

    Args:
        estatisticas: saída de ``medir_video`` (usa ``duracao_s``).
        pares: distâncias consecutivas do vídeo.
        limiar: limiar de corte.

    Returns:
        ``{"cortes": n, "cortes_por_min": x}``; ``x`` é ``None`` se a duração for zero.
    """
    n = len(cortes(pares, limiar))
    minutos = estatisticas["duracao_s"] / 60
    return {
        "cortes": n,
        "cortes_por_min": round(n / minutos, 4) if minutos > 0 else None,
    }


def distribuicao(pares: Sequence[Par]) -> dict:
    """Quantis e histogramas das distâncias, sobre todos os pares medidos.

    Args:
        pares: todos os pares de todos os vídeos medidos.

    Returns:
        Um dicionário com a contagem de pares, os quantis e os histogramas.
    """
    if not pares:
        return {"pares": 0}
    bh = np.array([p.bhattacharyya for p in pares])
    md = np.array([p.mad for p in pares])
    arestas_bh = np.linspace(0.0, 1.0, 21)
    arestas_md = np.arange(0.0, 260.0, 10.0)
    cont_bh, _ = np.histogram(bh, bins=arestas_bh)
    cont_md, _ = np.histogram(md, bins=arestas_md)
    return {
        "pares": len(pares),
        "quantis_bhattacharyya": {str(q): float(np.quantile(bh, q)) for q in QUANTIS},
        "quantis_mad": {str(q): float(np.quantile(md, q)) for q in QUANTIS},
        "histograma_bhattacharyya": {
            "arestas": arestas_bh.round(2).tolist(),
            "contagem": cont_bh.tolist(),
        },
        "histograma_mad": {
            "arestas": arestas_md.tolist(),
            "contagem": cont_md.tolist(),
        },
    }


def sensibilidade(pares: Sequence[tuple[str, Par]]) -> dict:
    """Quantos cortes e vídeos com corte cada limiar da grade daria.

    Args:
        pares: pares de ``(arquivo, Par)`` de todos os vídeos medidos.

    Returns:
        Tabelas por limiar, para Bhattacharyya e para a diferença média em cinza.
    """
    por_bh = {}
    for limiar in GRADE_BHATTACHARYYA:
        acima = [(a, p) for a, p in pares if p.bhattacharyya > limiar]
        por_bh[str(limiar)] = {
            "cortes": len(acima),
            "videos_com_corte": len({a for a, _ in acima}),
        }
    por_mad = {}
    for limiar in GRADE_MAD:
        acima = [(a, p) for a, p in pares if p.mad > limiar]
        por_mad[str(limiar)] = {
            "pares": len(acima),
            "videos_com_par": len({a for a, _ in acima}),
        }
    return {"pares": len(pares), "bhattacharyya": por_bh, "mad": por_mad}


def _linha_da_tabela(nome: str, grupo: Sequence[dict]) -> dict:
    """Uma linha da tabela por canal: vídeos, minutos, cortes e cortes por minuto."""
    minutos = sum(v["duracao_s"] for v in grupo) / 60
    cortes_n = sum(v["cortes"] for v in grupo)
    por_video = [v["cortes_por_min"] for v in grupo if v["cortes_por_min"] is not None]
    return {
        "canal": nome,
        "videos": len(grupo),
        "minutos": round(minutos, 1),
        "cortes": cortes_n,
        "cortes_por_min": round(cortes_n / minutos, 3) if minutos > 0 else None,
        "mediana_por_video": round(float(np.median(por_video)), 3)
        if por_video
        else None,
        "sem_corte": sum(1 for v in grupo if v["cortes"] == 0),
    }


def tabela_por_canal(videos: Sequence[dict]) -> list[dict]:
    """Tabela por canal (e total), só com os vídeos medidos sem erro.

    Args:
        videos: estatísticas de todos os vídeos, já com ``cortes``.

    Returns:
        Uma linha por canal, em ordem alfabética, e a linha ``TOTAL`` no fim.
    """
    ok = [v for v in videos if v["erro"] is None]
    tabela = [
        _linha_da_tabela(canal, [v for v in ok if v["canal"] == canal])
        for canal in sorted({v["canal"] for v in ok})
    ]
    tabela.append(_linha_da_tabela("TOTAL", ok))
    return tabela


def _ascii(texto: str) -> str:
    """Versão só ASCII de um texto, para a fonte do OpenCV (sem acento nem kana).

    Args:
        texto: texto original.

    Returns:
        O texto sem os caracteres fora de ASCII (acentos viram a letra base).
    """
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _painel(
    antes: np.ndarray,
    depois: np.ndarray,
    caixas: Sequence[tuple[int, int, int, int]],
    legenda: Sequence[str],
) -> np.ndarray:
    """Um par de quadros lado a lado, com as caixas da tablatura e a legenda.

    Args:
        antes: quadro anterior, BGR, na escala da folha.
        depois: quadro posterior, BGR, na escala da folha.
        caixas: caixas da tablatura do censo, na escala da folha.
        legenda: linhas de texto (ASCII) da faixa de cima.

    Returns:
        A imagem do painel.
    """

    def com_caixas(quadro: np.ndarray) -> np.ndarray:
        """Cópia do quadro com a tablatura do censo contornada."""
        saida = quadro.copy()
        for x0, y0, x1, y1 in caixas:
            cv2.rectangle(saida, (x0, y0), (x1 - 1, y1 - 1), COR_CAIXA, 1)
        return saida

    separador = np.full((ALTURA_FOLHA, 6, 3), 255, dtype=np.uint8)
    corpo = np.hstack([com_caixas(antes), separador, com_caixas(depois)])
    faixa = np.full((44, corpo.shape[1], 3), 30, dtype=np.uint8)
    for n, texto in enumerate(legenda):
        cv2.putText(
            faixa,
            texto,
            (6, 16 + 16 * n),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return np.vstack([faixa, corpo])


def _grade(paineis: Sequence[np.ndarray], colunas: int) -> np.ndarray:
    """Junta painéis de mesmo tamanho numa grade, com espaço branco entre eles.

    Args:
        paineis: imagens de mesmo tamanho.
        colunas: painéis por linha.

    Returns:
        A imagem da grade.
    """
    altura = paineis[0].shape[0]
    gap = 10
    linhas = []
    for k in range(0, len(paineis), colunas):
        fila = list(paineis[k : k + colunas])
        fila += [np.full_like(paineis[0], 255)] * (colunas - len(fila))
        blocos = []
        for n, painel in enumerate(fila):
            if n:
                blocos.append(np.full((altura, gap, 3), 255, dtype=np.uint8))
            blocos.append(painel)
        linhas.append(np.hstack(blocos))
        linhas.append(np.full((gap, linhas[-1].shape[1], 3), 255, dtype=np.uint8))
    return np.vstack(linhas[:-1])


def folhas(
    pasta: Path,
    raiz: Path,
    linhas_por_arquivo: dict[str, dict],
    vids: dict[str, int],
    limiar: float,
    pares: Sequence[tuple[str, Par]],
) -> dict[tuple[str, int], str]:
    """Grava a conferência visual: uma imagem por corte e a folha dos quase-cortes.

    Cada corte vira um painel "antes | depois" (quadros-chave consecutivos), com a
    tablatura do censo contornada em verde. A folha ``quase_cortes.jpg`` reúne os
    ``QUASE_CORTES`` pares de maior distância que ficaram abaixo do limiar.

    Args:
        pasta: pasta de saída das imagens.
        raiz: pasta do acervo.
        linhas_por_arquivo: linha do censo de cada vídeo, pelo ``arquivo``.
        vids: número de conferência (``V01``...) de cada vídeo, pelo ``arquivo``.
        limiar: limiar de corte.
        pares: ``(arquivo, Par)`` de todos os vídeos medidos.

    Returns:
        O nome da imagem de cada corte, pela chave ``(arquivo, índice do par)``.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    cortes_ = sorted(
        ((a, p) for a, p in pares if p.bhattacharyya > limiar),
        key=lambda ap: (vids[ap[0]], ap[1].t_a),
    )
    abaixo = sorted(
        (ap for ap in pares if ap[1].bhattacharyya <= limiar),
        key=lambda ap: -ap[1].bhattacharyya,
    )[:QUASE_CORTES]
    pedidos: dict[str, set[int]] = {}
    for arquivo, par in [*cortes_, *abaixo]:
        pedidos.setdefault(arquivo, set()).add(par.i)
    quadros: dict[tuple[str, int], np.ndarray] = {}
    for arquivo, indices in pedidos.items():
        achados = _frames_em_escala(
            raiz / arquivo, indices, LARGURA_FOLHA, ALTURA_FOLHA
        )
        quadros.update({(arquivo, i): q for i, q in achados.items()})

    def painel(arquivo: str, par: Par) -> np.ndarray:
        """Painel de um par, com a legenda do vídeo, do tempo e da distância."""
        linha = linhas_por_arquivo[arquivo]
        caixas = [
            escala_do_rect(
                q["rect"],
                linha["largura"],
                linha["altura"],
                (LARGURA_FOLHA, ALTURA_FOLHA),
            )
            for q in linha["quadros"]
            if q.get("rect")
        ]
        legenda = [
            f"V{vids[arquivo]:02d} {_ascii(linha['canal'])}  "
            f"t={par.t_a:.2f}->{par.t_b:.2f}s",
            f"bhatt={par.bhattacharyya:.3f}  mad={par.mad:.1f}  "
            "(verde = tablatura do censo)",
        ]
        return _painel(
            quadros[(arquivo, par.i)],
            quadros[(arquivo, par.i + 1)],
            caixas,
            legenda,
        )

    nomes: dict[tuple[str, int], str] = {}
    for k, (arquivo, par) in enumerate(cortes_, start=1):
        nome = f"corte_{k:03d}_V{vids[arquivo]:02d}.jpg"
        cv2.imwrite(
            str(pasta / nome), painel(arquivo, par), [cv2.IMWRITE_JPEG_QUALITY, 90]
        )
        nomes[(arquivo, par.i)] = nome
    if abaixo:
        paineis = [painel(arquivo, par) for arquivo, par in abaixo]
        cv2.imwrite(
            str(pasta / "quase_cortes.jpg"),
            _grade(paineis, colunas=2),
            [cv2.IMWRITE_JPEG_QUALITY, 88],
        )
    return nomes


def _gravar_json(caminho: Path, dados: object) -> None:
    """Grava um objeto em JSON legível (UTF-8).

    Args:
        caminho: arquivo de saída.
        dados: objeto serializável.
    """
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def _gravar_jsonl(caminho: Path, registros: Sequence[dict]) -> None:
    """Grava uma linha JSON por registro (UTF-8).

    Args:
        caminho: arquivo de saída.
        registros: registros serializáveis.
    """
    with caminho.open("w", encoding="utf-8") as arquivo:
        for registro in registros:
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def medir(
    linhas: Sequence[dict],
    raiz: Path,
    saida: Path,
    limiar: float | None,
    por_canal: int,
    semente: int,
    com_folhas: bool,
) -> list[dict]:
    """Mede a amostra sorteada e grava os resultados em ``saida``.

    Grava sempre: ``amostra.json``, ``distancias.jsonl`` (todas as distâncias),
    ``distribuicao.json``, ``sensibilidade.json`` e ``videos.jsonl``. Com ``limiar``,
    grava também ``cortes.jsonl``, ``canais.json`` e, se ``com_folhas``, as folhas.

    Args:
        linhas: linhas do censo de mãos.
        raiz: pasta do acervo.
        saida: pasta de saída.
        limiar: limiar de corte, ou ``None`` para só medir a distribuição.
        por_canal: vídeos sorteados por canal.
        semente: semente do sorteio.
        com_folhas: se ``True`` (e com limiar), grava as imagens de conferência.

    Returns:
        As estatísticas de cada vídeo da amostra, na ordem de ``vid``.
    """
    saida.mkdir(parents=True, exist_ok=True)
    amostra = sorted(
        sortear(linhas, semente, por_canal),
        key=lambda linha: (linha["canal"], linha["arquivo"]),
    )
    vids = {linha["arquivo"]: n for n, linha in enumerate(amostra, start=1)}
    por_arquivo = {linha["arquivo"]: linha for linha in amostra}
    _gravar_json(
        saida / "amostra.json",
        [
            {
                "vid": vids[linha["arquivo"]],
                "canal": linha["canal"],
                "arquivo": linha["arquivo"],
            }
            for linha in amostra
        ],
    )

    videos: list[dict] = []
    pares_todos: list[tuple[str, Par]] = []
    registros_distancia: list[dict] = []
    for linha in amostra:
        arquivo = linha["arquivo"]
        try:
            estatisticas, pares = medir_video(linha, raiz)
        except Exception as erro:  # o erro vai para videos.jsonl; nada se perde
            estatisticas = {
                "arquivo": arquivo,
                "canal": linha["canal"],
                "erro": f"{type(erro).__name__}: {erro}",
            }
            pares = []
        estatisticas["vid"] = vids[arquivo]
        if limiar is not None and estatisticas["erro"] is None:
            estatisticas.update(contar(estatisticas, pares, limiar))
        videos.append(estatisticas)
        for par in pares:
            pares_todos.append((arquivo, par))
            registros_distancia.append(
                {
                    "vid": vids[arquivo],
                    "arquivo": arquivo,
                    "t_a": round(par.t_a, 4),
                    "t_b": round(par.t_b, 4),
                    "bhattacharyya": round(par.bhattacharyya, 6),
                    "mad": round(par.mad, 4),
                }
            )
        resumo = (
            f"erro: {estatisticas['erro']}"
            if estatisticas["erro"]
            else f"{estatisticas['quadros_chave']} quadros-chave, {len(pares)} pares"
        )
        print(
            f"V{vids[arquivo]:02d} {linha['canal']} | {resumo}",
            flush=True,
        )

    _gravar_jsonl(saida / "distancias.jsonl", registros_distancia)
    _gravar_jsonl(saida / "videos.jsonl", videos)
    _gravar_json(saida / "distribuicao.json", distribuicao([p for _, p in pares_todos]))
    _gravar_json(saida / "sensibilidade.json", sensibilidade(pares_todos))

    if limiar is not None:
        nomes = {}
        if com_folhas:
            nomes = folhas(
                saida / "folhas", raiz, por_arquivo, vids, limiar, pares_todos
            )
        cortes_lista = sorted(
            (
                {
                    "vid": vids[arquivo],
                    "arquivo": arquivo,
                    "canal": por_arquivo[arquivo]["canal"],
                    "t_a": round(par.t_a, 4),
                    "t_b": round(par.t_b, 4),
                    "bhattacharyya": round(par.bhattacharyya, 6),
                    "mad": round(par.mad, 4),
                    "imagem": nomes.get((arquivo, par.i)),
                }
                for arquivo, par in pares_todos
                if par.bhattacharyya > limiar
            ),
            key=lambda c: (c["vid"], c["t_a"]),
        )
        _gravar_jsonl(saida / "cortes.jsonl", cortes_lista)
        _gravar_json(saida / "canais.json", tabela_por_canal(videos))
    return videos


def _imprimir_tabela(tabela: Sequence[dict]) -> None:
    """Imprime a tabela por canal em texto alinhado.

    Args:
        tabela: linhas de ``tabela_por_canal``.
    """
    cabecalho = [
        "canal",
        "videos",
        "minutos",
        "cortes",
        "cortes/min",
        "med/video",
        "sem corte",
    ]
    print(" | ".join(cabecalho))
    for linha in tabela:
        print(
            " | ".join(
                [
                    linha["canal"],
                    str(linha["videos"]),
                    f"{linha['minutos']}",
                    str(linha["cortes"]),
                    f"{linha['cortes_por_min']}",
                    f"{linha['mediana_por_video']}",
                    str(linha["sem_corte"]),
                ]
            ),
            flush=True,
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada da CLI: ``python -m tab.maos_cortes medir``.

    Args:
        argv: argumentos da linha de comando (``None`` usa ``sys.argv``).

    Returns:
        Código de saída (0 se rodou, mesmo com vídeos marcados com erro).
    """
    parser = argparse.ArgumentParser(
        prog="python -m tab.maos_cortes",
        description="Cortes de câmera no acervo (medida 1009-b).",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    medir_p = sub.add_parser(
        "medir", help="mede a amostra; com --limiar, conta cortes e grava folhas"
    )
    medir_p.add_argument(
        "--limiar",
        type=float,
        default=LIMIAR_CORTE,
        help="limiar de Bhattacharyya para corte (padrão: LIMIAR_CORTE, None = só distribuição)",
    )
    medir_p.add_argument("--saida", type=Path, default=MAOS_M11 / "cortes")
    medir_p.add_argument("--censo", type=Path, default=CENSO_MAOS)
    medir_p.add_argument(
        "--raiz", type=Path, default=None, help="pasta do acervo (padrão: tab.caminhos)"
    )
    medir_p.add_argument("--por-canal", type=int, default=POR_CANAL)
    medir_p.add_argument("--semente", type=int, default=SEMENTE)
    medir_p.add_argument("--sem-folhas", action="store_true")
    args = parser.parse_args(argv)

    raiz = args.raiz if args.raiz is not None else acervo()
    videos = medir(
        ler_censo(args.censo),
        raiz,
        args.saida,
        args.limiar,
        args.por_canal,
        args.semente,
        com_folhas=not args.sem_folhas,
    )
    erros = [v for v in videos if v["erro"] is not None]
    print(f"\nvídeos: {len(videos)} | com erro: {len(erros)}", flush=True)
    for v in erros:
        print(f"  ERRO V{v['vid']:02d} {v['arquivo']}: {v['erro']}", flush=True)
    if args.limiar is not None:
        _imprimir_tabela(tabela_por_canal(videos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
