"""Gerador sintético de SISTEMAS de tablatura (6 cordas), com rótulo por nota.

Diferença para `tab.sintetico.gerar_linha`: aquele desenha uma linha de algarismos.
Este desenha um sistema inteiro, com acordes empilhados (que se encostam na vertical),
técnicas entre notas da mesma corda e distratores que NÃO são nota: barlines, ritmo
(com haste que sobe por dentro do sistema), fundo cinza atrás de uma nota, faixa do
marcador, número de compasso, rótulo TAB e nome de acorde.

Determinismo: toda escolha vem de `rng`. A mesma semente dá a mesma imagem e os mesmos
rótulos. Nada usa o gerador global de `random` nem o de `numpy`, e nenhum conjunto é
iterado (a ordem de conjuntos de str muda entre execuções).

Coordenadas: a imagem devolvida tem o mesmo tamanho do desenho (a degradação de
reescala volta ao tamanho original), então as coordenadas do dict valem para ela.

Uso:
    python -m tab.sintetico_sistema folha --saida data/saida/n1/folha.png \\
        --n 12 --semente 0
"""

from __future__ import annotations

import argparse
import functools
import math
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .sintetico import CORES_VOZ, PRESETS_FONTES, _resolver_fontes

#: Rótulos possíveis: casas 0-24 (com dois algarismos como UM rótulo) e "x" (abafada).
ROTULOS = (*(str(casa) for casa in range(25)), "x")

#: Técnicas possíveis; `None` é a nota sem técnica.
TECNICAS = (None, "h", "p", "/", "\\", "harm", "lig")

#: Nomes de acorde desenhados acima do sistema (distrator sem rótulo).
ACORDES = ("Am7", "C", "G7", "Dm", "Em", "F#m7", "D7", "Bm7", "A", "Cmaj7")

#: Cores da faixa do marcador: as vozes do gerador e três cores vivas.
CORES_FAIXA = (*CORES_VOZ, (255, 220, 0), (255, 140, 0), (120, 255, 120))

#: Altura do algarismo, em fração do corpo da fonte (Liberation). Converte altura
#: alvo em passo para tamanho de fonte.
DIGITO_ALTURA_EM = 0.716

PASSO_MIN = 12.0
PASSO_MAX = 40.0

# ---- Probabilidades (ajuste aqui; cada uma é uma chance por imagem ou por nota) ----

#: Fundo: nome e peso. `escuro` tem texto claro; `gradiente` vai de claro a um pouco
#: mais escuro de cima para baixo.
P_FUNDO = (
    ("branco", 0.40),
    ("quase_branco", 0.20),
    ("cinza", 0.15),
    ("escuro", 0.15),
    ("gradiente", 0.10),
)
#: Cordas tracejadas (como no gerador antigo, só em fundo claro).
P_CORDA_TRACEJADA = 0.15
#: Cordas cortadas sob o algarismo; o complemento é a corda passando por cima.
P_CORDA_CORTADA = 0.5
#: Chance de uma nota ser casa 13-24 (o resto é 0-12).
P_CASA_ALTA = 0.15
#: Chance de a nota ser "x" (abafada).
P_MUDO = 0.05
#: Chance de uma coluna ter uma nota só (o resto tem 2 a 6 cordas).
P_UMA_NOTA_COLUNA = 0.5
#: Chance de uma nota ser harmônico `<n>`.
P_HARMONICO = 0.06
#: Chance de uma nota ser ligada `(n)`.
P_LIGADA = 0.05
#: Chance de uma coluna (a partir da segunda) começar um par h/p/"/"/"\\".
P_TECNICA_PAR = 0.35
#: Pesos dos tipos de técnica de par (a técnica vai na nota de DESTINO).
TIPOS_PAR = ("h", "p", "/", "\\")
PESOS_PAR = (0.40, 0.30, 0.15, 0.15)
#: Chance de uma nota de voz colorida (em vez da cor da tinta).
P_COR_VOZ = 0.25
#: Chance de um fundo cinza retangular atrás de uma nota.
P_FUNDO_NOTA = 0.30
#: Chance de uma barline interna (entre colunas); as de borda sempre existem.
P_BARLINE_INTERNA = 0.3
#: Chance de a barline interna ser dupla (o resto é simples).
P_BARLINE_DUPLA = 0.3
#: Chance de o sistema ter ritmo (hastes e vigas abaixo da corda 6).
P_RITMO = 0.6
#: Dado ritmo, chance de a haste SUBIR até o algarismo mais baixo da coluna.
#: Com P_RITMO = 0.6, isso dá cerca de 40% das imagens.
P_HASTE_SOBE = 0.67
#: Chance de um compasso pequeno acima da corda 1.
P_COMPASSO = 0.5
#: Chance de as letras TAB à esquerda.
P_TAB = 0.35
#: Chance de um nome de acorde acima do sistema.
P_ACORDE_NOME = 0.3
#: Chance de a faixa do marcador aparecer (larga ou cursor fino).
P_FAIXA = 0.40
#: Dentro da faixa, chance de ser um cursor fino de 2-3 px.
P_CURSOR_FINO = 0.25
#: Chance de a imagem ser reescalada para baixo e voltar (0,5 a 1,0).
P_REESCALA = 0.6
#: Chance de desfoque (0,3 a 1,0 px).
P_DESFOQUE = 0.5

