"""Geometria da mão como âncora do braço (M3b, rodada 1006): funções puras.

A mão esquerda (Wholebody) está em cima das cordas. Daí: (1) a direção das cordas
sai da orientação dominante de bordas num disco em volta das pontas dos dedos; (2)
as cordas são as retas paralelas com maior energia ao longo dessa direção, perto
da mão; (3) os trastes são picos transversais entre as cordas de fora, e a numeração
sai do modelo projetivo das 12 notas (``tab.maos_braco_geometria``).

Tudo aqui é numpy puro (sem cv2, sem GPU) e tem teste em ``tests/test_maos_ancora.py``.
Coordenadas: imagem (x para a direita, y para baixo). ``u`` é a direção do braço
(``u_x > 0``) e ``n = (-u_y, u_x)`` aponta para baixo na imagem.
"""

from __future__ import annotations

import numpy as np

from .maos_braco import picos

#: Índices das pontas (MediaPipe / COCO-WholeBody): indicador, médio, anelar, mínimo.
DEDOS_PONTAS = (8, 12, 16, 20)

#: Raio do disco como fração do tamanho da mão (maior lado da caixa dos 21 pontos).
FRACAO_RAIO = 0.5

#: Passo de amostragem ao longo do braço e transversal, em px.
PASSO = 1.0

#: Número de casas de referência (a lei das 12 notas vale até aqui).
N_TRASTES = 20


def tamanho_da_mao(pts: np.ndarray) -> float:
    """Tamanho da mão: o maior lado da caixa dos seus pontos.

    Args:
        pts: pontos ``(21, 2)`` (ou ``(21, 3)``; só x e y contam).

    Returns:
        Maior lado da caixa, em px.
    """
    xy = np.asarray(pts, dtype=float)[:, :2]
    return float(max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1])))


def raio_do_disco(pts: np.ndarray, fracao: float = FRACAO_RAIO) -> float:
    """Raio do disco em volta de uma ponta, proporcional ao tamanho da mão.

    Args:
        pts: pontos da mão ``(21, 2)``.
        fracao: fração do tamanho da mão.

    Returns:
        Raio em px.
    """
    return fracao * tamanho_da_mao(pts)


def pontas(pts: np.ndarray) -> np.ndarray:
    """Pontas dos dedos (indicador, médio, anelar, mínimo) em ``(4, 2)``.

    Args:
        pts: pontos da mão ``(21, 2)`` ou ``(21, 3)``.

    Returns:
        Coordenadas ``[x, y]`` das quatro pontas.
    """
    return np.asarray(pts, dtype=float)[list(DEDOS_PONTAS), :2]


def tensor_da_orientacao(
    gx: np.ndarray, gy: np.ndarray, centro: np.ndarray, raio: float
) -> tuple[float, float]:
    """Direção dominante das retas num disco, pelo tensor de estrutura.

    A orientação do gradiente dominante é ``0.5 * atan2(2 Jxy, Jxx - Jyy)``; a da
    reta é ela mais 90 graus. A coerência (0 a 1) diz quão dominante ela é.

    Args:
        gx: gradiente horizontal, ``(altura, largura)``.
        gy: gradiente vertical, mesma forma.
        centro: centro do disco ``[x, y]``.
        raio: raio do disco, em px.

    Returns:
        ``(theta, coerencia)``: direção da reta em graus, em ``[0, 180)``, e a
        coerência. ``(0, 0)`` se o disco cai fora da imagem.
    """
    altura, largura = gx.shape
    cx, cy = float(centro[0]), float(centro[1])
    x0 = max(int(np.floor(cx - raio)), 0)
    x1 = min(int(np.ceil(cx + raio)) + 1, largura)
    y0 = max(int(np.floor(cy - raio)), 0)
    y1 = min(int(np.ceil(cy + raio)) + 1, altura)
    if x1 <= x0 or y1 <= y0:
        return 0.0, 0.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    mascara = (xx - cx) ** 2 + (yy - cy) ** 2 <= raio**2
    ex = gx[y0:y1, x0:x1][mascara]
    ey = gy[y0:y1, x0:x1][mascara]
    jxx = float(np.sum(ex * ex))
    jyy = float(np.sum(ey * ey))
    jxy = float(np.sum(ex * ey))
    energia = jxx + jyy
    if energia <= 0.0:
        return 0.0, 0.0
    grad = 0.5 * np.degrees(np.arctan2(2.0 * jxy, jxx - jyy))
    theta = (grad + 90.0) % 180.0
    coerencia = float(np.hypot(jxx - jyy, 2.0 * jxy) / energia)
    return float(theta), coerencia


