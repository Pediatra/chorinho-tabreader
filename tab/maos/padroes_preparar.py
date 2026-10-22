"""Preparo da ferramenta dos padrões da mão direita (M5), sem GPU.

Fase M5 da trilha das mãos (``docs/decisoes/1004-m5-padroes-da-mao-direita.md``). A unidade
é o compasso tocado (tela, compasso, exibição). Para cada compasso sorteado, gera:

- ``clipe.mp4``: o recorte da mão direita do primeiro ao último ``t_ini`` do compasso, com
  0,3 s de margem, em velocidade normal;
- ``clipe_lento.mp4``: o mesmo recorte a 0,5× (``setpts=2*PTS``);
- ``tab.png``: o quadro no meio da janela, com um retângulo em volta das colunas do compasso
  e, embaixo, a lista das notas (corda, casa, tempo).

Sorteia 10 compassos por vídeo, estratificados no tempo, com ``random.Random(20261013)``.
Grava ``indice.json`` e cria ou mescla o gabarito ``padroes_direita.json`` sem apagar
respostas. Não importa o detector de mãos (rtmlib): usa só as pontas já gravadas, então roda
na imagem do gate com ffmpeg e OpenCV.

Uso::

    python -m tab.maos_padroes_preparar
"""

from __future__ import annotations

import argparse
import random
import statistics
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

from tab.comum.arquivos import ler_json as _ler_json
from tab.comum.caminhos import (
    GABARITO_PADROES,
    MAOS_M3C,
    MAOS_M3D,
    MAOS_M5,
    MVP,
    acervo,
)
from tab.maos.gabarito import ampliar_caixa, gravar_atomico
from tab.maos.padroes import gabarito_novo, mesclar_gabarito

#: Semente do sorteio do M5 (a da decisão 1004).
SEMENTE_PADRAO = 20261013

#: Compassos sorteados por vídeo.
N_POR_VIDEO = 10

#: Um compasso só entra na amostra com pelo menos esta quantidade de notas com ``t_ini``.
MIN_NOTAS = 3

#: Margem, em segundos, antes do primeiro e depois do último ``t_ini``.
MARGEM_S = 0.3

#: Folga da caixa da mão direita, por lado, como fração do tamanho da caixa.
FOLGA_MAO = 0.6

#: Tolerância, em segundos, para casar o ``t_ini`` de uma nota com o de um instante.
TOLERANCIA_T = 0.002

#: Quantos instantes mais próximos usar quando o compasso não tem mão direita detectada.
N_PROXIMOS = 5

#: Margem, em pixels, do retângulo que marca o compasso no ``tab.png``.
MARGEM_RETANGULO_PX = 20

#: Os quatro vídeos do M5: o produto (telas e notas) e as pontas das mãos.
VIDEOS = (
    {
        "arquivo": "sky guitar/retrato brasileiro - tab & lesson.mp4",
        "produto": MVP,
        "pontas": MAOS_M3C / "pontas_mvp.json",
    },
    {
        "arquivo": "sky guitar/(chopin) nocturne no.20 - tab & lesson.mp4",
        "produto": MAOS_M3D / "q16_chopin_nocturne20.json",
        "pontas": MAOS_M3D / "pontas_q16.json",
    },
    {
        "arquivo": "sky guitar/lacrimosa (requiem k.626) - guitar lesson + tab.mp4",
        "produto": MAOS_M3D / "sky_4.json",
        "pontas": MAOS_M3D / "pontas_q21.json",
    },
    {
        "arquivo": "sky guitar/glimpse of us (joji) - fingerstyle lesson + tab.mp4",
        "produto": MAOS_M3D / "sky_8.json",
        "pontas": MAOS_M3D / "pontas_q23.json",
    },
)


def _log(msg: str) -> None:
    """Progresso no stderr (o stdout fica para o resumo final).

    Args:
        msg: texto da linha.
    """
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------
# Compassos e amostra (funções puras)
# ---------------------------------------------------------------------------------


def notas_com_tempo(notas: list[dict]) -> list[dict]:
    """Notas que têm ``t_ini``, tela, compasso e exibição (as que o M5 usa).

    Args:
        notas: notas do produto (``notas`` do JSON).

    Returns:
        Lista filtrada, na ordem original.
    """
    chaves = ("t_ini", "tela", "compasso", "exibicao")
    return [n for n in notas if all(n.get(c) is not None for c in chaves)]


