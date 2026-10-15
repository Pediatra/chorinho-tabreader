"""Tempo do gesto da mão direita: energia de movimento contra o ``t_ini`` (M7).

Pergunta da rodada 1011: o gesto da mão direita aparece no vídeo perto do ``t_ini`` das
notas da tablatura, e com que atraso? Não usa detector de mãos. Mede a energia de
movimento quadro a quadro no painel da mão direita, ``E(t)``, e a compara com um trem de
impulsos nos instantes das notas, ``N(t)``.

Para cada um dos quatro vídeos de ``tab.maos_padroes_preparar.VIDEOS``, sorteia três
trechos de 20 s com muitas notas, decodifica só o painel com ffmpeg, na taxa nativa do
vídeo, e calcula:

- a correlação cruzada entre ``E`` e ``N`` para atrasos de −0,5 a +0,5 s (passo de um
  quadro), com o pico e o percentil desse pico contra um embaralhamento circular de ``N``;
- a média sincronizada de ``E`` em janelas de ±0,5 s centradas em cada ``t_ini``.

Atraso positivo quer dizer que o movimento acontece depois do ``t_ini``. São medidos dois
recortes do painel: o painel inteiro e o quadrante inferior-direito (onde ficam as pontas
e as cordas).

Uso::

    python -m tab.maos_direita_tempo
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import MAOS_M7, acervo
from .maos_padroes_preparar import VIDEOS

#: Semente do sorteio dos trechos e do embaralhamento (a da rodada 1011).
SEMENTE = 20261015

#: Resolução de referência das coordenadas do painel.
RESOLUCAO_REF = (1920, 1080)

#: Painel da mão direita na resolução de referência: x0, y0, x1, y1.
PAINEL_REF = (0, 522, 655, 1080)

#: Tamanho, em pixels, do painel depois de escalado (cinza, quadros brutos no pipe).
PAINEL_LARGURA = 328
PAINEL_ALTURA = 280

#: Duração de cada trecho analisado, em segundos.
TRECHO_S = 20.0

#: Margem decodificada antes e depois do trecho, para os atrasos não caírem fora.
MARGEM_S = 1.0

#: Trechos sorteados por vídeo.
N_TRECHOS = 3

#: Meia-largura, em segundos, da janela da correlação e da média sincronizada.
JANELA_S = 0.5

#: Embaralhamentos circulares de ``N`` por trecho e recorte.
N_EMBARALHAR = 200

#: Deslocamento mínimo, em segundos, do embaralhamento.
DESLOC_MIN_S = 1.0

#: Nomes curtos dos vídeos, na ordem de ``VIDEOS``.
NOMES = ("retrato_brasileiro", "chopin_nocturne20", "lacrimosa", "glimpse_of_us")

#: Recortes medidos: painel inteiro e quadrante inferior-direito.
RECORTES = ("painel", "quadrante_inf_dir")


def _log(msg: str) -> None:
    """Progresso no stderr (o stdout fica para o resumo final).

    Args:
        msg: texto da linha.
    """
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------
# Trechos e trem de notas (funções puras)
# ---------------------------------------------------------------------------------


def instantes_distintos(notas: list[dict[str, Any]]) -> list[float]:
    """Instantes ``t_ini`` distintos do produto, em ordem crescente.

    Args:
        notas: lista ``notas`` do produto (as notas sem ``t_ini`` são ignoradas).

    Returns:
        Instantes arredondados a 3 casas, sem repetição.
    """
    return sorted(
        {round(float(n["t_ini"]), 3) for n in notas if n.get("t_ini") is not None}
    )


def escolher_trechos(
    instantes: list[float],
    duracao_s: float = TRECHO_S,
    n: int = N_TRECHOS,
    semente: int = SEMENTE,
) -> list[float]:
    """Sorteia ``n`` trechos de ``duracao_s`` com muitas notas, um por faixa de tempo.

    Candidatos são os inícios a cada segundo, dentro da faixa coberta pelos ``t_ini``, e
    que tenham pelo menos a mediana de instantes distintos no trecho. Os candidatos são
    divididos em ``n`` faixas cronológicas, e um é sorteado de cada uma com
    ``random.Random(semente)``.

    Args:
        instantes: instantes distintos, em ordem crescente.
        duracao_s: duração do trecho, em segundos.
        n: quantos trechos.
        semente: semente do sorteio.

    Returns:
        Inícios dos trechos, em segundos, em ordem crescente.
    """
    if len(instantes) < 2:
        return []
    arr = np.asarray(instantes, dtype=float)
    grade = np.arange(arr[0], arr[-1] - duracao_s + 1e-9, 1.0)
    if len(grade) == 0:
        return []
    densidade = np.searchsorted(arr, grade + duracao_s) - np.searchsorted(arr, grade)
    candidatos = grade[densidade >= np.median(densidade)]
    rng = random.Random(semente)
    escolhidos = []
    for faixa in np.array_split(candidatos, n):
        if len(faixa):
            escolhidos.append(float(rng.choice([float(s) for s in faixa])))
    return escolhidos


def trem_de_notas(
    instantes: list[float], inicio: float, fps: float, n_quadros: int
) -> np.ndarray:
    """Trem de impulsos: 1 no quadro mais próximo de cada instante, 0 nos demais.

    Args:
        instantes: instantes ``t_ini``, em segundos, do vídeo.
        inicio: instante, em segundos, do quadro 0 decodificado.
        fps: taxa de quadros do vídeo.
        n_quadros: tamanho do vetor.

    Returns:
        Vetor ``float`` de tamanho ``n_quadros``.
    """
    trem = np.zeros(n_quadros, dtype=float)
    for t in instantes:
        k = round((t - inicio) * fps)
        if 0 <= k < n_quadros:
            trem[k] = 1.0
    return trem


# ---------------------------------------------------------------------------------
# Vídeo e energia de movimento (funções puras, exceto a leitura do ffprobe)
# ---------------------------------------------------------------------------------


def recorte_do_painel(largura: int, altura: int) -> tuple[int, int, int, int]:
    """Caixa do painel da mão direita no quadro do vídeo, escalada da referência.

    Args:
        largura: largura do quadro, em pixels.
        altura: altura do quadro, em pixels.

    Returns:
        ``(largura, altura, x, y)`` no formato do filtro ``crop`` do ffmpeg.
    """
    sx = largura / RESOLUCAO_REF[0]
    sy = altura / RESOLUCAO_REF[1]
    x0, y0, x1, y1 = PAINEL_REF
    x0, x1 = round(x0 * sx), round(x1 * sx)
    y0, y1 = round(y0 * sy), round(y1 * sy)
    return (x1 - x0, y1 - y0, x0, y0)


def energia_movimento(quadros: np.ndarray) -> np.ndarray:
    """Média de ``|quadro_t - quadro_{t-1}|`` por quadro, em níveis de cinza.

    O quadro 0 não tem anterior: recebe o valor do quadro 1.

    Args:
        quadros: array ``(T, altura, largura)`` em ``uint8``, com ``T >= 2``.

    Returns:
        Vetor ``float`` de tamanho ``T``.

    Raises:
        ValueError: se houver menos de dois quadros.
    """
    if len(quadros) < 2:
        raise ValueError("energia de movimento precisa de pelo menos 2 quadros")
    dif = np.abs(np.diff(quadros.astype(np.int16), axis=0)).mean(axis=(1, 2))
    return np.concatenate(([dif[0]], dif)).astype(float)


def metade_inferior_direita(quadros: np.ndarray) -> np.ndarray:
    """Quadrante inferior-direito de cada quadro (metade de baixo e metade da direita).

    Args:
        quadros: array ``(T, altura, largura)``.

    Returns:
        Visão ``(T, altura // 2, largura - largura // 2)`` do quadrante.
    """
    altura, largura = quadros.shape[1], quadros.shape[2]
    return quadros[:, altura // 2 :, largura // 2 :]


def zscore(x: np.ndarray) -> np.ndarray:
    """Normaliza para média 0 e desvio 1; um vetor constante vira zeros.

    Args:
        x: vetor de valores.

    Returns:
        Vetor ``float`` normalizado.
    """
    x = np.asarray(x, dtype=float)
    dp = x.std()
    if dp == 0:
        return np.zeros_like(x)
    return (x - x.mean()) / dp


def matriz_de_atrasos(e: np.ndarray, i0: int, i1: int, lag: int) -> np.ndarray:
    """Linhas ``zscore(e[i0+d : i1+d])`` para cada atraso ``d`` em ``[-lag, lag]``.

    Args:
        e: energia de movimento, já no tempo decodificado.
        i0: primeiro quadro da janela da nota.
        i1: fim (exclusivo) da janela da nota.
        lag: maior atraso, em quadros.

    Returns:
        Matriz ``(2*lag+1, i1-i0)``; a linha ``k`` corresponde a ``d = k - lag``.
    """
    return np.stack([zscore(e[i0 + d : i1 + d]) for d in range(-lag, lag + 1)])


def correlacao_por_atraso(
    e: np.ndarray, n: np.ndarray, i0: int, i1: int, lag: int
) -> np.ndarray:
    """Correlação de Pearson entre ``E(t+d)`` e ``N(t)`` para cada atraso ``d``.

    Args:
        e: energia de movimento.
        n: trem de notas, do mesmo tamanho de ``e``.
        i0: primeiro quadro da janela.
        i1: fim (exclusivo) da janela.
        lag: maior atraso, em quadros.

    Returns:
        Vetor ``float`` de tamanho ``2*lag+1``, na ordem de ``d`` crescente.
    """
    zn = zscore(n[i0:i1])
    return matriz_de_atrasos(e, i0, i1, lag) @ zn / (i1 - i0)


def picos_embaralhados(
    e: np.ndarray,
    n: np.ndarray,
    i0: int,
    i1: int,
    lag: int,
    fps: float,
    n_desloc: int = N_EMBARALHAR,
    semente: int = SEMENTE,
) -> np.ndarray:
    """Pico da correlação com ``N`` deslocado circularmente por acaso.

    Cada embaralhamento desloca ``N`` dentro da janela por ``k`` quadros, sorteado em
    ``[DESLOC_MIN_S, janela - DESLOC_MIN_S]`` segundos, e guarda o máximo sobre os atrasos.

    Args:
        e: energia de movimento.
        n: trem de notas.
        i0: primeiro quadro da janela.
        i1: fim (exclusivo) da janela.
        lag: maior atraso, em quadros.
        fps: taxa de quadros do vídeo.
        n_desloc: quantos deslocamentos.
        semente: semente do sorteio dos deslocamentos.

    Returns:
        Vetor ``float`` com os ``n_desloc`` picos embaralhados.
    """
    matriz = matriz_de_atrasos(e, i0, i1, lag)
    janela = i1 - i0
    minimo = round(DESLOC_MIN_S * fps)
    rng = random.Random(semente)
    base = n[i0:i1]
    picos = []
    for _ in range(n_desloc):
        k = rng.randint(minimo, janela - minimo)
        picos.append(float(np.max(matriz @ zscore(np.roll(base, k)) / janela)))
    return np.array(picos)


def janelas_sincronizadas(e_z: np.ndarray, indices: np.ndarray, lag: int) -> np.ndarray:
    """Recortes de ``E`` de ``-lag`` a ``+lag`` quadros, centrados em cada índice.

    Args:
        e_z: energia já normalizada.
        indices: quadros centrais (um por ``t_ini``).
        lag: meia-largura, em quadros.

    Returns:
        Array ``(k, 2*lag+1)``, com ``k`` as janelas que cabem no vetor.
    """
    linhas = [
        e_z[int(i) - lag : int(i) + lag + 1]
        for i in indices
        if int(i) - lag >= 0 and int(i) + lag < len(e_z)
    ]
    if not linhas:
        return np.zeros((0, 2 * lag + 1))
    return np.stack(linhas)


def pico_da_curva(r: np.ndarray, lags_s: np.ndarray) -> tuple[float, float]:
    """Atraso e valor do maior ponto de uma curva de correlação.

    Args:
        r: curva de correlação.
        lags_s: atrasos, em segundos, do mesmo tamanho de ``r``.

    Returns:
        ``(atraso_em_s, valor)`` do máximo.
    """
    k = int(np.argmax(r))
    return float(lags_s[k]), float(r[k])


def percentil(valor: float, referencia: np.ndarray) -> float:
    """Percentual dos valores de ``referencia`` estritamente abaixo de ``valor``.

    Args:
        valor: valor medido.
        referencia: distribuição de comparação.

    Returns:
        Percentil em ``[0, 100]``.
    """
    return float(100.0 * np.mean(referencia < valor))


# ---------------------------------------------------------------------------------
# Leitura do vídeo e medição por trecho (usa ffmpeg e o acervo)
# ---------------------------------------------------------------------------------


def ler_video(caminho: Path) -> tuple[int, int, float]:
    """Largura, altura e taxa de quadros nativa do primeiro fluxo de vídeo.

    Args:
        caminho: arquivo de vídeo.

    Returns:
        ``(largura, altura, fps)``, com o fps de ``r_frame_rate``.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate",
        "-of",
        "json",
        str(caminho),
    ]
    saida = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    fluxo = json.loads(saida)["streams"][0]
    num, den = fluxo["r_frame_rate"].split("/")
    return int(fluxo["width"]), int(fluxo["height"]), float(num) / float(den)


