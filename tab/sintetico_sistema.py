"""Gerador sintético de SISTEMAS de tablatura (6 cordas), com rótulo por nota.

Diferença para `tab.sintetico.gerar_linha`: aquele desenha uma linha de algarismos.
Este desenha um sistema inteiro, com acordes empilhados (que se encostam na vertical),
técnicas entre notas da mesma corda, técnicas NA nota (bend, vibrato), marcações de
REGIÃO (let ring, P.M., trêmolo, rasgueado, arpejo) e distratores que NÃO são nota:
barlines, ritmo (com haste que sobe por dentro do sistema, e pausas no lugar de
algumas hastes), fundo cinza atrás de uma nota, faixa do marcador, número de compasso,
rótulo TAB e nome de acorde.

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
TECNICAS = (None, "h", "p", "/", "\\", "harm", "lig", "bend", "vib", "orn", "enfeite")

#: Tipos de item de "estrutura" (ritornelo, casa de volta, texto de navegação, fórmula).
ESTRUTURA_TIPOS = (
    "ritornelo_inicio",
    "ritornelo_fim",
    "volta_1",
    "volta_2",
    "texto_navegacao",
    "formula_compasso",
    "letras_gp",
    "diagrama_acorde",
    "marca_acima",
    "pausa_interna",
)

#: Fórmulas de compasso possíveis ("C" é o compasso comum).
FORMULAS = ("4/4", "3/4", "6/8", "2/4", "12/8", "C")

#: Marcações de região (cobrem várias notas ou cordas): let ring, P.M., trêmolo,
#: rasgueado e arpejo. O código aparece no campo "tecnica" de cada região.
REGIOES = ("let ring", "pm", "trem", "rasg", "arpejo")

#: Nomes de acorde desenhados acima do sistema (distrator sem rótulo).
ACORDES = ("Am7", "C", "G7", "Dm", "Em", "F#m7", "D7", "Bm7", "A", "Cmaj7")

#: Cores da faixa do marcador: as vozes do gerador e três cores vivas.
CORES_FAIXA = (*CORES_VOZ, (255, 220, 0), (255, 140, 0), (120, 255, 120))

#: Amarelo pálido da faixa do marcador (nota clara amarelada, como o eob #16/#18).
_AMARELO_PALIDO = (255, 240, 160)

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
#: Chance de uma nota vir entre parênteses `(n)`: nota opcional ou fantasma, atacada
#: (dono, 2026-10-18; rodada 0203, G7). Antes era técnica "lig" (sem ataque).
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
#: Chance de uma nota ter `bend` (seta curva para cima-direita).
P_BEND = 0.05
#: Dentro do bend, chance de a ponta ter o texto "full" ou "1/2".
P_BEND_TEXTO = 0.5
#: Chance de uma nota ter `vib` (linha ondulada à direita, na altura da corda).
P_VIB = 0.05
#: Chance de uma coluna de ritmo virar pausa (no lugar da haste).
P_PAUSA_RITMO = 0.2
#: Chance de o sistema ter "let ring" acima da corda 1 (linha tracejada).
P_LET_RING = 0.12
#: Chance de o sistema ter "P.M." acima da corda 1 (linha tracejada).
P_PM = 0.10
#: Dentro de let ring / P.M., chance de a linha terminar em gancho "|".
P_GANCHO = 0.4
#: Chance de o sistema ter barras de trêmolo sobre uma nota.
P_TREM = 0.15
#: Dentro do trêmolo, chance de ser "trem. pick" (com tracejado).
P_TREM_PICK = 0.4
#: Chance de o sistema ter um rasgueado: seta vertical reta, com cabeça cheia, sobre
#: 3 a 6 cordas.
P_RASG = 0.25
#: Chance de o sistema ter um arpejo estilo Guitar Pro: linha vertical grossa em
#: zigue-zague, com ponta de seta cheia, à esquerda de uma coluna de notas.
P_ARPEJO = 0.35
#: Chance de o sistema começar no estilo Guitar Pro ("T", "A", "B" e fórmula grandes).
P_GP_INICIO = 0.4
#: Chance de o sistema ter pausas DENTRO dele, sobre as cordas 2-4, perto de "x".
P_PAUSA_INTERNA = 0.25
#: Chance de o sistema ter um diagrama de acorde acima da corda 1 (às vezes invade).
P_DIAGRAMA = 0.15
#: Chance de o sistema ter "o", "*" ou "harm." em fonte serif acima da corda 1.
P_MARCA_ACIMA = 0.2
#: Chance de uma nota ser desenhada na fonte serif (o "1" de pé horizontal).
P_SERIF = 0.3
#: Dentro de nota serif, chance de a corda passar POR CIMA dela (sem buraco).
P_CORDA_SOBRE = 0.5
#: Dentro de nota serif com corda por cima, chance de a casa virar "1" ou "11".
P_CASA_1 = 0.6
#: Chance de a faixa do marcador ser amarela pálida.
P_FAIXA_AMARELA = 0.3
#: Chance de uma nota sem técnica (com coluna vizinha livre) ter enfeite "orn".
P_ORN = 0.04
#: Dado orn, chance de haver um mordente (zigue-zague) acima da nota.
P_MORDENTE = 0.4
#: Chance de uma coluna (a partir da segunda) ter ligadura de prolongamento (tie).
P_TIE = 0.05
#: Chance de uma nota sem técnica ser um slide sem nota de origem (entrada ou saída).
P_SLIDE_SOLTO = 0.04
#: Chance de um legato h/p ter a letra; o resto é só o arco.
P_LETRA_LEGATO = 0.6
#: Rodada 0203 (R4b): estilos de arco medidos nos erros do R4a.
#: G1: chance de o arco de h/p/tie ficar abaixo da corda.
P_ARCO_ABAIXO = 0.4
#: G3: chance de o arco partir do centro das notas (por cima ou por baixo do algarismo).
P_ARCO_CENTRO = 0.4
#: G2: chance de um par h/p ligar notas a 2-4 colunas, com a corda vazia no meio.
P_PAR_LONGO = 0.3
#: G4: chance de o sistema ter um mordente de três notas (a-b-a sob um arco só).
P_MORDENTE_TRES = 0.15
#: G5: chance de uma nota sem técnica ter o zigue-zague de mordente sozinho (atacada).
P_ZIGUE_SOZINHO = 0.03
#: G6: chance de o sistema ter colunas apertadas (algarismos quase encostados).
P_APERTADO = 0.2
#: Chance de um grupo de 2 ou mais colcheias ter viga dupla (semicolcheias).
P_VIGA_DUPLA = 0.3
#: Chance de uma barline virar ritornelo (barra dupla com dois pontos).
P_RITORNELO = 0.12
#: Chance de o sistema ter uma casa de volta "1." ou "2.".
P_VOLTA = 0.1
#: Chance de o sistema ter texto de navegação (D.S., D.C., Fine, Coda ou símbolo).
P_NAV = 0.1
#: Chance de o sistema ter fórmula de compasso logo depois do TAB.
P_FORMULA = 0.4
#: Chance de cada barline interna trazer uma mudança de fórmula.
P_FORMULA_MEIO = 0.08
#: Dentro das pausas internas, chance de a pausa ficar ENTRE duas cordas, no desenho
#: de duas cabeças com haste diagonal (a pausa "7" do canal Room 335). Não é nota.
P_PAUSA_ENTRE = 0.3
#: Chance de a fórmula de compasso (depois do TAB) sair cinza, como texto de partitura.
P_FORMULA_CINZA = 0.15
#: Chance de o rótulo TAB sair cinza (como no From This Place).
P_TAB_CINZA = 0.15

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
        "<n>" para harmônico, "(n)" para nota entre parênteses (opcional ou fantasma,
        sem técnica) e o rótulo nos demais casos.
    """
    if nota["tecnica"] == "harm":
        return f"<{nota['rotulo']}>"
    if nota.get("parenteses"):
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
            nota["parenteses"] = True


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
        destino_existente = grade.get((c, s))
        if destino_existente is not None and destino_existente["tecnica"] is not None:
            continue
        col_origem = c - 1
        if tipo in ("h", "p") and rng.random() < P_PAR_LONGO:  # G2: arco longo
            k = rng.randint(2, 4)
            meio = [(cc, s) for cc in range(c - k + 1, c)]
            if c - k >= 0 and all(
                grade[m]["tecnica"] is None and len(grade[m]) == 2
                for m in meio
                if m in grade
            ):  # a corda fica vazia entre as duas notas
                for m in meio:
                    grade.pop(m, None)
                col_origem = c - k
        for chave in ((col_origem, s), (c, s)):
            if chave not in grade:
                grade[chave] = {"rotulo": _sortear_rotulo(rng), "tecnica": None}
        origem, destino = grade[(col_origem, s)], grade[(c, s)]
        if "x" in (origem["rotulo"], destino["rotulo"]):
            continue
        if origem["tecnica"] is not None or destino["tecnica"] is not None:
            continue
        if "parenteses" in origem or "parenteses" in destino:
            continue
        destino["tecnica"] = tipo
        if col_origem != c - 1:
            destino["col_origem"] = col_origem


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
    d: ImageDraw.ImageDraw,
    grade: dict[tuple[int, int], dict],
    xs: list[float],
    ys: list[int],
    cores: list[tuple[int, int, int]],
    tamanho: int,
    largura: int,
    altura: int,
) -> dict[tuple[int, int], dict]:
    """Mede a posição e a caixa de cada nota, sem desenhar.

    Args:
        d: desenho usado para medir.
        grade: notas por (coluna, corda), com "fonte" já sorteada.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        cores: cor de cada coluna.
        tamanho: tamanho da fonte, em pixels.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Mapa (coluna, corda) -> {"texto", "fonte", "px", "py", "caixa", "cor"}.
    """
    medidas: dict[tuple[int, int], dict] = {}
    for (c, s), nota in sorted(grade.items()):
        texto = _texto_da_nota(nota)
        fonte = _carregar_fonte(nota["fonte"], tamanho)
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
        tipo: "simples", "dupla", "final", "ritornelo_fim" (fina e grossa, com os
            pontos à esquerda) ou "ritornelo_inicio" (grossa e fina, pontos à direita).
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
    if tipo == "ritornelo_inicio":
        grossa = max(2, round(0.3 * passo))
        d.line([(round(x), topo), (round(x), base)], fill=cor, width=grossa)
        xx = round(x + 0.4 * passo)
        d.line([(xx, topo), (xx, base)], fill=cor, width=fina)
        return round(x + 0.2 * passo)
    if tipo in ("final", "ritornelo_fim"):
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


