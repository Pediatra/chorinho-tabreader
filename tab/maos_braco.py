"""Geometria do braço do violão (M3): cordas, trastes e alvo de cada nota.

Só numpy. Recebe a imagem já lida (uma matriz de cinza) e devolve geometria. A leitura
do vídeo fica em ``tab.maos_calibrar_braco``, para que os testes do gate rodem sem
cv2, sem GPU e sem acervo.

Convenções:

- cada corda é ``y = a + b * x`` (uma reta por corda; o braço pode estar levemente
  inclinado). Cordas numeradas de 1 (mi agudo, a mais aguda) a 6 (mi grave);
- trastes: ``x_k`` para k = 0 (o nut, traste 0) até k = 14. A distância entre trastes
  vizinhos diminui em direção ao CORPO, ou seja, para a esquerda na imagem (a cabeça
  está à direita). A razão entre espaçamentos vizinhos é ``2^(-1/12)``, ~0,944;
- casa k fica entre o traste k-1 e o traste k, contando a partir do nut.
"""

from __future__ import annotations

import numpy as np

#: Razão teórica entre espaçamentos de trastes vizinhos (temperamento igual).
RAZAO_TEORICA = 2 ** (-1 / 12)

#: Maior casa modelada. Os trastes 0 a 14 cobrem as casas 0 a 7 com folga.
N_TRASTES = 14

#: Fração do caminho, do traste k-1 ao traste k, onde o dedo pisa (perto do traste).
FRACAO_PISADA = 0.7


def realcar(cinza: np.ndarray, eixo: int, janela: int = 11) -> np.ndarray:
    """Tira o fundo local ao longo de um eixo, deixando as linhas finas claras.

    Com ``eixo=0`` a média é tomada em y (realça cordas, que são horizontais). Com
    ``eixo=1``, em x (realça trastes, que são verticais).

    Args:
        cinza: imagem em tons de cinza, forma ``(altura, largura)``.
        eixo: 0 para realçar linhas horizontais, 1 para verticais.
        janela: tamanho da média móvel, em pixels.

    Returns:
        Imagem realçada, da mesma forma, em ``float``.
    """
    base = cinza.astype(float)
    kernel = np.ones(janela) / janela
    media = np.apply_along_axis(
        lambda v: np.convolve(v, kernel, mode="same"), eixo, base
    )
    return base - media


def picos(perfil: np.ndarray, minimo: float, distancia: int) -> list[int]:
    """Máximos locais de um perfil 1D, acima de um mínimo e espaçados.

    Os picos são escolhidos do mais forte para o mais fraco; um pico é descartado se
    estiver a menos de ``distancia`` de um pico já escolhido.

    Args:
        perfil: valores 1D.
        minimo: valor mínimo para um pico contar.
        distancia: separação mínima, em índices, entre dois picos escolhidos.

    Returns:
        Índices dos picos escolhidos, em ordem crescente.
    """
    locais = [
        i
        for i in range(1, len(perfil) - 1)
        if perfil[i] >= perfil[i - 1]
        and perfil[i] > perfil[i + 1]
        and perfil[i] > minimo
    ]
    escolhidos: list[int] = []
    for i in sorted(locais, key=lambda j: -perfil[j]):
        if all(abs(i - j) >= distancia for j in escolhidos):
            escolhidos.append(i)
    return sorted(escolhidos)


def ajustar_reta(xs: np.ndarray, ys: np.ndarray) -> tuple[float, float, float]:
    """Reta ``y = a + b * x`` por mínimos quadrados, com o resíduo RMS.

    Args:
        xs: abscissas.
        ys: ordenadas, da mesma forma.

    Returns:
        ``(a, b, rms)``: intercepto, inclinação e raiz do erro quadrático médio.
    """
    b, a = np.polyfit(xs, ys, 1)
    rms = float(np.sqrt(np.mean((ys - (a + b * xs)) ** 2)))
    return float(a), float(b), rms