_COR_BANDA_INICIO = 0.12
_COR_BANDA_FIM = 0.35

_TAMANHOS_CORDA = (1, 2, 3)


def _sortear(rng: random.Random, pesos: tuple[tuple[str, float], ...]) -> str:
    """Sorteia um nome segundo os pesos dados.

    Args:
        rng: gerador aleatório.
        pesos: pares (nome, peso).

    Returns:
        O nome sorteado.
    """
    nomes = [nome for nome, _ in pesos]
    return rng.choices(nomes, weights=[peso for _, peso in pesos])[0]


@functools.lru_cache(maxsize=64)
def _carregar_fonte(caminho: str, tamanho: int) -> ImageFont.FreeTypeFont:
    """Carrega uma fonte com cache, para não reabrir o arquivo a cada nota.

    Args:
        caminho: caminho do arquivo .ttf.
        tamanho: tamanho em pixels.

    Returns:
        A fonte carregada.
    """
    return ImageFont.truetype(caminho, tamanho)


def _limitar(caixa: list[int], largura: int, altura: int) -> list[int]:
    """Recorta uma caixa para ficar dentro da imagem.

    Args:
        caixa: [x0, y0, x1, y1].
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        A caixa recortada, com pelo menos 1 px de área.
    """
    x0 = max(0, min(caixa[0], largura - 1))
    y0 = max(0, min(caixa[1], altura - 1))
    x1 = min(largura, max(caixa[2], x0 + 1))
    y1 = min(altura, max(caixa[3], y0 + 1))
    return [x0, y0, x1, y1]


def _posicionar(
    d: ImageDraw.ImageDraw,
    texto: str,
    cx: float,
    cy: float,
    fonte: ImageFont.FreeTypeFont,
    largura: int,
    altura: int,
) -> tuple[int, int, list[int]]:
    """Calcula onde desenhar um texto para que o centro da caixa caia em (cx, cy).

    Args:
        d: desenho onde o texto será medido.
        texto: texto a desenhar.
        cx: centro horizontal desejado.
        cy: centro vertical desejado.
        fonte: fonte usada.
        largura: largura da imagem (para recortar a caixa).
        altura: altura da imagem (para recortar a caixa).

    Returns:
        (px, py, caixa): origem para `d.text` e a caixa [x0, y0, x1, y1] já recortada.
    """
    bb = d.textbbox((0, 0), texto, font=fonte)
    px = round(cx - (bb[0] + bb[2]) / 2)
    py = round(cy - (bb[1] + bb[3]) / 2)
    caixa = [px + bb[0], py + bb[1], px + bb[2], py + bb[3]]
    return px, py, _limitar(caixa, largura, altura)


def _texto_da_nota(nota: dict) -> str:
    """Texto desenhado para uma nota, conforme a técnica.

    Args:
        nota: dict com "rotulo" e "tecnica".

    Returns:
        "<n>" para harmônico, "(n)" para ligada, e o próprio rótulo nos demais casos.
    """
    if nota["tecnica"] == "harm":
        return f"<{nota['rotulo']}>"
    if nota["tecnica"] == "lig":
        return f"({nota['rotulo']})"
    return nota["rotulo"]


def _sortear_rotulo(rng: random.Random) -> str:
    """Sorteia o rótulo de uma nota.

    Args:
        rng: gerador aleatório.

    Returns:
        "x" com P_MUDO, casa 13-24 com P_CASA_ALTA, ou casa 0-12.
    """
    if rng.random() < P_MUDO:
        return "x"
    if rng.random() < P_CASA_ALTA:
        return str(rng.randint(13, 24))
    return str(rng.randint(0, 12))