def media_de_orientacoes(
    orientacoes: list[tuple[float, float]],
) -> tuple[float, float]:
    """Média das direções (de linha) ponderada pela coerência, com 2*theta.

    Direções de linha têm período de 180 graus, então a média é feita no dobro do
    ângulo. Entradas com coerência zero não pesam.

    Args:
        orientacoes: pares ``(theta_graus, coerencia)``.

    Returns:
        ``(theta_medio, coerencia_media)``; ``(0, 0)`` sem entradas úteis.
    """
    sx = sy = peso = 0.0
    for theta, coer in orientacoes:
        r = np.radians(2.0 * theta)
        sx += coer * np.cos(r)
        sy += coer * np.sin(r)
        peso += coer
    if peso <= 0.0:
        return 0.0, 0.0
    theta = float(np.degrees(np.arctan2(sy, sx)) / 2.0) % 180.0
    coerencia = float(np.hypot(sx, sy) / peso)
    return theta, coerencia


def base_do_braco(theta_graus: float) -> tuple[np.ndarray, np.ndarray]:
    """Vetores ``u`` (braço) e ``n`` (transversal) para uma direção de linha.

    Args:
        theta_graus: direção da reta em graus.

    Returns:
        ``(u, n)`` unitários, com ``u_x > 0`` (ou ``u_x == 0`` e ``u_y > 0``) e
        ``n = (-u_y, u_x)``, que aponta para baixo na imagem.
    """
    r = np.radians(theta_graus)
    u = np.array([np.cos(r), np.sin(r)])
    if u[0] < 0.0 or (abs(u[0]) < 1e-12 and u[1] < 0.0):
        u = -u
    n = np.array([-u[1], u[0]])
    return u, n