def decodificar_painel(
    caminho: Path, inicio: float, duracao: float, largura: int, altura: int
) -> np.ndarray:
    """Quadros em cinza do painel da mão direita, lidos do pipe do ffmpeg.

    Usa a taxa nativa do vídeo (sem ``fps`` no filtro e com ``-fps_mode passthrough``,
    sem duplicar nem descartar quadros).

    Args:
        caminho: arquivo de vídeo.
        inicio: instante inicial, em segundos.
        duracao: duração a decodificar, em segundos.
        largura: largura do quadro original.
        altura: altura do quadro original.

    Returns:
        Array ``uint8`` ``(T, PAINEL_ALTURA, PAINEL_LARGURA)``.
    """
    w, h, x, y = recorte_do_painel(largura, altura)
    filtro = f"crop={w}:{h}:{x}:{y},scale={PAINEL_LARGURA}:{PAINEL_ALTURA},format=gray"
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-ss",
        f"{inicio:.3f}",
        "-i",
        str(caminho),
        "-t",
        f"{duracao:.3f}",
        "-vf",
        filtro,
        "-fps_mode",
        "passthrough",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    ]
    bruto = subprocess.run(cmd, capture_output=True, check=True).stdout
    tamanho = PAINEL_LARGURA * PAINEL_ALTURA
    n = len(bruto) // tamanho
    return np.frombuffer(bruto[: n * tamanho], dtype=np.uint8).reshape(
        n, PAINEL_ALTURA, PAINEL_LARGURA
    )


