"""Rodada 1031, método V: numeração com o nut fora pelos quadros vizinhos que mostram o nut."""

import itertools

import numpy as np

#: Fração do menor lado da imagem que o nut e as cordas mantêm da borda.
FRACAO_BORDA_NUT = 0.05
#: Janela, em segundos, para procurar um quadro de referência com nut visível.
JANELA_S = 30.0
#: Tolerância do casamento, em fração do espaçamento local dos trastes.
TOLERANCIA_CASA = 0.25
#: Número mínimo de trastes casados para aceitar um casamento entre quadros.
MIN_CASADOS = 3


def _distancia_borda(ponto: np.ndarray, largura: float, altura: float) -> float:
    """Calcula a distância de um ponto à borda mais próxima da imagem.

    Args:
        ponto: Coordenadas [x, y] do ponto, em pixels.
        largura: Largura da imagem, em pixels.
        altura: Altura da imagem, em pixels.

    Returns:
        Menor distância, em pixels, entre o ponto e as quatro bordas.
    """
    x, y = float(ponto[0]), float(ponto[1])
    return min(x, y, largura - x, altura - y)


def _extremo_mais_perto(corda: list, nut: list) -> np.ndarray:
    """Escolhe a ponta de uma corda mais próxima do nut.

    Args:
        corda: Lista com as duas pontas [[x, y], [x, y]] da corda.
        nut: Ponto [x, y] do nut.

    Returns:
        A ponta da corda com menor distância euclidiana até o nut.
    """
    ponto_nut = np.asarray(nut, dtype=float)
    pontas = [np.asarray(p, dtype=float) for p in corda]
    return min(pontas, key=lambda p: float(np.linalg.norm(p - ponto_nut)))


def nut_confiante(registro: dict) -> bool:
    """Diz se o nut do quadro é confiável para ancorar a numeração.

    O quadro precisa ter o braço achado, sem sinalização, com nut e as duas
    cordas (1 e 6) detectados. A ponta de cada corda mais próxima do nut
    deve ficar longe da borda da imagem, para que o nut não esteja cortado.

    Args:
        registro: Quadro com as chaves "dimensoes" e "previsto".

    Returns:
        True se o nut é confiável; False caso contrário.
    """
    previsto = registro["previsto"]
    if not previsto.get("achou") or previsto.get("sinalizado"):
        return False
    nut = previsto.get("nut")
    corda1 = previsto.get("corda1")
    corda6 = previsto.get("corda6")
    if nut is None or corda1 is None or corda6 is None:
        return False
    dimensoes = registro.get("dimensoes")
    if dimensoes is None:
        return False
    largura, altura = dimensoes
    margem = FRACAO_BORDA_NUT * min(largura, altura)
    for corda in (corda1, corda6):
        ponta = _extremo_mais_perto(corda, nut)
        if _distancia_borda(ponta, largura, altura) <= margem:
            return False
    return True


def eixo(registro: dict) -> tuple[np.ndarray, np.ndarray]:
    """Calcula o eixo do braço, com origem no nut e direção das cordas.

    Args:
        registro: Quadro com "previsto" contendo "corda1" e "corda6".

    Returns:
        Tupla (origem, u): origem é o ponto médio das pontas iniciais das
        cordas 1 e 6; u é o vetor unitário do início ao fim do braço.
    """
    previsto = registro["previsto"]
    corda1 = np.asarray(previsto["corda1"], dtype=float)
    corda6 = np.asarray(previsto["corda6"], dtype=float)
    origem = (corda1[0] + corda6[0]) / 2
    fim = (corda1[1] + corda6[1]) / 2
    vetor = fim - origem
    u = vetor / np.linalg.norm(vetor)
    return origem, u