def _pontos_arco(
    rng: random.Random,
    caixa_a: tuple[float, ...],
    caixa_b: tuple[float, ...],
    y: float,
    passo: float,
    marcas: list[str],
    centro: bool | None = None,
) -> list[tuple[int, int]]:
    """Pontos de um arco entre duas notas da mesma corda, com estilo sorteado (R4b).

    Lado (acima ou abaixo da corda, G1), ponta (na borda das caixas ou no centro das
    notas, passando por cima ou por baixo do algarismo, G3), afastamento da corda e altura
    da curva (G3).

    Args:
        rng: gerador aleatório.
        caixa_a: caixa da nota de origem.
        caixa_b: caixa da nota de destino.
        y: linha da corda.
        passo: passo do sistema.
        marcas: lista onde se registram as variantes desenhadas.
        centro: força a ponta no centro (True) ou na borda (False); None sorteia.

    Returns:
        11 pontos do arco.
    """
    abaixo = rng.random() < P_ARCO_ABAIXO
    if centro is None:
        centro = rng.random() < P_ARCO_CENTRO
    if centro:
        xa, xb = (caixa_a[0] + caixa_a[2]) / 2, (caixa_b[0] + caixa_b[2]) / 2
        base = rng.uniform(0.5, 0.75) * passo
    else:
        xa, xb = caixa_a[2] + 0.1 * passo, caixa_b[0] - 0.1 * passo
        base = rng.uniform(0.1, 0.6) * passo
    altura = rng.uniform(0.15, 0.7) * passo
    sinal = 1 if abaixo else -1
    if abaixo:
        marcas.append("arco_abaixo")
    if centro:
        marcas.append("arco_centro")
    return [
        (
            round(xa + (xb - xa) * i / 10),
            round(y + sinal * (base + altura * math.sin(math.pi * i / 10))),
        )
        for i in range(11)
    ]


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
    marcas: list[str],
) -> None:
    """Desenha a ligação de cada par de técnica (letra e arco, ou diagonal).

    O legato pode vir só com o arco (sem a letra); registra "legato_sem_letra".

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
        marcas: lista onde se registram as variantes desenhadas.
    """
    espessura_traco = max(1, espessura - 1)
    tamanho_letra = max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
    for (c, s), nota in sorted(grade.items()):
        tipo = nota["tecnica"]
        if tipo not in ("h", "p", "/", "\\") or "lado" in nota:
            continue
        origem = medidas[(nota.get("col_origem", c - 1), s)]["caixa"]
        destino = medidas[(c, s)]["caixa"]
        if "col_origem" in nota:
            marcas.append("arco_longo")
        xa = origem[2] + 0.1 * passo
        xb = destino[0] - 0.1 * passo
        y = ys[s]
        if tipo in ("h", "p"):
            xm = (xa + xb) / 2
            com_letra = rng.random() < P_LETRA_LEGATO
            if not com_letra or rng.random() < 0.5:  # arco de ligado
                pontos = _pontos_arco(rng, origem, destino, y, passo, marcas)
                d.line(pontos, fill=tinta, width=espessura_traco)
                if not com_letra:
                    marcas.append("legato_sem_letra")
            if com_letra:
                fonte = _carregar_fonte(rng.choice(fontes), tamanho_letra)
                px, py, _ = _posicionar(
                    d, tipo, xm, y - 1.1 * passo, fonte, 10**6, 10**6
                )
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
    marcas: list[str],
) -> None:
    """Desenha hastes, vigas (simples ou duplas), colcheias, semicolcheias e pausas.

    Com `sobe`, a haste vai da viga até o algarismo mais baixo da coluna (encostando
    nele), como no canal guitarous. Sem `sobe`, a haste desce da corda 6 até a viga.
    Uma coluna sorteada pode virar pausa em vez de haste. Nota isolada tem 1 bandeirola
    (colcheia) ou 2 (semicolcheia).

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
        marcas: lista onde se registram as variantes desenhadas.
    """
    viga_y = round(ys[5] + 2.6 * passo)
    espessura_haste = max(1, round(0.1 * passo))
    espessura_viga = max(2, round(0.25 * passo))
    colunas = [c for c in range(n_col) if rng.random() < 0.6]
    pausas = [c for c in colunas if rng.random() < P_PAUSA_RITMO]
    hastes = [c for c in colunas if c not in pausas]
    for c in pausas:
        _desenhar_pausa(d, rng, passo, round(xs[c]), ys, tinta, espessura_haste)
        marcas.append("pausa")
    for grupo in _agrupar_consecutivos(hastes, 3):
        for c in grupo:
            topo = ys[5] + 0.5 * passo
            if sobe and c in base_por_coluna:
                topo = base_por_coluna[c] + 1
            x = round(xs[c])
            d.line([(x, round(topo)), (x, viga_y)], fill=tinta, width=espessura_haste)
        xa, xb = round(xs[grupo[0]]), round(xs[grupo[-1]])
        if len(grupo) >= 2:
            d.line([(xa, viga_y), (xb, viga_y)], fill=tinta, width=espessura_viga)
            if rng.random() < P_VIGA_DUPLA:
                y2 = round(viga_y - 0.4 * passo)
                d.line([(xa, y2), (xb, y2)], fill=tinta, width=espessura_viga)
                marcas.append("viga_dupla")
            continue
        bandeirolas = rng.choice((1, 2))
        marcas.append("colcheia" if bandeirolas == 1 else "semicolcheia")
        for k in range(bandeirolas):
            yk = viga_y - k * 0.4 * passo
            d.line(
                [(xa, round(yk)), (round(xa + 0.5 * passo), round(yk - 0.5 * passo))],
                fill=tinta,
                width=espessura_haste,
            )