def compassos_tocados(notas: list[dict]) -> list[dict]:
    """Agrupa as notas por compasso tocado e mantém os com pelo menos ``MIN_NOTAS``.

    Args:
        notas: notas já filtradas por ``notas_com_tempo``.

    Returns:
        Lista de compassos ``{tela, compasso, exibicao, t0, t1, notas, n_notas}``,
        ordenada por ``t0`` (e pela chave, para desempatar).
    """
    grupos: dict[tuple[int, int, int], list[dict]] = {}
    for nota in notas:
        chave = (nota["tela"], nota["compasso"], nota["exibicao"])
        grupos.setdefault(chave, []).append(nota)
    compassos = []
    for (tela, compasso, exibicao), grupo in grupos.items():
        if len(grupo) < MIN_NOTAS:
            continue
        ordenadas = sorted(grupo, key=lambda n: n["t_ini"])
        compassos.append(
            {
                "tela": tela,
                "compasso": compasso,
                "exibicao": exibicao,
                "t0": ordenadas[0]["t_ini"],
                "t1": ordenadas[-1]["t_ini"],
                "notas": ordenadas,
                "n_notas": len(ordenadas),
            }
        )
    compassos.sort(key=lambda c: (c["t0"], c["tela"], c["compasso"], c["exibicao"]))
    return compassos