def _sortear_grade(rng: random.Random, n_col: int) -> dict[tuple[int, int], dict]:
    """Sorteia as notas de cada coluna, com acordes empilhados.

    Args:
        rng: gerador aleatório.
        n_col: número de colunas.

    Returns:
        Mapa (coluna, corda 0-5) -> {"rotulo", "tecnica"}.
    """
    grade: dict[tuple[int, int], dict] = {}
    for c in range(n_col):
        if rng.random() < P_UMA_NOTA_COLUNA:
            cordas = [rng.randrange(6)]
        else:
            n = rng.randint(2, 6)
            if rng.random() < 0.5:  # cordas vizinhas
                ini = rng.randint(0, 6 - n)
                cordas = list(range(ini, ini + n))
            else:
                cordas = sorted(rng.sample(range(6), n))
        for s in cordas:
            grade[(c, s)] = {"rotulo": _sortear_rotulo(rng), "tecnica": None}
    return grade


def _tecnicas_isoladas(rng: random.Random, grade: dict[tuple[int, int], dict]) -> None:
    """Marca harmônicos e ligadas sem par, em notas que não são "x".

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar.
    """
    for nota in grade.values():
        if nota["rotulo"] == "x":
            continue
        r = rng.random()
        if r < P_HARMONICO:
            nota["tecnica"] = "harm"
        elif r < P_HARMONICO + P_LIGADA:
            nota["tecnica"] = "lig"


def _tecnicas_pares(
    rng: random.Random, grade: dict[tuple[int, int], dict], n_col: int
) -> None:
    """Cria pares h/p/"/"/"\\" entre duas notas da mesma corda em colunas vizinhas.

    Cria as notas que faltarem para o par existir. A técnica vai na nota de DESTINO
    (a da coluna da direita). Pula o par se alguma nota for "x" ou já tiver técnica.

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar.
        n_col: número de colunas.
    """
    for c in range(1, n_col):
        if rng.random() >= P_TECNICA_PAR:
            continue
        s = rng.randrange(6)
        tipo = rng.choices(TIPOS_PAR, weights=PESOS_PAR)[0]
        for chave in ((c - 1, s), (c, s)):
            if chave not in grade:
                grade[chave] = {"rotulo": _sortear_rotulo(rng), "tecnica": None}
        origem, destino = grade[(c - 1, s)], grade[(c, s)]
        if "x" in (origem["rotulo"], destino["rotulo"]):
            continue
        if origem["tecnica"] is not None or destino["tecnica"] is not None:
            continue
        destino["tecnica"] = tipo


def _montar_fundo(
    rng: random.Random, nome: str, altura: int, largura: int
) -> tuple[np.ndarray, tuple[int, int, int], tuple[int, int, int], bool]:
    """Desenha o fundo e escolhe as cores de tinta e de linha.

    Args:
        rng: gerador aleatório.
        nome: "branco", "quase_branco", "cinza", "escuro" ou "gradiente".
        altura: altura da imagem.
        largura: largura da imagem.

    Returns:
        (imagem RGB uint8, cor da tinta, cor da linha, se o fundo é escuro).
    """
    if nome == "escuro":
        arr = np.full((altura, largura, 3), rng.randint(15, 40), np.uint8)
        return arr, (230, 230, 230), (190, 190, 190), True
    if nome == "gradiente":
        topo = rng.randint(225, 250)
        coluna = np.linspace(topo, topo - 30, altura).astype(np.uint8)
        arr = np.broadcast_to(coluna[:, None, None], (altura, largura, 3)).copy()
        return arr, (25, 25, 25), (60, 60, 60), False
    if nome == "cinza":
        arr = np.full((altura, largura, 3), rng.randint(190, 225), np.uint8)
        return arr, (30, 30, 30), (70, 70, 70), False
    valor = 255 if nome == "branco" else rng.randint(238, 250)
    arr = np.full((altura, largura, 3), valor, np.uint8)
    return arr, (20, 20, 20), (60, 60, 60), False


def _sortear_cores(
    rng: random.Random, n_col: int, tinta: tuple[int, int, int], escuro: bool
) -> list[tuple[int, int, int]]:
    """Cor de cada coluna: a tinta, ou uma das vozes com P_COR_VOZ.

    Args:
        rng: gerador aleatório.
        n_col: número de colunas.
        tinta: cor da tinta do fundo.
        escuro: se o fundo é escuro (o preto de voz vira branco).

    Returns:
        Uma cor RGB por coluna.
    """
    cores = []
    for _ in range(n_col):
        if rng.random() < P_COR_VOZ:
            cor = rng.choice(CORES_VOZ)
            if escuro and cor == (0, 0, 0):
                cor = (255, 255, 255)
        else:
            cor = tinta
        cores.append(cor)
    return cores