def ajustar_reta_robusta(
    xs: np.ndarray, ys: np.ndarray, limiar: float = 2.0, rodadas: int = 3
) -> tuple[float, float, float]:
    """Reta por mínimos quadrados, descartando pontos longe da reta a cada rodada.

    Args:
        xs: abscissas.
        ys: ordenadas, da mesma forma.
        limiar: distância vertical, em px, acima da qual um ponto é descartado.
        rodadas: quantas vezes refazer o ajuste sem os pontos ruins.

    Returns:
        ``(a, b, rms)`` calculado sobre os pontos que ficaram.
    """
    mascara = np.ones(len(xs), dtype=bool)
    a, b, rms = ajustar_reta(xs, ys)
    for _ in range(rodadas):
        resto = np.abs(ys - (a + b * xs))
        nova = resto <= limiar
        if nova.sum() < 3:
            break
        mascara = nova
        a, b, rms = ajustar_reta(xs[mascara], ys[mascara])
    return a, b, rms


def _seguir(
    alt: np.ndarray,
    gray: np.ndarray,
    prever,
    x_ini: int,
    x_fim: int,
    passo: int,
    janela: int,
    forca_minima: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Acompanha uma corda coluna a coluna, pegando o pico perto da previsão.

    Args:
        alt: imagem realçada em y (cordas aparecem como picos positivos).
        gray: imagem em cinza, para medir o brilho da corda.
        prever: função ``x -> y`` com a previsão da corda naquela coluna.
        x_ini: primeira coluna.
        x_fim: última coluna (inclusive).
        passo: intervalo entre colunas medidas.
        janela: semi-largura, em px, da busca em torno da previsão.
        forca_minima: valor mínimo do realce para o pico contar.

    Returns:
        ``(xs, ys, brilhos)`` dos pontos aceitos.
    """
    xs: list[float] = []
    ys: list[float] = []
    brilhos: list[float] = []
    for x in range(x_ini, x_fim + 1, passo):
        yc = round(prever(x))
        lo, hi = max(0, yc - janela), min(alt.shape[0] - 1, yc + janela)
        coluna = alt[lo : hi + 1, max(0, x - 2) : x + 3].mean(axis=1)
        i = int(np.argmax(coluna))
        if coluna[i] < forca_minima:
            continue
        y = lo + i
        xs.append(float(x))
        ys.append(float(y))
        brilhos.append(float(gray[y, x]))
    return np.asarray(xs), np.asarray(ys), np.asarray(brilhos)


def achar_cordas(
    cinza: np.ndarray,
    x_ini: int,
    x_fim: int,
    y_ini: int,
    y_fim: int,
    n_cordas: int = 6,
) -> list[dict]:
    """Acha as cordas do braço: uma reta por corda, de cima para baixo na imagem.

    Procura os picos de uma coluna de referência no meio da faixa, escolhe a janela
    de ``n_cordas`` picos com espaçamento mais uniforme (descarta a borda do
    braço), e acompanha cada corda em duas passadas: a primeira com janela larga, a
    segunda com a reta já ajustada.

    Args:
        cinza: imagem em tons de cinza do quadro (mediana), ``(altura, largura)``.
        x_ini: primeira coluna da região onde as cordas são medidas.
        x_fim: última coluna da região.
        y_ini: primeira linha da faixa de busca.
        y_fim: última linha da faixa de busca.
        n_cordas: número de cordas a achar.

    Returns:
        Lista de dicionários, de cima para baixo: ``a``, ``b`` (``y = a + b x``),
        ``rms`` (resíduo), ``n`` (pontos usados), ``brilho`` (mediana do cinza sobre a
        corda). A numeração ``corda`` NÃO é atribuída aqui: ver ``numerar_cordas``.

    Raises:
        ValueError: se a faixa não tem ``n_cordas`` picos bem espaçados.
    """
    alt = realcar(cinza, eixo=0)
    alt = alt[y_ini:y_fim]
    gray = cinza[y_ini:y_fim]
    x_ref = (x_ini + x_fim) // 2
    perfil = alt[:, x_ref - 10 : x_ref + 11].mean(axis=1)
    minimo = 0.25 * float(perfil.max())
    candidatos = picos(perfil, minimo=minimo, distancia=8)
    if len(candidatos) < n_cordas:
        raise ValueError(f"{len(candidatos)} picos de corda, eram {n_cordas}")
    melhor: tuple[float, list[int]] | None = None
    for i in range(len(candidatos) - n_cordas + 1):
        janela = candidatos[i : i + n_cordas]
        espacos = np.diff(janela)
        dispersao = float(np.std(espacos))
        if melhor is None or dispersao < melhor[0]:
            melhor = (dispersao, janela)
    assert melhor is not None
    cordas: list[dict] = []
    for y0 in melhor[1]:
        xs, ys, brilhos = _seguir(
            alt,
            gray,
            lambda _x, y0=y0: y0,
            x_ini,
            x_fim,
            passo=6,
            janela=15,
            forca_minima=8.0,
        )
        a, b, rms = ajustar_reta_robusta(xs, ys)
        xs, ys, brilhos = _seguir(
            alt,
            gray,
            lambda x, a=a, b=b: a + b * x,
            x_ini,
            x_fim,
            passo=4,
            janela=4,
            forca_minima=8.0,
        )
        a, b, rms = ajustar_reta_robusta(xs, ys)
        cordas.append(
            {
                "a": a + y_ini,
                "b": b,
                "rms": rms,
                "n": len(xs),
                "brilho": float(np.median(brilhos)),
            }
        )
    return sorted(cordas, key=lambda c: c["a"] + c["b"] * x_ref)


def numerar_cordas(cordas: list[dict]) -> list[dict]:
    """Atribui o número de corda (1 a 6) às retas, pela posição física e conferido.

    Ordem física (regra principal): a câmera é frontal, com a cabeça do violão à
    direita, e a mão esquerda chega por BAIXO do braço, pelo lado das cordas agudas.
    Logo a linha mais perto da mão, a de baixo na imagem, é a corda 1 (mi agudo), e a
    de cima é a 6 (mi grave).

    Conferência pelo brilho: num violão de náilon, os bordões (4 a 6) são revestidos de
    metal e brilham; as primas (1 a 3) são de náilon transparente e ficam escuras sobre
    o braço. Logo as três linhas de cima (bordões) têm que ser mais claras que as três
    de baixo (primas).

    Se as duas regras discordam, a função levanta erro e NÃO escolhe uma delas.

    Args:
        cordas: saída de :func:`achar_cordas`, de cima para baixo, com ``brilho``.

    Returns:
        A mesma lista, com a chave ``corda`` (1 a 6) em cada item, ordenada por corda.

    Raises:
        ValueError: se as linhas de cima não são mais claras que as de baixo.
    """
    metade = len(cordas) // 2
    brilho_cima = float(np.mean([c["brilho"] for c in cordas[:metade]]))
    brilho_baixo = float(np.mean([c["brilho"] for c in cordas[metade:]]))
    if brilho_cima <= brilho_baixo:
        raise ValueError(
            f"brilho discorda da posição: topo {brilho_cima:.1f} <= base "
            f"{brilho_baixo:.1f}; a regra física põe o topo como corda 6 (bordão, "
            "mais claro). Não numerar sem entender a imagem."
        )
    total = len(cordas)
    saida = [{**c, "corda": total - i} for i, c in enumerate(cordas)]
    return sorted(saida, key=lambda c: c["corda"])


def achar_nut(
    cinza: np.ndarray, y_ini: int, y_fim: int, x_ini: int, x_fim: int
) -> float:
    """Posição, em x, do nut: a faixa branca mais clara perto da cabeça.

    Args:
        cinza: imagem em tons de cinza.
        y_ini: primeira linha da medição.
        y_fim: última linha da medição (exclusiva).
        x_ini: primeira coluna da busca.
        x_fim: última coluna da busca (exclusiva).

    Returns:
        Centro, em px, do bloco de colunas mais claras (que contém o pico).
    """
    perfil = cinza[y_ini:y_fim, x_ini:x_fim].mean(axis=0)
    pico = int(np.argmax(perfil))
    limiar = 0.85 * float(perfil[pico])
    esquerda = pico
    while esquerda > 0 and perfil[esquerda - 1] >= limiar:
        esquerda -= 1
    direita = pico
    while direita < len(perfil) - 1 and perfil[direita + 1] >= limiar:
        direita += 1
    return x_ini + (esquerda + direita) / 2


def achar_trastes(
    cinza: np.ndarray, y_ini: int, y_fim: int, x_ini: int, x_fim: int
) -> list[float]:
    """Posições em x dos trastes (linhas verticais claras) numa faixa de linhas.

    Args:
        cinza: imagem em tons de cinza.
        y_ini: primeira linha da faixa (fica acima da mão, onde ela não cobre).
        y_fim: última linha da faixa (exclusiva).
        x_ini: primeira coluna da busca.
        x_fim: última coluna da busca (exclusiva). Deve parar antes do nut.

    Returns:
        Abscissas dos trastes achados, em ordem crescente.
    """
    perfil = realcar(cinza, eixo=1)[y_ini:y_fim, x_ini:x_fim].mean(axis=0)
    minimo = 0.25 * float(perfil.max())
    return [float(x_ini + i) for i in picos(perfil, minimo=minimo, distancia=20)]


def ajustar_escala(
    x_nut: float,
    detectados: list[float],
    n_max: int = N_TRASTES,
    tolerancia: float = 6.0,
) -> dict:
    """Ajusta o modelo de trastes ``x_k = x_nut - L (1 - 2^(-k/12))`` aos detectados.

    Escolhe o comprimento ``L`` que mais trastes detectados explica (dentro de
    ``tolerancia`` px), depois refina ``x_nut`` e ``L`` por mínimos quadrados sobre os
    trastes casados. Trastes do modelo sem detecção ficam marcados como ``previsto``.

    Args:
        x_nut: posição medida do nut (traste 0).
        detectados: posições em x dos trastes detectados.
        n_max: maior traste modelado.
        tolerancia: distância máxima, em px, para casar um detectado com o modelo.

    Returns:
        ``x0``, ``L`` (px), ``trastes`` (``k -> {"x", "origem"}``, ``origem`` é
        ``detectado`` ou ``previsto``), ``residuo_px`` (RMS dos casados),
        ``razao_mediana`` (mediana das razões entre espaçamentos vizinhos; deve estar
        perto de 0,944) e ``casados`` (quantos trastes tiveram detecção).
    """
    ks = np.arange(1, n_max + 1)
    c = 1 - 2.0 ** (-ks / 12)
    det = np.sort(np.asarray(detectados, dtype=float))
    melhor: tuple[int, float, float] | None = None
    for comprimento in np.arange(1400.0, 2600.0, 1.0):
        previstos = x_nut - comprimento * c
        dist = np.abs(previstos[:, None] - det[None, :]).min(axis=1)
        casados = int((dist <= tolerancia).sum())
        erro = float(dist[dist <= tolerancia].sum())
        if (
            melhor is None
            or casados > melhor[0]
            or (casados == melhor[0] and erro < melhor[1])
        ):
            melhor = (casados, erro, comprimento)
    assert melhor is not None
    _, _, L0 = melhor
    # Refina: casa cada traste ao modelo atual, refaz o ajuste e repete. Com a
    # perspectiva, o modelo do primeiro ajuste erra alguns px, e a 2a rodada
    # (com tolerancia 2x) pega trastes que a 1a deixou de fora.
    x0, L = float(x_nut), float(L0)
    pares: list[tuple[float, float]] = []
    for rodada in range(3):
        tol = tolerancia if rodada == 0 else 2 * tolerancia
        previstos = x0 - L * c
        pares = []
        for k, previsto in zip(ks, previstos, strict=True):
            j = int(np.argmin(np.abs(det - previsto)))
            if abs(det[j] - previsto) <= tol:
                pares.append((float(c[k - 1]), float(det[j])))
        pares.append((0.0, float(x_nut)))
        sc = np.array([p[0] for p in pares])
        sx = np.array([p[1] for p in pares])
        matriz = np.column_stack([np.ones_like(sc), -sc])
        (x0, L), *_ = np.linalg.lstsq(matriz, sx, rcond=None)
        x0, L = float(x0), float(L)
    residuo = float(np.sqrt(np.mean((matriz @ np.array([x0, L]) - sx) ** 2)))
    trastes: dict[int, dict] = {0: {"x": float(x_nut), "origem": "detectado"}}
    for k in ks:
        previsto = x0 - L * (1 - 2.0 ** (-k / 12))
        j = int(np.argmin(np.abs(det - previsto)))
        if abs(det[j] - previsto) <= 2 * tolerancia:
            trastes[int(k)] = {"x": float(det[j]), "origem": "detectado"}
        else:
            trastes[int(k)] = {"x": float(previsto), "origem": "previsto"}
    xs_ordenados = [trastes[k]["x"] for k in range(n_max + 1)]
    espacos = np.diff(xs_ordenados) * -1
    razoes = espacos[1:] / espacos[:-1]
    return {
        "x0": x0,
        "L": L,
        "trastes": trastes,
        "residuo_px": residuo,
        "razao_mediana": float(np.median(razoes)),
        "casados": len(pares) - 1,
    }


def x_da_pisada(
    casa: int, trastes: dict[int, dict], frac: float = FRACAO_PISADA
) -> float:
    """Posição em x onde o dedo pisa a casa: ``frac`` do caminho até o traste.

    Args:
        casa: casa da nota, de 1 em diante (a casa 0 não é pisada).
        trastes: ``k -> {"x": ...}``, com o traste ``casa-1`` e o ``casa``.
        frac: fração do caminho, a partir do traste ``casa-1``, em direção ao
            traste ``casa``.

    Returns:
        A abscissa do alvo.

    Raises:
        ValueError: se a casa é 0 ou não há trastes para ela.
    """
    if casa < 1:
        raise ValueError("casa 0 é corda solta: não há ponto pisado")
    x_antes = trastes[casa - 1]["x"]
    x_depois = trastes[casa]["x"]
    return x_antes + frac * (x_depois - x_antes)


def y_da_corda(cordas: dict[int, dict], corda: int, x: float) -> float:
    """Ordenada da corda ``corda`` na abscissa ``x``.

    Args:
        cordas: ``corda -> {"a", "b"}`` (saída de :func:`numerar_cordas`, indexada).
        corda: número da corda, de 1 a 6.
        x: abscissa.

    Returns:
        ``a + b * x``.
    """
    reta = cordas[corda]
    return reta["a"] + reta["b"] * x


def alvo_da_nota(
    corda: int,
    casa: int,
    cordas: dict[int, dict],
    trastes: dict[int, dict],
    frac: float = FRACAO_PISADA,
) -> tuple[float, float]:
    """Ponto (x, y) onde a nota é pisada: na corda, a ``frac`` do traste anterior.

    Args:
        corda: número da corda, de 1 a 6 (1 é a mais aguda).
        casa: casa da nota, de 1 em diante.
        cordas: retas das cordas, indexadas pelo número.
        trastes: trastes do :func:`ajustar_escala`.
        frac: fração do caminho do traste ``casa-1`` ao traste ``casa``.

    Returns:
        ``(x, y)`` do alvo no quadro.
    """
    x = x_da_pisada(casa, trastes, frac)
    return x, y_da_corda(cordas, corda, x)


def meia_largura_casa(casa: int, trastes: dict[int, dict]) -> float:
    """Metade da largura, em px, da casa: meia distância entre seus dois trastes.

    Args:
        casa: casa da nota, de 1 em diante.
        trastes: trastes do :func:`ajustar_escala`.

    Returns:
        ``|x_{casa-1} - x_casa| / 2``.
    """
    return abs(trastes[casa - 1]["x"] - trastes[casa]["x"]) / 2


def dedo_mais_perto(
    alvo: tuple[float, float], pontas: dict[int, tuple[float, float]]
) -> tuple[str, float, float]:
    """Dedo cuja ponta está mais perto do alvo, com a distância e a segunda.

    Args:
        alvo: ``(x, y)`` do ponto pisado.
        pontas: ``dedo -> (x, y)`` das pontas, com dedos 1 a 4. Ponta ausente não entra.

    Returns:
        ``(dedo, distancia, segunda_distancia)``, com o dedo como texto ``"1"`` a
        ``"4"``. A segunda distância é ``inf`` se só há uma ponta.

    Raises:
        ValueError: se não há nenhuma ponta.
    """
    if not pontas:
        raise ValueError("nenhuma ponta de dedo")
    distancias = sorted(
        (float(np.hypot(x - alvo[0], y - alvo[1])), str(dedo))
        for dedo, (x, y) in pontas.items()
    )
    primeira, dedo = distancias[0]
    segunda = distancias[1][0] if len(distancias) > 1 else float("inf")
    return dedo, primeira, segunda


def votar(decisoes: list[str | None], padrao: str | None) -> str | None:
    """Maioria entre as decisões dos quadros; empate ou vazio fica com ``padrao``.

    Args:
        decisoes: uma decisão por quadro (``None`` = não decidiu, não conta).
        padrao: decisão do quadro central, usada em empate.

    Returns:
        O dedo da maioria, ou ``padrao`` se não há maioria estrita.
    """
    contagem: dict[str, int] = {}
    for d in decisoes:
        if d is not None:
            contagem[d] = contagem.get(d, 0) + 1
    if not contagem:
        return padrao
    maximo = max(contagem.values())
    vencedores = [d for d, n in contagem.items() if n == maximo]
    if len(vencedores) == 1:
        return vencedores[0]
    return padrao


def escolher_mao_esquerda(
    maos: list[dict], x_min: float = 670.0, y_min: float = 520.0
) -> dict | None:
    """A mão esquerda que está na câmera do braço (a da metade direita do quadro).

    Entre as candidatas, fica com a de maior área: é a mão mais perto da câmera. A
    câmera do braço começa em x 670 e y 520 (medido no quadro do vídeo).

    Args:
        maos: saída de ``DetectorMaos.detectar`` (chave ``maos``), com ``lado``,
            ``caixa`` e ``pts``.
        x_min: abscissa mínima do centro da mão para contar como câmera do braço.
        y_min: ordenada mínima do centro da mão.

    Returns:
        A mão escolhida, ou ``None`` se não há mão esquerda na câmera do braço.
    """
    candidatas = []
    for mao in maos:
        if mao["lado"] != "esquerda":
            continue
        x0, y0, x1, y1 = mao["caixa"]
        if (x0 + x1) / 2 < x_min or (y0 + y1) / 2 < y_min:
            continue
        candidatas.append(mao)
    if not candidatas:
        return None
    return max(
        candidatas,
        key=lambda m: (m["caixa"][2] - m["caixa"][0]) * (m["caixa"][3] - m["caixa"][1]),
    )


#: Índices das pontas dos dedos 1 a 4 nos 21 pontos da mão (mesmo esquema no MediaPipe
#: e no COCO-WholeBody).
PONTA_DOS_DEDOS: dict[int, int] = {1: 8, 2: 12, 3: 16, 4: 20}


def pontas_da_mao(mao: dict) -> dict[int, tuple[float, float]]:
    """Pontas dos dedos 1 a 4 de uma mão (indicador, médio, anelar, mínimo).

    Args:
        mao: mão com ``pts`` (21 pontos ``[x, y]`` ou ``[x, y, score]``, na ordem do
            MediaPipe).

    Returns:
        ``dedo -> (x, y)`` para os dedos 1 a 4.
    """
    pontos = mao["pts"]
    return {
        dedo: (float(pontos[i][0]), float(pontos[i][1]))
        for dedo, i in PONTA_DOS_DEDOS.items()
    }
