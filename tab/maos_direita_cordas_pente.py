"""Cordas pela imagem mediana e um pente de 6 retas (M7, item 3 da rodada 1012).

Pergunta: as retas de corda atuais (``tab.maos_direita_cordas``, por filtro de linha) estão
sobre as cordas? A rodada 1011 registrou cordas aproximadas, sobretudo as cordas 1 a 3 do
noturno e as 5 e 6 do noturno e do glimpse, mal posicionadas no cavalete.

Método:

1. Quadros do painel (câmera da mão direita) amostrados nos trechos com nota de
   ``tempo.json``. Cada quadro é levado ao quadro do meio por transformação afim parcial
   (escala, rotação e translação) de correspondências ORB com RANSAC. A correlação de fase
   e a normalizada, com busca de ±40 px, falharam: a câmera faz pan e zoom de dezenas a
   centenas de pixels, e o painel tem corte diagonal. A mediana temporal por pixel, sobre
   os pixels válidos, faz a mão que se mexe sumir.
2. Resposta de linha fina: intensidade no centro da reta menos a média a 2 px de cada
   lado, perpendicular à reta. Para degraus largos (bordas de cavalete ou roseta) dá
   ~0. Não se usa gradiente, Canny nem Sobel.
3. Âncoras: cada bordão (cordas 4, 5 e 6) é posicionado por busca fina em torno da reta
   atual, pela maior resposta de linha fina.
4. Modelo de pente com 5 graus de liberdade ``(m0, kappa, Y0, d, rho)`` ajustado por
   mínimos quadrados às três âncoras. ``kappa`` fica em zero, porque três âncoras só
   determinam uma variação de inclinação, e ``rho`` (perspectiva) é essa variação. As
   cordas 1, 2 e 3 não são ajustadas: saem do modelo. A corda ``k`` é a reta
   ``y = m_k x + q_k``, com 6 em cima.
5. Comparação com as retas atuais, levadas para o quadro da mediana pela afim de ORB
   entre o quadro em que elas foram medidas e o quadro de referência. Mesma medida de
   crista (``tab.maos_direita_cordas.cresta_da_reta``) nas duas.

Saídas em ``MAOS_M7``: ``mediana_<v>.png``, ``cordas_pente_<v>.jpg`` (sobre a mediana),
``cordas_pente_quadro_<v>.jpg`` (sobre um quadro real), ``cordas_pente_<v>_cavalete.jpg``
(recorte 2x), ``medianas.json`` e ``pente.json``.

Uso::

    python -m tab.maos_direita_cordas_pente [--video NOME]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import MAOS_M7, acervo
from .maos_direita_cordas import cresta_da_reta, espacamento_das_cordas
from .maos_direita_tempo import NOMES, ler_video, recorte_do_painel
from .maos_padroes_preparar import VIDEOS

#: Quadros amostrados por trecho com nota (3 trechos por vídeo, ~150 quadros no total).
QUADROS_POR_TRECHO = 50

#: Peso das cordas 1, 2 e 3 na pontuação do modelo (informativo; as 4, 5 e 6 pesam 1).
PESO_AGUDAS = 0.3

#: Distância, em pixels perpendiculares à corda, usada na resposta de linha fina.
DIST_LINHA_PX = 2.0

#: Fração da resposta que conta (os pontos mais fortes da corda, como na crista).
FRAC_TOPO = 0.4

#: Recorte do cavalete (x0, y0, x1, y1) no painel, para o zoom 2x (pixels; ver o desenho).
RECORTE_CAVALETE = (300, 120, 560, 330)

#: Cores BGR das seis cordas, da 1 (amarelo) à 6 (vermelho), para o desenho.
CORES_CORDAS = {
    1: (0, 255, 255),
    2: (0, 200, 255),
    3: (0, 255, 0),
    4: (255, 255, 0),
    5: (255, 0, 255),
    6: (0, 0, 255),
}


def _log(msg: str) -> None:
    """Progresso no stderr.

    Args:
        msg: texto da linha.
    """
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------------


def amostrar_indices(total: int, n: int) -> np.ndarray:
    """Até ``n`` índices espalhados de ``0`` a ``total - 1``, sem repetição.

    Args:
        total: quantidade de quadros disponíveis.
        n: quantidade desejada.

    Returns:
        Array ``int`` ordenado.
    """
    if total <= n:
        return np.arange(total)
    return np.unique(np.round(np.linspace(0, total - 1, n)).astype(int))


#: Correspondências ORB por quadro (o teto do detector).
N_CARACTERISTICAS = 2000

#: Inliers mínimos (RANSAC) para o quadro entrar na mediana.
INLIERS_MIN = 40

#: Erro de reprojeção do RANSAC, em pixels.
ERRO_RANSAC_PX = 3.0


def estimar_afim(
    orb: Any,
    bf: Any,
    ref_kp: list[Any],
    ref_des: np.ndarray,
    quadro: np.ndarray,
) -> tuple[np.ndarray | None, int]:
    """Transformação afim parcial (escala, rotação e translação) do quadro para a referência.

    Correspondências ORB entre o quadro e a referência, com RANSAC. A transformação foi
    escolhida porque a câmera de cada trecho faz pan e zoom de dezenas a centenas de
    pixels, e a correlação de fase e a normalizada (com busca de ±40 px) falharam nos
    testes. Mãos em movimento viram outliers.

    Args:
        orb: detector ORB.
        bf: casador de força bruta com Hamming e ``crossCheck``.
        ref_kp: pontos-chave da referência.
        ref_des: descritores da referência.
        quadro: quadro em tons de cinza ``uint8``.

    Returns:
        ``(M, inliers)``: matriz ``2x3`` que leva o quadro para a referência, ou None; e o
        número de inliers.
    """
    kp, des = orb.detectAndCompute(quadro, None)
    if des is None or ref_des is None or len(kp) < 8:
        return None, 0
    casamentos = bf.match(des, ref_des)
    if len(casamentos) < 8:
        return None, 0
    src = np.float32([kp[m.queryIdx].pt for m in casamentos])
    dst = np.float32([ref_kp[m.trainIdx].pt for m in casamentos])
    m, mascara = cv2.estimateAffine2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=ERRO_RANSAC_PX
    )
    if m is None or mascara is None:
        return None, 0
    return m, int(mascara.sum())


def alinhar_quadros(
    quadros: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Leva cada quadro colorido para a referência (o quadro do meio) por afim de ORB.

    Quadros sem inliers suficientes (``INLIERS_MIN``) ficam de fora (máscara falsa).

    Args:
        quadros: array ``(T, altura, largura, 3)`` ``uint8``.

    Returns:
        ``(pilha, validos, medidas)``: ``pilha`` ``float32`` ``(T, altura, largura, 3)``
        com NaN fora do quadro; ``validos`` ``bool`` ``(T,)``; e ``medidas``, uma entrada
        por quadro com ``inliers`` e ``M`` (lista, ou None).
    """
    cinzas = [cv2.cvtColor(q, cv2.COLOR_BGR2GRAY) for q in quadros]
    ref_idx = len(quadros) // 2
    orb = cv2.ORB_create(nfeatures=N_CARACTERISTICAS)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref_kp, ref_des = orb.detectAndCompute(cinzas[ref_idx], None)
    altura, largura = cinzas[0].shape
    pilha = np.full(quadros.shape, np.nan, dtype=np.float32)
    validos = np.zeros(len(quadros), dtype=bool)
    medidas: list[dict[str, Any]] = []
    for t, (quadro, cinza) in enumerate(zip(quadros, cinzas, strict=True)):
        if t == ref_idx:
            m, n_in = np.float32([[1, 0, 0], [0, 1, 0]]), len(ref_kp)
        else:
            m, n_in = estimar_afim(orb, bf, ref_kp, ref_des, cinza)
        ok = m is not None and n_in >= INLIERS_MIN
        validos[t] = ok
        medidas.append(
            {
                "inliers": n_in,
                "M": None if m is None else np.round(m, 4).tolist(),
                "usado": bool(ok),
            }
        )
        if ok:
            pilha[t] = cv2.warpAffine(
                quadro,
                m,
                (largura, altura),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(np.nan, np.nan, np.nan),
            ).astype(np.float32)
    return pilha, validos, medidas