def _desenhar_faixa(
    arr: np.ndarray,
    rng: random.Random,
    passo: float,
    xs: list[float],
    ys: list[int],
    marcas: list[str],
) -> None:
    """Mistura sobre uma coluna uma faixa translúcida (ou um cursor fino) do marcador.

    Args:
        arr: imagem RGB uint8, alterada no lugar.
        rng: gerador aleatório.
        passo: passo do sistema.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        marcas: lista onde se registram as variantes desenhadas.
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
    if rng.random() < P_FAIXA_AMARELA:
        cor = np.array(_AMARELO_PALIDO, np.float32)
        marcas.append("faixa_amarela")
    else:
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


def _cordas_sobre_notas(
    d: ImageDraw.ImageDraw,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    ys: list[int],
    espessura: int,
    cor: tuple[int, int, int],
) -> None:
    """Desenha a corda POR CIMA de cada nota marcada com "sobre".

    Usado depois de desenhar as notas: a corda cruza o algarismo sem buraco.

    Args:
        d: desenho.
        grade: notas (as com "sobre" ganham a corda por cima).
        medidas: saída de `_medir_notas`.
        ys: linha de cada corda.
        espessura: espessura da corda.
        cor: cor da corda.
    """
    for (c, s), nota in sorted(grade.items()):
        if not nota.get("sobre"):
            continue
        x0, _, x1, _ = medidas[(c, s)]["caixa"]
        d.line([(x0 - 2, ys[s]), (x1 + 2, ys[s])], fill=cor, width=espessura)


def _desenhar_inicio_gp(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    passo: float,
    ys: list[int],
    formula: str,
    fontes: list[str],
    cor: tuple[int, int, int],
    largura: int,
    altura: int,
) -> list[dict]:
    """Desenha o início estilo Guitar Pro: "T", "A", "B" grandes e a fórmula grande.

    As letras são negrito sans, com cerca de 1,7 passo de altura, e ocupam as seis
    cordas (centros em 0, 2,5 e 5 passos da corda 1). A fórmula fica logo à direita,
    com algarismos de 2 passos de altura. Nada disso é nota.

    Args:
        d: desenho.
        rng: gerador aleatório (usado pela fórmula).
        passo: passo do sistema.
        ys: linha de cada corda.
        formula: fórmula de compasso, como "3/4", ou "C".
        fontes: caminhos de fontes em negrito sans (usa a primeira).
        cor: cor da tinta.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Dois itens de estrutura: "letras_gp" (caixa das três letras) e
        "formula_compasso" (com "texto").
    """
    tamanho = max(6, round(1.7 * passo / DIGITO_ALTURA_EM))
    fonte = _carregar_fonte(fontes[0], tamanho)
    caixas_letras = []
    for j, letra in enumerate("TAB"):
        px, py, caixa = _posicionar(
            d, letra, 1.0 * passo, ys[0] + 2.5 * j * passo, fonte, largura, altura
        )
        d.text((px, py), letra, font=fonte, fill=cor)
        caixas_letras.append(caixa)
    cx_formula = 3.5 * passo
    caixa_formula = _desenhar_compasso(
        d, rng, formula, cx_formula, passo, ys, fontes, 2.0, cor, largura, altura
    )
    return [
        {
            "tipo": "letras_gp",
            "x": round(passo),
            "caixa": _caixa_uniao(caixas_letras),
        },
        {
            "tipo": "formula_compasso",
            "x": round(cx_formula),
            "caixa": caixa_formula,
            "texto": formula,
        },
    ]


def _desenhar_pausa_em(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    passo: float,
    x: float,
    y: float,
    tinta: tuple[int, int, int],
    espessura_haste: int,
) -> str:
    """Desenha uma pausa de colcheia ("7" com ponto) ou de semínima, centrada em (x, y).

    Args:
        d: desenho.
        rng: gerador aleatório.
        passo: passo do sistema.
        x: centro horizontal da pausa.
        y: centro vertical da pausa (dentro do sistema, sobre as cordas).
        tinta: cor da pausa.
        espessura_haste: espessura do traço.

    Returns:
        "colcheia" ou "seminima", conforme o desenho.
    """
    if rng.random() < 0.5:
        raio = max(1, round(0.13 * passo))
        px, py = round(x - 0.25 * passo), round(y)
        d.ellipse([px - raio, py - raio, px + raio, py + raio], fill=tinta)
        topo = round(y - 0.45 * passo)
        d.line(
            [(round(x - 0.1 * passo), topo), (round(x + 0.35 * passo), topo)],
            fill=tinta,
            width=espessura_haste,
        )
        d.line(
            [
                (round(x + 0.35 * passo), topo),
                (round(x + 0.05 * passo), round(y + 0.6 * passo)),
            ],
            fill=tinta,
            width=espessura_haste,
        )
        return "colcheia"
    pontos = [
        (
            round(x + (0.25 if i % 2 else -0.25) * passo),
            round(y - 0.6 * passo + 0.3 * passo * i),
        )
        for i in range(5)
    ]
    d.line(pontos, fill=tinta, width=espessura_haste)
    return "seminima"


def _desenhar_pausa_entre_cordas(
    d: ImageDraw.ImageDraw,
    passo: float,
    x: float,
    y: float,
    tinta: tuple[int, int, int],
    espessura_haste: int,
) -> None:
    """Desenha a pausa de colcheia com duas cabeças e haste diagonal, entre cordas.

    Duas cabeças cheias à esquerda e uma haste grossa que sai de cima à direita e
    desce para a esquerda. É o desenho que o detector lia como nota 7.

    Args:
        d: desenho.
        passo: passo do sistema.
        x: centro horizontal da pausa.
        y: centro vertical da pausa (entre duas cordas).
        tinta: cor da pausa.
        espessura_haste: espessura base do traço (a haste usa o dobro).
    """
    # medidas dos recortes reais do Room 335 (passo ~87 px): da cabeça de cima à ponta
    # da haste ~1,8 passo; cabeças de ~0,35 passo, ligadas à haste por um gancho curto
    raio = max(1, round(0.17 * passo))
    topo = (round(x + 0.35 * passo), round(y - 0.6 * passo))
    base = (round(x - 0.1 * passo), round(y + 1.2 * passo))
    d.line([topo, base], fill=tinta, width=max(2, round(0.11 * passo)))
    for dy in (-0.45, 0.25):
        cx, cy = round(x - 0.15 * passo), round(y + dy * passo)
        d.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=tinta)
        frac = (cy + 0.1 * passo - topo[1]) / (base[1] - topo[1])
        hx = round(topo[0] + frac * (base[0] - topo[0]))
        d.line(
            [(cx, cy + raio // 2), (hx, round(cy + 0.1 * passo))],
            fill=tinta,
            width=max(1, espessura_haste),
        )


def _cor_cinza(rng: random.Random, escuro: bool) -> tuple[int, int, int]:
    """Cinza de texto de partitura: médio em fundo claro, claro em fundo escuro.

    Args:
        rng: gerador aleatório.
        escuro: se o fundo é escuro.

    Returns:
        Cor RGB cinza.
    """
    tom = rng.randint(150, 190) if escuro else rng.randint(110, 160)
    return (tom, tom, tom)


def _desenhar_pausas_internas(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    xs: list[float],
    ys: list[int],
    n_col: int,
    passo: float,
    espaco: float,
    tinta: tuple[int, int, int],
    marcas: list[str],
    largura: int,
    altura: int,
) -> list[dict]:
    """Desenha de 1 a 3 pausas DENTRO do sistema, sobre as cordas 2-4.

    As pausas ficam entre a coluna de uma nota "x" (abafada) e a seguinte; sem "x" no
    sistema, usam uma coluna qualquer. Uma pausa só é desenhada se ficar a 0,2 passo de
    qualquer nota.

    Args:
        d: desenho.
        rng: gerador aleatório.
        grade: notas por (coluna, corda).
        medidas: saída de `_medir_notas`.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        n_col: número de colunas.
        passo: passo do sistema.
        espaco: distância entre colunas.
        tinta: cor da pausa.
        marcas: lista onde se registram as variantes desenhadas.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Itens de estrutura {"tipo": "pausa_interna", "x", "caixa"} das pausas desenhadas.
    """
    colunas_x = sorted({c for (c, _), nota in grade.items() if nota["rotulo"] == "x"})
    alvo = colunas_x or list(range(n_col))
    espessura_haste = max(1, round(0.1 * passo))
    x0 = xs[rng.choice(alvo)] + 0.5 * espaco
    itens: list[dict] = []
    for k in range(rng.randint(1, 3)):
        corda = rng.randint(1, 3)
        entre = rng.random() < P_PAUSA_ENTRE
        y = (ys[corda - 1] + ys[corda]) / 2 if entre else ys[corda]
        x = x0 + k * 0.9 * passo
        caixa = _limitar(
            [
                round(x - 0.5 * passo),
                round(y - 0.7 * passo),
                round(x + 0.5 * passo),
                round(y + 0.7 * passo),
            ],
            largura,
            altura,
        )
        if not _livre_de_notas(caixa, medidas, passo):
            continue
        if entre:
            _desenhar_pausa_entre_cordas(d, passo, x, y, tinta, espessura_haste)
            marcas.append("pausa_entre_cordas")
        else:
            _desenhar_pausa_em(d, rng, passo, x, y, tinta, espessura_haste)
        marcas.append("pausa_interna")
        itens.append({"tipo": "pausa_interna", "x": round(x), "caixa": caixa})
    return itens


def _desenhar_diagrama(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    cx: float,
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    fontes: list[str],
    largura: int,
    altura: int,
) -> dict:
    """Desenha um diagrama de acorde (grade com bolinhas e números de dedo).

    A grade tem de 5 a 6 linhas verticais e de 4 a 5 horizontais. Acima da corda 1 ela
    cabe no sistema; em 40% dos casos a base desce e invade as cordas.

    Args:
        d: desenho.
        rng: gerador aleatório.
        cx: centro horizontal da grade.
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        fontes: caminhos das fontes.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Item de estrutura {"tipo": "diagrama_acorde", "x", "caixa"}.
    """
    nv = rng.randint(5, 6)
    nh = rng.randint(4, 5)
    larg = rng.uniform(1.3, 1.7) * passo
    alt = rng.uniform(1.5, 1.8) * passo
    base = ys[0] + 0.3 * passo if rng.random() < 0.4 else ys[0] - 0.5 * passo
    topo = base - alt
    x0 = cx - larg / 2
    espessura_traco = max(1, espessura - 1)
    colunas_v = [x0 + i * larg / (nv - 1) for i in range(nv)]
    linhas_h = [topo + j * alt / (nh - 1) for j in range(nh)]
    for xx in colunas_v:
        d.line(
            [(round(xx), round(topo)), (round(xx), round(base))],
            fill=tinta,
            width=espessura_traco,
        )
    for yy in linhas_h:
        d.line(
            [(round(x0), round(yy)), (round(x0 + larg), round(yy))],
            fill=tinta,
            width=espessura_traco,
        )
    raio = max(2, round(0.13 * passo))
    for _ in range(rng.randint(2, 4)):
        px = round(colunas_v[rng.randrange(nv)])
        j = rng.randrange(nh - 1)
        py = round((linhas_h[j] + linhas_h[j + 1]) / 2)
        d.ellipse([px - raio, py - raio, px + raio, py + raio], fill=tinta)
    tamanho = max(6, round(0.45 * passo / DIGITO_ALTURA_EM))
    fonte = _carregar_fonte(rng.choice(fontes), tamanho)
    for xx in colunas_v:
        if rng.random() < 0.5:
            numero = str(rng.randint(1, 4))
            px, py, _ = _posicionar(
                d, numero, xx, base + 0.35 * passo, fonte, largura, altura
            )
            d.text((px, py), numero, font=fonte, fill=tinta)
    caixa = _limitar(
        [
            round(x0) - 2,
            round(topo) - 2,
            round(x0 + larg) + 2,
            round(base + 0.6 * passo),
        ],
        largura,
        altura,
    )
    return {"tipo": "diagrama_acorde", "x": round(cx), "caixa": caixa}


def _desenhar_marca_acima(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    xs: list[float],
    ys: list[int],
    passo: float,
    tinta: tuple[int, int, int],
    fontes: list[str],
    largura: int,
    altura: int,
) -> dict:
    """Desenha "o", "*" ou "harm." em fonte serif, acima da corda 1.

    Args:
        d: desenho.
        rng: gerador aleatório.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        passo: passo do sistema.
        tinta: cor da tinta.
        fontes: caminhos das fontes (usa as serif).
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Item de estrutura {"tipo": "marca_acima", "x", "caixa", "texto"}.
    """
    texto = rng.choice(("o", "*", "harm."))
    serifs = [f for f in fontes if "Serif" in Path(f).name] or fontes
    fonte = _carregar_fonte(
        rng.choice(serifs), max(6, round(0.6 * passo / DIGITO_ALTURA_EM))
    )
    cx = rng.choice(xs)
    px, py, caixa = _posicionar(
        d, texto, cx, ys[0] - 1.0 * passo, fonte, largura, altura
    )
    d.text((px, py), texto, font=fonte, fill=tinta)
    return {"tipo": "marca_acima", "x": round(cx), "caixa": caixa, "texto": texto}


def _interceptam(a: list[int], b: list[int], margem: float) -> bool:
    """Diz se a caixa `a` cruza a caixa `b` ampliada em `margem` px de cada lado.

    Args:
        a: caixa [x0, y0, x1, y1] do distrator.
        b: caixa [x0, y0, x1, y1] de uma nota.
        margem: folga em px em volta de `b`.

    Returns:
        True se as caixas se cruzam.
    """
    return (
        a[0] < b[2] + margem
        and b[0] - margem < a[2]
        and a[1] < b[3] + margem
        and b[1] - margem < a[3]
    )


def _livre_de_notas(
    caixa: list[int],
    medidas: dict[tuple[int, int], dict],
    passo: float,
    folga: float = 0.2,
) -> bool:
    """Diz se um distrator pode ser desenhado: nenhuma nota a menos de `folga` passo.

    Args:
        caixa: caixa prevista do distrator.
        medidas: caixas das notas e dos enfeites (ver `gerar_sistema`).
        passo: passo do sistema.
        folga: folga mínima, em passos, entre a caixa e qualquer nota.

    Returns:
        True se a caixa fica longe de todas as notas.
    """
    return not any(
        _interceptam(caixa, m["caixa"], folga * passo) for m in medidas.values()
    )


def _ensaiar(
    desenhar: functools.partial, rng: random.Random, largura: int, altura: int
) -> object:
    """Roda `desenhar` numa tela descartável, com uma cópia do rng.

    Serve para medir a caixa de um distrator antes de desenhá-lo de verdade. O rng real
    não é gasto: a chamada de verdade sorteia exatamente a mesma sequência.

    Args:
        desenhar: chamada parcial que recebe (desenho, rng).
        rng: gerador aleatório real.
        largura: largura da tela descartável.
        altura: altura da tela descartável.

    Returns:
        O que `desenhar` devolveu.
    """
    copia = random.Random()
    copia.setstate(rng.getstate())
    return desenhar(ImageDraw.Draw(Image.new("RGB", (largura, altura))), copia)


def gerar_sistema(rng: random.Random, fontes: list[str]) -> tuple[np.ndarray, dict]:
    """Desenha um sistema de tablatura de 6 cordas e devolve a imagem e os rótulos.

    O espaçamento entre colunas é o maior entre o sorteado e o necessário para que as
    notas vizinhas não se encostem (ver `_xs_por_medida`).

    Args:
        rng: gerador aleatório; a mesma semente dá a mesma imagem e os mesmos rótulos.
        fontes: caminhos das fontes (com repetição = peso).

    Returns:
        Tupla (imagem BGR uint8, dict) com:
            "passo": passo do sistema, em px (float).
            "linhas_y": y de cada corda, da 1 (em cima) à 6, em px (6 ints).
            "barlines_x": x do centro de cada barline, em px.
            "notas": lista de {"corda" (1-6), "rotulo", "tecnica", "x" (centro),
            "caixa" ([x0, y0, x1, y1])}, na ordem coluna a coluna; inclui os
            enfeites ("tecnica": "enfeite") depois das notas.
            "regioes": lista de {"tecnica" (código de REGIOES), "cordas": [a, b],
            "caixa"}.
            "estrutura": lista de {"tipo" (ESTRUTURA_TIPOS), "x", "caixa"} e, nas
            fórmulas, no texto de navegação e na marca acima, "texto". Não são notas.
            "variantes": nomes (ordenados) das variantes de desenho presentes.

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
    if rng.random() < P_APERTADO:  # G6: algarismos quase encostados
        espaco = passo * rng.uniform(0.6, 1.1)
        marcas_apertado = True
    else:
        marcas_apertado = False
    tem_formula = rng.random() < P_FORMULA
    formula = rng.choice(FORMULAS) if tem_formula else ""
    gp = rng.random() < P_GP_INICIO
    if gp:  # início estilo Guitar Pro: letras e fórmula grandes (a fórmula é dele)
        tem_formula = True
        formula = rng.choice(FORMULAS)
    x_ini = (5.2 if gp else 4.6 if tem_formula else 2.6) * passo
    if marcas_apertado:  # a 1ª coluna fica onde ficaria com o espaço mínimo de antes
        x_ini += 0.5 * (1.2 * passo - espaco)
    ys = [round(2.4 * passo + i * passo) for i in range(6)]
    altura = round(ys[5] + (3.4 if tem_ritmo else 1.6) * passo)

    marcas: list[str] = ["colunas_apertadas"] if marcas_apertado else []
    grade = _sortear_grade(rng, n_col)
    _tecnicas_isoladas(rng, grade)
    _tecnicas_bend_vib(rng, grade)
    _sortear_orn(rng, grade)
    _sortear_mordente_tres(rng, grade, n_col)
    _sortear_ligaduras(rng, grade, n_col)
    _sortear_slides_soltos(rng, grade)
    _tecnicas_pares(rng, grade, n_col)
    _sortear_zigues(rng, grade)
    _sortear_serif(rng, grade)
    if any(n.get("sobre") for n in grade.values()):
        marcas.append("corda_sobre_serif")
    if any(n.get("sobre") and n["rotulo"] in ("1", "11") for n in grade.values()):
        marcas.append("serif_casa_1")
    tamanho = max(6, round(passo * rng.uniform(0.55, 1.05) / DIGITO_ALTURA_EM))
    _escolher_fontes(rng, grade, fontes)
    xs = _xs_por_medida(grade, n_col, passo, espaco, x_ini, tamanho)
    x_fim = xs[-1] + 0.5 * espaco
    largura = round(x_fim + 2.2 * passo)
    x_linha0 = 0.4 * passo
    x_linha1 = largura - 0.4 * passo

    arr, tinta, cor_linha, escuro = _montar_fundo(rng, fundo, altura, largura)
    topo_cinza = int(arr[0, 0, 0])
    cor_fundo_nota = (
        (min(255, topo_cinza + 45),) * 3 if escuro else (max(0, topo_cinza - 35),) * 3
    )
    cores = _sortear_cores(rng, n_col, tinta, escuro)

    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    medidas = _medir_notas(d, grade, xs, ys, cores, tamanho, largura, altura)

    if medidas and rng.random() < P_FUNDO_NOTA:  # fundo cinza atrás de uma nota
        x0, y0, x1, y1 = medidas[rng.choice(sorted(medidas))]["caixa"]
        m = round(0.2 * passo)
        d.rectangle([x0 - m, y0 - m, x1 + m, y1 + m], fill=cor_fundo_nota)

    buracos: list[list[tuple[float, float]]] = [[] for _ in range(6)]
    if corta:
        for (c, s), m in medidas.items():
            if grade[(c, s)].get("sobre"):  # a corda passa por cima dessa nota
                continue
            caixa = m["caixa"]
            buracos[s].append((caixa[0] - 2, caixa[2] + 2))
        _desenhar_cordas(
            d, ys, x_linha0, x_linha1, buracos, tracejada, passo, espessura, cor_linha
        )

    barras = [(x_ini, "simples")]
    for c in range(1, n_col):
        if rng.random() < P_BARLINE_INTERNA:
            tipo = "dupla" if rng.random() < P_BARLINE_DUPLA else "simples"
            barras.append(((xs[c - 1] + xs[c]) / 2, tipo))
    barras.append((x_fim, "final"))
    if rng.random() < P_RITORNELO:  # uma barline vira ritornelo (com dois pontos)
        idx = rng.randrange(len(barras) - 1)
        tipo_r = "ritornelo_inicio" if idx == 0 else "ritornelo_fim"
        barras[idx] = (barras[idx][0], tipo_r)

    estrutura: list[dict] = []
    barlines_x: list[int] = []
    for x, tipo in barras:
        barlines_x.append(_desenhar_barra(d, x, tipo, ys, passo, espessura, cor_linha))
        if tipo.startswith("ritornelo"):
            caixa = _desenhar_pontos_ritornelo(
                d, x, tipo, ys, passo, cor_linha, largura, altura
            )
            estrutura.append({"tipo": tipo, "x": round(x), "caixa": caixa})
    if rng.random() < P_TAB and not gp:  # rótulo TAB
        cor_tab = cor_linha
        if rng.random() < P_TAB_CINZA:
            cor_tab = _cor_cinza(rng, escuro)
            marcas.append("tab_cinza")
        fonte = _carregar_fonte(
            rng.choice(fontes), max(6, round(0.9 * passo / DIGITO_ALTURA_EM))
        )
        for j, letra in enumerate("TAB"):
            px, py, _ = _posicionar(
                d, letra, 0.9 * passo, ys[j], fonte, largura, altura
            )
            d.text((px, py), letra, font=fonte, fill=cor_tab)
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
    if tem_formula and not gp:  # fórmula de compasso logo depois do TAB
        cor_formula = cor_linha
        if rng.random() < P_FORMULA_CINZA:
            cor_formula = _cor_cinza(rng, escuro)
            marcas.append("formula_cinza")
        caixa = _desenhar_compasso(
            d,
            rng,
            formula,
            2.4 * passo,
            passo,
            ys,
            list(fontes),
            2.2,
            cor_formula,
            largura,
            altura,
        )
        estrutura.append(
            {
                "tipo": "formula_compasso",
                "x": round(2.4 * passo),
                "caixa": caixa,
                "texto": formula,
            }
        )
    if rng.random() < P_VOLTA:  # casa de volta sobre uma barline
        x_v = barras[rng.randrange(len(barras) - 1)][0]
        estrutura.append(
            _desenhar_volta(
                d,
                rng,
                x_v,
                ys,
                passo,
                espessura,
                cor_linha,
                list(fontes),
                largura,
                altura,
            )
        )
    if rng.random() < P_NAV:  # texto de navegação
        estrutura.append(
            _desenhar_navegacao(
                d,
                rng,
                xs,
                ys,
                passo,
                espessura,
                cor_linha,
                list(fontes),
                largura,
                altura,
            )
        )

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
        _cordas_sobre_notas(d, grade, medidas, ys, espessura, cor_linha)

    _desenhar_tecnicas_notas(
        d, rng, grade, medidas, ys, passo, espessura, tinta, list(fontes)
    )
    _desenhar_tecnicas_pares(
        d, rng, grade, medidas, ys, passo, espessura, tinta, list(fontes), marcas
    )
    _desenhar_ligaduras(d, rng, grade, medidas, ys, passo, espessura, tinta, marcas)
    _desenhar_mordentes_tres(
        d, rng, grade, medidas, ys, passo, espessura, tinta, marcas
    )
    _desenhar_zigues(d, grade, medidas, passo, espessura, tinta, marcas)
    _desenhar_slides_soltos(d, grade, medidas, ys, passo, espessura, tinta, marcas)
    enfeites = _desenhar_enfeites(
        d,
        rng,
        grade,
        medidas,
        ys,
        passo,
        espessura,
        tinta,
        tamanho,
        largura,
        altura,
        marcas,
    )
    regioes = _desenhar_regioes(
        d,
        rng,
        grade,
        medidas,
        xs,
        ys,
        n_col,
        passo,
        espaco,
        espessura,
        tinta,
        list(fontes),
        largura,
        altura,
    )
    alvos = {**medidas}  # notas e enfeites: nada pode cobrir isso
    for i, enf in enumerate(enfeites):
        alvos[(-1, i)] = {"caixa": enf["caixa"]}
    for x, _ in barras[1:-1]:  # mudança de fórmula depois de uma barline interna
        if rng.random() < P_FORMULA_MEIO:
            texto = rng.choice(FORMULAS)
            cx = x + 0.35 * passo
            previa = functools.partial(
                _desenhar_compasso,
                texto=texto,
                cx=cx,
                passo=passo,
                ys=ys,
                fontes=list(fontes),
                altura_passos=1.4,
                tinta=cor_linha,
                largura=largura,
                altura=altura,
            )
            if _livre_de_notas(_ensaiar(previa, rng, largura, altura), alvos, passo):
                caixa = previa(d, rng)
                estrutura.append(
                    {
                        "tipo": "formula_compasso",
                        "x": round(cx),
                        "caixa": caixa,
                        "texto": texto,
                    }
                )

    if gp:  # início estilo Guitar Pro (letras e fórmula grandes, não são nota)
        negrito = [f for f in fontes if "Sans-Bold" in Path(f).name] or list(fontes)
        previa = functools.partial(
            _desenhar_inicio_gp,
            passo=passo,
            ys=ys,
            formula=formula,
            fontes=negrito,
            cor=cor_linha,
            largura=largura,
            altura=altura,
        )
        itens = _ensaiar(previa, rng, largura, altura)
        if all(_livre_de_notas(it["caixa"], alvos, passo) for it in itens):
            estrutura.extend(previa(d, rng))
    if rng.random() < P_DIAGRAMA:  # diagrama de acorde, às vezes invadindo o sistema
        previa = functools.partial(
            _desenhar_diagrama,
            cx=rng.choice(xs),
            ys=ys,
            passo=passo,
            espessura=espessura,
            tinta=tinta,
            fontes=list(fontes),
            largura=largura,
            altura=altura,
        )
        if _livre_de_notas(
            _ensaiar(previa, rng, largura, altura)["caixa"], alvos, passo
        ):
            estrutura.append(previa(d, rng))
    if rng.random() < P_MARCA_ACIMA:  # "o", "*" ou "harm." acima da corda 1
        previa = functools.partial(
            _desenhar_marca_acima,
            xs=xs,
            ys=ys,
            passo=passo,
            tinta=tinta,
            fontes=list(fontes),
            largura=largura,
            altura=altura,
        )
        if _livre_de_notas(
            _ensaiar(previa, rng, largura, altura)["caixa"], medidas, passo
        ):
            estrutura.append(previa(d, rng))
    for funcao, marca, p in (
        (_marcar_rasgueado, "rasgueado_gp", P_RASG),
        (_marcar_arpejo, "arpejo_gp", P_ARPEJO),
    ):
        if rng.random() >= p:
            continue
        for c in rng.sample(range(n_col), n_col):  # a primeira coluna que couber
            previa = functools.partial(
                funcao,
                c=c,
                medidas=medidas,
                xs=xs,
                ys=ys,
                espaco=espaco,
                passo=passo,
                tinta=tinta,
                largura=largura,
                altura=altura,
            )
            if _livre_de_notas(
                _ensaiar(previa, rng, largura, altura)["caixa"], alvos, passo, 0.1
            ):
                regioes.append(previa(d, rng))
                marcas.append(marca)
                break
    if rng.random() < P_PAUSA_INTERNA:  # pausas dentro do sistema, perto de "x"
        estrutura.extend(
            _desenhar_pausas_internas(
                d,
                rng,
                grade,
                alvos,
                xs,
                ys,
                n_col,
                passo,
                espaco,
                tinta,
                marcas,
                largura,
                altura,
            )
        )

    if tem_ritmo:
        base_por_coluna: dict[int, int] = {}
        for (c, _), m in medidas.items():
            base_por_coluna[c] = max(base_por_coluna.get(c, 0), m["caixa"][3])
        _desenhar_ritmo(
            d, rng, passo, xs, ys, n_col, base_por_coluna, haste_sobe, tinta, marcas
        )

    arr = np.asarray(img).copy()
    if rng.random() < P_FAIXA:
        _desenhar_faixa(arr, rng, passo, xs, ys, marcas)

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
    notas.extend(enfeites)
    info = {
        "passo": float(passo),
        "linhas_y": ys,
        "barlines_x": barlines_x,
        "notas": notas,
        "regioes": regioes,
        "estrutura": estrutura,
        "variantes": sorted(set(marcas)),
    }
    return img_bgr, info