def _medir_notas(
    rng: random.Random,
    d: ImageDraw.ImageDraw,
    grade: dict[tuple[int, int], dict],
    xs: list[float],
    ys: list[int],
    cores: list[tuple[int, int, int]],
    tamanho: int,
    fontes: list[str],
    largura: int,
    altura: int,
) -> dict[tuple[int, int], dict]:
    """Mede a posição e a caixa de cada nota, sem desenhar.

    Args:
        rng: gerador aleatório (escolhe a fonte de cada nota).
        d: desenho usado para medir.
        grade: notas por (coluna, corda).
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        cores: cor de cada coluna.
        tamanho: tamanho da fonte, em pixels.
        fontes: caminhos das fontes.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Mapa (coluna, corda) -> {"texto", "fonte", "px", "py", "caixa", "cor"}.
    """
    medidas: dict[tuple[int, int], dict] = {}
    for (c, s), nota in sorted(grade.items()):
        texto = _texto_da_nota(nota)
        fonte = _carregar_fonte(rng.choice(fontes), tamanho)
        px, py, caixa = _posicionar(d, texto, xs[c], ys[s], fonte, largura, altura)
        medidas[(c, s)] = {
            "texto": texto,
            "fonte": fonte,
            "px": px,
            "py": py,
            "caixa": caixa,
            "cor": cores[c],
        }
    return medidas


def _trechos(
    a0: float,
    a1: float,
    buracos: list[tuple[float, float]],
    tracejada: bool,
    passo: float,
) -> list[tuple[float, float]]:
    """Partes de uma corda entre a0 e a1, sem os buracos e, se for o caso, tracejadas.

    Args:
        a0: início da corda.
        a1: fim da corda.
        buracos: intervalos (x0, x1) onde a corda é cortada.
        tracejada: se a corda é tracejada.
        passo: passo do sistema (define o tamanho do traço).

    Returns:
        Lista de intervalos (x0, x1) a desenhar.
    """
    segmentos: list[tuple[float, float]] = []
    cursor = a0
    for b0, b1 in sorted(buracos):
        if b0 > cursor:
            segmentos.append((cursor, min(b0, a1)))
        cursor = max(cursor, b1)
    if cursor < a1:
        segmentos.append((cursor, a1))
    if not tracejada:
        return [(x0, x1) for x0, x1 in segmentos if x1 > x0]
    tracos: list[tuple[float, float]] = []
    for x0, x1 in segmentos:
        x = x0
        while x < x1:
            tracos.append((x, min(x + 0.8 * passo, x1)))
            x += 1.6 * passo
    return tracos


def _desenhar_cordas(
    d: ImageDraw.ImageDraw,
    ys: list[int],
    x0: float,
    x1: float,
    buracos: list[list[tuple[float, float]]],
    tracejada: bool,
    passo: float,
    espessura: int,
    cor: tuple[int, int, int],
) -> None:
    """Desenha as seis cordas, com os buracos e o tracejado pedidos.

    Args:
        d: desenho.
        ys: linha de cada corda.
        x0: início horizontal das cordas.
        x1: fim horizontal das cordas.
        buracos: por corda, intervalos onde a corda é cortada.
        tracejada: se as cordas são tracejadas.
        passo: passo do sistema.
        espessura: espessura da corda em px.
        cor: cor da corda.
    """
    for s, y in enumerate(ys):
        for a, b in _trechos(x0, x1, buracos[s], tracejada, passo):
            d.line([(round(a), y), (round(b), y)], fill=cor, width=espessura)


def _desenhar_barra(
    d: ImageDraw.ImageDraw,
    x: float,
    tipo: str,
    ys: list[int],
    passo: float,
    espessura: int,
    cor: tuple[int, int, int],
) -> int:
    """Desenha uma barline da corda 1 à 6 e devolve a posição do seu centro.

    Args:
        d: desenho.
        x: posição horizontal da barline.
        tipo: "simples", "dupla" ou "final".
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda (base para o traço fino).
        cor: cor da barline.

    Returns:
        Posição horizontal do centro do grupo de traços, em px.
    """
    topo, base = ys[0], ys[5]
    fina = max(1, espessura - 1)
    if tipo == "dupla":
        for dx in (0.0, 0.35 * passo):
            xx = round(x + dx)
            d.line([(xx, topo), (xx, base)], fill=cor, width=fina)
        return round(x + 0.175 * passo)
    if tipo == "final":
        xx = round(x - 0.4 * passo)
        d.line([(xx, topo), (xx, base)], fill=cor, width=fina)
        grossa = max(2, round(0.3 * passo))
        d.line([(round(x), topo), (round(x), base)], fill=cor, width=grossa)
        return round(x - 0.2 * passo)
    d.line([(round(x), topo), (round(x), base)], fill=cor, width=fina)
    return round(x)