def medir_trecho(
    caminho: Path,
    inicio: float,
    instantes: list[float],
    largura: int,
    altura: int,
    fps: float,
) -> dict[str, Any]:
    """Mede um trecho: correlação, pico, embaralhamento e janelas sincronizadas.

    Args:
        caminho: arquivo de vídeo.
        inicio: início do trecho (com ``TRECHO_S`` de duração), em segundos.
        instantes: ``t_ini`` distintos que caem no trecho.
        largura: largura do quadro original.
        altura: altura do quadro original.
        fps: taxa de quadros nativa.

    Returns:
        ``{"inicio_s", "n_instantes", "decodificados", "recortes": {...}, "janelas":
        {...}}``. Em ``recortes``, cada recorte tem ``atraso_pico_s``, ``pico_r``,
        ``percentil_embaralhado`` e ``curva_r``. ``janelas`` são arrays e não vão para o
        JSON.

    Raises:
        RuntimeError: se o vídeo não der quadros suficientes para o trecho.
    """
    decodificar_de = inicio - MARGEM_S
    quadros = decodificar_painel(
        caminho, decodificar_de, TRECHO_S + 2 * MARGEM_S, largura, altura
    )
    i0 = round(MARGEM_S * fps)
    i1 = i0 + round(TRECHO_S * fps)
    lag = round(JANELA_S * fps)
    if len(quadros) < i1 + lag + 1:
        raise RuntimeError(f"trecho {inicio:.2f}s: só {len(quadros)} quadros")
    n = trem_de_notas(instantes, decodificar_de, fps, len(quadros))
    indices = np.round((np.asarray(instantes) - decodificar_de) * fps).astype(int)
    lags_s = np.arange(-lag, lag + 1) / fps

    recortes: dict[str, Any] = {}
    janelas: dict[str, np.ndarray] = {}
    for nome in RECORTES:
        q = quadros if nome == "painel" else metade_inferior_direita(quadros)
        e = energia_movimento(q)
        curva = correlacao_por_atraso(e, n, i0, i1, lag)
        atraso, pico = pico_da_curva(curva, lags_s)
        nulos = picos_embaralhados(e, n, i0, i1, lag, fps)
        recortes[nome] = {
            "atraso_pico_s": atraso,
            "pico_r": pico,
            "percentil_embaralhado": percentil(pico, nulos),
            "curva_r": [round(float(v), 4) for v in curva],
        }
        janelas[nome] = janelas_sincronizadas(zscore(e), indices, lag)
    return {
        "inicio_s": inicio,
        "n_instantes": len(instantes),
        "decodificados": len(quadros),
        "recortes": recortes,
        "janelas": janelas,
    }


