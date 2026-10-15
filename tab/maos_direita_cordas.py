"""Diagnóstico M7: a câmera da mão direita, sozinha, mostra a corda atacada?

Fase 1 da decisão 1005 (``docs/decisoes/1005-mao-direita-serve-a-corda.md``). Sem
preditor: só mede. Para cada vídeo do M5 (sky guitar, com tablatura na tela):

1. ``achar_painel``: o recorte da câmera da mão direita, embaixo e à esquerda da faixa
   preta vertical;
2. ``achar_retas``, ``consolidar_retas``, ``ordenar_cordas``: as 6 cordas no painel,
   como retas (pela mediana de cinco quadros), numeradas 1 (aguda) a 6 (grave) pela
   espessura medida em ``espessura_corda``;
3. ``registrar_ataque``: para 30 ataques sorteados, o ``DetectorMaos`` em volta do
   ``t_ini`` e a mão direita dentro do painel, com as 21 pontas e os scores;
4. ``desenhar_folha``: imagens para conferência visual (cordas e pontas por ataque).

Fica fora do gate: as trajetórias precisam de GPU e do acervo montado.

Uso::

    python -m tab.maos_direita_cordas --etapa tudo
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np

#: Semente do sorteio dos ataques (a da decisão 1005 e a do M7).
SEMENTE = 20261015

#: Deslocamentos, em segundos, dos quadros em volta de cada ataque.
DELTAS_S = (-0.20, -0.13, -0.07, 0.0, 0.07)

#: Ataques sorteados por vídeo.
N_ATAQUES = 30

#: Ataques na folha de conferência por vídeo.
N_FOLHA = 8

#: Quadros usados para achar as cordas (espalhados nos instantes com nota).
N_QUADROS_CORDAS = 5

#: Cordas do violão.
N_CORDAS = 6

#: Nomes curtos dos vídeos (chave da linha de comando e dos arquivos de saída); a
#: ordem é a de ``VIDEOS`` em ``tab.maos_padroes_preparar``.
NOMES_VIDEOS = ("retrato_brasileiro", "chopin_nocturne20", "lacrimosa", "glimpse_of_us")

#: Pixels abaixo deste nível de cinza contam como preto.
LIMIAR_PRETO = 12.0

#: Faixa preta vertical procurada entre estas frações da largura.
FRAC_FAIXA_MIN = 0.2
FRAC_FAIXA_MAX = 0.6

#: Altura mínima, em pixels, da faixa preta horizontal que separa tablatura e câmeras.
MIN_FAIXA_PRETA_PX = 6

#: Ângulos de busca das cordas, em graus (negativo = sobe para a direita na imagem).
ANG_BUSCA_MIN = -75.0
ANG_BUSCA_MAX = -20.0
PASSO_BUSCA = 1.0

#: Sigma, em pixels, do fundo subtraído no relevo usado para alinhar os quadros.
SIGMA_FUNDO = 5.0

#: Comprimento, em pixels, do núcleo que realça linhas retas (cordas).
TAMANHO_FILTRO_PX = 41

#: Vale e separação mínima entre cordas, em pixels da imagem girada.
JANELA_PICO_PX = 20
SEPARACAO_PICO_PX = 15

#: Contraste mínimo de cada corda sobre a mediana do perfil, para aceitar um ajuste.
CONTRASTE_MIN = 1.5

#: Distância máxima, em pixels no eixo y do meio do painel, entre uma corda de um
#: quadro e a referência dela; e iterações do casamento entre quadros.
TOL_CASAMENTO_PX = 15.0
ITERACOES_CASAMENTO = 3

#: Quadros mínimos em que uma corda precisa aparecer para entrar no resultado.
MIN_QUADROS = 3

#: Cores fixas (BGR) das pontas nas folhas (polegar não entra).
CORES_PONTAS = {4: (0, 0, 255), 8: (0, 255, 0), 12: (255, 0, 0), 16: (0, 255, 255)}

#: Cores fixas (BGR) das cordas 1 a 6 nas imagens.
CORES_CORDAS = [
    (0, 0, 255),
    (0, 255, 0),
    (255, 0, 0),
    (0, 255, 255),
    (255, 0, 255),
    (255, 255, 0),
]

#: Quadros cujo deslocamento das pontas é medido (segundos em volta do ataque).
DELTA_DESL_INICIO = -0.13
DELTA_DESL_FIM = 0.07

#: Tolerância, em segundos, para casar o ``t_ini`` de uma nota com o do ataque.
TOLERANCIA_T = 0.002


# ---------------------------------------------------------------------------------
# Painel
# ---------------------------------------------------------------------------------


def achar_painel(bgr: np.ndarray) -> tuple[int, int, int, int]:
    """Acha o retângulo da câmera da mão direita num quadro inteiro.

    A câmera fica na metade de baixo, à esquerda de uma faixa preta vertical. A faixa é
    o trecho mais longo de colunas quase pretas na metade de baixo. O topo do painel é o
    fim da primeira faixa preta horizontal, com pelo menos ``MIN_FAIXA_PRETA_PX`` linhas,
    que separa a tablatura (branca) da câmera.

    Args:
        bgr: quadro inteiro em BGR.

    Returns:
        ``(x0, y0, x1, y1)`` do painel, com ``x1`` e ``y1`` exclusivos.

    Raises:
        ValueError: se a faixa preta vertical ou a horizontal não aparecem.
    """
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = cinza.shape
    media_colunas = cinza[h // 2 :, :].mean(axis=0)
    candidatas = np.where(media_colunas < LIMIAR_PRETO)[0]
    candidatas = candidatas[
        (candidatas > FRAC_FAIXA_MIN * w) & (candidatas < FRAC_FAIXA_MAX * w)
    ]
    if candidatas.size == 0:
        raise ValueError("faixa preta vertical não achada")
    trechos = np.split(candidatas, np.where(np.diff(candidatas) > 1)[0] + 1)
    x1 = int(max(trechos, key=len)[0])
    escuro = cinza[:, : max(x1 - 2, 1)].mean(axis=1) < LIMIAR_PRETO
    y = int(0.4 * h)
    while y < h:
        if not escuro[y]:
            y += 1
            continue
        fim = y
        while fim < h and escuro[fim]:
            fim += 1
        if fim - y >= MIN_FAIXA_PRETA_PX:
            return (0, fim, x1, h)
        y = fim
    raise ValueError("faixa preta horizontal não achada")


# ---------------------------------------------------------------------------------
# Cordas como retas
# ---------------------------------------------------------------------------------


def _relevo_de_linha(cinza: np.ndarray) -> np.ndarray:
    """Realce de linhas finas claras: o quadro menos um fundo borrado.

    Args:
        cinza: painel em tons de cinza.

    Returns:
        ``float32`` com o relevo positivo (linhas claras e finas acima do fundo).
    """
    f = cinza.astype(np.float32)
    fundo = cv2.GaussianBlur(f, (0, 0), SIGMA_FUNDO)
    return np.clip(f - fundo, 0.0, None)


def _filtro_de_linha(theta: float, tamanho: int = TAMANHO_FILTRO_PX) -> np.ndarray:
    """Núcleo de média zero que responde a uma linha fina e reta na direção ``theta``.

    Perfil transversal de diferença de gaussianas (sigma 1 px menos um terço de sigma
    3 px), truncado ao comprimento ``tamanho`` na direção da linha. Arcos e grão da
    madeira, que não são retos por esse comprimento, respondem pouco.

    Args:
        theta: direção da linha, em radianos (imagem, y para baixo).
        tamanho: lado do núcleo, em pixels (ímpar).

    Returns:
        Núcleo ``float32`` de média zero dentro da máscara.
    """
    meio = tamanho // 2
    u, v = np.meshgrid(np.arange(-meio, meio + 1), np.arange(-meio, meio + 1))
    ao = u * np.cos(theta) + v * np.sin(theta)
    ac = -u * np.sin(theta) + v * np.cos(theta)
    mascara = np.abs(ao) <= meio
    perfil = np.exp(-(ac**2) / 2.0) - (1.0 / 3.0) * np.exp(-(ac**2) / 18.0)
    nucleo = np.where(mascara, perfil, 0.0)
    nucleo[mascara] -= nucleo[mascara].mean()
    return nucleo.astype(np.float32)


def _picos_do_perfil(
    perfil: np.ndarray, n: int, janela: int, separacao: int
) -> list[tuple[int, float]]:
    """Os ``n`` picos mais proeminentes de um perfil 1D.

    A proeminência é a altura do pico acima do maior dos dois vales vizinhos, em
    ``janela`` posições para cada lado. Picos mais próximos que ``separacao`` não se
    repetem (fica o mais proeminente).

    Args:
        perfil: valores ao longo de um eixo.
        n: quantos picos devolver, no máximo.
        janela: alcance, em posições, para procurar os vales.
        separacao: distância mínima, em posições, entre picos escolhidos.

    Returns:
        Pares ``(índice, proeminência)``, do mais proeminente para o menos.
    """
    p = np.convolve(perfil, [0.25, 0.5, 0.25], mode="same")
    candidatos = []
    for i in range(1, len(p) - 1):
        if p[i] >= p[i - 1] and p[i] > p[i + 1]:
            vale_e = float(p[max(0, i - janela) : i + 1].min())
            vale_d = float(p[i : i + janela + 1].min())
            candidatos.append((float(p[i] - max(vale_e, vale_d)), i))
    escolhidos: list[tuple[int, float]] = []
    for prom, i in sorted(candidatos, reverse=True):
        if all(abs(i - j) >= separacao for j, _ in escolhidos):
            escolhidos.append((i, prom))
        if len(escolhidos) == n:
            break
    return escolhidos


def achar_retas(painel: np.ndarray) -> list[dict[str, Any]]:
    """As seis cordas de um recorte do painel, de um quadro, ou nenhuma.

    Para cada ângulo de busca: filtra o painel com um núcleo de linha reta
    (``_filtro_de_linha``), gira a resposta para deixar as cordas horizontais, soma cada
    linha e ajusta seis posições igualmente espaçadas (``_ajustar_seis_linhas``). Fica o
    ângulo de maior pontuação. Cada posição vira uma reta de volta às coordenadas do
    painel.

    Args:
        painel: recorte BGR do painel (só a câmera da mão direita).

    Returns:
        Seis retas ``{theta, y_centro, suporte, contraste, angulo_busca}`` de cima para
        baixo, ou lista vazia se nenhum ângulo passa no contraste mínimo.
        ``theta`` é a direção em radianos (módulo pi), ``y_centro`` a altura em
        ``x = largura/2``, ``suporte`` o valor do perfil na corda.
    """
    cinza = cv2.cvtColor(painel, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = cinza.shape
    centro = (w / 2.0, h / 2.0)
    melhor: tuple[float, float, np.ndarray, np.ndarray, np.ndarray] | None = None
    for angulo in np.arange(ANG_BUSCA_MIN, ANG_BUSCA_MAX + PASSO_BUSCA, PASSO_BUSCA):
        nucleo = _filtro_de_linha(np.deg2rad(180.0 + float(angulo)))
        resposta = np.clip(cv2.filter2D(cinza, -1, nucleo), 0.0, None)
        m = cv2.getRotationMatrix2D(centro, float(angulo), 1.0)
        girada = cv2.warpAffine(resposta, m, (w, h), flags=cv2.INTER_LINEAR)
        perfil = girada.sum(axis=1)
        mediana = float(np.median(perfil)) + 1e-6
        picos = _picos_do_perfil(perfil, N_CORDAS, JANELA_PICO_PX, SEPARACAO_PICO_PX)
        if len(picos) < N_CORDAS:
            continue
        contrastes_a = [prom / mediana for _, prom in picos]
        if min(contrastes_a) < CONTRASTE_MIN:
            continue
        pontuacao = float(sum(contrastes_a))
        if melhor is None or pontuacao > melhor[0]:
            melhor = (
                pontuacao,
                float(angulo),
                m,
                np.array([float(i) for i, _ in picos]),
                np.array(contrastes_a),
            )
    if melhor is None:
        return []
    _, angulo, m, ys, contrastes = melhor
    inversa = cv2.invertAffineTransform(m)
    direcao = inversa[:, :2] @ np.array([1.0, 0.0])
    theta = float(np.mod(np.arctan2(direcao[1], direcao[0]), np.pi))
    retas = []
    for y_r, contraste in zip(ys, contrastes, strict=True):
        px, py = inversa @ np.array([w / 2.0, float(y_r), 1.0])
        retas.append(
            {
                "theta": theta,
                "y_centro": float(py + (w / 2.0 - px) * np.tan(theta)),
                "suporte": float(contraste),
                "contraste": float(contraste),
                "angulo_busca": angulo,
            }
        )
    return sorted(retas, key=lambda r: r["y_centro"])


def deslocamento_entre_quadros(
    relevo_ref: np.ndarray, relevo_i: np.ndarray
) -> tuple[float, float]:
    """Translação do painel de um quadro em relação ao de referência.

    A câmera se desloca alguns pixels entre quadros. Usa correlação de fase no relevo
    das linhas. Um ponto do quadro de referência aparece em ``(dx, dy)`` no quadro
    ``i``.

    Args:
        relevo_ref: relevo de linhas do quadro de referência (``float32``).
        relevo_i: relevo de linhas do quadro ``i`` (mesmo tamanho).

    Returns:
        ``(dx, dy)`` em pixels.
    """
    janela = cv2.createHanningWindow(
        (relevo_ref.shape[1], relevo_ref.shape[0]), cv2.CV_32F
    )
    (dx, dy), _ = cv2.phaseCorrelate(relevo_ref, relevo_i, janela)
    return float(dx), float(dy)


def alinhar_retas(
    retas: list[dict[str, Any]], deslocamento: tuple[float, float]
) -> list[dict[str, Any]]:
    """Leva as retas de um quadro para as coordenadas do quadro de referência.

    Uma reta ``y = yc + tan(theta) * (x - w/2)`` do quadro ``i`` passa, no de
    referência, por ``yc - dy + dx * tan(theta)`` em ``x = w/2``.

    Args:
        retas: retas de ``achar_retas`` do quadro ``i``.
        deslocamento: ``(dx, dy)`` de ``deslocamento_entre_quadros``.

    Returns:
        Cópias das retas com ``y_centro`` no quadro de referência.
    """
    dx, dy = deslocamento
    return [
        {**r, "y_centro": float(r["y_centro"] - dy + dx * np.tan(r["theta"]))}
        for r in retas
    ]


def consolidar_retas(
    retas_por_quadro: list[list[dict[str, Any]]],
    minimo_quadros: int = MIN_QUADROS,
    n_cordas: int = N_CORDAS,
) -> list[dict[str, Any]]:
    """Junta as retas de vários quadros numa lista de cordas.

    A câmera é fixa, mas as cordas se deslocam de 5 a 10 px entre quadros. Começa de
    referências no quadro com mais retas (até ``n_cordas``). Depois, repete três vezes:
    cada reta de cada quadro vai para a referência mais próxima, se estiver a até
    ``TOL_CASAMENTO_PX`` dela (uma por referência e por quadro), e cada referência
    passa a ser a mediana das retas casadas. Mantém as referências casadas em pelo menos
    ``minimo_quadros`` quadros.

    Args:
        retas_por_quadro: lista, por quadro, das retas de ``achar_retas``.
        minimo_quadros: quadros mínimos em que a corda aparece.
        n_cordas: quantas cordas no máximo.

    Returns:
        Cordas ``{theta, y_centro, suporte, n_quadros}`` de cima para baixo.
    """
    if not any(retas_por_quadro):
        return []
    inicial = max(retas_por_quadro, key=len)
    refs = sorted(r["y_centro"] for r in inicial)
    for _ in range(ITERACOES_CASAMENTO):
        casados: list[list[dict[str, Any]]] = [[] for _ in refs]
        for retas in retas_por_quadro:
            usados: set[int] = set()
            for k, ref in enumerate(refs):
                distancias = [abs(r["y_centro"] - ref) for r in retas]
                if not distancias:
                    continue
                i = int(np.argmin(distancias))
                if distancias[i] <= TOL_CASAMENTO_PX and i not in usados:
                    usados.add(i)
                    casados[k].append(retas[i])
        refs = [
            float(np.median([r["y_centro"] for r in c])) if c else ref
            for c, ref in zip(casados, refs, strict=True)
        ]
    cordas = []
    for c in casados:
        if len(c) < minimo_quadros:
            continue
        cordas.append(
            {
                "theta": float(np.median([r["theta"] for r in c])),
                "y_centro": float(np.median([r["y_centro"] for r in c])),
                "suporte": float(sum(r["suporte"] for r in c)),
                "n_quadros": len(c),
            }
        )
    if len(cordas) > n_cordas:
        cordas = sorted(cordas, key=lambda c: c["suporte"], reverse=True)[:n_cordas]
    return sorted(cordas, key=lambda c: c["y_centro"])


def espessura_corda(cinza: np.ndarray, reta: dict[str, Any]) -> dict[str, float] | None:
    """Espessura aparente de uma corda, pelo perfil de brilho perpendicular a ela.

    Amostra perfis perpendiculares em vários pontos ao longo da reta, sem os que caem
    na borda do painel. Em cada perfil, o fundo é a mediana e o sinal (claro ou escuro)
    é o do maior desvio. Devolve a mediana da largura a meia altura (FWHM) e da área
    acima do fundo, em pixels.

    Args:
        cinza: painel em tons de cinza, ``float32``.
        reta: corda de ``consolidar_retas`` (``theta`` e ``y_centro`` no painel).

    Returns:
        ``{"fwhm", "area", "perfis"}``, ou None se nenhum perfil tem contraste.
    """
    h, w = cinza.shape
    th = reta["theta"]
    direcao = np.array([np.cos(th), np.sin(th)])
    normal = np.array([-np.sin(th), np.cos(th)])
    origem = np.array([w / 2, reta["y_centro"]])
    offsets = np.arange(-6.0, 6.0 + 0.25, 0.25)
    passo = float(offsets[1] - offsets[0])
    fwhms, areas = [], []
    for t in np.linspace(-0.35 * w, 0.35 * w, 24):
        q = (origem + t * direcao)[None, :] + offsets[:, None] * normal[None, :]
        if (q[:, 0] < 4).any() or (q[:, 0] > w - 5).any():
            continue
        if (q[:, 1] < 4).any() or (q[:, 1] > h - 5).any():
            continue
        perfil = cv2.remap(
            cinza,
            q[:, 0].astype(np.float32).reshape(1, -1),
            q[:, 1].astype(np.float32).reshape(1, -1),
            cv2.INTER_LINEAR,
        ).ravel()
        fundo = float(np.median(perfil))
        sinal = 1.0 if perfil.max() - fundo >= fundo - perfil.min() else -1.0
        vals = sinal * (perfil - fundo)
        pico = float(vals.max())
        if pico < 8.0:
            continue
        fwhms.append(float((vals >= pico / 2).sum()) * passo)
        areas.append(float(np.clip(vals, 0, None).sum()) * passo)
    if not fwhms:
        return None
    return {
        "fwhm": float(np.median(fwhms)),
        "area": float(np.median(areas)),
        "perfis": len(fwhms),
    }


def ordenar_cordas(
    cordas: list[dict[str, Any]], espessuras: list[float]
) -> list[dict[str, Any]]:
    """Numera as cordas: 1 é a mais aguda, 6 a mais grave.

    As cordas 1 a 3 são de nylon liso e as 4 a 6 são enroladas, mais grossas. As seis
    estão em ordem espacial, de cima para baixo. A metade do painel com as três mais
    grossas é a das cordas graves. Se a metade de cima for a mais grossa, numera-se de
    cima para baixo como 6 a 1; senão, como 1 a 6.

    Args:
        cordas: cordas de ``consolidar_retas`` (de cima para baixo), com 6 itens.
        espessuras: área média de cada corda, na mesma ordem.

    Returns:
        Cópias das cordas com ``corda`` (1 a 6) e ``espessura_area``, de cima para baixo.

    Raises:
        ValueError: se não houver exatamente ``N_CORDAS`` cordas.
    """
    if len(cordas) != N_CORDAS:
        raise ValueError(f"esperava {N_CORDAS} cordas, veio {len(cordas)}")
    alta = float(np.mean(espessuras[:3]))
    baixa = float(np.mean(espessuras[3:]))
    graves_em_cima = alta > baixa
    numeros = list(range(N_CORDAS, 0, -1)) if graves_em_cima else list(range(1, 7))
    return [
        {**corda, "corda": numero, "espessura_area": float(esp)}
        for corda, numero, esp in zip(cordas, numeros, espessuras, strict=True)
    ]


def _reta_no_quadro(
    reta: dict[str, Any], painel: tuple[int, int, int, int]
) -> dict[str, Any]:
    """Reta do painel em coordenadas do quadro inteiro, na forma ``a*x + b*y = c``.

    Args:
        reta: corda com ``theta`` e ``y_centro`` (coordenadas do painel).
        painel: retângulo do painel no quadro.

    Returns:
        ``{a, b, c, ponto, direcao}``, com ``ponto`` no meio do painel.
    """
    x0, y0, x1, _ = painel
    th = reta["theta"]
    a, b = float(-np.sin(th)), float(np.cos(th))
    ponto = [float(x0 + (x1 - x0) / 2), float(y0 + reta["y_centro"])]
    return {
        "a": a,
        "b": b,
        "c": a * ponto[0] + b * ponto[1],
        "ponto": ponto,
        "direcao": [float(np.cos(th)), float(np.sin(th))],
    }


def achar_cordas(
    frames: list[np.ndarray], painel: tuple[int, int, int, int]
) -> dict[str, Any]:
    """Cordas de um vídeo, a partir de quadros inteiros e do painel.

    Args:
        frames: quadros inteiros em BGR, do mesmo vídeo.
        painel: retângulo do painel (``achar_painel``).

    Returns:
        ``{painel, retas_por_quadro, cordas_brutas, cordas}``. ``cordas`` vem numerada e
        com a forma no quadro inteiro quando há exatamente 6 cordas; senão, é vazia.
    """
    x0, y0, x1, y1 = painel
    recortes = [f[y0:y1, x0:x1] for f in frames]
    retas_por_quadro = [achar_retas(r) for r in recortes]
    relevos = [_relevo_de_linha(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)) for r in recortes]
    ref = int(np.argmax([sum(r["suporte"] for r in rs) for rs in retas_por_quadro]))
    alinhadas = [
        alinhar_retas(rs, deslocamento_entre_quadros(relevos[ref], relevos[i]))
        for i, rs in enumerate(retas_por_quadro)
    ]
    brutas = consolidar_retas(alinhadas)
    resultado: dict[str, Any] = {
        "painel": list(painel),
        "retas_por_quadro": [len(r) for r in retas_por_quadro],
        "quadro_de_referencia": ref,
        "cordas_brutas": len(brutas),
        "retas_consolidadas": brutas,
        "cordas": [],
    }
    if len(brutas) != N_CORDAS:
        return resultado
    cinzas = [cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).astype(np.float32) for r in recortes]
    espessuras = []
    for corda in brutas:
        medidas = [espessura_corda(c, corda) for c in cinzas]
        validas = [m["area"] for m in medidas if m is not None]
        espessuras.append(float(np.median(validas)) if validas else 0.0)
    numeradas = ordenar_cordas(brutas, espessuras)
    resultado["cordas"] = [{**c, **_reta_no_quadro(c, painel)} for c in numeradas]
    return resultado


# ---------------------------------------------------------------------------------
# Ataques e trajetórias
# ---------------------------------------------------------------------------------


def instantes_distintos(notas: list[dict[str, Any]]) -> list[float]:
    """Instantes ``t_ini`` distintos do produto, em ordem crescente.

    Args:
        notas: lista ``notas`` do produto.

    Returns:
        Instantes arredondados a 3 casas, sem repetição.
    """
    return sorted(
        {round(float(n["t_ini"]), 3) for n in notas if n.get("t_ini") is not None}
    )


def ataques_sorteados(instantes: list[float], n: int, semente: int) -> list[float]:
    """Sorteia até ``n`` instantes espalhados no vídeo, um por faixa de tempo.

    Divide os instantes em ``n`` faixas cronológicas de tamanho parecido e sorteia um de
    cada faixa com ``random.Random(semente)``.

    Args:
        instantes: instantes distintos, em ordem crescente.
        n: quantos ataques.
        semente: semente do sorteio.

    Returns:
        Instantes sorteados, em ordem crescente (no máximo ``n``).
    """
    rng = random.Random(semente)
    faixas = [f for f in np.array_split(np.array(instantes), n) if len(f)]
    return [float(rng.choice([float(x) for x in f])) for f in faixas]


def instantes_de_referencia(instantes: list[float], n: int) -> list[float]:
    """Instantes para achar as cordas, espalhados por quantis.

    Args:
        instantes: instantes distintos, em ordem crescente.
        n: quantos instantes.

    Returns:
        ``n`` instantes, em posições relativas igualmente espaçadas entre 10% e 90%.
    """
    if not instantes:
        return []
    return [instantes[int(len(instantes) * f)] for f in np.linspace(0.1, 0.9, n)]


def cordas_do_ataque(notas: list[dict[str, Any]], t: float) -> list[dict[str, Any]]:
    """Notas da tablatura que começam no instante ``t``.

    Args:
        notas: lista ``notas`` do produto.
        t: instante do ataque, em segundos.

    Returns:
        ``{corda, casa, tecnica}`` de cada nota com ``t_ini`` igual a ``t``.
    """
    return [
        {"corda": n["corda"], "casa": n.get("casa"), "tecnica": n.get("tecnica")}
        for n in notas
        if n.get("t_ini") is not None and abs(float(n["t_ini"]) - t) <= TOLERANCIA_T
    ]


def mao_direita_no_painel(
    maos: list[dict[str, Any]], painel: tuple[int, int, int, int]
) -> int | None:
    """Índice da mão direita cuja caixa tem o centro dentro do painel.

    Se houver mais de uma, fica a de maior média de scores.

    Args:
        maos: mãos de um quadro, como em ``mao_para_registro`` (``lado``, ``caixa``).
        painel: retângulo do painel no quadro.

    Returns:
        Índice em ``maos`` da mão escolhida, ou None.
    """
    x0, y0, x1, y1 = painel
    candidatas = []
    for i, mao in enumerate(maos):
        if mao["lado"] != "direita":
            continue
        cx = (mao["caixa"][0] + mao["caixa"][2]) / 2
        cy = (mao["caixa"][1] + mao["caixa"][3]) / 2
        if x0 <= cx < x1 and y0 <= cy < y1:
            media = mao.get("media")
            candidatas.append((-1.0 if media is None else float(media), i))
    if not candidatas:
        return None
    return max(candidatas)[1]


# ---------------------------------------------------------------------------------
# Imagens
# ---------------------------------------------------------------------------------


def ponto_do_rotulo(
    y_centro: float, theta: float, largura: int, altura: int, margem: int = 25
) -> tuple[int, int]:
    """Ponto de uma reta de corda, dentro do painel, para escrever o número dela.

    Interseciona a reta com as bordas do painel recuadas por ``margem``, na ordem:
    embaixo, à esquerda, à direita, em cima. Usa a primeira interseção que cai dentro.

    Args:
        y_centro: altura da reta em ``x = largura/2`` (coordenadas do painel).
        theta: direção da reta, em radianos.
        largura: largura do painel, em pixels.
        altura: altura do painel, em pixels.
        margem: afastamento das bordas, em pixels.

    Returns:
        ``(x, y)`` inteiros dentro do painel.
    """
    x_mid = largura / 2.0
    dx, dy = float(np.cos(theta)), float(np.sin(theta))
    bordas = []
    if abs(dy) > 1e-9:
        for alvo in (altura - margem, margem):
            s_ = (alvo - y_centro) / dy
            bordas.append((x_mid + s_ * dx, float(alvo)))
    if abs(dx) > 1e-9:
        for alvo in (margem, largura - margem):
            s_ = (alvo - x_mid) / dx
            bordas.append((float(alvo), y_centro + s_ * dy))
    for x, y in bordas:
        if margem <= x <= largura - margem and margem <= y <= altura - margem:
            return round(x), round(y)
    return round(x_mid), round(min(max(y_centro, margem), altura - margem))


def desenhar_cordas(
    painel_bgr: np.ndarray, cordas: list[dict[str, Any]], titulo: str
) -> np.ndarray:
    """Cópia do painel com as 6 retas de cordas, numeradas, e um título.

    Args:
        painel_bgr: recorte BGR do painel.
        cordas: cordas com ``theta`` e ``y_centro`` (coordenadas do painel) e ``corda``.
        titulo: texto no topo da imagem.

    Returns:
        Imagem BGR com as retas e o título.
    """
    img = painel_bgr.copy()
    h, w = img.shape[:2]
    for corda in cordas:
        th = corda["theta"]
        x_mid, y_mid = w / 2, corda["y_centro"]
        d = np.array([np.cos(th), np.sin(th)])
        pa = (int(x_mid - d[0] * w), int(y_mid - d[1] * w))
        pb = (int(x_mid + d[0] * w), int(y_mid + d[1] * w))
        cor = CORES_CORDAS[(corda["corda"] - 1) % len(CORES_CORDAS)]
        cv2.line(img, pa, pb, cor, 1, cv2.LINE_AA)
        x_r, y_r = ponto_do_rotulo(y_mid, th, w, h)
        cv2.putText(
            img,
            str(corda["corda"]),
            (x_r, y_r),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            cor,
            2,
            cv2.LINE_AA,
        )
    cv2.rectangle(img, (0, 0), (img.shape[1], 28), (0, 0, 0), -1)
    cv2.putText(
        img, titulo, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1
    )
    return img


def pontas_no_painel(
    registro: dict[str, Any], painel: tuple[int, int, int, int]
) -> dict[int, tuple[int, int]]:
    """Pontas 4, 8, 12 e 16 da mão direita, em pixels do recorte do painel.

    Args:
        registro: mão direita de um quadro (``pts`` no quadro inteiro).
        painel: retângulo do painel no quadro.

    Returns:
        ``ponto -> (x, y)`` no recorte do painel.
    """
    x0, y0, _, _ = painel
    pts = registro["pts"]
    return {
        ponto: (round(pts[ponto][0] - x0), round(pts[ponto][1] - y0))
        for ponto in CORES_PONTAS
    }


def desenhar_quadro_ataque(
    painel_bgr: np.ndarray,
    quadro: dict[str, Any],
    painel: tuple[int, int, int, int],
    escala: float,
) -> np.ndarray:
    """Recorte do painel de um quadro, com as pontas da mão direita desenhadas.

    Args:
        painel_bgr: recorte BGR do painel desse quadro.
        quadro: quadro de ``registrar_ataque`` (``delta``, ``direita``).
        painel: retângulo do painel no quadro inteiro.
        escala: fator de redução do recorte.

    Returns:
        Imagem BGR, com uma legenda no topo (``delta`` e se há mão direita).
    """
    img = painel_bgr.copy()
    direita = quadro["direita"]
    if direita is not None:
        for ponto, (x, y) in pontas_no_painel(direita, painel).items():
            cv2.circle(img, (x, y), 7, CORES_PONTAS[ponto], -1, cv2.LINE_AA)
            cv2.putText(
                img,
                str(ponto),
                (x + 8, y - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                CORES_PONTAS[ponto],
                2,
                cv2.LINE_AA,
            )
    legenda = f"d={quadro['delta']:+.2f}" + ("" if direita else " sem direita")
    cv2.rectangle(img, (0, 0), (img.shape[1], 30), (0, 0, 0), -1)
    cv2.putText(
        img, legenda, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
    )
    return cv2.resize(img, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)


def desenhar_folha(
    linhas: list[tuple[str, list[np.ndarray]]],
) -> np.ndarray:
    """Folha com um ataque por linha: os quadros do painel em sequência.

    Args:
        linhas: pares ``(rótulo, quadros)``. Os quadros de cada linha já têm o mesmo
            tamanho. O rótulo (cordas da tablatura) vai numa faixa acima da linha.

    Returns:
        Imagem BGR com todas as linhas empilhadas.
    """
    blocos = []
    for rotulo, quadros in linhas:
        faixa = np.full((26, sum(q.shape[1] for q in quadros), 3), 245, np.uint8)
        cv2.putText(faixa, rotulo, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        linha = np.hstack(quadros)
        blocos.extend([faixa, linha, np.full((8, linha.shape[1], 3), 255, np.uint8)])
    return np.vstack(blocos)


# ---------------------------------------------------------------------------------
# Etapas
# ---------------------------------------------------------------------------------


def _gravar(caminho: Path, dados: Any) -> None:
    """Grava um JSON em UTF-8, criando a pasta se faltar.

    Args:
        caminho: arquivo de destino.
        dados: objeto serializável em JSON.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def _quadro_do_delta(ataque: dict[str, Any], delta: float) -> dict[str, Any] | None:
    """Quadro de um ataque com um dado deslocamento, ou None se não existe.

    Args:
        ataque: ataque de ``registrar_ataque``.
        delta: deslocamento em segundos.

    Returns:
        O quadro, ou None.
    """
    for quadro in ataque["quadros"]:
        if abs(quadro["delta"] - delta) < 1e-9:
            return quadro
    return None