def _desenhar_notas(
    d: ImageDraw.ImageDraw, medidas: dict[tuple[int, int], dict]
) -> None:
    """Desenha o texto de cada nota na posição medida.

    Args:
        d: desenho.
        medidas: saída de `_medir_notas`.
    """
    for m in medidas.values():
        d.text((m["px"], m["py"]), m["texto"], font=m["fonte"], fill=m["cor"])


def _desenhar_tecnicas_pares(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    fontes: list[str],
) -> None:
    """Desenha a ligação de cada par de técnica (letra e arco, ou diagonal).

    Args:
        d: desenho.
        rng: gerador aleatório.
        grade: notas (a técnica está na nota de destino).
        medidas: saída de `_medir_notas`.
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        fontes: caminhos das fontes.
    """
    espessura_traco = max(1, espessura - 1)
    tamanho_letra = max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
    for (c, s), nota in sorted(grade.items()):
        tipo = nota["tecnica"]
        if tipo not in ("h", "p", "/", "\\"):
            continue
        origem = medidas[(c - 1, s)]["caixa"]
        destino = medidas[(c, s)]["caixa"]
        xa = origem[2] + 0.1 * passo
        xb = destino[0] - 0.1 * passo
        y = ys[s]
        if tipo in ("h", "p"):
            xm = (xa + xb) / 2
            if rng.random() < 0.5:  # arco de ligado por cima da ligação
                pontos = []
                for i in range(11):
                    t = i / 10
                    pontos.append(
                        (
                            round(xa + t * (xb - xa)),
                            round(
                                y - 0.5 * passo - 0.35 * passo * math.sin(math.pi * t)
                            ),
                        )
                    )
                d.line(pontos, fill=tinta, width=espessura_traco)
            fonte = _carregar_fonte(rng.choice(fontes), tamanho_letra)
            px, py, _ = _posicionar(d, tipo, xm, y - 1.1 * passo, fonte, 10**6, 10**6)
            d.text((px, py), tipo, font=fonte, fill=tinta)
        else:
            if tipo == "/":
                pa, pb = y + 0.25 * passo, y - 0.25 * passo
            else:
                pa, pb = y - 0.25 * passo, y + 0.25 * passo
            d.line(
                [(round(xa), round(pa)), (round(xb), round(pb))],
                fill=tinta,
                width=espessura_traco,
            )


def _agrupar_consecutivos(colunas: list[int], tamanho_max: int) -> list[list[int]]:
    """Agrupa colunas vizinhas (c, c+1, ...) em grupos de até `tamanho_max`.

    Args:
        colunas: índices de colunas, em ordem crescente.
        tamanho_max: tamanho máximo de cada grupo.

    Returns:
        Lista de grupos.
    """
    grupos: list[list[int]] = []
    for c in colunas:
        if grupos and c == grupos[-1][-1] + 1 and len(grupos[-1]) < tamanho_max:
            grupos[-1].append(c)
        else:
            grupos.append([c])
    return grupos


def _desenhar_ritmo(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    passo: float,
    xs: list[float],
    ys: list[int],
    n_col: int,
    base_por_coluna: dict[int, int],
    sobe: bool,
    tinta: tuple[int, int, int],
) -> None:
    """Desenha hastes e vigas de ritmo abaixo da corda 6.

    Com `sobe`, a haste vai da viga até o algarismo mais baixo da coluna (encostando
    nele), como no canal guitarous. Sem `sobe`, a haste desce da corda 6 até a viga.

    Args:
        d: desenho.
        rng: gerador aleatório.
        passo: passo do sistema.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        n_col: número de colunas.
        base_por_coluna: y da parte de baixo do algarismo mais baixo de cada coluna.
        sobe: se a haste sobe por dentro do sistema.
        tinta: cor do ritmo.
    """
    viga_y = round(ys[5] + 2.6 * passo)
    espessura_haste = max(1, round(0.1 * passo))
    espessura_viga = max(2, round(0.25 * passo))
    colunas = [c for c in range(n_col) if rng.random() < 0.6]
    for grupo in _agrupar_consecutivos(colunas, 3):
        for c in grupo:
            topo = ys[5] + 0.5 * passo
            if sobe and c in base_por_coluna:
                topo = base_por_coluna[c] + 1
            x = round(xs[c])
            d.line([(x, round(topo)), (x, viga_y)], fill=tinta, width=espessura_haste)
        xa, xb = round(xs[grupo[0]]), round(xs[grupo[-1]])
        if len(grupo) >= 2:
            d.line([(xa, viga_y), (xb, viga_y)], fill=tinta, width=espessura_viga)
        else:  # colchete
            d.line(
                [(xa, viga_y), (round(xa + 0.5 * passo), round(viga_y - 0.5 * passo))],
                fill=tinta,
                width=espessura_haste,
            )