def _projetar(trastes: list, origem: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Projeta os pontos dos trastes sobre um eixo.

    Args:
        trastes: Lista de trastes [{"numero": int, "ponto": [x, y]}, ...].
        origem: Origem do eixo.
        u: Vetor unitário do eixo.

    Returns:
        Array com a coordenada de cada traste ao longo do eixo.
    """
    return np.array(
        [
            float(np.dot(np.asarray(t["ponto"], dtype=float) - origem, u))
            for t in trastes
        ]
    )


def _espacos(s: np.ndarray) -> np.ndarray:
    """Calcula o espaçamento local de cada traste.

    O espaçamento é a menor distância até um vizinho na ordem ordenada.
    Um traste nas pontas usa apenas o único vizinho que tem.

    Args:
        s: Coordenadas projetadas dos trastes (pelo menos dois).

    Returns:
        Array com o espaçamento local de cada traste, na ordem original.
    """
    ordem = np.argsort(s)
    ordenado = s[ordem]
    n = len(s)
    espaco = np.empty(n, dtype=float)
    for k in range(n):
        vizinhas = []
        if k > 0:
            vizinhas.append(float(ordenado[k] - ordenado[k - 1]))
        if k < n - 1:
            vizinhas.append(float(ordenado[k + 1] - ordenado[k]))
        espaco[ordem[k]] = min(vizinhas)
    return espaco


def casar(a: dict, b: dict) -> list[tuple[int, int]] | None:
    """Casa os trastes de um quadro com os do quadro seguinte.

    Os trastes de ambos os quadros são projetados no eixo de b. Cada traste
    de a é ligado ao traste de b mais próximo, se a distância for no máximo
    TOLERANCIA_CASA vezes o espaçamento local de b. O casamento é um a um.

    Args:
        a: Quadro de origem do casamento.
        b: Quadro de destino do casamento.

    Returns:
        Lista de pares (índice em a, índice em b), ou None se algum quadro
        não tem o braço achado ou se houver menos de MIN_CASADOS pares.
    """
    pa = a["previsto"]
    pb = b["previsto"]
    if not pa.get("achou") or not pb.get("achou"):
        return None
    trastes_a = pa.get("trastes") or []
    trastes_b = pb.get("trastes") or []
    if len(trastes_a) < MIN_CASADOS or len(trastes_b) < MIN_CASADOS:
        return None
    origem, u = eixo(b)
    s_a = _projetar(trastes_a, origem, u)
    s_b = _projetar(trastes_b, origem, u)
    espaco = _espacos(s_b)
    melhor: dict[int, tuple[float, int]] = {}
    for i, sa in enumerate(s_a):
        diferencas = np.abs(s_b - sa)
        j = int(np.argmin(diferencas))
        d = float(diferencas[j])
        if d > TOLERANCIA_CASA * espaco[j]:
            continue
        if j not in melhor or d < melhor[j][0]:
            melhor[j] = (d, i)
    pares = sorted((i, j) for j, (_, i) in melhor.items())
    if len(pares) < MIN_CASADOS:
        return None
    return pares


def propagar_k(caminho: list[dict]) -> int | None:
    """Propaga a numeração do quadro de referência até o último quadro.

    O primeiro quadro é a referência, com k = 0. Em cada elo (A, B), um
    traste casado tem número verdadeiro numero_A + k_A, e então
    k_B = numero_A[i] + k_A - numero_B[j]. Todos os pares do elo devem dar o
    mesmo k_B.

    Args:
        caminho: Quadros em ordem temporal a partir da referência.

    Returns:
        O k do último quadro, ou None se algum elo não casar ou se os pares
        de um elo derem k diferentes.
    """
    k = 0
    for a, b in itertools.pairwise(caminho):
        pares = casar(a, b)
        if pares is None:
            return None
        trastes_a = a["previsto"]["trastes"]
        trastes_b = b["previsto"]["trastes"]
        ks = {trastes_a[i]["numero"] + k - trastes_b[j]["numero"] for i, j in pares}
        if len(ks) != 1:
            return None
        k = ks.pop()
    return k


def _referencia(
    registros: list[dict], indices_confiantes: list[int], idx: int
) -> int | None:
    """Acha o quadro com nut confiante mais próximo no tempo.

    Args:
        registros: Quadros do vídeo, em ordem temporal.
        indices_confiantes: Índices dos quadros com nut confiante.
        idx: Índice do quadro-alvo.

    Returns:
        Índice do quadro de referência, ou None se não há nenhum a até
        JANELA_S segundos. Em empate de distância, vence o mais antigo.
    """
    t_alvo = registros[idx]["t"]
    candidatos = [
        (abs(registros[c]["t"] - t_alvo), registros[c]["t"], c)
        for c in indices_confiantes
        if abs(registros[c]["t"] - t_alvo) <= JANELA_S
    ]
    if not candidatos:
        return None
    return min(candidatos)[2]


def metodo_v(registros: list[dict]) -> dict[str, dict]:
    """Numera a tablatura de um vídeo pelo método dos quadros vizinhos.

    Para cada quadro com braço achado, usa o próprio quadro se o nut for
    confiável; senão, propaga a numeração do quadro de nut confiável mais
    próximo no tempo (até JANELA_S segundos) pelo caminho de quadros entre
    eles. Quadros sem braço achado não entram na saída.

    Args:
        registros: Quadros densos de um vídeo, em ordem temporal.

    Returns:
        Dicionário id -> {"k": int ou None, "referencia": str ou None,
        "motivo": str}.
    """
    confiantes = [i for i, r in enumerate(registros) if nut_confiante(r)]
    saida: dict[str, dict] = {}
    for idx, registro in enumerate(registros):
        if not registro["previsto"].get("achou"):
            continue
        id_quadro = registro["id"]
        if nut_confiante(registro):
            saida[id_quadro] = {
                "k": 0,
                "referencia": id_quadro,
                "motivo": "nut visível",
            }
            continue
        ref = _referencia(registros, confiantes, idx)
        if ref is None:
            saida[id_quadro] = {
                "k": None,
                "referencia": None,
                "motivo": "sem nut a até 30 s",
            }
            continue
        ref_id = registros[ref]["id"]
        if ref < idx:
            caminho = registros[ref : idx + 1]
        else:
            caminho = list(reversed(registros[idx : ref + 1]))
        if any(not c["previsto"].get("achou") for c in caminho):
            saida[id_quadro] = {
                "k": None,
                "referencia": ref_id,
                "motivo": "caminho sem braço",
            }
            continue
        k = propagar_k(caminho)
        saida[id_quadro] = {
            "k": k,
            "referencia": ref_id,
            "motivo": "caminho quebrou" if k is None else "seguido",
        }
    return saida