def _tecnicas_bend_vib(rng: random.Random, grade: dict[tuple[int, int], dict]) -> None:
    """Marca bend e vib, técnicas NA nota, em notas sem técnica que não são "x".

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar.
    """
    for nota in grade.values():
        if nota["rotulo"] == "x" or nota["tecnica"] is not None:
            continue
        r = rng.random()
        if r < P_BEND:
            nota["tecnica"] = "bend"
        elif r < P_BEND + P_VIB:
            nota["tecnica"] = "vib"


def _sortear_orn(rng: random.Random, grade: dict[tuple[int, int], dict]) -> None:
    """Marca `orn` em notas com a casa à esquerda livre (sem nota na mesma corda).

    O algarismo do enfeite e o mordente são sorteados aqui; o desenho é feito em
    `_desenhar_enfeites`.

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar.
    """
    for (c, s), nota in sorted(grade.items()):
        if c == 0 or nota["rotulo"] == "x" or nota["tecnica"] is not None:
            continue
        if (c - 1, s) in grade or rng.random() >= P_ORN:
            continue
        nota["tecnica"] = "orn"
        nota["enfeite"] = str(rng.randint(0, 12))
        nota["mordente"] = rng.random() < P_MORDENTE


def _sortear_mordente_tres(
    rng: random.Random, grade: dict[tuple[int, int], dict], n_col: int
) -> None:
    """G4 (R4b): mordente de três notas, ``a-b-a`` na mesma corda sob um arco só.

    A 2ª e a 3ª nota levam "orn" (sem ataque, como no gabarito do dono) e a marca
    ``mordente3`` ("meio" ou "fim"); não têm enfeite.

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar.
        n_col: número de colunas.
    """
    if n_col < 3 or rng.random() >= P_MORDENTE_TRES:
        return
    c = rng.randrange(n_col - 2)
    s = rng.randrange(6)
    chaves = [(c, s), (c + 1, s), (c + 2, s)]
    if any(
        k in grade and (grade[k]["tecnica"] is not None or "parenteses" in grade[k])
        for k in chaves
    ):
        return
    a = rng.randint(0, 10)
    b = a + rng.choice((1, 2))
    for k, rotulo in zip(chaves, (a, b, a), strict=True):
        grade[k] = {"rotulo": str(rotulo), "tecnica": None}
    grade[chaves[1]].update(tecnica="orn", mordente3="meio")
    grade[chaves[2]].update(tecnica="orn", mordente3="fim")