def _desenhar_faixa(
    arr: np.ndarray,
    rng: random.Random,
    passo: float,
    xs: list[float],
    ys: list[int],
) -> None:
    """Mistura sobre uma coluna uma faixa translúcida (ou um cursor fino) do marcador.

    Args:
        arr: imagem RGB uint8, alterada no lugar.
        rng: gerador aleatório.
        passo: passo do sistema.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
    """
    altura, largura = arr.shape[:2]
    x_c = xs[rng.randrange(len(xs))]
    topo = max(0, round(ys[0] - 0.6 * passo))
    base = min(altura, round(ys[5] + 0.6 * passo))
    if rng.random() < P_CURSOR_FINO:
        espessura = rng.choice((2, 3))
        x0 = round(x_c - espessura / 2)
        x1 = x0 + espessura
        alfa = rng.uniform(0.5, 0.9)
    else:
        largura_faixa = passo * rng.uniform(0.3, 1.5)
        x0 = round(x_c - largura_faixa / 2)
        x1 = round(x_c + largura_faixa / 2)
        alfa = rng.uniform(_COR_BANDA_INICIO, _COR_BANDA_FIM)
    x0, x1 = max(0, x0), min(largura, max(x1, x0 + 1))
    cor = np.array(rng.choice(CORES_FAIXA), np.float32)
    regiao = arr[topo:base, x0:x1].astype(np.float32)
    arr[topo:base, x0:x1] = (regiao * (1 - alfa) + cor * alfa).astype(np.uint8)


def _degradar(rng: random.Random, img: np.ndarray) -> np.ndarray:
    """Degrada a imagem como uma captura de vídeo: reescala, desfoque, JPEG e ruído.

    Args:
        rng: gerador aleatório.
        img: imagem BGR uint8.

    Returns:
        Imagem BGR uint8, do mesmo tamanho da entrada.
    """
    altura, largura = img.shape[:2]
    if rng.random() < P_REESCALA:
        fator = rng.uniform(0.5, 1.0)
        pequena = cv2.resize(
            img,
            (max(1, round(largura * fator)), max(1, round(altura * fator))),
            interpolation=cv2.INTER_AREA,
        )
        img = cv2.resize(pequena, (largura, altura), interpolation=cv2.INTER_LINEAR)
    if rng.random() < P_DESFOQUE:
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.3, 1.0))
    qualidade = rng.randint(30, 95)
    _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, qualidade])
    img = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    gerador = np.random.default_rng(rng.getrandbits(32))
    ruido = gerador.normal(0.0, rng.uniform(0.0, 4.0), img.shape)
    return np.clip(img + ruido, 0, 255).astype(np.uint8)


