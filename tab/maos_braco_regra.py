"""Regra das 12 notas para prever os trastes do braço a partir de poucos cliques.

Com a pestana (nut), as cordas 1 e 6 e 2 trastes clicados (as âncoras, por padrão o
5 e o 12), prevê os outros trastes. A posição do traste ``n`` é
``L * (1 - 2 ** (-n / 12))`` (``s_do_traste``), e a câmera distorce o braço ao longo
do eixo: o ajuste é projetivo, ``t = (a*s + b) / (c*s + 1)``, com 3 pontos (nut e as
duas âncoras), o que o fecha de forma exata.

Este módulo é independente da ferramenta e da geometria: só numpy e stdlib. A conta é
a mesma de ``tab.maos_braco_geometria`` (testada contra ela em
``tests/test_maos_braco_regra.py``). Não importa ``maos_braco_gabarito`` nem a
geometria, para não criar import circular.

Uso: ``prever_trastes(nut, corda1, corda6, ancoras, dimensoes)``, chamada pela ação
``prever_trastes`` da ferramenta do braço.
"""

from __future__ import annotations

import itertools

import numpy as np

#: Traste mais alto previsto (o violão clássico tem 19 trastes).
N_MAXIMO = 19

#: Âncoras: o maior número tem que ser pelo menos este (senão a curva fica curta).
MAIOR_ANCORA_MINIMA = 9

#: Âncoras: a diferença entre os números tem que ser pelo menos esta.
DIFERENCA_ANCORAS_MINIMA = 5


def s_do_traste(n: int) -> float:
    """Posição física do traste ``n``, como fração do comprimento da escala.

    Args:
        n: número do traste (0 é o nut).

    Returns:
        ``1 - 2 ** (-n / 12)``: 0 no nut e 0,5 no traste 12.
    """
    return 1.0 - 2.0 ** (-n / 12.0)


def _unitario(vetor: np.ndarray) -> np.ndarray:
    """Vetor unitário na mesma direção.

    Args:
        vetor: vetor 2D não nulo.

    Returns:
        ``vetor / |vetor|``.

    Raises:
        ValueError: se o vetor for nulo.
    """
    norma = float(np.linalg.norm(vetor))
    if norma == 0.0:
        raise ValueError("corda sem direção (dois pontos iguais)")
    return vetor / norma


def eixo_do_braco(corda1: list, corda6: list) -> tuple[np.ndarray, np.ndarray]:
    """Eixo do braço: a linha média entre as cordas 1 e 6.

    A direção é a bissetriz das duas cordas (cada uma com o sinal que a alinha à
    outra). A origem é o ponto médio dos pontos médios das duas cordas.

    Args:
        corda1: dois pontos ``[x, y]`` da corda 1.
        corda6: dois pontos ``[x, y]`` da corda 6.

    Returns:
        ``(origem, u)``: um ponto do eixo e o vetor unitário (sentido ainda não
        definido; ``prever_trastes`` o orienta para as âncoras).
    """
    c1 = np.asarray(corda1, dtype=float)
    c6 = np.asarray(corda6, dtype=float)
    d1 = _unitario(c1[1] - c1[0])
    d6 = _unitario(c6[1] - c6[0])
    if float(np.dot(d1, d6)) < 0.0:
        d6 = -d6
    u = _unitario(d1 + d6)
    origem = (c1.mean(axis=0) + c6.mean(axis=0)) / 2.0
    return origem, u


def _ajuste_projetivo(pontos: list[tuple[int, float]]) -> np.ndarray:
    """Ajuste exato do modelo projetivo por 3 pontos ``(número, t)``.

    Resolve ``a*s + b - c*s*t = t`` para os 3 pontos. O número 0 (nut) fixa ``b``.

    Args:
        pontos: três pares ``(número, t)``, com números distintos.

    Returns:
        ``[a, b, c]``.

    Raises:
        ValueError: se o sistema for singular (pontos alinhados demais).
    """
    s = np.array([s_do_traste(n) for n, _ in pontos], dtype=float)
    t = np.array([valor for _, valor in pontos], dtype=float)
    matriz = np.column_stack([s, np.ones_like(s), -t * s])
    try:
        return np.linalg.solve(matriz, t)
    except np.linalg.LinAlgError as erro:
        raise ValueError("âncoras não permitem ajustar a curva") from erro