def mediana_temporal(pilha: np.ndarray) -> np.ndarray:
    """Mediana por pixel, ignorando NaN (fora do quadro alinhado), ao longo do eixo 0.

    Args:
        pilha: array ``float32`` ``(T, altura, largura, 3)`` com NaN onde não há dado.

    Returns:
        Imagem ``uint8`` ``(altura, largura, 3)``; pixels sem nenhum dado valem 0.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        med = np.nanmedian(pilha, axis=0)
    return np.nan_to_num(med, nan=0.0).clip(0, 255).astype(np.uint8)


def resposta_linha_fina(
    cinza: np.ndarray, m: float, q: float, dist_px: float = DIST_LINHA_PX
) -> np.ndarray:
    """Resposta de linha fina de uma reta ``y = m x + q``, ponto a ponto em ``x``.

    Para cada ``x``, compara o centro da reta com a média de dois pontos a ``dist_px``
    pixels perpendiculares, para cima e para baixo. A distância vertical equivalente é
    ``dist_px * sqrt(1 + m^2)``. Uma corda clara dá valor positivo.

    Args:
        cinza: imagem em tons de cinza ``float32``.
        m: inclinação da reta (``dy/dx``).
        q: ordenada na origem (``y`` em ``x = 0``).
        dist_px: distância perpendicular, em pixels.

    Returns:
        Vetor ``float32`` com um valor por coluna ``x`` válida (dentro da imagem).
    """
    altura, largura = cinza.shape
    xs = np.arange(largura, dtype=np.float32)
    ys = m * xs + q
    dv = dist_px * float(np.sqrt(1.0 + m * m))
    ok = (ys - dv >= 0) & (ys + dv <= altura - 1)
    xs, ys = xs[ok], ys[ok]
    centro = _amostra(cinza, xs, ys)
    cima = _amostra(cinza, xs, ys - dv)
    baixo = _amostra(cinza, xs, ys + dv)
    return centro - 0.5 * (cima + baixo)


def _amostra(cinza: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Valores bilineares da imagem nos pontos ``(xs, ys)``.

    Args:
        cinza: imagem ``float32``.
        xs: coordenadas x, ``float32``.
        ys: coordenadas y, ``float32``.

    Returns:
        Vetor ``float32`` com os valores.
    """
    return cv2.remap(
        cinza,
        xs.reshape(1, -1).astype(np.float32),
        ys.reshape(1, -1).astype(np.float32),
        cv2.INTER_LINEAR,
    ).ravel()