def gerar_sistema(rng: random.Random, fontes: list[str]) -> tuple[np.ndarray, dict]:
    """Desenha um sistema de tablatura de 6 cordas e devolve a imagem e os rótulos.

    Args:
        rng: gerador aleatório; a mesma semente dá a mesma imagem e os mesmos rótulos.
        fontes: caminhos das fontes (com repetição = peso).

    Returns:
        Tupla (imagem BGR uint8, dict) com:
            "passo": passo do sistema, em px (float).
            "linhas_y": y de cada corda, da 1 (em cima) à 6, em px (6 ints).
            "barlines_x": x do centro de cada barline, em px.
            "notas": lista de {"corda" (1-6), "rotulo", "tecnica", "x" (centro),
            "caixa" ([x0, y0, x1, y1])}, na ordem coluna a coluna.

    Raises:
        ValueError: se `fontes` estiver vazio.
    """
    if not fontes:
        raise ValueError("gerar_sistema precisa de ao menos uma fonte")

    passo = rng.uniform(PASSO_MIN, PASSO_MAX)
    fundo = _sortear(rng, P_FUNDO)
    tem_ritmo = rng.random() < P_RITMO
    haste_sobe = tem_ritmo and rng.random() < P_HASTE_SOBE
    corta = rng.random() < P_CORDA_CORTADA
    tracejada = rng.random() < P_CORDA_TRACEJADA
    espessura = rng.choice(_TAMANHOS_CORDA)
    n_col = rng.randint(4, 9)
    espaco = passo * rng.uniform(1.2, 2.6)
    x_ini = 2.6 * passo
    x_fim = x_ini + n_col * espaco
    largura = round(x_fim + 2.2 * passo)
    ys = [round(2.4 * passo + i * passo) for i in range(6)]
    altura = round(ys[5] + (3.4 if tem_ritmo else 1.6) * passo)
    xs = [x_ini + (c + 0.5) * espaco for c in range(n_col)]
    x_linha0 = 0.4 * passo
    x_linha1 = largura - 0.4 * passo

    arr, tinta, cor_linha, escuro = _montar_fundo(rng, fundo, altura, largura)
    topo_cinza = int(arr[0, 0, 0])
    cor_fundo_nota = (
        (min(255, topo_cinza + 45),) * 3 if escuro else (max(0, topo_cinza - 35),) * 3
    )

    grade = _sortear_grade(rng, n_col)
    _tecnicas_isoladas(rng, grade)
    _tecnicas_pares(rng, grade, n_col)
    cores = _sortear_cores(rng, n_col, tinta, escuro)
    tamanho = max(6, round(passo * rng.uniform(0.55, 1.05) / DIGITO_ALTURA_EM))

    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    medidas = _medir_notas(
        rng, d, grade, xs, ys, cores, tamanho, list(fontes), largura, altura
    )

    if medidas and rng.random() < P_FUNDO_NOTA:  # fundo cinza atrás de uma nota
        x0, y0, x1, y1 = medidas[rng.choice(sorted(medidas))]["caixa"]
        m = round(0.2 * passo)
        d.rectangle([x0 - m, y0 - m, x1 + m, y1 + m], fill=cor_fundo_nota)

    buracos: list[list[tuple[float, float]]] = [[] for _ in range(6)]
    if corta:
        for (_, s), m in medidas.items():
            caixa = m["caixa"]
            buracos[s].append((caixa[0] - 2, caixa[2] + 2))
        _desenhar_cordas(
            d, ys, x_linha0, x_linha1, buracos, tracejada, passo, espessura, cor_linha
        )

    barras = [(x_ini, "simples")]
    for c in range(1, n_col):
        if rng.random() < P_BARLINE_INTERNA:
            tipo = "dupla" if rng.random() < P_BARLINE_DUPLA else "simples"
            barras.append((x_ini + c * espaco, tipo))
    barras.append((x_fim, "final"))
    barlines_x = [
        _desenhar_barra(d, x, tipo, ys, passo, espessura, cor_linha)
        for x, tipo in barras
    ]

    if rng.random() < P_TAB:  # rótulo TAB
        fonte = _carregar_fonte(
            rng.choice(fontes), max(6, round(0.9 * passo / DIGITO_ALTURA_EM))
        )
        for j, letra in enumerate("TAB"):
            px, py, _ = _posicionar(
                d, letra, 0.9 * passo, ys[j], fonte, largura, altura
            )
            d.text((px, py), letra, font=fonte, fill=cor_linha)
    if rng.random() < P_COMPASSO:  # número de compasso pequeno acima da corda 1
        fonte = _carregar_fonte(
            rng.choice(fontes), max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
        )
        numero = str(rng.randint(1, 9))
        px, py, _ = _posicionar(
            d, numero, x_ini + 0.3 * passo, ys[0] - 1.1 * passo, fonte, largura, altura
        )
        d.text((px, py), numero, font=fonte, fill=cor_linha)
    if rng.random() < P_ACORDE_NOME:  # nome de acorde acima do sistema
        fonte = _carregar_fonte(
            rng.choice(fontes), max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
        )
        nome = rng.choice(ACORDES)
        px, py, _ = _posicionar(
            d, nome, rng.choice(xs), ys[0] - 1.8 * passo, fonte, largura, altura
        )
        d.text((px, py), nome, font=fonte, fill=cor_linha)

    if not corta:
        _desenhar_notas(d, medidas)
        _desenhar_cordas(
            d,
            ys,
            x_linha0,
            x_linha1,
            [[] for _ in range(6)],
            tracejada,
            passo,
            espessura,
            cor_linha,
        )
    else:
        _desenhar_notas(d, medidas)

    _desenhar_tecnicas_pares(
        d, rng, grade, medidas, ys, passo, espessura, tinta, list(fontes)
    )

    if tem_ritmo:
        base_por_coluna: dict[int, int] = {}
        for (c, _), m in medidas.items():
            base_por_coluna[c] = max(base_por_coluna.get(c, 0), m["caixa"][3])
        _desenhar_ritmo(
            d, rng, passo, xs, ys, n_col, base_por_coluna, haste_sobe, tinta
        )

    arr = np.asarray(img).copy()
    if rng.random() < P_FAIXA:
        _desenhar_faixa(arr, rng, passo, xs, ys)

    img_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    img_bgr = _degradar(rng, img_bgr)

    notas = [
        {
            "corda": s + 1,
            "rotulo": grade[(c, s)]["rotulo"],
            "tecnica": grade[(c, s)]["tecnica"],
            "x": round(xs[c]),
            "caixa": medidas[(c, s)]["caixa"],
        }
        for (c, s) in sorted(grade)
    ]
    info = {
        "passo": float(passo),
        "linhas_y": ys,
        "barlines_x": barlines_x,
        "notas": notas,
    }
    return img_bgr, info