def deslocamentos_pontas(ataque: dict[str, Any]) -> dict[int, float | None]:
    """Deslocamento, em pixels do quadro, de cada ponta de -0,13 s a +0,07 s.

    Args:
        ataque: ataque de ``registrar_ataque``.

    Returns:
        ``ponto -> distância`` em pixels, ou None se a mão direita falta num dos dois
        quadros.
    """
    inicio = _quadro_do_delta(ataque, DELTA_DESL_INICIO)
    fim = _quadro_do_delta(ataque, DELTA_DESL_FIM)
    if (
        inicio is None
        or fim is None
        or inicio["direita"] is None
        or fim["direita"] is None
    ):
        return dict.fromkeys(CORES_PONTAS)
    saida: dict[int, float | None] = {}
    for ponto in CORES_PONTAS:
        a = np.array(inicio["direita"]["pts"][ponto], dtype=float)
        b = np.array(fim["direita"]["pts"][ponto], dtype=float)
        saida[ponto] = round(float(np.hypot(*(a - b))), 1)
    return saida


def resumo_deslocamentos(ataques: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Mediana e p90 do deslocamento de cada ponta, entre os ataques com mão.

    Args:
        ataques: ataques de ``registrar_ataque``.

    Returns:
        ``"ponto" -> {n, mediana, p90}`` (px); ``n`` é quantos ataques entraram.
    """
    resumo: dict[str, dict[str, Any]] = {}
    for ponto in CORES_PONTAS:
        valores = [
            d[ponto]
            for d in (deslocamentos_pontas(a) for a in ataques)
            if d[ponto] is not None
        ]
        if not valores:
            resumo[str(ponto)] = {"n": 0, "mediana": None, "p90": None}
            continue
        resumo[str(ponto)] = {
            "n": len(valores),
            "mediana": round(float(np.median(valores)), 1),
            "p90": round(float(np.percentile(valores, 90)), 1),
        }
    return resumo


def texto_deslocamentos(ataque: dict[str, Any]) -> str:
    """Texto curto do deslocamento das pontas 4, 8, 12 e 16 de um ataque.

    Args:
        ataque: ataque de ``registrar_ataque``.

    Returns:
        Ex.: ``desl px 4=3.1 8=- 12=5.0 16=2.2`` (``-`` quando falta a mão).
    """
    d = deslocamentos_pontas(ataque)
    partes = [f"{p}={'-' if v is None else f'{v:.1f}'}" for p, v in d.items()]
    return "desl px -0.13..+0.07: " + " ".join(partes)


def rotulo_ataque(ataque: dict[str, Any]) -> str:
    """Texto curto com o instante e as cordas da tablatura de um ataque.

    Args:
        ataque: ataque de ``registrar_ataque``.

    Returns:
        Ex.: ``t=462.83  tab corda/casa: 6/0 4/2``.
    """
    partes = [f"{c['corda']}/{c['casa']}" for c in ataque["cordas_tab"]]
    return f"t={ataque['t_ini']:.2f}  tab corda/casa: {' '.join(partes) or '-'}"


# ---------------------------------------------------------------------------------
# Refinamento das retas pela crista (fase B)
# ---------------------------------------------------------------------------------

#: Busca local de cada reta: deslocamento máximo, em px, e de ângulo, em graus.
REFINO_DY_PX = 12.0
REFINO_PASSO_DY_PX = 1.0
REFINO_DTHETA_GRAUS = 2.0
REFINO_PASSO_DTHETA_GRAUS = 0.25

#: Folga, em pixels, em volta da caixa da mão ao excluir a região da mão.
MARGEM_MASCARA_PX = 6

#: Fração dos pontos mais fortes (corda visível) usada no contraste de crista.
FRAC_PONTOS_CRISTA = 0.4
#: Pontos válidos mínimos ao longo da reta para medir a crista.
MIN_PONTOS_CRISTA = 12


def mascara_de_caixas(
    shape: tuple[int, int],
    caixas: list[tuple[float, float, float, float]],
    margem: int = MARGEM_MASCARA_PX,
) -> np.ndarray:
    """Máscara booleana, True onde há mão, com folga em volta de cada caixa.

    Args:
        shape: ``(altura, largura)`` do painel.
        caixas: caixas ``(x0, y0, x1, y1)`` em coordenadas do painel.
        margem: folga, em pixels, em cada lado.

    Returns:
        Máscara ``bool`` com a forma do painel.
    """
    h, w = shape
    mascara = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1 in caixas:
        cv2.rectangle(
            mascara,
            (int(x0) - margem, int(y0) - margem),
            (int(x1) + margem, int(y1) + margem),
            1,
            -1,
        )
    return mascara.astype(bool)


def _amostrar_linha(
    cinza: np.ndarray,
    mascara: np.ndarray,
    theta: float,
    y_centro: float,
    deslocamento: float,
    ts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Valores do painel numa linha paralela à corda, deslocada ``deslocamento`` px.

    Args:
        cinza: painel em tons de cinza (``float32``).
        mascara: região da mão (True = excluir).
        theta: direção da corda, em radianos.
        y_centro: altura da corda em ``x = largura/2``.
        deslocamento: distância perpendicular à corda, em pixels.
        ts: posições ao longo da corda, em pixels a partir do centro.

    Returns:
        ``(valores, valido)``: valor em cada ponto e se o ponto é utilizável (dentro
        do painel e fora da mão).
    """
    h, w = cinza.shape
    d = np.array([np.cos(theta), np.sin(theta)])
    n = np.array([-np.sin(theta), np.cos(theta)])
    p = np.array([w / 2.0, y_centro])[None, :] + ts[:, None] * d[None, :]
    p = p + deslocamento * n[None, :]
    x, y = p[:, 0], p[:, 1]
    valido = (x >= 4) & (x <= w - 5) & (y >= 4) & (y <= h - 5)
    xi = np.clip(np.round(x).astype(int), 0, w - 1)
    yi = np.clip(np.round(y).astype(int), 0, h - 1)
    valido &= ~mascara[yi, xi]
    valores = cv2.remap(
        cinza,
        x.astype(np.float32).reshape(1, -1),
        y.astype(np.float32).reshape(1, -1),
        cv2.INTER_LINEAR,
    ).ravel()
    return valores, valido


def cresta_da_reta(
    cinza: np.ndarray,
    mascara: np.ndarray,
    theta: float,
    y_centro: float,
    espacamento: float,
) -> float | None:
    """Contraste de crista de uma reta num quadro, nos trechos em que a corda aparece.

    Para cada ponto ao longo da reta: média de três linhas sobre a corda (``-1``, ``0`` e
    ``+1`` px) menos a média de três linhas a cada lado, a ±meio espaçamento. Pontos
    fora do painel ou dentro da mão não contam. O contraste da reta é a média dos
    ``FRAC_PONTOS_CRISTA`` pontos mais fortes, porque a corda só aparece em parte do
    painel.

    Args:
        cinza: painel em tons de cinza (``float32``).
        mascara: região da mão (True = excluir).
        theta: direção da corda, em radianos.
        y_centro: altura da corda em ``x = largura/2``.
        espacamento: distância entre cordas vizinhas, em pixels.

    Returns:
        Contraste (níveis de cinza), ou None se há menos de ``MIN_PONTOS_CRISTA`` pontos
        válidos.
    """
    w = cinza.shape[1]
    ts = np.linspace(-0.45 * w, 0.45 * w, 80)
    sobre, lados, ok = [], [], np.ones(len(ts), bool)
    for off in (-1.0, 0.0, 1.0):
        v, val = _amostrar_linha(cinza, mascara, theta, y_centro, off, ts)
        sobre.append(v)
        ok &= val
    meia = espacamento / 2.0
    for off in (-meia - 1, -meia, -meia + 1, meia - 1, meia, meia + 1):
        v, val = _amostrar_linha(cinza, mascara, theta, y_centro, off, ts)
        lados.append(v)
        ok &= val
    if ok.sum() < MIN_PONTOS_CRISTA:
        return None
    crista = np.mean(sobre, axis=0)[ok] - np.mean(lados, axis=0)[ok]
    n_topo = max(1, round(FRAC_PONTOS_CRISTA * crista.size))
    return float(np.sort(crista)[-n_topo:].mean())


def _crista_media(
    cinzas: list[np.ndarray],
    mascaras: list[np.ndarray],
    theta: float,
    y_centro: float,
    espacamento: float,
) -> float | None:
    """Média da crista de uma reta sobre os quadros em que ela é mensurável."""
    valores = [
        c
        for c in (
            cresta_da_reta(ci, mi, theta, y_centro, espacamento)
            for ci, mi in zip(cinzas, mascaras, strict=True)
        )
        if c is not None
    ]
    if not valores:
        return None
    return float(np.mean(valores))


def espacamento_das_cordas(cordas: list[dict[str, Any]]) -> float:
    """Distância mediana entre cordas vizinhas, em pixels do painel.

    Args:
        cordas: cordas com ``y_centro`` (painel).

    Returns:
        Mediana das diferenças entre alturas consecutivas.
    """
    ys = sorted(c["y_centro"] for c in cordas)
    return float(np.median(np.diff(ys)))


def refinar_reta(
    cinzas: list[np.ndarray],
    mascaras: list[np.ndarray],
    reta: dict[str, Any],
    espacamento: float,
) -> dict[str, Any]:
    """Busca local (deslocamento e ângulo) que maximiza a crista média de uma corda.

    Varre ``REFINO_DY_PX`` (altura) e ``REFINO_DTHETA_GRAUS`` (ângulo, que inclina as
    duas pontas em sentidos opostos) em passos fixos, em torno da reta inicial.

    Args:
        cinzas: painéis em tons de cinza, de vários quadros.
        mascaras: regiões da mão de cada quadro (True = excluir).
        reta: corda com ``theta`` e ``y_centro`` (painel).
        espacamento: distância entre cordas vizinhas, em pixels.

    Returns:
        A corda com ``theta`` e ``y_centro`` refinados, mais ``crista_antes``,
        ``crista_depois``, ``dy_px`` e ``dtheta_graus`` aplicados.
    """
    th0, y0 = reta["theta"], reta["y_centro"]
    antes = _crista_media(cinzas, mascaras, th0, y0, espacamento)
    melhor: tuple[float, float, float] | None = None
    for dt in np.arange(
        -REFINO_DTHETA_GRAUS,
        REFINO_DTHETA_GRAUS + 1e-9,
        REFINO_PASSO_DTHETA_GRAUS,
    ):
        for dy in np.arange(-REFINO_DY_PX, REFINO_DY_PX + 1e-9, REFINO_PASSO_DY_PX):
            th = th0 + np.deg2rad(dt)
            c = _crista_media(cinzas, mascaras, th, y0 + dy, espacamento)
            if c is not None and (melhor is None or c > melhor[0]):
                melhor = (c, float(dt), float(dy))
    if melhor is None:
        return {
            **reta,
            "crista_antes": antes,
            "crista_depois": antes,
            "dy_px": 0.0,
            "dtheta_graus": 0.0,
        }
    depois, dt, dy = melhor
    return {
        **reta,
        "theta": float(th0 + np.deg2rad(dt)),
        "y_centro": float(y0 + dy),
        "crista_antes": antes,
        "crista_depois": depois,
        "dy_px": dy,
        "dtheta_graus": dt,
    }


def refinar_cordas(
    cinzas: list[np.ndarray],
    mascaras: list[np.ndarray],
    cordas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Refina cada corda separadamente, com o espaçamento médio do conjunto.

    Args:
        cinzas: painéis em tons de cinza, de vários quadros.
        mascaras: regiões da mão de cada quadro.
        cordas: cordas numeradas (``corda``, ``theta``, ``y_centro``).

    Returns:
        Cordas refinadas, na mesma ordem.
    """
    espaco = espacamento_das_cordas(cordas)
    return [refinar_reta(cinzas, mascaras, c, espaco) for c in cordas]


# ---------------------------------------------------------------------------------
# Controles, sinal x ruído, preditor e base (fase B)
# ---------------------------------------------------------------------------------


def instantes_de_controle(
    instantes: list[float],
    t_min: float,
    t_max: float,
    n: int,
    semente: int,
    longe: float = 0.30,
) -> list[float]:
    """Instantes de controle: sorteados no vídeo, longe de qualquer ``t_ini``.

    Sorteia uniformemente em ``[t_min, t_max]`` com ``random.Random(semente)``, rejeitando
    instantes a menos de ``longe`` s de um ``t_ini`` do produto ou de outro controle.

    Args:
        instantes: ``t_ini`` distintos do produto.
        t_min: início da faixa de sorteio, em segundos.
        t_max: fim da faixa de sorteio, em segundos.
        n: quantos controles.
        semente: semente do sorteio.
        longe: distância mínima, em segundos.

    Returns:
        ``n`` instantes em ordem crescente.

    Raises:
        RuntimeError: se não achar ``n`` instantes em 100 mil tentativas.
    """
    rng = random.Random(semente)
    arr = np.array(instantes, dtype=float)
    escolhidos: list[float] = []
    for _ in range(100_000):
        if len(escolhidos) == n:
            break
        t = round(rng.uniform(t_min, t_max), 3)
        if arr.size and float(np.min(np.abs(arr - t))) < longe:
            continue
        if any(abs(t - e) < longe for e in escolhidos):
            continue
        escolhidos.append(t)
    if len(escolhidos) < n:
        raise RuntimeError(f"só {len(escolhidos)} de {n} controles achados")
    return sorted(escolhidos)


def auc(positivos: list[float], negativos: list[float]) -> float | None:
    """Área sob a curva ROC: chance de um positivo passar de um negativo.

    Empates contam meio.

    Args:
        positivos: valores dos casos (ataques).
        negativos: valores dos controles.

    Returns:
        Valor em ``[0, 1]``, ou None se alguma lista está vazia.
    """
    if not positivos or not negativos:
        return None
    p = np.asarray(positivos, dtype=float)[:, None]
    q = np.asarray(negativos, dtype=float)[None, :]
    return float(((p > q).sum() + 0.5 * (p == q).sum()) / (p.size * q.size))


def _estatisticas(valores: list[float]) -> dict[str, Any]:
    """Quantidade, mediana e p90 de uma lista de valores (None se vazia)."""
    if not valores:
        return {"n": 0, "mediana": None, "p90": None}
    return {
        "n": len(valores),
        "mediana": round(float(np.median(valores)), 1),
        "p90": round(float(np.percentile(valores, 90)), 1),
    }


def sinal_ruido(
    ataques: list[dict[str, Any]], controles: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compara os deslocamentos das pontas em ataques e em controles.

    Por dedo: mediana, p90 e AUC (ataque contra controle). Também a AUC do
    deslocamento máximo entre as quatro pontas.

    Args:
        ataques: ataques de ``registrar_ataque``.
        controles: controles de ``registrar_ataque`` (sem nota nos 0,30 s em volta).

    Returns:
        ``{por_dedo, maximo}`` com ``ataque``, ``controle`` e ``auc`` em cada um.
    """
    por_dedo: dict[str, Any] = {}
    for ponto in CORES_PONTAS:
        a = [
            d[ponto]
            for d in (deslocamentos_pontas(x) for x in ataques)
            if d[ponto] is not None
        ]
        c = [
            d[ponto]
            for d in (deslocamentos_pontas(x) for x in controles)
            if d[ponto] is not None
        ]
        por_dedo[str(ponto)] = {
            "ataque": _estatisticas(a),
            "controle": _estatisticas(c),
            "auc": auc(a, c),
        }
    maximos_a = _maximos_por_evento(ataques)
    maximos_c = _maximos_por_evento(controles)
    return {
        "por_dedo": por_dedo,
        "maximo": {
            "ataque": _estatisticas(maximos_a),
            "controle": _estatisticas(maximos_c),
            "auc": auc(maximos_a, maximos_c),
        },
    }


def _maximos_por_evento(eventos: list[dict[str, Any]]) -> list[float]:
    """Maior deslocamento entre as quatro pontas de cada evento (se houver)."""
    saida = []
    for ev in eventos:
        valores = [v for v in deslocamentos_pontas(ev).values() if v is not None]
        if valores:
            saida.append(max(valores))
    return saida


def dedo_que_mais_se_move(ataque: dict[str, Any]) -> int | None:
    """Ponta (4, 8, 12 ou 16) com o maior deslocamento entre -0,13 s e +0,07 s.

    Args:
        ataque: ataque de ``registrar_ataque``.

    Returns:
        O número da ponta, ou None se não há medida.
    """
    validos = {k: v for k, v in deslocamentos_pontas(ataque).items() if v is not None}
    if not validos:
        return None
    return max(validos, key=lambda k: validos[k])


def corda_mais_proxima(xy: tuple[float, float], cordas: list[dict[str, Any]]) -> int:
    """Número da corda cuja reta (``a*x + b*y = c``) está mais perto do ponto.

    Args:
        xy: ponto no quadro inteiro.
        cordas: cordas com ``a``, ``b``, ``c`` e ``corda``.

    Returns:
        O número da corda mais próxima.
    """
    x, y = xy
    distancias = [
        abs(c["a"] * x + c["b"] * y - c["c"]) / float(np.hypot(c["a"], c["b"]))
        for c in cordas
    ]
    return int(cordas[int(np.argmin(distancias))]["corda"])


def preditor_ataque(
    ataque: dict[str, Any], cordas: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Corda prevista por um ataque: a ponta que mais se move, em -0,07 s, na reta mais
    próxima.

    Args:
        ataque: ataque de ``registrar_ataque``.
        cordas: cordas numeradas, no quadro inteiro (``a``, ``b``, ``c``).

    Returns:
        ``{t_ini, dedo, corda_prevista, cordas_tab, acerto}``, ou None se falta a mão.
    """
    dedo = dedo_que_mais_se_move(ataque)
    quadro = _quadro_do_delta(ataque, -0.07)
    if dedo is None or quadro is None or quadro["direita"] is None:
        return None
    x, y = quadro["direita"]["pts"][dedo]
    prevista = corda_mais_proxima((x, y), cordas)
    tab = sorted({c["corda"] for c in ataque["cordas_tab"]})
    return {
        "t_ini": ataque["t_ini"],
        "dedo": dedo,
        "corda_prevista": prevista,
        "cordas_tab": tab,
        "acerto": prevista in tab,
    }


def corda_mais_frequente(
    notas: list[dict[str, Any]], excluir: list[float]
) -> int | None:
    """Corda mais frequente nas notas do produto, sem os instantes excluídos.

    Args:
        notas: notas do produto (``corda``, ``t_ini``).
        excluir: instantes (``t_ini``) dos ataques avaliados, a deixar de fora.

    Returns:
        O número da corda mais frequente, ou None se não sobra nota.
    """
    fora = {round(t, 3) for t in excluir}
    contagem: dict[int, int] = {}
    for n in notas:
        t = n.get("t_ini")
        if t is not None and round(float(t), 3) in fora:
            continue
        contagem[n["corda"]] = contagem.get(n["corda"], 0) + 1
    if not contagem:
        return None
    return max(contagem, key=lambda k: contagem[k])


def polegar_diagnostico(
    ataques: list[dict[str, Any]], cordas: list[dict[str, Any]]
) -> dict[str, int]:
    """Diagnóstico: a corda mais próxima do polegar (ponta 4) acerta nas cordas 4 a 6.

    Só entram os ataques cuja tablatura tem alguma nota nas cordas 4, 5 ou 6.

    Args:
        ataques: ataques de ``registrar_ataque``.
        cordas: cordas numeradas (``a``, ``b``, ``c``).

    Returns:
        ``{avaliados, acertos}``.
    """
    avaliados = acertos = 0
    for ataque in ataques:
        tab = {c["corda"] for c in ataque["cordas_tab"]}
        if not tab & {4, 5, 6}:
            continue
        quadro = _quadro_do_delta(ataque, -0.07)
        if quadro is None or quadro["direita"] is None:
            continue
        x, y = quadro["direita"]["pts"][4]
        avaliados += 1
        acertos += corda_mais_proxima((x, y), cordas) in tab
    return {"avaliados": avaliados, "acertos": acertos}