def _posicoes_t(params: np.ndarray, n_max: int) -> list[float]:
    """Posição ao longo do eixo de cada traste de 0 (nut) a ``n_max``.

    Args:
        params: ``[a, b, c]`` do ajuste projetivo.
        n_max: último traste.

    Returns:
        ``t_0 .. t_n_max``, em px a partir da origem do eixo.
    """
    a, b, c = (float(v) for v in params)
    return [
        (a * s_do_traste(n) + b) / (c * s_do_traste(n) + 1.0) for n in range(n_max + 1)
    ]


def prever_trastes(
    nut: object,
    corda1: object,
    corda6: object,
    ancoras: dict[int, list[float]],
    dimensoes: tuple[int, int],
    n_max: int = N_MAXIMO,
) -> dict[int, list[float]]:
    """Prevê a posição dos trastes 1 a ``n_max`` a partir do nut e de 2 âncoras.

    O eixo é o de ``eixo_do_braco``, orientado do nut para as âncoras. Cada traste fica
    no eixo, na posição que o ajuste projetivo dá a ele, arredondada a 1 casa como os
    cliques. Nos números das âncoras devolve o ponto CLICADO, não o previsto. Trastes
    que saem do quadro ficam de fora (não há ponto para eles).

    Args:
        nut: ponto ``[x, y]`` da pestana (``"fora"`` ou ``None`` recusam).
        corda1: dois pontos ``[x, y]`` da corda 1.
        corda6: dois pontos ``[x, y]`` da corda 6.
        ancoras: ``{numero: [x, y]}`` com exatamente 2 trastes clicados.
        dimensoes: ``(largura, altura)`` do quadro original.
        n_max: último traste previsto (até 19 por padrão).

    Returns:
        ``{numero: [x, y]}`` para os trastes de 1 a ``n_max`` que caem no quadro.

    Raises:
        ValueError: com mensagem em português se a regra não se aplica: nut ausente,
            cordas incompletas, âncoras iguais, fora de 1..``n_max`` ou mal espalhadas,
            ou a curva prevista não cresce do nut para fora.
    """
    if not isinstance(nut, list) or len(nut) != 2:
        raise ValueError("a pestana (nut) precisa estar marcada")
    for nome, corda in (("corda 1", corda1), ("corda 6", corda6)):
        if not isinstance(corda, list) or len(corda) != 2:
            raise ValueError(f"a {nome} precisa ter 2 pontos")
    if len(ancoras) != 2:
        raise ValueError("a previsão precisa de exatamente 2 âncoras")
    na, nb = sorted(ancoras)
    if na == nb:
        raise ValueError("as duas âncoras têm o mesmo número")
    if na < 1 or nb > n_max:
        raise ValueError(f"números das âncoras fora de 1..{n_max}")
    if nb < MAIOR_ANCORA_MINIMA or nb - na < DIFERENCA_ANCORAS_MINIMA:
        raise ValueError(
            "âncoras mal espalhadas: use um traste a partir do 9 e outro a pelo "
            f"menos {DIFERENCA_ANCORAS_MINIMA} casas de distância"
        )
    origem, u = eixo_do_braco(corda1, corda6)
    ponto_nut = np.asarray(nut, dtype=float)
    media_ancoras = np.asarray(list(ancoras.values()), dtype=float).mean(axis=0)
    if float(np.dot(media_ancoras - ponto_nut, u)) < 0.0:
        u = -u
    t_nut = float(np.dot(ponto_nut - origem, u))
    t_a = float(np.dot(np.asarray(ancoras[na], dtype=float) - origem, u))
    t_b = float(np.dot(np.asarray(ancoras[nb], dtype=float) - origem, u))
    params = _ajuste_projetivo([(0, t_nut), (na, t_a), (nb, t_b)])
    # O denominador c*s+1 é linear em s e vale 1 no nut: basta conferir o último traste.
    if float(params[2]) * s_do_traste(n_max) + 1.0 <= 0.0:
        raise ValueError("a curva prevista tem um polo dentro dos trastes")
    t_valores = _posicoes_t(params, n_max)
    if any(x >= y for x, y in itertools.pairwise(t_valores)):
        raise ValueError("a curva prevista não cresce do nut para fora")
    largura, altura = dimensoes
    previstos: dict[int, list[float]] = {}
    for n in range(1, n_max + 1):
        if n in ancoras:
            previstos[n] = [float(v) for v in ancoras[n]]
            continue
        ponto = origem + u * t_valores[n]
        x, y = round(float(ponto[0]), 1), round(float(ponto[1]), 1)
        if 0 <= x < largura and 0 <= y < altura:
            previstos[n] = [x, y]
    return previstos