def score_linha(cinza: np.ndarray, m: float, q: float) -> float:
    """Pontuação de uma corda: média dos ``FRAC_TOPO`` pontos mais fortes da resposta.

    Args:
        cinza: imagem em tons de cinza ``float32``.
        m: inclinação da reta.
        q: ordenada na origem.

    Returns:
        Pontuação em níveis de cinza; ``-inf`` se a reta não tem pontos válidos.
    """
    resp = resposta_linha_fina(cinza, m, q)
    if resp.size == 0:
        return float("-inf")
    n_topo = max(1, round(FRAC_TOPO * resp.size))
    return float(np.sort(resp)[-n_topo:].mean())


def retas_do_pente(
    params: tuple[float, float, float, float, float], largura: int
) -> list[tuple[int, float, float]]:
    """Seis retas ``(corda, m, q)`` do modelo de pente, em coordenadas do painel.

    Com ``u = k - 3,5`` (corda 6 em cima, ``u = 2,5``) e ``t = x - largura/2``, o espaçamento
    vertical no ponto ``x`` é ``d * (1 + rho * t / (largura/2))`` (perspectiva: as cordas
    se aproximam do cavalete). A corda ``k`` é a reta ``y = m_k t + Y0 - d u`` com
    ``m_k = m0 + kappa * u - d * rho * u / (largura/2)``.

    Args:
        params: ``(m0, kappa, Y0, d, rho)``.
        largura: largura do painel, em pixels.

    Returns:
        Lista de ``(corda, m, q)`` das cordas 1 a 6, com ``y = m x + q``.
    """
    m0, kappa, y0, d, rho = params
    meio = largura / 2.0
    saida = []
    for corda in range(1, 7):
        u = corda - 3.5
        m = m0 + kappa * u - d * rho * u / meio
        y_meio = y0 - d * u
        q = y_meio - m * meio
        saida.append((corda, float(m), float(q)))
    return saida