def desenhar_grafico(
    curvas: dict[str, np.ndarray], lags_s: np.ndarray, caminho: Path
) -> None:
    """Gráfico das médias sincronizadas, uma curva por vídeo, com linha em 0 s.

    Args:
        curvas: média sincronizada por nome de vídeo, do mesmo tamanho de ``lags_s``.
        lags_s: atrasos, em segundos, no eixo x.
        caminho: arquivo PNG de saída.
    """
    largura, altura = 1000, 600
    esq, dir_, topo, base = 90, 260, 50, 70
    img = np.full((altura, largura, 3), 255, dtype=np.uint8)
    valores = np.concatenate(list(curvas.values()))
    vmin, vmax = float(valores.min()), float(valores.max())
    if vmax - vmin < 1e-9:
        vmax = vmin + 1.0
    x0, x1 = float(lags_s[0]), float(lags_s[-1])

    def px(lag: float) -> int:
        return int(esq + (lag - x0) / (x1 - x0) * (largura - esq - dir_))

    def py(v: float) -> int:
        return int(topo + (vmax - v) / (vmax - vmin) * (altura - topo - base))

    cinza = (120, 120, 120)
    cv2.rectangle(img, (esq, topo), (largura - dir_, altura - base), cinza, 1)
    for lag in (-0.5, -0.25, 0.0, 0.25, 0.5):
        cv2.line(img, (px(lag), topo), (px(lag), altura - base), (220, 220, 220), 1)
        cv2.putText(
            img,
            f"{lag:+.2f}",
            (px(lag) - 22, altura - base + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (60, 60, 60),
            1,
        )
    cv2.line(img, (px(0.0), topo), (px(0.0), altura - base), (0, 0, 0), 2)
    cv2.putText(
        img,
        "atraso do movimento em relacao ao t_ini (s)",
        (esq + 120, altura - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        1,
    )
    cv2.putText(
        img,
        "energia z",
        (10, topo + 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        1,
    )
    cv2.putText(
        img,
        "media sincronizada, painel inteiro (+-0.5 s), por video",
        (esq, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        1,
    )
    cores = [(200, 80, 20), (40, 160, 40), (30, 30, 200), (160, 60, 160)]
    for i, (nome, curva) in enumerate(curvas.items()):
        cor = cores[i % len(cores)]
        pontos = np.array(
            [(px(a), py(v)) for a, v in zip(lags_s, curva, strict=True)], np.int32
        )
        cv2.polylines(img, [pontos], False, cor, 2)
        y = topo + 20 + 22 * i
        cv2.line(img, (largura - dir_ + 15, y), (largura - dir_ + 45, y), cor, 3)
        cv2.putText(
            img,
            nome,
            (largura - dir_ + 55, y + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
        )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(caminho), img)


def main() -> None:
    """Mede os quatro vídeos, grava ``tempo.json`` e ``tempo.png`` em ``MAOS_M7``."""
    saida: dict[str, Any] = {
        "semente": SEMENTE,
        "trecho_s": TRECHO_S,
        "janela_s": JANELA_S,
        "embaralhamentos": N_EMBARALHAR,
        "recortes": {
            "painel": "painel da mão direita inteiro",
            "quadrante_inf_dir": "metade de baixo e metade da direita do painel",
        },
        "convencao": "atraso > 0: movimento depois do t_ini",
        "videos": [],
    }
    curvas_grafico: dict[str, np.ndarray] = {}
    lags_s = np.array([])
    for indice, video in enumerate(VIDEOS):
        nome = NOMES[indice]
        caminho = acervo() / video["arquivo"]
        notas = json.loads(Path(video["produto"]).read_text())["notas"]
        instantes = instantes_distintos(notas)
        largura, altura, fps = ler_video(caminho)
        _log(f"{nome}: {largura}x{altura} {fps:.4f} fps, {len(instantes)} instantes")
        trechos = []
        janelas_video: dict[str, list[np.ndarray]] = {r: [] for r in RECORTES}
        for inicio in escolher_trechos(instantes):
            no_trecho = [t for t in instantes if inicio <= t < inicio + TRECHO_S]
            medido = medir_trecho(caminho, inicio, no_trecho, largura, altura, fps)
            for r in RECORTES:
                janelas_video[r].append(medido["janelas"][r])
            del medido["janelas"]
            trechos.append(medido)
            _log(f"  trecho {inicio:.1f}s: {len(no_trecho)} instantes")
        lags_s = np.arange(-round(JANELA_S * fps), round(JANELA_S * fps) + 1) / fps
        media = {}
        for r in RECORTES:
            todas = np.vstack(janelas_video[r])
            media[r] = {
                "n_eventos": len(todas),
                "curva": [round(float(v), 4) for v in todas.mean(axis=0)],
            }
        curvas_grafico[nome] = np.array(media["painel"]["curva"])
        saida["videos"].append(
            {
                "nome": nome,
                "arquivo": video["arquivo"],
                "largura": largura,
                "altura": altura,
                "fps": round(fps, 4),
                "trechos": trechos,
                "media_sincronizada": media,
            }
        )
    saida["lags_s"] = [round(float(v), 4) for v in lags_s]
    MAOS_M7.mkdir(parents=True, exist_ok=True)
    (MAOS_M7 / "tempo.json").write_text(json.dumps(saida, indent=2))
    desenhar_grafico(curvas_grafico, lags_s, MAOS_M7 / "tempo.png")
    for video in saida["videos"]:
        for t in video["trechos"]:
            for r in RECORTES:
                c = t["recortes"][r]
                print(
                    f"{video['nome']} {t['inicio_s']:.1f}s {r}: "
                    f"pico {c['pico_r']:+.3f} em {c['atraso_pico_s']:+.3f}s, "
                    f"percentil {c['percentil_embaralhado']:.1f}"
                )


if __name__ == "__main__":
    main()