def _sortear_zigues(rng: random.Random, grade: dict[tuple[int, int], dict]) -> None:
    """G5 (R4b): zigue-zague de mordente sozinho sobre nota comum (atacada).

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar (ganham ``zigue``).
    """
    for nota in grade.values():
        if (
            nota["tecnica"] is None
            and nota["rotulo"] != "x"
            and rng.random() < P_ZIGUE_SOZINHO
        ):
            nota["zigue"] = True


def _zigue(
    d: ImageDraw.ImageDraw,
    mx: float,
    y0: float,
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    vertical: bool,
) -> None:
    """Desenha o zigue-zague de mordente acima de uma nota.

    Args:
        d: desenho.
        mx: centro da nota.
        y0: topo da caixa da nota.
        passo: passo do sistema.
        espessura: espessura do traço.
        tinta: cor da tinta.
        vertical: desenha o traço vertical do mordente.
    """
    topo = y0 - 0.35 * passo
    zig = [
        (round(mx - 0.25 * passo), round(topo)),
        (round(mx - 0.1 * passo), round(topo - 0.15 * passo)),
        (round(mx + 0.1 * passo), round(topo)),
        (round(mx + 0.25 * passo), round(topo - 0.15 * passo)),
    ]
    d.line(zig, fill=tinta, width=espessura)
    if vertical:
        d.line(
            [
                (round(mx), round(topo - 0.15 * passo)),
                (round(mx), round(topo - 0.45 * passo)),
            ],
            fill=tinta,
            width=espessura,
        )


def _desenhar_mordentes_tres(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    marcas: list[str],
) -> None:
    """Desenha o arco único de cada mordente de três notas (G4).

    Args:
        d: desenho.
        rng: gerador aleatório.
        grade: notas (a 3ª nota do mordente tem ``mordente3`` "fim").
        medidas: saída de `_medir_notas`.
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        marcas: lista onde se registram as variantes desenhadas.
    """
    for (c, s), nota in sorted(grade.items()):
        if nota.get("mordente3") != "fim":
            continue
        pontos = _pontos_arco(
            rng,
            medidas[(c - 2, s)]["caixa"],
            medidas[(c, s)]["caixa"],
            ys[s],
            passo,
            marcas,
            centro=True,
        )
        d.line(pontos, fill=tinta, width=max(1, espessura - 1))
        marcas.append("mordente_tres")


def _desenhar_zigues(
    d: ImageDraw.ImageDraw,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    marcas: list[str],
) -> None:
    """Desenha o zigue-zague sozinho das notas com ``zigue`` (G5).

    Args:
        d: desenho.
        grade: notas.
        medidas: saída de `_medir_notas`.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        marcas: lista onde se registram as variantes desenhadas.
    """
    for chave, nota in sorted(grade.items()):
        if not nota.get("zigue"):
            continue
        x0, y0, x1, _ = medidas[chave]["caixa"]
        _zigue(d, (x0 + x1) / 2, y0, passo, max(1, espessura - 1), tinta, False)
        marcas.append("zigue_sozinho")


def _sortear_ligaduras(
    rng: random.Random, grade: dict[tuple[int, int], dict], n_col: int
) -> None:
    """Cria ligaduras de prolongamento: duas notas na mesma corda e mesma casa.

    A segunda nota leva técnica "lig" e `tie=True` (desenho de arco, sem parênteses).

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar.
        n_col: número de colunas.
    """
    for c in range(1, n_col):
        if rng.random() >= P_TIE:
            continue
        s = rng.randrange(6)
        origem = grade.get((c - 1, s))
        destino = grade.get((c, s))
        if origem is None:
            origem = {"rotulo": str(rng.randint(0, 12)), "tecnica": None}
            grade[(c - 1, s)] = origem
        if destino is None:
            destino = {"rotulo": origem["rotulo"], "tecnica": None}
            grade[(c, s)] = destino
        if "x" in (origem["rotulo"], destino["rotulo"]):
            continue
        if origem["tecnica"] is not None or destino["tecnica"] is not None:
            continue
        destino["rotulo"] = origem["rotulo"]
        destino["tecnica"] = "lig"
        destino["tie"] = True


def _sortear_slides_soltos(
    rng: random.Random, grade: dict[tuple[int, int], dict]
) -> None:
    """Marca slides sem nota de origem: um traço curto antes ou depois da nota.

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar (ganham "lado": "antes" ou "depois").
    """
    for nota in grade.values():
        if nota["rotulo"] == "x" or nota["tecnica"] is not None:
            continue
        if rng.random() < P_SLIDE_SOLTO:
            nota["tecnica"] = rng.choice(("/", "\\"))
            nota["lado"] = rng.choice(("antes", "depois"))


def _desenhar_slides_soltos(
    d: ImageDraw.ImageDraw,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    marcas: list[str],
) -> None:
    """Desenha o traço curto de cada slide sem origem, antes ou depois da nota.

    Args:
        d: desenho.
        grade: notas (as com "lado" são slides soltos).
        medidas: saída de `_medir_notas`.
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        marcas: lista onde se registram as variantes desenhadas.
    """
    espessura_traco = max(1, espessura - 1)
    for (c, s), nota in sorted(grade.items()):
        if "lado" not in nota:
            continue
        x0, _, x1, _ = medidas[(c, s)]["caixa"]
        y = ys[s]
        if nota["lado"] == "antes":
            xa, xb = x0 - 0.45 * passo, x0 - 0.1 * passo
        else:
            xa, xb = x1 + 0.1 * passo, x1 + 0.45 * passo
        if nota["tecnica"] == "/":
            pa, pb = y + 0.25 * passo, y - 0.25 * passo
        else:
            pa, pb = y - 0.25 * passo, y + 0.25 * passo
        d.line(
            [(round(xa), round(pa)), (round(xb), round(pb))],
            fill=tinta,
            width=espessura_traco,
        )
        marcas.append("slide_solo")


def _desenhar_ligaduras(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    marcas: list[str],
) -> None:
    """Desenha o arco de cada ligadura de prolongamento (sem letra e sem parênteses).

    Args:
        d: desenho.
        rng: gerador aleatório (estilo do arco).
        grade: notas (as com `tie` são a segunda nota da ligadura).
        medidas: saída de `_medir_notas`.
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        marcas: lista onde se registram as variantes desenhadas.
    """
    espessura_traco = max(1, espessura - 1)
    for (c, s), nota in sorted(grade.items()):
        if not nota.get("tie"):
            continue
        pontos = _pontos_arco(
            rng,
            medidas[(c - 1, s)]["caixa"],
            medidas[(c, s)]["caixa"],
            ys[s],
            passo,
            marcas,
        )
        d.line(pontos, fill=tinta, width=espessura_traco)
        marcas.append("ligadura")