def amostrar(imagem: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Valores da imagem em pontos não inteiros, por interpolação bilinear.

    Pontos fora da imagem valem 0.

    Args:
        imagem: matriz ``(altura, largura)``.
        xs: coordenadas x dos pontos.
        ys: coordenadas y dos pontos (mesma forma de ``xs``).

    Returns:
        Valores na forma de ``xs``.
    """
    altura, largura = imagem.shape
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    dentro = (xs >= 0) & (xs <= largura - 1) & (ys >= 0) & (ys <= altura - 1)
    x = np.clip(xs, 0, largura - 1.000001)
    y = np.clip(ys, 0, altura - 1.000001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = x - x0
    fy = y - y0
    v = (
        imagem[y0, x0] * (1 - fx) * (1 - fy)
        + imagem[y0, x0 + 1] * fx * (1 - fy)
        + imagem[y0 + 1, x0] * (1 - fx) * fy
        + imagem[y0 + 1, x0 + 1] * fx * fy
    )
    return np.where(dentro, v, 0.0)


def _grade_s(alcance: float) -> np.ndarray:
    """Grade ao longo do braço, simétrica em torno de 0.

    Args:
        alcance: meia-largura da grade, em px.

    Returns:
        Valores de ``-alcance`` a ``alcance`` com passo ``PASSO``.
    """
    return np.arange(-alcance, alcance + PASSO / 2, PASSO)


def perfil_longitudinal(
    resposta: np.ndarray,
    centro: np.ndarray,
    u: np.ndarray,
    n: np.ndarray,
    alcance_s: float,
    alcance_t: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Energia de bordas ao longo de cada reta paralela a ``u``.

    Para cada deslocamento transversal ``t`` (linhas paralelas ao braço), a média
    da resposta sobre ``s`` em ``[-alcance_s, alcance_s]``. Cordas são retas longas,
    então aparecem como picos aqui; figuras curtas (dedos, letras) não.

    Args:
        resposta: mapa de bordas ``(altura, largura)``, não negativo.
        centro: ponto de referência ``[x, y]`` (em s = 0, t = 0).
        u: direção do braço (unitária).
        n: direção transversal (unitária).
        alcance_s: meia-largura ao longo do braço.
        alcance_t: meia-largura transversal.

    Returns:
        ``(t_valores, perfil)``: o eixo transversal e a média por ``t``.
    """
    s = _grade_s(alcance_s)
    t = _grade_s(alcance_t)
    ss, tt = np.meshgrid(s, t, indexing="xy")
    xs = centro[0] + ss * u[0] + tt * n[0]
    ys = centro[1] + ss * u[1] + tt * n[1]
    valores = amostrar(resposta, xs, ys)
    return t, valores.mean(axis=1)


def melhor_angulo(
    resposta: np.ndarray,
    centro: np.ndarray,
    theta0: float,
    alcance_s: float,
    alcance_t: float,
    varredura_graus: float = 10.0,
    passo_graus: float = 0.5,
) -> float:
    """Ângulo que concentra mais energia de reta, perto de ``theta0``.

    Critério: a soma dos quadrados do perfil longitudinal, sem a mediana (uma reta
    nítida e paralela ao braço concentra energia; uma reta inclinada se espalha).

    Args:
        resposta: mapa de bordas.
        centro: ponto de referência ``[x, y]``.
        theta0: direção inicial, em graus.
        alcance_s: meia-largura ao longo do braço.
        alcance_t: meia-largura transversal.
        varredura_graus: quanto girar para cada lado de ``theta0``.
        passo_graus: passo da varredura.

    Returns:
        Direção da reta, em graus, em ``[0, 180)``.
    """
    melhor, melhor_e = theta0, -1.0
    for delta in np.arange(-varredura_graus, varredura_graus + 1e-9, passo_graus):
        theta = theta0 + float(delta)
        u, n = base_do_braco(theta)
        _, perfil = perfil_longitudinal(resposta, centro, u, n, alcance_s, alcance_t)
        energia = float(np.sum((perfil - np.median(perfil)) ** 2))
        if energia > melhor_e:
            melhor, melhor_e = theta, energia
    return float(melhor % 180.0)


def achar_cordas(
    t_valores: np.ndarray,
    perfil: np.ndarray,
    minimo_frac: float = 0.35,
    distancia: int = 6,
    min_cordas: int = 4,
) -> list[float]:
    """Cordas: o grupo de picos transversais com espaçamento parecido.

    Pega os picos do perfil; separa em sequências onde os intervalos entre picos
    vizinhos ficam entre 0,6 e 1,6 vez a mediana; escolhe a sequência mais longa
    (desempate pela soma das alturas).

    Args:
        t_valores: eixo transversal.
        perfil: média longitudinal por ``t``.
        minimo_frac: altura mínima de pico, como fração do máximo acima da mediana.
        distancia: distância mínima entre picos, em px.
        min_cordas: número mínimo de cordas no grupo.

    Returns:
        Posições ``t`` das cordas do grupo escolhido, em ordem crescente; lista
        vazia se nenhum grupo tem ``min_cordas``.
    """
    base = perfil - np.median(perfil)
    if base.max() <= 0.0:
        return []
    idx = picos(base, minimo_frac * base.max(), distancia)
    if len(idx) < min_cordas:
        return []
    ts = t_valores[idx]
    alt = base[idx]
    mediana = float(np.median(np.diff(ts)))
    if mediana <= 0.0:
        return []
    melhor: tuple[int, float, int, int] = (0, 0.0, 0, 0)
    inicio = 0
    for fim in range(1, len(ts) + 1):
        quebra = fim == len(ts)
        if not quebra:
            gap = ts[fim] - ts[fim - 1]
            quebra = not (0.6 * mediana <= gap <= 1.6 * mediana)
        if quebra:
            tamanho = fim - inicio
            soma = float(alt[inicio:fim].sum())
            if (tamanho, soma) > (melhor[0], melhor[1]):
                melhor = (tamanho, soma, inicio, fim)
            inicio = fim
    tamanho, _soma, inicio, fim = melhor
    if tamanho < min_cordas:
        return []
    return [float(v) for v in ts[inicio:fim]]


def rastrear_linha(
    resposta: np.ndarray,
    centro: np.ndarray,
    u: np.ndarray,
    n: np.ndarray,
    t0: float,
    limiar: float,
    alcance_s: float,
    tolerancia: float = 2.0,
    lacuna_max: float = 25.0,
) -> tuple[float, float, float, float, int]:
    """Segue uma reta paralela ao braço a partir de ``s = 0`` para os dois lados.

    Em cada ``s`` procura o máximo da resposta a até ``tolerancia`` px do ponto
    previsto. Para ao passar ``lacuna_max`` px sem achado (mão e trastes quebram a
    reta). No fim, ajusta ``t = a + b * s`` pelos pontos aceitos.

    Args:
        resposta: mapa de bordas.
        centro: ponto de referência ``[x, y]``.
        u: direção do braço.
        n: direção transversal.
        t0: posição transversal da reta em ``s = 0``.
        limiar: resposta mínima para aceitar um ponto.
        alcance_s: até quanto andar para cada lado.
        tolerancia: busca transversal por passo, em px.
        lacuna_max: lacuna máxima sem achado, em px.

    Returns:
        ``(a, b, s_min, s_max, n_pontos)``; ``n_pontos`` zero se a reta some logo.
    """
    aceitos: list[tuple[float, float]] = [(0.0, t0)]
    deltas = np.arange(-tolerancia, tolerancia + 1e-9, 0.5)
    for sentido in (1.0, -1.0):
        t_prev = t0
        falta = 0.0
        s = PASSO
        while s <= alcance_s:
            xs = centro[0] + sentido * s * u[0] + (t_prev + deltas) * n[0]
            ys = centro[1] + sentido * s * u[1] + (t_prev + deltas) * n[1]
            vals = amostrar(resposta, xs, ys)
            k = int(np.argmax(vals))
            if vals[k] >= limiar:
                t_prev = float(t_prev + deltas[k])
                aceitos.append((sentido * s, t_prev))
                falta = 0.0
            else:
                falta += PASSO
                if falta > lacuna_max:
                    break
            s += PASSO
    if len(aceitos) < 3:
        return 0.0, t0, 0.0, 0.0, len(aceitos)
    arr = np.asarray(aceitos)
    b, a = np.polyfit(arr[:, 0], arr[:, 1], 1)
    return float(a), float(b), float(arr[:, 0].min()), float(arr[:, 0].max()), len(arr)


def reta_em(a: float, b: float, s: np.ndarray | float) -> np.ndarray | float:
    """Valor de ``t`` da reta ``t = a + b * s``.

    Args:
        a: intercepto.
        b: inclinação.
        s: posição ao longo do braço.

    Returns:
        ``t`` na forma de ``s``.
    """
    return a + b * s


def perfil_trastes(
    resposta: np.ndarray,
    centro: np.ndarray,
    u: np.ndarray,
    n: np.ndarray,
    reta_lo: tuple[float, float],
    reta_hi: tuple[float, float],
    s_ini: float,
    s_fim: float,
    janela: float = 41.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Perfil transversal do braço: picos de trasto ao longo de ``s``.

    A média da resposta na faixa entre as duas cordas de fora (frações 0,15 a 0,85
    da largura, para não pegar as cordas), menos a mediana corrente. Trastes são
    retas transversais, então aparecem como picos; as cordas, constantes, somem.

    Args:
        resposta: mapa de bordas.
        centro: ponto de referência ``[x, y]``.
        u: direção do braço.
        n: direção transversal.
        reta_lo: ``(a, b)`` da corda de fora de ``t`` menor.
        reta_hi: ``(a, b)`` da corda de fora de ``t`` maior.
        s_ini: início do trecho, em ``s``.
        s_fim: fim do trecho, em ``s``.
        janela: janela da mediana corrente, em px.

    Returns:
        ``(s_valores, sinal)``: ``sinal`` é o perfil menos a mediana corrente.
    """
    s = np.arange(s_ini, s_fim + PASSO / 2, PASSO)
    lo = reta_em(reta_lo[0], reta_lo[1], s)
    hi = reta_em(reta_hi[0], reta_hi[1], s)
    fracoes = np.linspace(0.15, 0.85, 9)
    tt = lo[None, :] + (hi - lo)[None, :] * fracoes[:, None]
    xs = centro[0] + s[None, :] * u[0] + tt * n[0]
    ys = centro[1] + s[None, :] * u[1] + tt * n[1]
    perfil = amostrar(resposta, xs, ys).mean(axis=0)
    meia = int(janela // 2)
    pad = np.pad(perfil, meia, mode="edge")
    mediana = np.array(
        [np.median(pad[i : i + 2 * meia + 1]) for i in range(len(perfil))]
    )
    return s, perfil - mediana


def achar_trastes(
    s_valores: np.ndarray,
    sinal: np.ndarray,
    fracao_minima: float = 0.25,
    distancia: int = 10,
) -> list[float]:
    """Posições ``s`` dos trastes: picos do perfil transversal.

    Args:
        s_valores: eixo ao longo do braço.
        sinal: perfil de ``perfil_trastes``.
        fracao_minima: altura mínima como fração do máximo.
        distancia: distância mínima entre picos, em px.

    Returns:
        Posições ``s`` dos trastes, em ordem crescente.
    """
    if sinal.max() <= 0.0:
        return []
    idx = picos(sinal, fracao_minima * sinal.max(), distancia)
    return [float(s_valores[i]) for i in idx]


def x_da_casa(numero: np.ndarray | int) -> np.ndarray:
    """Coordenada ideal da casa ``n`` pela lei das 12 notas: ``1 - 2^(-n/12)``.

    Args:
        numero: número da casa (0 é o nut).

    Returns:
        Posição normalizada, em ``[0, 1)`` para ``n >= 0``.
    """
    return 1.0 - 2.0 ** (-np.asarray(numero, dtype=float) / 12.0)


def ajustar_projetivo(
    x: np.ndarray, s: np.ndarray
) -> tuple[float, float, float, float]:
    """Ajusta ``s = (a x + b) / (c x + 1)`` por mínimos quadrados lineares.

    Args:
        x: coordenadas ideais (``x_da_casa``).
        s: posições medidas no braço.

    Returns:
        ``(a, b, c, residuo)``: o residuo é a raiz do erro quadrático médio, em px.
    """
    m = np.column_stack([x, np.ones_like(x), -x * s])
    (a, b, c), *_ = np.linalg.lstsq(m, s, rcond=None)
    previsto = (a * x + b) / (c * x + 1.0)
    residuo = float(np.sqrt(np.mean((previsto - s) ** 2)))
    return float(a), float(b), float(c), residuo


def numerar_trastes(s_trastes: list[float], max_inicio: int = 12) -> dict | None:
    """Numera os trastes achados pelo modelo projetivo das 12 notas.

    Duas hipóteses de sentido (o nut está no lado de ``s`` menor ou maior) e um
    deslocamento ``m0`` (número do primeiro traste visível menos 1). Para cada uma,
    ajusta o modelo e fica com o menor resíduo. O sentido sai sozinho: o espaçamento
    das casas diminui do nut para o corpo, então só uma das hipóteses é coerente.

    Args:
        s_trastes: posições ``s`` dos trastes, em ordem crescente. Precisa de 4.
        max_inicio: maior ``m0`` testado.

    Returns:
        ``{"sentido", "m0", "a", "b", "c", "residuo", "s_nut", "numeros"}`` com
        ``numeros`` na mesma ordem de ``s_trastes``; ``None`` se faltam trastes.
        ``sentido`` é ``"crescente"`` (nut em ``s`` pequeno) ou ``"decrescente"``.
    """
    k = len(s_trastes)
    if k < 4:
        return None
    s = np.asarray(sorted(s_trastes), dtype=float)
    melhor: dict | None = None
    for sentido in ("crescente", "decrescente"):
        for m0 in range(max_inicio + 1):
            ordem = np.arange(1, k + 1)
            if sentido == "decrescente":
                ordem = k + 1 - ordem
            numeros = ordem + m0
            if numeros.max() > N_TRASTES + max_inicio:
                continue
            a, b, c, res = ajustar_projetivo(x_da_casa(numeros), s)
            if melhor is None or res < melhor["residuo"]:
                melhor = {
                    "sentido": sentido,
                    "m0": m0,
                    "a": a,
                    "b": b,
                    "c": c,
                    "residuo": res,
                    "s_nut": b,
                    "numeros": [int(v) for v in numeros],
                }
    if melhor is not None:
        melhor["numeros"] = [int(v) for v in melhor["numeros"]]
    return melhor


def projetar_em_s(
    ponto: np.ndarray, centro: np.ndarray, u: np.ndarray, n: np.ndarray
) -> tuple[float, float]:
    """Coordenadas ``(s, t)`` de um ponto da imagem no referencial do braço.

    Args:
        ponto: ponto ``[x, y]``.
        centro: origem ``[x, y]``.
        u: direção do braço.
        n: direção transversal.

    Returns:
        ``(s, t)``.
    """
    d = np.asarray(ponto, dtype=float) - np.asarray(centro, dtype=float)
    return float(d @ u), float(d @ n)


def de_s_t(
    s: float, t: float, centro: np.ndarray, u: np.ndarray, n: np.ndarray
) -> np.ndarray:
    """Ponto da imagem de coordenadas ``(s, t)`` no referencial do braço.

    Args:
        s: posição ao longo do braço.
        t: posição transversal.
        centro: origem ``[x, y]``.
        u: direção do braço.
        n: direção transversal.

    Returns:
        Ponto ``[x, y]``.
    """
    return np.asarray(centro, dtype=float) + s * u + t * n