def prever_trastes_sem_nut(
    corda1: object,
    corda6: object,
    ancoras: dict[int, list[float]],
    dimensoes: tuple[int, int],
    n_max: int = N_MAXIMO,
) -> dict[int, list[float]]:
    """Prevê os trastes 1 a ``n_max`` sem o nut, com 3 âncoras e ajuste de a, b e c.

    Rodada 1028 (P1). Sem o nut, ``b`` não é fixado: o modelo ``t = (a s + b)/(c s + 1)``
    é ajustado nas 3 âncoras, que dão um sistema linear exato. O sentido do eixo é o
    que faz o traste de número maior ficar mais longe da origem que o de número menor.

    Args:
        corda1: dois pontos ``[x, y]`` da corda 1.
        corda6: dois pontos ``[x, y]`` da corda 6.
        ancoras: ``{numero: [x, y]}`` com exatamente 3 trastes clicados.
        dimensoes: ``(largura, altura)`` do quadro original.
        n_max: último traste previsto.

    Returns:
        ``{numero: [x, y]}`` para os trastes de 1 a ``n_max`` que caem no quadro; as
        âncoras voltam com o ponto clicado.

    Raises:
        ValueError: com mensagem em português se houver menos de 3 âncoras (sem o nut a
            curva com 2 âncoras não é determinada), se os números forem repetidos ou
            fora de 1..``n_max``, se as cordas forem inválidas, ou se a curva prevista
            não cresce ou tem polo dentro dos trastes.
    """
    if len(ancoras) < 3:
        raise ValueError(
            "sem a pestana (nut) são precisas 3 âncoras: com 2 a curva não fica "
            "determinada"
        )
    for nome, corda in (("corda 1", corda1), ("corda 6", corda6)):
        if not isinstance(corda, list) or len(corda) != 2:
            raise ValueError(f"a {nome} precisa ter 2 pontos")
    if any(n < 1 or n > n_max for n in ancoras):
        raise ValueError(f"números das âncoras fora de 1..{n_max}")
    origem, u = eixo_do_braco(corda1, corda6)
    numeros = sorted(ancoras)
    pontos = {n: np.asarray(ancoras[n], dtype=float) for n in numeros}
    t_ancoras = {n: float(np.dot(pontos[n] - origem, u)) for n in numeros}
    if t_ancoras[numeros[-1]] < t_ancoras[numeros[0]]:
        u = -u
        t_ancoras = {n: -t for n, t in t_ancoras.items()}
    s = np.array([s_do_traste(n) for n in numeros], dtype=float)
    t = np.array([t_ancoras[n] for n in numeros], dtype=float)
    matriz = np.column_stack([s, np.ones_like(s), -t * s])
    try:
        params = np.linalg.solve(matriz, t)
    except np.linalg.LinAlgError as erro:
        raise ValueError("âncoras não permitem ajustar a curva") from erro
    if float(params[2]) * s_do_traste(n_max) + 1.0 <= 0.0:
        raise ValueError("a curva prevista tem um polo dentro dos trastes")
    t_valores = _posicoes_t(params, n_max)
    if any(x >= y for x, y in itertools.pairwise(t_valores[1:])):
        raise ValueError("a curva prevista não cresce do nut para fora")
    largura, altura = dimensoes
    previstos: dict[int, list[float]] = {}
    for n in range(1, n_max + 1):
        if n in ancoras:
            previstos[n] = [float(v) for v in ancoras[n]]
            continue
        ponto = origem + u * t_valores[n]
        x, y = round(float(ponto[0]), 1), round(float(ponto[1]), 1)
        if 0 <= x < largura and 0 <= y < altura:
            previstos[n] = [x, y]
    return previstos