def _folha(
    sistemas: list[tuple[np.ndarray, dict]], com_rotulos: bool, colunas: int = 4
) -> np.ndarray:
    """Monta uma grade de sistemas; com `com_rotulos`, anota caixas e rótulos.

    Args:
        sistemas: pares (imagem, dict) de `gerar_sistema`.
        com_rotulos: se True, desenha a caixa de cada nota em verde e o rótulo em
            vermelho ao lado.
        colunas: número de colunas da grade.

    Returns:
        Imagem BGR uint8 com a grade.
    """
    margem = 10
    largura = max(img.shape[1] for img, _ in sistemas) + 2 * margem
    altura = max(img.shape[0] for img, _ in sistemas) + 2 * margem
    linhas = math.ceil(len(sistemas) / colunas)
    folha = np.full((linhas * altura, colunas * largura, 3), 255, np.uint8)
    for i, (img, info) in enumerate(sistemas):
        ox = (i % colunas) * largura + margem
        oy = (i // colunas) * altura + margem
        h, w = img.shape[:2]
        folha[oy : oy + h, ox : ox + w] = img
        if not com_rotulos:
            continue
        for nota in info["notas"]:
            x0, y0, x1, y1 = nota["caixa"]
            cv2.rectangle(
                folha,
                (ox + x0, oy + y0),
                (ox + x1, oy + y1),
                (0, 200, 0),
                1,
            )
            texto = nota["rotulo"]
            if nota["tecnica"] is not None:
                texto = f"{texto} {nota['tecnica']}"
            cv2.putText(
                folha,
                texto,
                (ox + x1 + 3, oy + y0 + 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )
    return folha


def _gravar(caminho: Path, img: np.ndarray) -> None:
    """Grava uma imagem, criando a pasta se preciso.

    Args:
        caminho: arquivo de destino (PNG).
        img: imagem BGR uint8.

    Raises:
        OSError: se o OpenCV não conseguir gravar o arquivo.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(caminho), img):
        raise OSError(f"não consegui gravar {caminho}")


def _parser() -> argparse.ArgumentParser:
    """Monta o parser da CLI.

    Returns:
        O parser com o subcomando `folha`.
    """
    parser = argparse.ArgumentParser(
        description="Gera sistemas sintéticos de tablatura (6 cordas)."
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    folha = sub.add_parser("folha", help="grava uma grade de sistemas")
    folha.add_argument("--saida", type=Path, required=True)
    folha.add_argument("--n", type=int, default=12)
    folha.add_argument("--semente", type=int, default=0)
    folha.add_argument("--fontes", choices=sorted(PRESETS_FONTES), default="padrao")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI.

    Grava `<saida>` (só a imagem) e `<saida>_rotulos` (com caixas e rótulos).

    Args:
        argv: argumentos (padrão: sys.argv).

    Returns:
        Código de saída (0 em caso de sucesso).
    """
    args = _parser().parse_args(argv)
    fontes = _resolver_fontes(PRESETS_FONTES[args.fontes][0])
    rng = random.Random(args.semente)
    sistemas = [gerar_sistema(rng, fontes) for _ in range(args.n)]
    saida: Path = args.saida
    _gravar(saida, _folha(sistemas, com_rotulos=False))
    _gravar(
        saida.with_name(f"{saida.stem}_rotulos{saida.suffix}"),
        _folha(sistemas, com_rotulos=True),
    )
    print(f"{len(sistemas)} sistemas gravados em {saida.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