def _desenhar_enfeites(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    tamanho: int,
    largura: int,
    altura: int,
    marcas: list[str],
) -> list[dict]:
    """Desenha o enfeite (algarismo pequeno ligado à nota) e o mordente de cada `orn`.

    Args:
        d: desenho.
        rng: gerador aleatório.
        grade: notas (as com tecnica "orn" ganham enfeite, com "fonte_enfeite").
        medidas: saída de `_medir_notas`.
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        tamanho: tamanho da fonte da nota principal, em px.
        largura: largura da imagem.
        altura: altura da imagem.
        marcas: lista onde se registram as variantes desenhadas.

    Returns:
        Uma nota {"corda", "rotulo", "tecnica": "enfeite", "x", "caixa"} por enfeite.
    """
    espessura_traco = max(1, espessura - 1)
    tamanho_enfeite = max(6, round(0.5 * tamanho))
    enfeites: list[dict] = []
    for (c, s), nota in sorted(grade.items()):
        if nota["tecnica"] != "orn" or "enfeite" not in nota:
            continue
        x0, y0, x1, _ = medidas[(c, s)]["caixa"]
        y = ys[s]
        texto = nota["enfeite"]
        fonte = _carregar_fonte(nota["fonte_enfeite"], tamanho_enfeite)
        bb = d.textbbox((0, 0), texto, font=fonte)
        cx = x0 - 0.45 * passo - (bb[2] - bb[0]) / 2
        px, py, caixa = _posicionar(d, texto, cx, y, fonte, largura, altura)
        d.text((px, py), texto, font=fonte, fill=tinta)
        xa, xb = caixa[2] + 0.05 * passo, x0 - 0.05 * passo
        if rng.random() < 0.5:  # arco pequeno
            pontos = [
                (
                    round(xa + (xb - xa) * i / 10),
                    round(y - 0.3 * passo * math.sin(math.pi * i / 10)),
                )
                for i in range(11)
            ]
            d.line(pontos, fill=tinta, width=espessura_traco)
        else:  # traço curto, acima da linha da corda
            ya = round(y - 0.3 * passo)
            d.line(
                [(round(xa), ya), (round(xb), ya)], fill=tinta, width=espessura_traco
            )
        if nota["mordente"]:
            _zigue(
                d, (x0 + x1) / 2, y0, passo, espessura_traco, tinta, rng.random() < 0.5
            )
            marcas.append("mordente")
        marcas.append("enfeite")
        enfeites.append(
            {
                "corda": s + 1,
                "rotulo": texto,
                "tecnica": "enfeite",
                "x": round(cx),
                "caixa": caixa,
            }
        )
    return enfeites


