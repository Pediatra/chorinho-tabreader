"""Cordas e trastes na imagem retificada pela homografia (M3c, rodada 1007).

Com a H da música, a região e a orientação do braço são conhecidas. O braço é
retificado para o retângulo ``(u, v)``: cordas viram linhas quase horizontais e
trastes, quase verticais. Cada linha é procurada só numa janela em volta da posição
prevista, nunca no quadro inteiro (a tablatura tem as mesmas retas).

Funções puras (numpy e o realce de :mod:`tab.maos_braco`): a matriz de retificação,
o perfil de linhas, o pico dentro de uma janela e a leitura de uma lista de posições.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .maos_braco import realcar

#: Distância, em pixels, abaixo da qual um pico é descartado como ruído.
FATOR_RUIDO = 2.5


def mapa_retificacao(
    H: np.ndarray, ku: float, kv: float, u0: float, v0: float
) -> np.ndarray:
    """Matriz para ``cv2.warpPerspective`` que retifica o braço.

    A imagem retificada tem o pixel ``(x, y)`` no ponto ``(u, v) = (u0 + x / ku,
    v0 + y / kv)``. ``warpPerspective`` precisa do mapa da origem (a imagem) para o
    destino (a retificada): é a inversa de ``H . T``, com ``T`` a escala e a origem.

    Args:
        H: homografia que leva ``(u, v)`` para pixels da imagem.
        ku: pixels por unidade de ``u``.
        kv: pixels por unidade de ``v``.
        u0: valor de ``u`` no canto superior esquerdo da retificada.
        v0: valor de ``v`` no canto superior esquerdo da retificada.

    Returns:
        Matriz 3 x 3 para ``cv2.warpPerspective``.
    """
    T = np.array([[1.0 / ku, 0.0, u0], [0.0, 1.0 / kv, v0], [0.0, 0.0, 1.0]])
    return np.linalg.inv(H @ T)


def perfil_linhas(
    cinza: np.ndarray, orientacao: str, faixa: tuple[int, int], janela: int
) -> np.ndarray:
    """Perfil 1D de linhas: realce do fundo e média ao longo da linha.

    Args:
        cinza: imagem em tons de cinza ``(altura, largura)``.
        orientacao: ``"horizontal"`` (linhas horizontais, como as cordas: perfil em
            ``y``, média em ``x`` sobre ``faixa``) ou ``"vertical"`` (como os trastes:
            perfil em ``x``, média em ``y`` sobre ``faixa``).
        faixa: ``(inicio, fim)`` em pixels, no eixo ao longo da linha. ``fim`` exclusivo.
        janela: tamanho, em pixels, do fundo removido (média móvel).

    Returns:
        Perfil 1D, ``float``.

    Raises:
        ValueError: se a orientação não é ``"horizontal"`` nem ``"vertical"``.
    """
    if orientacao == "horizontal":
        realce = realcar(cinza, eixo=0, janela=janela)
        return realce[:, faixa[0] : faixa[1]].mean(axis=1)
    if orientacao == "vertical":
        realce = realcar(cinza, eixo=1, janela=janela)
        return realce[faixa[0] : faixa[1], :].mean(axis=0)
    raise ValueError(f"orientação desconhecida: {orientacao!r}")


def ruido_do_perfil(perfil: np.ndarray) -> float:
    """Ruído típico do perfil: desvio absoluto mediano vezes 1,4826.

    Args:
        perfil: perfil 1D.

    Returns:
        Desvio-padrão robusto, ``float``.
    """
    mediana = float(np.median(perfil))
    return 1.4826 * float(np.median(np.abs(perfil - mediana)))


def pico_na_janela(
    perfil: np.ndarray,
    centro: float,
    meia: float,
    sinal: str = "claro",
    minimo: float = 0.0,
) -> dict[str, Any] | None:
    """Pico do perfil dentro de ``centro +/- meia``, com refino parabólico.

    Args:
        perfil: perfil 1D.
        centro: posição prevista, em índices (fracionários).
        meia: meia largura da janela, em índices.
        sinal: ``"claro"`` procura o maior valor; ``"qualquer"`` o maior valor absoluto
            (serve a linha escura, como o nut).
        minimo: contraste mínimo, em unidades do perfil, para o pico contar.

    Returns:
        ``posicao`` (índice fracionário), ``contraste`` (valor absoluto do pico) e
        ``sinal_pico`` (``+1`` ou ``-1``); ``None`` se a janela cai fora do perfil ou o
        contraste não passa de ``minimo``.

    Raises:
        ValueError: se ``sinal`` não é ``"claro"`` nem ``"qualquer"``.
    """
    if sinal not in ("claro", "qualquer"):
        raise ValueError(f"sinal desconhecido: {sinal!r}")
    ini = max(int(np.ceil(centro - meia)), 1)
    fim = min(int(np.floor(centro + meia)), len(perfil) - 2)
    if ini > fim:
        return None
    v = perfil if sinal == "claro" else np.abs(perfil)
    i = ini + int(np.argmax(v[ini : fim + 1]))
    y0, y1, y2 = float(v[i - 1]), float(v[i]), float(v[i + 1])
    den = y0 - 2.0 * y1 + y2
    delta = 0.5 * (y0 - y2) / den if den < 0 else 0.0
    delta = float(np.clip(delta, -0.5, 0.5))
    contraste = float(v[i])
    if contraste <= minimo:
        return None
    return {
        "posicao": i + delta,
        "contraste": contraste,
        "sinal_pico": 1 if perfil[i] >= 0 else -1,
    }


def achar_linhas(
    perfil: np.ndarray,
    previstos: list[float],
    meias: list[float],
    sinal: str,
    minimo: float,
) -> list[dict[str, Any]]:
    """Procura uma linha em cada posição prevista, cada uma na sua janela.

    Args:
        perfil: perfil 1D de :func:`perfil_linhas`.
        previstos: posição prevista de cada linha, em índices.
        meias: meia largura da janela de cada linha, em índices.
        sinal: ``"claro"`` ou ``"qualquer"`` (ver :func:`pico_na_janela`).
        minimo: contraste mínimo para a linha contar.

    Returns:
        Uma entrada por posição, com ``previsto``, ``achado`` (``bool``), ``posicao``
        (``None`` se não achou), ``contraste`` e ``sinal_pico``.

    Raises:
        ValueError: se ``previstos`` e ``meias`` têm tamanhos diferentes.
    """
    if len(previstos) != len(meias):
        raise ValueError("previstos e meias têm tamanhos diferentes")
    saida = []
    for previsto, meia in zip(previstos, meias, strict=True):
        pico = pico_na_janela(perfil, previsto, meia, sinal=sinal, minimo=minimo)
        saida.append(
            {
                "previsto": float(previsto),
                "achado": pico is not None,
                "posicao": None if pico is None else pico["posicao"],
                "contraste": None if pico is None else pico["contraste"],
                "sinal_pico": None if pico is None else pico["sinal_pico"],
            }
        )
    return saida