def pontuacao_do_pente(
    cinza: np.ndarray,
    params: tuple[float, float, float, float, float],
) -> float:
    """Soma ponderada das pontuações das seis retas do pente (cordas 4 a 6 pesam 1).

    Args:
        cinza: imagem em tons de cinza ``float32``.
        params: ``(m0, kappa, Y0, d, g)``.

    Returns:
        A soma ponderada das pontuações; ``-inf`` se alguma reta não tem pontos.
    """
    total = 0.0
    for corda, m, q in retas_do_pente(params, cinza.shape[1]):
        peso = 1.0 if corda >= 4 else PESO_AGUDAS
        s = score_linha(cinza, m, q)
        if not np.isfinite(s):
            return float("-inf")
        total += peso * s
    return total


#: Busca fina de cada bordão: inclinação ±0,03 (passo 0,005) e ordenada ±15 px (passo 1).
BUSCA_M_BORDAO = 0.03
PASSO_M_BORDAO = 0.005
BUSCA_Y_BORDAO = 15.0


def ancorar_bordoes(
    cinza: np.ndarray, retas: list[dict[str, Any]]
) -> dict[int, tuple[float, float]]:
    """Posição de cada bordão (cordas 4, 5 e 6) por busca fina em torno da reta atual.

    Para cada corda, varre a inclinação e a ordenada no centro do painel e fica com a reta
    de maior pontuação de linha fina (``score_linha``).

    Args:
        cinza: imagem em tons de cinza ``float32``.
        retas: retas atuais no quadro da mediana (``corda``, ``theta``, ``y_centro``).

    Returns:
        ``{corda: (m, y_meio)}`` para as cordas 4, 5 e 6, com ``y_meio`` a ordenada em
        ``x = largura / 2``.
    """
    meio = cinza.shape[1] / 2.0
    ancoras: dict[int, tuple[float, float]] = {}
    for r in retas:
        corda = int(r["corda"])
        if corda < 4:
            continue
        m0 = float(np.tan(float(r["theta"])))
        y0 = float(r["y_centro"])
        melhor = (-np.inf, m0, y0)
        for m in np.arange(
            m0 - BUSCA_M_BORDAO, m0 + BUSCA_M_BORDAO + 1e-9, PASSO_M_BORDAO
        ):
            for y in np.arange(y0 - BUSCA_Y_BORDAO, y0 + BUSCA_Y_BORDAO + 1e-9, 1.0):
                sc = score_linha(cinza, float(m), float(y - m * meio))
                if sc > melhor[0]:
                    melhor = (sc, float(m), float(y))
        ancoras[corda] = (melhor[1], melhor[2])
    return ancoras