def _quadratica(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    """Ponto de uma curva quadrática de Bézier no instante t.

    Args:
        p0: ponto inicial.
        p1: ponto de controle.
        p2: ponto final.
        t: instante em [0, 1].

    Returns:
        (x, y) da curva em t.
    """
    a = (1 - t) ** 2
    b = 2 * (1 - t) * t
    c = t**2
    return (
        a * p0[0] + b * p1[0] + c * p2[0],
        a * p0[1] + b * p1[1] + c * p2[1],
    )


def _desenhar_tecnicas_notas(
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
    """Desenha bend (seta curva para cima-direita) e vib (onda à direita da nota).

    O bend às vezes tem "full" ou "1/2" na ponta. O vib é uma linha ondulada, na altura
    da corda, logo à direita da nota.

    Args:
        d: desenho.
        rng: gerador aleatório.
        grade: notas (a técnica está na própria nota).
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
        if tipo not in ("bend", "vib"):
            continue
        x1 = medidas[(c, s)]["caixa"][2]
        y = ys[s]
        xa = x1 + 0.1 * passo
        if tipo == "vib":
            pontos = [
                (
                    round(xa + 0.8 * passo * i / 24),
                    round(y + 0.12 * passo * math.sin(2 * math.pi * 2 * i / 24)),
                )
                for i in range(25)
            ]
            d.line(pontos, fill=tinta, width=espessura_traco)
            continue
        p0 = (xa, y - 0.2 * passo)
        p1 = (xa + 0.6 * passo, y - 0.2 * passo)
        p2 = (x1 + 0.9 * passo, y - 0.9 * passo)
        pontos = [
            (round(px), round(py))
            for px, py in (_quadratica(p0, p1, p2, i / 10) for i in range(11))
        ]
        d.line(pontos, fill=tinta, width=espessura_traco)
        ax, ay = _quadratica(p0, p1, p2, 0.9)
        dx, dy = p2[0] - ax, p2[1] - ay
        norma = math.hypot(dx, dy) or 1.0
        ux, uy = dx / norma, dy / norma
        for angulo in (math.radians(150), math.radians(-150)):  # asas da ponta
            rx = ux * math.cos(angulo) - uy * math.sin(angulo)
            ry = ux * math.sin(angulo) + uy * math.cos(angulo)
            asa = (p2[0] + 0.25 * passo * rx, p2[1] + 0.25 * passo * ry)
            d.line(
                [(round(p2[0]), round(p2[1])), (round(asa[0]), round(asa[1]))],
                fill=tinta,
                width=espessura_traco,
            )
        if rng.random() < P_BEND_TEXTO:
            texto = rng.choice(("full", "1/2"))
            fonte = _carregar_fonte(rng.choice(fontes), tamanho_letra)
            px, py, _ = _posicionar(
                d, texto, p2[0], p2[1] - 0.45 * passo, fonte, 10**6, 10**6
            )
            d.text((px, py), texto, font=fonte, fill=tinta)


def _desenhar_pausa(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    passo: float,
    x: int,
    ys: list[int],
    tinta: tuple[int, int, int],
    espessura_haste: int,
) -> None:
    """Desenha uma pausa de ritmo abaixo da corda 6, no lugar de uma haste.

    Sorteia entre semínima (zigue-zague), colcheia (um "7" pequeno inclinado) e
    mínima (retângulo). Não tem rótulo.

    Args:
        d: desenho.
        rng: gerador aleatório.
        passo: passo do sistema.
        x: centro horizontal da pausa.
        ys: linha de cada corda.
        tinta: cor do ritmo.
        espessura_haste: espessura do traço.
    """
    topo = ys[5] + 0.6 * passo
    tipo = rng.choice(("seminima", "colcheia", "minima"))
    if tipo == "seminima":
        pontos = [
            (
                round(x + (0.25 if i % 2 else -0.25) * passo),
                round(topo + 0.3 * i * passo),
            )
            for i in range(5)
        ]
        d.line(pontos, fill=tinta, width=espessura_haste)
    elif tipo == "colcheia":
        d.line(
            [
                (round(x - 0.2 * passo), round(topo)),
                (round(x + 0.25 * passo), round(topo)),
            ],
            fill=tinta,
            width=espessura_haste,
        )
        d.line(
            [
                (round(x + 0.25 * passo), round(topo)),
                (round(x - 0.05 * passo), round(topo + 0.9 * passo)),
            ],
            fill=tinta,
            width=espessura_haste,
        )
    else:
        d.rectangle(
            [
                round(x - 0.25 * passo),
                round(topo),
                round(x + 0.25 * passo),
                round(topo + 0.3 * passo),
            ],
            outline=tinta,
            width=espessura_haste,
        )


def _caixa_uniao(caixas: list[list[int]]) -> list[int]:
    """Caixa que envolve todas as caixas dadas.

    Args:
        caixas: lista de [x0, y0, x1, y1].

    Returns:
        [x0, y0, x1, y1] da união.
    """
    return [
        min(c[0] for c in caixas),
        min(c[1] for c in caixas),
        max(c[2] for c in caixas),
        max(c[3] for c in caixas),
    ]


def _posicionar_esquerda(
    d: ImageDraw.ImageDraw,
    texto: str,
    x_esq: float,
    cy: float,
    fonte: ImageFont.FreeTypeFont,
    largura: int,
    altura: int,
) -> tuple[int, int, list[int]]:
    """Posiciona um texto com a borda esquerda da caixa em `x_esq`.

    Args:
        d: desenho onde o texto será medido.
        texto: texto a desenhar.
        x_esq: posição horizontal da borda esquerda da caixa.
        cy: centro vertical desejado.
        fonte: fonte usada.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        (px, py, caixa): origem para `d.text` e a caixa já recortada.
    """
    bb = d.textbbox((0, 0), texto, font=fonte)
    return _posicionar(
        d, texto, x_esq + (bb[2] - bb[0]) / 2, cy, fonte, largura, altura
    )


def _marcar_linha(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    tecnica: str,
    texto: str,
    passo: float,
    xs: list[float],
    espaco: float,
    ys: list[int],
    n_col: int,
    espessura: int,
    tinta: tuple[int, int, int],
    fontes: list[str],
    largura: int,
    altura: int,
) -> dict:
    """Desenha "let ring" ou "P.M." acima da corda 1, com linha tracejada e gancho.

    Args:
        d: desenho.
        rng: gerador aleatório.
        tecnica: código da região ("let ring" ou "pm").
        texto: texto desenhado ("let ring" ou "P.M.").
        passo: passo do sistema.
        xs: centro horizontal de cada coluna.
        espaco: distância entre colunas.
        ys: linha de cada corda.
        n_col: número de colunas.
        espessura: espessura da corda.
        tinta: cor da tinta.
        fontes: caminhos das fontes.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Região {"tecnica", "cordas": [1, 6], "caixa"}.
    """
    tamanho = max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
    espessura_traco = max(1, espessura - 1)
    c0 = rng.randrange(n_col - 1)
    k = rng.randint(2, min(6, n_col - c0))
    cy = ys[0] - 0.9 * passo
    fonte = _carregar_fonte(rng.choice(fontes), tamanho)
    px, py, caixa_texto = _posicionar_esquerda(
        d, texto, xs[c0] - 0.3 * passo, cy, fonte, largura, altura
    )
    d.text((px, py), texto, font=fonte, fill=tinta)
    xa = caixa_texto[2] + 0.2 * passo
    xb = min(largura - 1, max(xs[c0 + k - 1] + 0.3 * espaco, xa + passo))
    for a, b in _trechos(xa, xb, [], True, passo):
        d.line(
            [(round(a), round(cy)), (round(b), round(cy))],
            fill=tinta,
            width=espessura_traco,
        )
    caixas = [caixa_texto, [round(xa), round(cy) - 1, round(xb) + 1, round(cy) + 1]]
    if rng.random() < P_GANCHO:
        fim = round(cy + 0.5 * passo)
        d.line(
            [(round(xb), round(cy)), (round(xb), fim)],
            fill=tinta,
            width=espessura_traco,
        )
        caixas.append([round(xb), round(cy), round(xb) + 1, fim + 1])
    return {
        "tecnica": tecnica,
        "cordas": [1, 6],
        "caixa": _limitar(_caixa_uniao(caixas), largura, altura),
    }


def _marcar_trem(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    fontes: list[str],
    largura: int,
    altura: int,
) -> dict:
    """Desenha barras de trêmolo (///) sobre uma nota, às vezes com "trem. pick".

    Args:
        d: desenho.
        rng: gerador aleatório.
        grade: notas por (coluna, corda).
        medidas: saída de `_medir_notas`.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        fontes: caminhos das fontes.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Região {"tecnica": "trem", "cordas": [s, s], "caixa"}.
    """
    c, s = rng.choice(sorted(grade))
    x0, y0, x1, _ = medidas[(c, s)]["caixa"]
    cx = (x0 + x1) / 2
    base = y0 - 0.15 * passo
    espessura_traco = max(1, espessura - 1)
    n = rng.randint(2, 3)
    meia = (n - 1) / 2 * 0.3 * passo + 0.12 * passo
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * 0.3 * passo
        d.line(
            [
                (round(x - 0.12 * passo), round(base + 0.2 * passo)),
                (round(x + 0.12 * passo), round(base - 0.2 * passo)),
            ],
            fill=tinta,
            width=espessura_traco,
        )
    caixas = [
        [
            round(cx - meia),
            round(base - 0.2 * passo),
            round(cx + meia) + 1,
            round(base + 0.2 * passo) + 1,
        ]
    ]
    if rng.random() < P_TREM_PICK:
        tamanho = max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
        fonte = _carregar_fonte(rng.choice(fontes), tamanho)
        cy = base - 0.9 * passo
        px, py, caixa_t = _posicionar(d, "trem. pick", cx, cy, fonte, largura, altura)
        d.text((px, py), "trem. pick", font=fonte, fill=tinta)
        xa = caixa_t[2] + 0.2 * passo
        xb = xa + 1.5 * passo
        for a, b in _trechos(xa, xb, [], True, passo):
            d.line(
                [(round(a), round(cy)), (round(b), round(cy))],
                fill=tinta,
                width=espessura_traco,
            )
        caixas += [caixa_t, [round(xa), round(cy) - 1, round(xb) + 1, round(cy) + 1]]
    return {
        "tecnica": "trem",
        "cordas": [s + 1, s + 1],
        "caixa": _limitar(_caixa_uniao(caixas), largura, altura),
    }


def _borda_da_coluna(
    medidas: dict[tuple[int, int], dict],
    c: int,
    xs: list[float],
    espaco: float,
) -> float:
    """Borda esquerda da caixa mais à esquerda da coluna c (ou um vão padrão, sem notas).

    Args:
        medidas: caixas das notas, por (coluna, corda).
        c: índice da coluna.
        xs: centro horizontal de cada coluna.
        espaco: distância entre colunas.

    Returns:
        x (px) da borda esquerda.
    """
    bordas = [m["caixa"][0] for (cc, _), m in medidas.items() if cc == c]
    return min(bordas) if bordas else xs[c] - 0.5 * espaco


def _marcar_rasgueado(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    medidas: dict[tuple[int, int], dict],
    c: int,
    xs: list[float],
    ys: list[int],
    espaco: float,
    passo: float,
    tinta: tuple[int, int, int],
    largura: int,
    altura: int,
) -> dict:
    """Desenha um rasgueado: seta vertical reta, com cabeça triangular cheia.

    O traço fica à esquerda de uma coluna, com vão de 0,1 a 0,4 passo até a borda
    esquerda da caixa mais larga da coluna; a cabeça (meia largura de 0,3 passo) fica
    entre o traço e a coluna. Cobre de 3 a 6 cordas; a cabeça vai em cima ou embaixo.

    Args:
        d: desenho.
        rng: gerador aleatório.
        medidas: caixas das notas, por (coluna, corda).
        c: coluna à direita do traço.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        espaco: distância entre colunas.
        passo: passo do sistema.
        tinta: cor da tinta.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Região {"tecnica": "rasg", "cordas": [a, b], "caixa"}.
    """
    esquerda = _borda_da_coluna(medidas, c, xs, espaco)
    x = esquerda - rng.uniform(0.1, 0.4) * passo - 0.3 * passo
    a = rng.randint(0, 3)
    b = min(5, a + rng.randint(2, 5))
    topo, base = ys[a] - 0.4 * passo, ys[b] + 0.4 * passo
    para_cima = rng.random() < 0.5
    raiz = topo if para_cima else base
    ponta = topo - 0.5 * passo if para_cima else base + 0.5 * passo
    d.line(
        [(round(x), round(topo)), (round(x), round(base))],
        fill=tinta,
        width=rng.choice((1, 2)),
    )
    d.polygon(
        [
            (round(x), round(ponta)),
            (round(x - 0.3 * passo), round(raiz)),
            (round(x + 0.3 * passo), round(raiz)),
        ],
        fill=tinta,
    )
    caixa = _limitar(
        [
            round(x - 0.3 * passo),
            round(min(ponta, topo)),
            round(x + 0.3 * passo) + 1,
            round(max(ponta, base)) + 1,
        ],
        largura,
        altura,
    )
    return {"tecnica": "rasg", "cordas": [a + 1, b + 1], "caixa": caixa}


def _marcar_arpejo(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    medidas: dict[tuple[int, int], dict],
    c: int,
    xs: list[float],
    ys: list[int],
    espaco: float,
    passo: float,
    tinta: tuple[int, int, int],
    largura: int,
    altura: int,
) -> dict:
    """Desenha um arpejo estilo Guitar Pro: linha vertical grossa em zigue-zague.

    Fica à esquerda de uma coluna de notas: a borda direita do traço está a 0,1 a 0,4
    passo da borda esquerda da caixa mais larga da coluna. Tem de 0,3 a 0,45 passo de
    largura e cobre de 3 a 6 cordas. Em 40% dos casos com a última corda alvo, desce
    além da corda 6. A ponta de seta cheia vai em cima ou embaixo.

    Args:
        d: desenho.
        rng: gerador aleatório.
        medidas: caixas das notas, por (coluna, corda).
        c: coluna à direita do traço.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        espaco: distância entre colunas.
        passo: passo do sistema.
        tinta: cor da tinta.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Região {"tecnica": "arpejo", "cordas": [a, b], "caixa"}.
    """
    esquerda = _borda_da_coluna(medidas, c, xs, espaco)
    x_dir = esquerda - rng.uniform(0.1, 0.4) * passo
    meia = rng.uniform(0.3, 0.45) * passo / 2
    x_c = x_dir - meia
    a = rng.randint(0, 3)
    b = min(5, a + rng.randint(2, 5))
    topo, base = ys[a] - 0.4 * passo, ys[b] + 0.4 * passo
    if b == 5 and rng.random() < 0.4:
        base = ys[5] + rng.uniform(0.6, 1.1) * passo
    picos = max(3, round((base - topo) / (0.4 * passo)))
    pontos = [
        (
            round(x_c + (meia if k % 2 else -meia)),
            round(topo + (base - topo) * k / (2 * picos)),
        )
        for k in range(2 * picos + 1)
    ]
    d.line(pontos, fill=tinta, width=rng.choice((2, 3)), joint="curve")
    para_cima = rng.random() < 0.5
    raiz = topo if para_cima else base
    ponta = topo - 0.5 * passo if para_cima else base + 0.5 * passo
    d.polygon(
        [
            (round(x_c), round(ponta)),
            (round(x_c - 0.3 * passo), round(raiz)),
            (round(x_c + 0.3 * passo), round(raiz)),
        ],
        fill=tinta,
    )
    caixa = _limitar(
        [
            round(x_c - 0.3 * passo),
            round(min(ponta, topo)),
            round(x_c + 0.3 * passo) + 1,
            round(max(ponta, base)) + 1,
        ],
        largura,
        altura,
    )
    return {"tecnica": "arpejo", "cordas": [a + 1, b + 1], "caixa": caixa}


def _desenhar_regioes(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    grade: dict[tuple[int, int], dict],
    medidas: dict[tuple[int, int], dict],
    xs: list[float],
    ys: list[int],
    n_col: int,
    passo: float,
    espaco: float,
    espessura: int,
    tinta: tuple[int, int, int],
    fontes: list[str],
    largura: int,
    altura: int,
) -> list[dict]:
    """Desenha let ring, P.M. e trêmolo. Rasgueado e arpejo são tratados em
    `gerar_sistema`, que confere se cabem antes de desenhar.

    Args:
        d: desenho.
        rng: gerador aleatório.
        grade: notas por (coluna, corda).
        medidas: saída de `_medir_notas`.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        n_col: número de colunas.
        passo: passo do sistema.
        espaco: distância entre colunas.
        espessura: espessura da corda.
        tinta: cor da tinta.
        fontes: caminhos das fontes.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Lista de regiões {"tecnica", "cordas": [a, b], "caixa"}.
    """
    regioes: list[dict] = []
    if rng.random() < P_LET_RING:
        regioes.append(
            _marcar_linha(
                d,
                rng,
                "let ring",
                "let ring",
                passo,
                xs,
                espaco,
                ys,
                n_col,
                espessura,
                tinta,
                fontes,
                largura,
                altura,
            )
        )
    if rng.random() < P_PM:
        regioes.append(
            _marcar_linha(
                d,
                rng,
                "pm",
                "P.M.",
                passo,
                xs,
                espaco,
                ys,
                n_col,
                espessura,
                tinta,
                fontes,
                largura,
                altura,
            )
        )
    if rng.random() < P_TREM:
        regioes.append(
            _marcar_trem(
                d, rng, grade, medidas, passo, espessura, tinta, fontes, largura, altura
            )
        )
    return regioes


def _desenhar_pontos_ritornelo(
    d: ImageDraw.ImageDraw,
    x: float,
    tipo: str,
    ys: list[int],
    passo: float,
    tinta: tuple[int, int, int],
    largura: int,
    altura: int,
) -> list[int]:
    """Desenha os dois pontos de um ritornelo, entre as cordas 2-3 e 4-5.

    Os pontos ficam à direita da barline no início do ritornelo e à esquerda no fim.

    Args:
        d: desenho.
        x: posição horizontal da barline.
        tipo: "ritornelo_inicio" ou "ritornelo_fim".
        ys: linha de cada corda.
        passo: passo do sistema.
        tinta: cor dos pontos.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Caixa [x0, y0, x1, y1] que envolve os dois pontos.
    """
    raio = max(1, round(0.12 * passo))
    dx = 0.6 * passo if tipo == "ritornelo_inicio" else -0.6 * passo
    caixas = []
    for y in ((ys[1] + ys[2]) / 2, (ys[3] + ys[4]) / 2):
        cx, cy = round(x + dx), round(y)
        d.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=tinta)
        caixas.append([cx - raio, cy - raio, cx + raio + 1, cy + raio + 1])
    return _limitar(_caixa_uniao(caixas), largura, altura)


def _desenhar_volta(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    x: float,
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    fontes: list[str],
    largura: int,
    altura: int,
) -> dict:
    """Desenha uma casa de volta ("1." ou "2.") com colchete acima da corda 1.

    Args:
        d: desenho.
        rng: gerador aleatório.
        x: posição horizontal do início do colchete (uma barline).
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        fontes: caminhos das fontes.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Item de estrutura {"tipo": "volta_1" ou "volta_2", "x", "caixa"}.
    """
    numero = rng.choice(("1.", "2."))
    tipo = "volta_1" if numero == "1." else "volta_2"
    espessura_traco = max(1, espessura - 1)
    y = ys[0] - 1.0 * passo
    fim = x + 1.5 * passo
    d.line(
        [(round(x), round(y)), (round(fim), round(y))],
        fill=tinta,
        width=espessura_traco,
    )
    d.line(
        [(round(fim), round(y)), (round(fim), round(y + 0.4 * passo))],
        fill=tinta,
        width=espessura_traco,
    )
    tamanho = max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
    fonte = _carregar_fonte(rng.choice(fontes), tamanho)
    px, py, caixa_t = _posicionar_esquerda(
        d, numero, x + 0.2 * passo, y + 0.5 * passo, fonte, largura, altura
    )
    d.text((px, py), numero, font=fonte, fill=tinta)
    caixa_linha = [round(x), round(y) - 1, round(fim) + 1, round(y + 0.4 * passo) + 1]
    return {
        "tipo": tipo,
        "x": round(x),
        "caixa": _limitar(_caixa_uniao([caixa_linha, caixa_t]), largura, altura),
    }


def _desenhar_navegacao(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    xs: list[float],
    ys: list[int],
    passo: float,
    espessura: int,
    tinta: tuple[int, int, int],
    fontes: list[str],
    largura: int,
    altura: int,
) -> dict:
    """Desenha texto de navegação acima da corda 1: D.S., D.C., Fine, Coda ou símbolo.

    O símbolo de coda é um círculo com cruz; nesse caso o texto guardado é
    "coda_simbolo".

    Args:
        d: desenho.
        rng: gerador aleatório.
        xs: centro horizontal de cada coluna.
        ys: linha de cada corda.
        passo: passo do sistema.
        espessura: espessura da corda.
        tinta: cor da tinta.
        fontes: caminhos das fontes.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Item de estrutura {"tipo": "texto_navegacao", "x", "caixa", "texto"}.
    """
    cx = rng.choice(xs)
    cy = ys[0] - 1.45 * passo
    espessura_traco = max(1, espessura - 1)
    if rng.random() < 0.3:  # símbolo de coda: círculo com cruz
        raio = 0.3 * passo
        d.ellipse(
            [cx - raio, cy - raio, cx + raio, cy + raio],
            outline=tinta,
            width=espessura_traco,
        )
        d.line([(cx - raio, cy), (cx + raio, cy)], fill=tinta, width=espessura_traco)
        d.line([(cx, cy - raio), (cx, cy + raio)], fill=tinta, width=espessura_traco)
        texto = "coda_simbolo"
        caixa = _limitar(
            [
                round(cx - raio) - 1,
                round(cy - raio) - 1,
                round(cx + raio) + 2,
                round(cy + raio) + 2,
            ],
            largura,
            altura,
        )
    else:
        texto = rng.choice(("D.S.", "D.C.", "Fine", "Coda"))
        tamanho = max(6, round(0.5 * passo / DIGITO_ALTURA_EM))
        fonte = _carregar_fonte(rng.choice(fontes), tamanho)
        px, py, caixa = _posicionar(d, texto, cx, cy, fonte, largura, altura)
        d.text((px, py), texto, font=fonte, fill=tinta)
    return {"tipo": "texto_navegacao", "x": round(cx), "caixa": caixa, "texto": texto}


def _desenhar_compasso(
    d: ImageDraw.ImageDraw,
    rng: random.Random,
    texto: str,
    cx: float,
    passo: float,
    ys: list[int],
    fontes: list[str],
    altura_passos: float,
    tinta: tuple[int, int, int],
    largura: int,
    altura: int,
) -> list[int]:
    """Desenha uma fórmula de compasso empilhada (ou "C") ocupando as cordas.

    Args:
        d: desenho.
        rng: gerador aleatório.
        texto: fórmula, como "3/4", ou "C".
        cx: centro horizontal.
        passo: passo do sistema.
        ys: linha de cada corda.
        fontes: caminhos das fontes.
        altura_passos: altura de cada número, em passos.
        tinta: cor da tinta.
        largura: largura da imagem.
        altura: altura da imagem.

    Returns:
        Caixa [x0, y0, x1, y1] que envolve os números.
    """
    tamanho = max(6, round(altura_passos * passo / DIGITO_ALTURA_EM))
    if texto == "C":
        partes = [(texto, (ys[0] + ys[5]) / 2)]
    else:
        numerador, denominador = texto.split("/")
        partes = [
            (numerador, (ys[0] + ys[2]) / 2),
            (denominador, (ys[3] + ys[5]) / 2),
        ]
    caixas = []
    for trecho, cy in partes:
        fonte = _carregar_fonte(rng.choice(fontes), tamanho)
        px, py, caixa = _posicionar(d, trecho, cx, cy, fonte, largura, altura)
        d.text((px, py), trecho, font=fonte, fill=tinta)
        caixas.append(caixa)
    return _caixa_uniao(caixas)


def _meia_largura(texto: str, caminho: str, tamanho: int) -> float:
    """Meia largura, em px, da caixa de um texto desenhado com a fonte dada.

    Args:
        texto: texto medido.
        caminho: arquivo .ttf da fonte.
        tamanho: tamanho da fonte, em pixels.

    Returns:
        Metade da largura da caixa do texto.
    """
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    bb = d.textbbox((0, 0), texto, font=_carregar_fonte(caminho, tamanho))
    return (bb[2] - bb[0]) / 2


def _sortear_serif(rng: random.Random, grade: dict[tuple[int, int], dict]) -> None:
    """Marca notas na fonte serif, às vezes com a corda passando por cima delas.

    O "1" de pé horizontal com a corda por cima foi lido como "4" pelo detector. Nota
    serif com corda por cima pode virar casa "1" ou "11". Nota de ligadura não muda de
    casa, para a ligadura continuar ligando casas iguais.

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar (ganham "serif" e, às vezes, "sobre").
    """
    for c, s in sorted(grade):
        nota = grade[(c, s)]
        if nota["rotulo"] == "x" or rng.random() >= P_SERIF:
            continue
        nota["serif"] = True
        if rng.random() >= P_CORDA_SOBRE:
            continue
        nota["sobre"] = True
        proxima = grade.get((c + 1, s), {})
        em_ligadura = bool(nota.get("tie")) or bool(proxima.get("tie"))
        if not em_ligadura and rng.random() < P_CASA_1:
            nota["rotulo"] = rng.choice(("1", "11"))


def _escolher_fontes(
    rng: random.Random, grade: dict[tuple[int, int], dict], fontes: list[str]
) -> None:
    """Sorteia a fonte de cada nota (e do enfeite, quando há), antes de medir.

    Nota marcada "serif" usa uma fonte serif; as demais usam sans. O enfeite sorteia
    entre todas.

    Args:
        rng: gerador aleatório.
        grade: notas, alteradas no lugar (ganham "fonte" e, no orn, "fonte_enfeite").
        fontes: caminhos das fontes (com repetição = peso).
    """
    serifs = [f for f in fontes if "Serif" in Path(f).name]
    sans = [f for f in fontes if "Serif" not in Path(f).name] or fontes
    for chave in sorted(grade):
        nota = grade[chave]
        if nota.get("serif") and serifs:
            nota["fonte"] = rng.choice(serifs)
        else:
            nota["fonte"] = rng.choice(sans)
        if nota["tecnica"] == "orn" and "enfeite" in nota:
            nota["fonte_enfeite"] = rng.choice(fontes)


def _xs_por_medida(
    grade: dict[tuple[int, int], dict],
    n_col: int,
    passo: float,
    espaco: float,
    x_ini: float,
    tamanho: int,
) -> list[float]:
    """Centro de cada coluna, com vão suficiente entre colunas vizinhas.

    Cada vão entre as colunas c e c+1 é o maior entre `espaco` e o necessário: entre
    as caixas de quaisquer duas notas dessas colunas sobra pelo menos 0,35 passo (mais
    1 px de folga para arredondamento), e o enfeite de uma nota da coluna c+1 fica a
    0,45 passo da nota principal e também respeita essa folga.

    Args:
        grade: notas com "fonte" (e "fonte_enfeite" no orn), já sorteadas.
        n_col: número de colunas.
        passo: passo do sistema.
        espaco: espaçamento sorteado (mínimo entre colunas).
        x_ini: início horizontal das colunas (primeira barline).
        tamanho: tamanho da fonte das notas, em pixels.

    Returns:
        Centro horizontal de cada coluna, em px.
    """
    tamanho_enfeite = max(6, round(0.5 * tamanho))
    folga = 0.35 * passo + 2
    por_coluna: dict[int, list[tuple[float, dict]]] = {}
    for (c, _), nota in sorted(grade.items()):
        meia = _meia_largura(_texto_da_nota(nota), nota["fonte"], tamanho)
        por_coluna.setdefault(c, []).append((meia, nota))
    xs: list[float] = []
    cursor = x_ini + 0.5 * espaco
    for c in range(n_col):
        xs.append(cursor)
        necessario = espaco
        for ha, _ in por_coluna.get(c, []):
            for hb, nota_b in por_coluna.get(c + 1, []):
                necessario = max(necessario, ha + hb + folga)
                if nota_b["tecnica"] == "orn" and "enfeite" in nota_b:
                    he = _meia_largura(
                        nota_b["enfeite"], nota_b["fonte_enfeite"], tamanho_enfeite
                    )
                    necessario = max(
                        necessario, ha + hb + 0.45 * passo + 2 * he + folga
                    )
        cursor += necessario
    return xs


def _folha(
    sistemas: list[tuple[np.ndarray, dict]], com_rotulos: bool, colunas: int = 4
) -> np.ndarray:
    """Monta uma grade de sistemas; com `com_rotulos`, anota caixas e rótulos.

    Com `com_rotulos`: notas em verde (rótulo em vermelho), regiões em azul e
    estrutura (ritornelos, voltas, fórmulas, navegação) em laranja.

    Args:
        sistemas: pares (imagem, dict) de `gerar_sistema`.
        com_rotulos: se True, desenha as caixas e os rótulos.
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
        for regiao in info["regioes"]:
            x0, y0, x1, y1 = regiao["caixa"]
            cv2.rectangle(folha, (ox + x0, oy + y0), (ox + x1, oy + y1), (255, 0, 0), 1)
            cv2.putText(
                folha,
                regiao["tecnica"],
                (ox + x0, oy + y1 + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (255, 0, 0),
                1,
                cv2.LINE_AA,
            )
        for item in info["estrutura"]:
            x0, y0, x1, y1 = item["caixa"]
            cor = (0, 140, 255)
            cv2.rectangle(folha, (ox + x0, oy + y0), (ox + x1, oy + y1), cor, 1)
            cv2.putText(
                folha,
                item["tipo"],
                (ox + x0, oy + y1 + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                cor,
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