def amostrar_compassos(elegiveis: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Sorteia ``n`` compassos estratificados no tempo, um por faixa de contagem igual.

    Se houver menos compassos elegíveis do que ``n``, devolve todos.

    Args:
        elegiveis: compassos de um vídeo (``compassos_tocados``).
        n: quantos sortear (uma faixa por sorteio).
        rng: gerador já semeado.

    Returns:
        Os compassos sorteados, em ordem de tempo.
    """
    ordenados = sorted(elegiveis, key=lambda c: (c["t0"], c["tela"], c["compasso"]))
    if len(ordenados) <= n:
        return ordenados
    total = len(ordenados)
    escolhidos = []
    for k in range(n):
        faixa = ordenados[k * total // n : (k + 1) * total // n]
        escolhidos.append(rng.choice(faixa))
    return sorted(escolhidos, key=lambda c: c["t0"])


# ---------------------------------------------------------------------------------
# Mão direita e janela (funções puras)
# ---------------------------------------------------------------------------------


def caixas_da_direita(instantes: list[dict]) -> list[tuple[float, list[float]]]:
    """Pares ``(t_ini, caixa)`` de cada mão com ``lado`` igual a ``direita``.

    Args:
        instantes: ``instantes`` do arquivo de pontas.

    Returns:
        Lista de pares, na ordem dos instantes.
    """
    pares = []
    for instante in instantes:
        for mao in instante.get("maos", []):
            if mao.get("lado") == "direita" and mao.get("caixa"):
                pares.append((float(instante["t_ini"]), list(mao["caixa"])))
    return pares


def _mediana_caixas(caixas: list[list[float]]) -> list[float]:
    """Mediana de cada coordenada de uma lista de caixas ``(x0, y0, x1, y1)``.

    Args:
        caixas: caixas no quadro.

    Returns:
        A caixa mediana, com 4 valores.
    """
    return [statistics.median(c[i] for c in caixas) for i in range(4)]


def caixa_da_direita(
    tempos: list[float], pares: list[tuple[float, list[float]]], t_meio: float
) -> tuple[list[float] | None, str]:
    """Caixa da mão direita de um compasso.

    Usa a mediana das caixas nos instantes do compasso. Se não houver nenhuma, usa a
    mediana das ``N_PROXIMOS`` caixas mais próximas do meio do compasso no vídeo.

    Args:
        tempos: ``t_ini`` das notas do compasso.
        pares: saída de ``caixas_da_direita`` para o vídeo inteiro.
        t_meio: instante de referência para o fallback.

    Returns:
        ``(caixa, origem)``, com origem ``compasso``, ``proximos`` ou
        ``sem_mao_direita`` (caixa ``None``).
    """
    do_compasso = [
        caixa for t, caixa in pares if any(abs(t - tn) <= TOLERANCIA_T for tn in tempos)
    ]
    if do_compasso:
        return _mediana_caixas(do_compasso), "compasso"
    if not pares:
        return None, "sem_mao_direita"
    proximos = sorted(pares, key=lambda p: abs(p[0] - t_meio))[:N_PROXIMOS]
    return _mediana_caixas([caixa for _, caixa in proximos]), "proximos"


def caixa_par(
    caixa: list[float], dimensoes: tuple[int, int]
) -> tuple[int, int, int, int]:
    """Caixa ampliada (``FOLGA_MAO`` por lado), dentro do quadro, com lados pares.

    Args:
        caixa: ``(x0, y0, x1, y1)`` no quadro.
        dimensoes: ``(largura, altura)`` do vídeo.

    Returns:
        ``(x0, y0, x1, y1)`` em inteiros, com largura e altura pares (para o H.264).
    """
    largura, altura = dimensoes
    x0, y0, x1, y1 = ampliar_caixa(caixa, FOLGA_MAO, (altura, largura))
    if (x1 - x0) % 2:
        if x1 < largura:
            x1 += 1
        else:
            x0 += 1
    if (y1 - y0) % 2:
        if y1 < altura:
            y1 += 1
        else:
            y0 += 1
    return x0, y0, x1, y1


def janela_do_compasso(
    t0: float, t1: float, duracao: float | None
) -> tuple[float, float]:
    """Janela do clipe: do primeiro ao último ``t_ini`` com ``MARGEM_S`` de cada lado.

    Args:
        t0: primeiro ``t_ini`` do compasso.
        t1: último ``t_ini`` do compasso.
        duracao: duração do vídeo, em segundos, ou ``None`` se desconhecida.

    Returns:
        ``(inicio, fim)`` em segundos.
    """
    inicio = max(0.0, t0 - MARGEM_S)
    fim = t1 + MARGEM_S
    if duracao is not None:
        fim = min(fim, duracao)
    return inicio, fim


def comando_clipe(
    video: Path,
    inicio: float,
    fim: float,
    caixa: tuple[int, int, int, int],
    saida: Path,
    lento: bool,
) -> list[str]:
    """Comando do ffmpeg que recorta a caixa e grava o clipe (H.264, sem áudio).

    Args:
        video: vídeo de origem (acervo).
        inicio: início da janela, em segundos (``-ss`` e ``-t`` antes de ``-i``: o
            ``-t`` na saída cortaria o clipe lento pela metade).
        fim: fim da janela, em segundos.
        caixa: ``(x0, y0, x1, y1)`` com lados pares.
        saida: arquivo de saída (``.mp4``).
        lento: se True, 0,5× (``setpts=2*PTS``).

    Returns:
        Lista de argumentos para ``subprocess.run``.
    """
    x0, y0, x1, y1 = caixa
    filtro = f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"
    if lento:
        filtro += ",setpts=2*PTS"
    return [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-ss",
        f"{inicio:.3f}",
        "-t",
        f"{fim - inicio:.3f}",
        "-i",
        str(video),
        "-vf",
        filtro,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(saida),
    ]


def nome_do_item(indice: int) -> str:
    """Id do compasso na amostra: ``c01``, ``c02``, ...

    Args:
        indice: posição, começando em 1.

    Returns:
        O id com dois dígitos.
    """
    return f"c{indice:02d}"


# ---------------------------------------------------------------------------------
# Página (funções puras)
# ---------------------------------------------------------------------------------


def escolher_pagina(itens: list[dict]) -> set[str]:
    """Ids da página: os compassos de posição ímpar dentro de cada vídeo.

    Mantém a estratificação: a amostra de cada vídeo vem em ordem de tempo, e a página
    fica com a 1ª, 3ª, 5ª... (c01, c03, ...). Os pares continuam no gabarito.

    Args:
        itens: entradas do ``indice.json``, na ordem da amostra.

    Returns:
        Conjunto dos ids que a página mostra.
    """
    posicao: dict[str, int] = {}
    escolhidos: set[str] = set()
    for item in itens:
        posicao[item["video"]] = posicao.get(item["video"], 0) + 1
        if posicao[item["video"]] % 2 == 1:
            escolhidos.add(item["id"])
    return escolhidos


# ---------------------------------------------------------------------------------
# Extração de quadro e desenho (ffmpeg e OpenCV)
# ---------------------------------------------------------------------------------


def extrair_quadro(video: Path, t: float) -> np.ndarray:
    """Quadro do vídeo no instante ``t``, em BGR, pelo ffmpeg.

    Args:
        video: caminho do vídeo.
        t: instante, em segundos.

    Returns:
        O quadro BGR.

    Raises:
        RuntimeError: se o ffmpeg não devolveu uma imagem.
    """
    proc = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{max(0.0, t):.3f}",
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
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        erro = proc.stderr.decode(errors="replace")[:300]
        raise RuntimeError(f"ffmpeg falhou em t={t:.3f}: {erro}")
    quadro = cv2.imdecode(np.frombuffer(proc.stdout, np.uint8), cv2.IMREAD_COLOR)
    if quadro is None:
        raise RuntimeError(f"ffmpeg não gerou imagem em t={t:.3f}")
    return quadro


def dimensoes_do_video(video: Path) -> tuple[int, int]:
    """Largura e altura do primeiro fluxo de vídeo, pelo ffprobe.

    Args:
        video: caminho do vídeo.

    Returns:
        ``(largura, altura)``.

    Raises:
        RuntimeError: se o ffprobe falhar.
    """
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falhou em {video}: {proc.stderr[:300]}")
    largura, altura = proc.stdout.strip().split("x")
    return int(largura), int(altura)


def painel_da_tela(telas: list[dict], tela: int, altura: int) -> tuple[int, int]:
    """Faixa vertical ``(y0, y1)`` do painel da tela; o quadro inteiro se faltar.

    Args:
        telas: lista ``telas`` do produto.
        tela: id da tela.
        altura: altura do quadro.

    Returns:
        ``(y0, y1)`` em pixels.
    """
    for t in telas:
        if t.get("id") == tela and t.get("painel"):
            return int(t["painel"][1]), int(t["painel"][3])
    return 0, altura


def desenhar_tab(
    quadro: np.ndarray,
    compasso: dict,
    faixa_y: tuple[int, int],
) -> np.ndarray:
    """Quadro com o retângulo do compasso e a lista de notas embaixo.

    Args:
        quadro: quadro BGR original (1920 px de largura).
        compasso: compasso (``notas`` com ``x_quadro``, ``corda``, ``casa``, ``t_ini``).
        faixa_y: ``(y0, y1)`` do painel da tela.

    Returns:
        Imagem BGR reduzida a 1280 px de largura, com as notas em texto embaixo.
    """
    xs = [n["x_quadro"] for n in compasso["notas"] if n.get("x_quadro") is not None]
    img = quadro.copy()
    if xs:
        x0 = max(0, int(min(xs)) - MARGEM_RETANGULO_PX)
        x1 = min(img.shape[1] - 1, int(max(xs)) + MARGEM_RETANGULO_PX)
        cv2.rectangle(img, (x0, faixa_y[0]), (x1, faixa_y[1]), (0, 0, 255), 3)
    largura = 1280
    escala = largura / img.shape[1]
    img = cv2.resize(
        img, (largura, int(img.shape[0] * escala)), interpolation=cv2.INTER_AREA
    )
    por_instante: dict[float, list[str]] = {}
    for nota in compasso["notas"]:
        t = round(float(nota["t_ini"]), 2)
        por_instante.setdefault(t, []).append(f"c{nota['corda']}:{nota['casa']}")
    linhas = [
        f"{t:8.2f} s   " + "  ".join(vals) for t, vals in sorted(por_instante.items())
    ]
    linhas.insert(
        0,
        f"compasso {compasso['compasso']}  tela {compasso['tela']}  "
        f"exibicao {compasso['exibicao']}   (corda:casa por instante)",
    )
    altura_texto = 26 * len(linhas) + 16
    painel = np.full((altura_texto, largura, 3), 255, dtype=np.uint8)
    for i, linha in enumerate(linhas):
        cv2.putText(
            painel,
            linha,
            (10, 26 + 26 * i),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
    return np.vstack([img, painel])


# ---------------------------------------------------------------------------------
# Preparo (ffmpeg, arquivos)
# ---------------------------------------------------------------------------------


def _preparar_compasso(
    video: Path,
    item: dict,
    compasso: dict,
    telas: list[dict],
    pares: list[tuple[float, list[float]]],
    duracao: float | None,
    dimensoes: tuple[int, int],
    pasta: Path,
) -> dict:
    """Gera clipes, ``tab.png`` e a entrada do índice para um compasso.

    Args:
        video: vídeo de origem.
        item: id e posição do compasso na amostra.
        compasso: compasso sorteado.
        telas: telas do produto.
        pares: caixas da direita do vídeo inteiro.
        duracao: duração do vídeo, ou ``None``.
        dimensoes: ``(largura, altura)`` do vídeo.
        pasta: pasta do compasso (``<id>/``), já criada.

    Returns:
        A entrada do ``indice.json``.
    """
    tempos = [n["t_ini"] for n in compasso["notas"]]
    inicio, fim = janela_do_compasso(compasso["t0"], compasso["t1"], duracao)
    caixa_bruta, origem = caixa_da_direita(tempos, pares, (inicio + fim) / 2)
    caixa = None
    if caixa_bruta is not None:
        caixa = caixa_par(caixa_bruta, dimensoes)
        subprocess.run(
            comando_clipe(video, inicio, fim, caixa, pasta / "clipe.mp4", False),
            check=True,
        )
        subprocess.run(
            comando_clipe(video, inicio, fim, caixa, pasta / "clipe_lento.mp4", True),
            check=True,
        )
    quadro = extrair_quadro(video, (inicio + fim) / 2)
    faixa = painel_da_tela(telas, compasso["tela"], quadro.shape[0])
    cv2.imwrite(str(pasta / "tab.png"), desenhar_tab(quadro, compasso, faixa))
    return {
        "id": item["id"],
        "video": item["video"],
        "tela": compasso["tela"],
        "compasso": compasso["compasso"],
        "exibicao": compasso["exibicao"],
        "janela": [round(inicio, 3), round(fim, 3)],
        "n_notas": compasso["n_notas"],
        "caixa": caixa,
        "caixa_origem": origem,
        "pasta": item["id"],
        "notas": [
            {"corda": n["corda"], "casa": n["casa"], "t_ini": n["t_ini"]}
            for n in compasso["notas"]
        ],
    }


def preparar(saida: Path, gabarito: Path, semente: int) -> int:
    """Amostra os compassos, gera o material e cria ou mescla o gabarito.

    Args:
        saida: pasta de saída (``MAOS_M5``).
        gabarito: arquivo do gabarito dos padrões.
        semente: semente do sorteio.

    Returns:
        Código de saída (0 se tudo deu certo).
    """
    rng = random.Random(semente)
    indice: list[dict] = []
    resumo: list[str] = []
    n_compassos_total = 0
    for video_cfg in VIDEOS:
        video = acervo() / video_cfg["arquivo"]
        produto = _ler_json(video_cfg["produto"])
        pontas = _ler_json(video_cfg["pontas"])
        notas = notas_com_tempo(produto["notas"])
        elegiveis = compassos_tocados(notas)
        n_compassos_total += len(elegiveis)
        duracao = produto.get("video", {}).get("duracao_s")
        dimensoes = dimensoes_do_video(video)
        pares = caixas_da_direita(pontas["instantes"])
        sorteados = amostrar_compassos(elegiveis, N_POR_VIDEO, rng)
        resumo.append(
            f"{video_cfg['arquivo']}: {len(elegiveis)} elegíveis, "
            f"{len(sorteados)} sorteados"
        )
        for compasso in sorteados:
            item = {"id": nome_do_item(len(indice) + 1), "video": video_cfg["arquivo"]}
            pasta = saida / item["id"]
            pasta.mkdir(parents=True, exist_ok=True)
            _log(
                f"{item['id']}: {video_cfg['arquivo']} compasso {compasso['compasso']}"
            )
            indice.append(
                _preparar_compasso(
                    video,
                    item,
                    compasso,
                    produto.get("telas", []),
                    pares,
                    duracao,
                    dimensoes,
                    pasta,
                )
            )
    na_pagina = escolher_pagina(indice)
    for entrada in indice:
        entrada["na_pagina"] = entrada["id"] in na_pagina
    gravar_atomico(
        saida / "indice.json",
        {"semente": semente, "itens": indice},
    )
    existente = _ler_json(gabarito) if gabarito.exists() else None
    novo = gabarito_novo(indice, semente)
    gravar_atomico(gabarito, mesclar_gabarito(novo, existente))
    for linha in resumo:
        print(linha)
    print(
        f"{n_compassos_total} compassos elegíveis; {len(indice)} amostrados; "
        f"gabarito: {gabarito}"
    )
    return 0


def main() -> int:
    """Ponto de entrada do CLI.

    Returns:
        Código de saída.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--saida", type=Path, default=MAOS_M5)
    parser.add_argument("--gabarito", type=Path, default=GABARITO_PADROES)
    parser.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    args = parser.parse_args()
    return preparar(args.saida, args.gabarito, args.semente)


if __name__ == "__main__":
    sys.exit(main())