def params_por_ancoras(
    ancoras: dict[int, tuple[float, float]], largura: int
) -> tuple[float, float, float, float, float]:
    """Modelo do pente por mínimos quadrados sobre as âncoras (cordas 4, 5 e 6).

    Com ``u = k - 3,5``, a ordenada no centro é ``Y0 - d u`` e a inclinação é
    ``m0 + (kappa - d rho / (largura/2)) u``. Com três âncoras só há duas incógnitas de
    inclinação, então ``kappa`` fica em zero e toda a variação de inclinação vai para
    ``rho`` (a perspectiva, que muda o espaçamento com ``x``).

    Args:
        ancoras: ``{corda: (m, y_meio)}`` das cordas 4, 5 e 6.
        largura: largura do painel, em pixels.

    Returns:
        ``(m0, kappa, Y0, d, rho)`` com ``kappa = 0``.
    """
    cordas = sorted(ancoras)
    us = np.array([k - 3.5 for k in cordas])
    ms = np.array([ancoras[k][0] for k in cordas])
    ys = np.array([ancoras[k][1] for k in cordas])
    a_y = np.column_stack([np.ones_like(us), us])
    c_y, *_ = np.linalg.lstsq(a_y, ys, rcond=None)
    a_m = np.column_stack([np.ones_like(us), us])
    c_m, *_ = np.linalg.lstsq(a_m, ms, rcond=None)
    m0 = float(c_m[0])
    y0 = float(c_y[0])
    d = float(-c_y[1])
    beta = float(c_m[1])
    meio = largura / 2.0
    rho = float(-beta * meio / d) if d else 0.0
    return (m0, 0.0, y0, d, rho)


def retas_em_theta(
    params: tuple[float, float, float, float, float], largura: int
) -> list[dict[str, Any]]:
    """Retas do pente no formato de ``tab.maos_direita_cordas`` (``theta``, ``y_centro``).

    Args:
        params: ``(m0, kappa, Y0, d, g)``.
        largura: largura do painel, em pixels.

    Returns:
        Lista de ``{corda, theta, y_centro, espacamento}`` com ``theta = atan(m)`` e
        ``y_centro`` a ordenada em ``x = largura / 2``.
    """
    meio = largura / 2.0
    saida = []
    for corda, m, q in retas_do_pente(params, largura):
        saida.append(
            {
                "corda": corda,
                "theta": float(np.arctan(m)),
                "y_centro": float(m * meio + q),
            }
        )
    return saida


def transformar_reta(
    theta: float, y_centro: float, m: np.ndarray, largura: int
) -> tuple[float, float]:
    """Reta ``(theta, y_centro)`` depois de uma transformação afim ``2x3`` ``m``.

    Toma dois pontos da reta (em ``x = largura / 2`` e a 100 px ao longo da direção),
    transforma os dois e recalcula a inclinação e a ordenada em ``x = largura / 2``.

    Args:
        theta: direção da corda, em radianos.
        y_centro: ordenada da corda em ``x = largura / 2``.
        m: matriz afim ``2x3`` que leva o quadro de origem ao de destino.
        largura: largura do painel, em pixels.

    Returns:
        ``(theta', y_centro')`` no quadro de destino.
    """
    x1 = largura / 2.0
    y1 = y_centro
    x2 = x1 + 100.0 * np.cos(theta)
    y2 = y1 + 100.0 * np.sin(theta)
    a = np.asarray(m, dtype=float)
    p1 = a[:, :2] @ np.array([x1, y1]) + a[:, 2]
    p2 = a[:, :2] @ np.array([x2, y2]) + a[:, 2]
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    ang = float(np.arctan2(dy, dx))
    if np.cos(ang) < 0:
        ang += np.pi
    m_ang = np.tan(ang)
    y_meio = float(p1[1] + m_ang * (largura / 2.0 - p1[0]))
    return float(np.arctan(m_ang)), y_meio


def crista_por_corda(
    cinza: np.ndarray, retas: list[dict[str, Any]], espacamento: float
) -> dict[int, float | None]:
    """Crista (``cresta_da_reta``) de cada reta, na mesma medida da fase B.

    Args:
        cinza: painel em tons de cinza ``float32``.
        retas: retas com ``corda``, ``theta`` e ``y_centro``.
        espacamento: espaçamento entre cordas, em pixels.

    Returns:
        ``{corda: crista}``, com None onde a reta não tem pontos válidos.
    """
    mascara = np.zeros(cinza.shape, dtype=bool)
    return {
        int(r["corda"]): cresta_da_reta(
            cinza, mascara, float(r["theta"]), float(r["y_centro"]), espacamento
        )
        for r in retas
    }


def contar_retas_que_cruzam(retas: list[dict[str, Any]]) -> bool:
    """Diz se a reta ``k=6`` está acima da ``k=1`` no meio do painel (convenção).

    Args:
        retas: retas no formato de ``retas_em_theta``.

    Returns:
        ``True`` se a corda 6 tem ``y_centro`` menor que a corda 1 (6 em cima).
    """
    y6 = next(r["y_centro"] for r in retas if int(r["corda"]) == 6)
    y1 = next(r["y_centro"] for r in retas if int(r["corda"]) == 1)
    return y6 < y1


# ---------------------------------------------------------------------------------
# Leitura do vídeo e desenho (usam ffmpeg e o acervo)
# ---------------------------------------------------------------------------------


def decodificar_painel_bgr(
    caminho: Path, inicio: float, duracao: float, largura: int, altura: int
) -> np.ndarray:
    """Quadros coloridos (BGR) do painel, em resolução nativa.

    Args:
        caminho: arquivo de vídeo.
        inicio: instante inicial, em segundos.
        duracao: duração, em segundos.
        largura: largura do quadro original.
        altura: altura do quadro original.

    Returns:
        Array ``uint8`` ``(T, h, w, 3)`` com o recorte do painel.
    """
    w, h, x, y = recorte_do_painel(largura, altura)
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
        f"crop={w}:{h}:{x}:{y}",
        "-fps_mode",
        "passthrough",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-",
    ]
    bruto = subprocess.run(cmd, capture_output=True, check=True).stdout
    tamanho = w * h * 3
    n = len(bruto) // tamanho
    return np.frombuffer(bruto[: n * tamanho], dtype=np.uint8).reshape(n, h, w, 3)


def _trechos_do_tempo(nome: str) -> list[float]:
    """Inícios dos trechos de 20 s usados na medição de tempo (``tempo.json``).

    Args:
        nome: nome curto do vídeo.

    Returns:
        Lista de inícios, em segundos.
    """
    dados = json.loads((MAOS_M7 / "tempo.json").read_text(encoding="utf-8"))
    video = next(v for v in dados["videos"] if v["nome"] == nome)
    return [float(t["inicio_s"]) for t in video["trechos"]]


def quadros_do_video(
    caminho: Path, nome: str, por_trecho: int = QUADROS_POR_TRECHO
) -> np.ndarray:
    """Quadros do painel nos trechos com nota, espalhados (``por_trecho`` por trecho).

    Args:
        caminho: arquivo de vídeo.
        nome: nome curto do vídeo (para achar os trechos).
        por_trecho: quadros por trecho.

    Returns:
        Array ``uint8`` ``(T, altura, largura, 3)`` com o recorte do painel.
    """
    largura, altura, _fps = ler_video(caminho)
    lotes = []
    for inicio in _trechos_do_tempo(nome):
        bruto = decodificar_painel_bgr(caminho, inicio, 20.0, largura, altura)
        idx = amostrar_indices(len(bruto), por_trecho)
        lotes.append(bruto[idx])
        _log(f"  trecho {inicio:.1f}s: {len(idx)} quadros de {len(bruto)}")
    return np.concatenate(lotes)


def retas_atuais_no_quadro_da_mediana(
    nome: str, caminho: Path, referencia_cinza: np.ndarray
) -> tuple[list[dict[str, Any]], float]:
    """Retas atuais (``cordas_<v>.json``) levadas para o quadro da mediana.

    As retas foram medidas no quadro ``quadro_de_referencia`` de ``t_quadros``. A afim de
    ORB leva esse quadro ao quadro de referência da mediana.

    Args:
        nome: nome curto do vídeo.
        caminho: arquivo de vídeo.
        referencia_cinza: quadro de referência da mediana, em tons de cinza ``uint8``.

    Returns:
        ``(retas, espacamento)``: retas ``{corda, theta, y_centro}`` no quadro da mediana,
        e o espaçamento médio entre cordas (em pixels).

    Raises:
        RuntimeError: se a afim entre os quadros não se estima.
    """
    atual = json.loads((MAOS_M7 / f"cordas_{nome}.json").read_text(encoding="utf-8"))
    t_ref = float(atual["t_quadros"][int(atual["quadro_de_referencia"])])
    largura, altura, _fps = ler_video(caminho)
    antigo = decodificar_painel_bgr(caminho, t_ref, 0.2, largura, altura)[0]
    orb = cv2.ORB_create(nfeatures=N_CARACTERISTICAS)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref_kp, ref_des = orb.detectAndCompute(referencia_cinza, None)
    m, n_in = estimar_afim(
        orb, bf, ref_kp, ref_des, cv2.cvtColor(antigo, cv2.COLOR_BGR2GRAY)
    )
    if m is None:
        raise RuntimeError(f"{nome}: afim entre o quadro das retas e a mediana falhou")
    w = referencia_cinza.shape[1]
    retas = []
    for c in atual["cordas"]:
        theta, y_c = transformar_reta(float(c["theta"]), float(c["y_centro"]), m, w)
        retas.append({"corda": int(c["corda"]), "theta": theta, "y_centro": y_c})
    _log(f"{nome}: afim das retas atuais com {n_in} inliers")
    return retas, espacamento_das_cordas(atual["cordas"])


def main() -> None:
    """Mediana alinhada, retas atuais e pente por vídeo; grava as saídas em ``MAOS_M7``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--video", choices=NOMES, action="append", default=None)
    args = parser.parse_args()
    nomes = args.video or list(NOMES)
    relatorio: dict[str, Any] = {"videos": {}}
    MAOS_M7.mkdir(parents=True, exist_ok=True)
    for indice, video in enumerate(VIDEOS):
        nome = NOMES[indice]
        if nome not in nomes:
            continue
        caminho = acervo() / video["arquivo"]
        _log(f"{nome}: quadros")
        quadros = quadros_do_video(caminho, nome)
        pilha, validos, medidas = alinhar_quadros(quadros)
        mediana = mediana_temporal(pilha[validos])
        cv2.imwrite(str(MAOS_M7 / f"mediana_{nome}.png"), mediana)
        cinza = cv2.cvtColor(mediana, cv2.COLOR_BGR2GRAY).astype(np.float32)
        ref_cinza = cv2.cvtColor(quadros[len(quadros) // 2], cv2.COLOR_BGR2GRAY)
        retas_antes, espac = retas_atuais_no_quadro_da_mediana(nome, caminho, ref_cinza)
        ancoras = ancorar_bordoes(cinza, retas_antes)
        params = params_por_ancoras(ancoras, cinza.shape[1])
        score = pontuacao_do_pente(cinza, params)
        retas_pente = retas_em_theta(params, cinza.shape[1])
        d_pente = params[3]
        crista_antes = crista_por_corda(cinza, retas_antes, espac)
        crista_pente = crista_por_corda(cinza, retas_pente, d_pente)
        y6_acima = contar_retas_que_cruzam(retas_pente)
        _log(
            f"{nome}: ancoras={ {k: (round(m, 4), round(y, 1)) for k, (m, y) in ancoras.items()} } "
            f"pente params={[round(v, 4) for v in params]} score={score:.1f} "
            f"6_em_cima={y6_acima}"
        )
        for corda in range(1, 7):
            _log(
                f"  corda {corda}: crista antes={crista_antes[corda]} "
                f"pente={crista_pente[corda]}"
            )
        relatorio["videos"][nome] = {
            "n_quadros": len(quadros),
            "n_validos": int(validos.sum()),
            "inliers_mediana": int(np.median([m["inliers"] for m in medidas])),
            "espacamento_antes": espac,
            "ancoras_bordoes": {
                k: [round(m, 5), round(y, 2)] for k, (m, y) in ancoras.items()
            },
            "params_pente": [round(v, 5) for v in params],
            "score_pente": round(score, 3),
            "seis_em_cima": bool(y6_acima),
            "retas_antes": retas_antes,
            "retas_pente": retas_pente,
            "crista_antes": {k: _r(v) for k, v in crista_antes.items()},
            "crista_pente": {k: _r(v) for k, v in crista_pente.items()},
        }
        desenhar_cordas_sobre(
            mediana, retas_antes, retas_pente, MAOS_M7 / f"cordas_pente_{nome}.jpg"
        )
        desenhar_cordas_sobre(
            quadros[len(quadros) // 2],
            retas_antes,
            retas_pente,
            MAOS_M7 / f"cordas_pente_quadro_{nome}.jpg",
        )
    (MAOS_M7 / "pente.json").write_text(
        json.dumps(relatorio, indent=1, ensure_ascii=False), encoding="utf-8"
    )


def _r(valor: float | None) -> float | None:
    """Arredonda a 2 casas, mantendo None.

    Args:
        valor: número ou None.

    Returns:
        ``round(valor, 2)`` ou None.
    """
    return None if valor is None else round(float(valor), 2)


def desenhar_cordas_sobre(
    imagem_bgr: np.ndarray,
    antes: list[dict[str, Any]],
    pente: list[dict[str, Any]],
    caminho: Path,
) -> None:
    """Desenha as retas antes (cinza, tracejada) e o pente (coloridas) sobre a imagem.

    Também grava um recorte 2x da região do cavalete (ver ``RECORTE_CAVALETE``).

    Args:
        imagem_bgr: imagem ``uint8`` BGR do painel.
        antes: retas atuais (``theta``, ``y_centro``, ``corda``).
        pente: retas do pente (``theta``, ``y_centro``, ``corda``).
        caminho: arquivo JPG de saída; o recorte vai para ``*_cavalete.jpg``.
    """
    img = imagem_bgr.copy()
    w = img.shape[1]
    for r in antes:
        _linha(img, r, (160, 160, 160), 1, w, pontilhada=True)
    for r in pente:
        _linha(img, r, CORES_CORDAS[int(r["corda"])], 1, w)
    for r in pente:
        xy = _rotulo(r, w)
        cv2.putText(
            img,
            str(r["corda"]),
            xy,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            CORES_CORDAS[int(r["corda"])],
            2,
        )
    cv2.imwrite(str(caminho), img)
    x0, y0, x1, y1 = RECORTE_CAVALETE
    recorte = img[y0:y1, x0:x1]
    recorte = cv2.resize(recorte, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(caminho.with_name(caminho.stem + "_cavalete.jpg")), recorte)


def _linha(
    img: np.ndarray,
    r: dict[str, Any],
    cor: tuple[int, int, int],
    espessura: int,
    largura: int,
    pontilhada: bool = False,
) -> None:
    """Desenha uma reta ``(theta, y_centro)`` de ``x=0`` a ``x=largura``.

    Args:
        img: imagem a desenhar (in place).
        r: reta com ``theta`` e ``y_centro``.
        cor: cor BGR.
        espessura: espessura, em pixels.
        largura: largura do painel.
        pontilhada: se True, desenha em trechos (tracejado).
    """
    m = np.tan(float(r["theta"]))
    meio = largura / 2.0
    passo = 8 if pontilhada else 2
    xs = np.arange(0, largura, passo, dtype=float)
    ys = r["y_centro"] + m * (xs - meio)
    for k in range(0, len(xs) - 1, 2 if pontilhada else 1):
        cv2.line(
            img,
            (int(xs[k]), int(np.rint(ys[k]))),
            (int(xs[k + 1]), int(np.rint(ys[k + 1]))),
            cor,
            espessura,
        )


def _rotulo(r: dict[str, Any], largura: int) -> tuple[int, int]:
    """Posição do número da corda, perto da borda direita da reta.

    Args:
        r: reta com ``theta`` e ``y_centro``.
        largura: largura do painel.

    Returns:
        ``(x, y)`` inteiros.
    """
    m = np.tan(float(r["theta"]))
    x = largura - 25
    y = r["y_centro"] + m * (x - largura / 2.0)
    return int(x), int(np.clip(y, 15, 540))


if __name__ == "__main__":
    main()
