"""Onde está o painel de tablatura no quadro — uma implementação só.

Havia **três** cópias desta escolha (`inventario.analisar_quadro`,
`transcrever.achar_painel`, `varredura.medir_quadro`) e as três erravam igual: ordenavam
por `(glifos_centrados, n_glifos)`.

Medido nesta noite num quadro real do `sky guitar` (t=88 s), com as caixas desenhadas no
quadro para conferir:

- a tablatura de verdade está na faixa `meio`: 6 linhas, passo 29,6, 36 glifos,
  uniformidade de fundo **0,888**;
- a faixa `base` é o **braço do violão** mais o corpo e a mão: 6 "linhas" (as cordas),
  39 "glifos" (trastes e cruzamentos), 34 "centrados" — e **ganhava** no critério antigo
  por ter mais glifos centrados. Uniformidade **0,842**.

O portão que separa os dois é a **uniformidade do fundo**, que já tinha sido medida nas
rodadas 42–45 e nunca havia entrado no código. Aqui ela entra como **primeiro critério**,
sem limiar fixo: entre candidatos com 6 linhas e glifos, ganha o de fundo mais liso.

Uso:
    from .painel import escolher
    c = escolher(frame)
    if c is not None:
        ...  # c.roi, c.grade, c.uniformidade, c.score
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import cv2
import numpy as np

from .tabseg import (
    Grade,
    _segmentar_de_mascara,
    _uniao_mascaras,
    delimitar_tokens,
    extensao_das_linhas,
    mascaras_candidatas,
    picos_de_linha,
    segmentar,
)

#: Faixas verticais onde o painel costuma estar (a posição varia por vídeo).
FAIXAS: list[tuple[str, int, int]] = [
    ("topo", 0, 400),
    ("meio", 300, 750),
    ("base", 620, 1080),
]

#: Mínimo de glifos para uma faixa ser considerada painel (evita região vazia).
MIN_GLIFOS = 5

#: Faixa de passo (distância entre cordas) medida no acervo: 14-45 px. Fora dela
#: não é tablatura — medido: um grupo com passo 7,6 px era painel falso e um com
#: 59,2 px era nome de acorde em texto (`violaodecria`).
PASSO_MINIMO_PX = 14.0
PASSO_MAXIMO_PX = 55.0


@dataclass
class Candidato:
    """Uma faixa candidata a painel, com o que foi medido nela."""

    nome: str
    y0: int
    y1: int
    roi: np.ndarray
    grade: Grade
    uniformidade: float
    score: tuple[float, int]
    #: Deslocamento em x do recorte ``roi`` no QUADRO (``x_quadro = x0 + x_roi``).
    x0: int = 0

    @property
    def passo(self) -> float:
        """Passo entre cordas, em px."""
        return float(self.grade.passo)


def uniformidade(roi: np.ndarray, k: int = 15, tol: int = 12) -> float:
    """Fração de pixels perto da mediana local — o fundo é liso?

    Papel e painel de cor sólida deixam a maior parte dos pixels perto da mediana
    local; madeira, sombra e brilho do braço não deixam.

    Args:
        roi: recorte (BGR ou cinza).
        k: tamanho do kernel da mediana (ímpar).
        tol: tolerância em níveis de cinza.

    Returns:
        Fração entre 0 e 1; quanto maior, mais liso o fundo.
    """
    cinza = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    if cinza.size == 0:
        return 0.0
    mediana = cv2.medianBlur(cinza, k)
    diferenca = np.abs(cinza.astype(np.int16) - mediana.astype(np.int16))
    return float((diferenca <= tol).mean())


def papel_branco(roi: np.ndarray, limiar: int = 200) -> float:
    """Fração de pixels de papel (cinza acima do limiar) no recorte.

    Medido na rodada 0007: a faixa da TAB sobre papel tem muito branco e a faixa do braço
    do violão quase nenhum. Usado para ordenar a reserva (C1).

    Args:
        roi: recorte (BGR ou cinza).
        limiar: nível de cinza acima do qual o pixel conta como papel.

    Returns:
        Fração entre 0 e 1 (0 se o recorte estiver vazio).
    """
    cinza = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    if cinza.size == 0:
        return 0.0
    return float((cinza > limiar).mean())


def candidatos(frame: np.ndarray, min_glifos: int = MIN_GLIFOS) -> list[Candidato]:
    """Todas as faixas com 6 cordas, medida a uniformidade do fundo de cada uma.

    Args:
        frame: quadro inteiro.
        min_glifos: mínimo de glifos para aceitar a faixa.

    Returns:
        Lista de candidatos, sem ordenar.
    """
    achados: list[Candidato] = []
    for nome, y0, y1 in FAIXAS:
        y1 = min(y1, frame.shape[0])
        if y1 - y0 < 60:
            continue
        roi = frame[y0:y1, :]
        try:
            g = segmentar(roi)
        except Exception:  # nunca derrubar a varredura por uma faixa ruim
            continue
        if len(g.linhas_y) != 6 or len(g.glifos) < min_glifos:
            continue
        u = uniformidade(roi)
        achados.append(
            Candidato(
                nome=nome,
                y0=y0,
                y1=y1,
                roi=roi,
                grade=g,
                uniformidade=u,
                score=(round(u, 3), g.glifos_centrados),
            )
        )
    return achados


#: Espessura, em px, a partir da qual uma linha de um grupo é tinta grossa e não corda.
#: Medido nos 63 quadros conferidos dos ouros (`data/saida/haiku_gym/espessura_pares.py`):
#: as cordas têm 2 a 5 px; a barra preta de borda que entrou no grupo ERRADO do
#: Gymnopédie (tela 10, t=136,5 s, linha y=1072) tem 10 px. Com 6 px de piso, nenhuma
#: corda medida passou para o lado de "grossa".
ESPESSURA_CORDA_MAXIMA = 6


def espessura_da_linha(cinza: np.ndarray, y: int, x0: int, x1: int) -> int:
    """Altura, em px, da faixa escura contígua em torno da linha ``y``.

    A escuridão de cada linha de pixels é a média em x (``x0`` a ``x1``) da tinta; a faixa
    vai até onde a escuridão cai abaixo da metade do pico, com no máximo 12 px para cada
    lado.

    Args:
        cinza: recorte em cinza (uint8).
        y: linha do centro da corda, relativa ao recorte.
        x0: início da extensão x onde se mede.
        x1: fim da extensão x (exclusivo).

    Returns:
        Número de linhas de pixels da faixa (0 se a linha não tiver tinta).
    """
    perfil = 255.0 - cinza[:, x0:x1].astype(np.float32).mean(axis=1)
    pico = float(perfil[max(0, y - 2) : y + 3].max())
    if pico <= 0:
        return 0
    corte = 0.5 * pico
    topo = base = y
    while topo - 1 >= 0 and perfil[topo - 1] >= corte and y - topo < 12:
        topo -= 1
    while base + 1 < len(perfil) and perfil[base + 1] >= corte and base - y < 12:
        base += 1
    return base - topo + 1


def linhas_grossas(frame: np.ndarray, y0: int, y1: int, grupo: list[int]) -> bool:
    """O grupo de 6 linhas tem uma linha que é tinta grossa, e não corda?

    A espessura é medida só na extensão x das próprias linhas (``extensao_das_linhas``),
    não na largura do quadro: a barra de borda do vídeo ao lado atravessa o quadro inteiro.
    É grossa a linha com pelo menos ``ESPESSURA_CORDA_MAXIMA`` px e pelo menos o dobro da
    mediana do grupo.

    Args:
        frame: quadro inteiro (BGR).
        y0: topo da faixa do grupo no quadro.
        y1: base da faixa do grupo no quadro.
        grupo: y das 6 linhas, no quadro.

    Returns:
        True se alguma linha do grupo for grossa.
    """
    roi = frame[y0:y1, :]
    cinza = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    cordas = [y - y0 for y in grupo]
    x0, x1 = extensao_das_linhas(roi, cordas)
    if x1 - x0 < 10:
        x0, x1 = 0, roi.shape[1]
    espessuras = [espessura_da_linha(cinza, c, x0, x1) for c in cordas]
    maior = max(espessuras)
    return maior >= ESPESSURA_CORDA_MAXIMA and maior >= 2 * float(np.median(espessuras))


def descartar_grossas(
    frame: np.ndarray, faixas: list[tuple[float, int, int, list[int]]]
) -> list[tuple[float, int, int, list[int]]]:
    """Tira o grupo grosso quando um vizinho de 5 linhas comuns é limpo.

    Medido no Gymnopédie (tela 10, t=136,5 s): os grupos ``[899..1043]`` (6 cordas, 3 px
    cada) e ``[928..1072]`` (5 das mesmas cordas mais a barra preta de 10 px) passam na
    regularidade e na faixa de passo, e o errado ganhava por uniformidade (0,827 contra
    0,820), porque o recorte dele inclui a barra. Um grupo grosso só sai quando existe
    um grupo limpo com 5 das suas 6 linhas: se todos forem grossos (texto, bloco), nada
    muda.

    Args:
        frame: quadro inteiro (BGR).
        faixas: ``(passo, y0, y1, grupo)`` de cada grupo regular.

    Returns:
        As faixas sem os grupos grossos que têm um vizinho limpo.
    """
    grossas = [linhas_grossas(frame, y0, y1, g) for _p, y0, y1, g in faixas]
    limpas = [
        set(f[3]) for f, grossa in zip(faixas, grossas, strict=True) if not grossa
    ]
    return [
        f
        for f, grossa in zip(faixas, grossas, strict=True)
        if not grossa or not any(len(set(f[3]) & limpa) >= 5 for limpa in limpas)
    ]


def candidatos_quadro(
    frame: np.ndarray,
    min_glifos: int = MIN_GLIFOS,
    passo_min: float = PASSO_MINIMO_PX,
    passo_max: float = PASSO_MAXIMO_PX,
    tolerancia: float = 1.6,
    max_candidatos: int = 8,
) -> list[Candidato]:
    """Procura o painel no **quadro inteiro**: a faixa é resultado, não entrada.

    As três faixas fixas (`FAIXAS`) **cortam o painel**. Medido no `sky guitar`
    (`(henze) nocturno`, t=228 s): a partitura ocupa o `topo` inteiro e a tablatura começa
    em `y≈342` e atravessa a fronteira `topo`/`meio` — **1 linha em cima, 5 embaixo**, e
    nenhuma faixa contém as 6. Foi isso que fez 61 % do lido virar bolinha de nota
    (decisão 0007).

    Aqui se acha o grupo de 6 linhas **igualmente espaçadas** em qualquer altura, com o
    passo na faixa medida no acervo (14–45 px), e só então se recorta.

    Args:
        frame: quadro inteiro.
        min_glifos: mínimo de glifos para aceitar.
        passo_min: passo mínimo aceitável, em px.
        passo_max: passo máximo aceitável, em px.
        tolerancia: razão máxima entre a maior e a menor lacuna do grupo de 6.
        max_candidatos: quantos candidatos avaliar com `segmentar` (corta custo).

    Returns:
        Candidatos, sem ordenar e sem repetição de faixa.
    """
    # Picos de linha somados por TODAS as máscaras da cascata do `segmentar` (Otsu global
    # e contraste local), com dois limiares de fração de tinta por máscara. Cada um destes
    # consertos foi medido numa falha real:
    #   - Otsu GLOBAL perde linha fina em quadro de iluminação forte: medido no
    #     `shin izumi` (que TEM tablatura, conferida na imagem), 3 de 4 vídeos não davam
    #     NENHUM grupo de 6 linhas, enquanto o `segmentar` (contraste local) achava;
    #   - um limiar só de 30 % perde a tablatura DENSA: medido no `sky guitar` (henze,
    #     frac 0,8), 48 glifos interrompem a linha e ela cai para ~15 % de tinta;
    #   - picos a menos de 3 px da borda são moldura (regra do `picos_de_linha`).
    picos: list[int] = []
    for _nome, mascara in mascaras_candidatas(frame):
        for fracao in (0.30, 0.15):
            for _v, y in picos_de_linha(mascara, fracao_min=fracao):
                y = int(y)
                if not picos or all(abs(y - p) > 2 for p in picos):
                    picos.append(y)
    picos.sort()
    if len(picos) < 6:
        return []
    # 1) grupos de 6 linhas regulares — só geometria, sem custo de segmentação
    faixas: list[tuple[float, int, int, list[int]]] = []
    for i in range(len(picos) - 5):
        grupo = picos[i : i + 6]
        passo = float(np.median([b - a for a, b in itertools.pairwise(grupo)]))
        if not (passo_min <= passo <= passo_max):
            continue
        if not espacamento_regular(grupo, tolerancia=tolerancia):
            continue
        margem = round(passo)  # round() de float já devolve int (regra 8)
        y0 = max(0, grupo[0] - margem)
        y1 = min(frame.shape[0], grupo[-1] + margem)
        if y1 - y0 < 60:
            continue
        faixas.append((passo, y0, y1, grupo))
    # 1b) grupo com uma linha GROSSA (barra de borda, bloco escuro) não é cordas
    faixas = descartar_grossas(frame, faixas)
    # 2) uniformidade do fundo é barata (medida: 38 ms) e ordena quem merece segmentação
    ordenadas: list[tuple[float, int, int]] = []
    vistos: list[int] = []
    for passo, y0, y1, _grupo in faixas:
        if any(abs(y0 - v) < passo for v in vistos):
            continue
        vistos.append(y0)
        ordenadas.append((uniformidade(frame[y0:y1, :]), y0, y1))
    ordenadas.sort(reverse=True)
    # 3) só os melhores pagam `segmentar` (medido: 52-758 ms por faixa)
    achados: list[Candidato] = []
    for _uniform, y0, y1 in ordenadas[:max_candidatos]:
        roi = frame[y0:y1, :]
        try:
            g = segmentar(roi)
        except Exception:  # nunca derrubar a varredura por uma faixa ruim
            continue
        c = criar(f"y{y0}", y0, y1, roi, g, min_glifos=min_glifos)
        if c is not None:
            achados.append(c)
    return achados


def extensao_por_fundo(
    roi: np.ndarray, largura_faixa: int = 40, delta: float = 0.05
) -> tuple[int, int]:
    """Maior trecho contíguo em x onde o fundo é tão liso quanto o mais liso.

    É o discriminador que funciona, e a razão é medida: o braço do violão tem 6 cordas
    com espaçamento parecido com o da tablatura, então alinhar por LINHA não separa os
    dois (o recorte por linha parou em 882 px onde a tablatura tem ~520). O que separa
    é o fundo: papel liso e contínuo contra vídeo de madeira, mão e sombra.

    Args:
        roi: recorte da faixa.
        largura_faixa: largura das colunas de medição, em px.
        delta: quanto o fundo pode ser menos liso que o mais liso para ainda valer.

    Returns:
        ``(x0, x1)`` do trecho; o recorte inteiro se nada for mais liso.
    """
    largura = roi.shape[1]
    if largura < 3 * largura_faixa:
        return 0, largura
    quantas = largura // largura_faixa
    medidas = [
        uniformidade(roi[:, i * largura_faixa : (i + 1) * largura_faixa])
        for i in range(quantas)
    ]
    if not medidas:
        return 0, largura
    corte = max(medidas) - delta
    bom = [u >= corte for u in medidas]
    if not any(bom):
        return 0, largura
    melhor = (0, 0)
    inicio = None
    buraco = 0
    for i, ok in enumerate(bom):
        if ok:
            if inicio is None:
                inicio = i
            buraco = 0
        elif inicio is not None:
            buraco += 1
            if buraco > 2:  # tolera duas colunas ruins no meio do painel
                if i - buraco - inicio > melhor[1] - melhor[0]:
                    melhor = (inicio, i - buraco)
                inicio = None
    if inicio is not None and quantas - inicio > melhor[1] - melhor[0]:
        melhor = (inicio, quantas)
    return int(melhor[0] * largura_faixa), int(min(largura, melhor[1] * largura_faixa))


def refinar(c: Candidato, margem: int = 12) -> Candidato:
    """Estreita o candidato ao retângulo onde as 6 linhas coexistem e re-segmenta.

    Args:
        c: candidato já escolhido.
        margem: pixels de folga de cada lado.

    Returns:
        Um candidato novo, recortado em x; o próprio ``c`` se o recorte não mudar
        nada ou se o recorte piorar a leitura.
    """
    x0, x1 = extensao_das_linhas(c.roi, c.grade.linhas_y)
    x0 = max(0, x0 - margem)
    x1 = min(c.roi.shape[1], x1 + margem)
    if x1 - x0 < 0.25 * c.roi.shape[1] or x1 - x0 == c.roi.shape[1]:
        return c
    recorte = c.roi[:, x0:x1]
    try:
        grade = segmentar(recorte)
    except Exception:
        return c
    # Piso 1, não 5: medido neste quadro, o painel de verdade tem TRÊS algarismos
    # (o `0 2 3` da 5ª corda) e um piso alto descartava a leitura correta para
    # ficar com 36 tokens, 33 deles lixo do vídeo ao lado. Painel pequeno é painel.
    novo = criar(c.nome, c.y0, c.y1, recorte, grade, min_glifos=1, x0=c.x0 + x0)
    if novo is None:
        return c
    # O recorte só estreita em x: as cordas têm de ser as mesmas em y. Medido (rodada 0007,
    # iwaki VN18 e FP38): a re-segmentação do recorte trocava as 6 cordas da TAB pelas da
    # pauta (6 linhas fortes, espaçamento 14, que e_pauta não separa aqui), e a caixa saía
    # sobre a partitura. Se as linhas mudaram, fica com o original.
    if not mesmas_linhas(novo.grade.linhas_y, c.grade.linhas_y):
        return c
    return novo


def mesmas_linhas(a: list[int], b: list[int], tolerancia: float = 2.0) -> bool:
    """As duas listas de cordas (em y) são as mesmas, a menos de ``tolerancia`` px?

    Args:
        a: y das linhas do primeiro grupo.
        b: y das linhas do segundo grupo.
        tolerancia: desvio máximo, em px, por linha.

    Returns:
        True se houver o mesmo número de linhas e cada uma bater com a sua.
    """
    if len(a) != len(b):
        return False
    return all(
        abs(x - y) <= tolerancia for x, y in zip(sorted(a), sorted(b), strict=True)
    )


def melhor(achados: list[Candidato]) -> Candidato | None:
    """O melhor candidato da lista (uniformidade primeiro, centrados depois).

    Args:
        achados: candidatos já medidos.

    Returns:
        O melhor, ou None se a lista estiver vazia.
    """
    return max(achados, key=lambda c: c.score) if achados else None


#: Razão máxima entre a maior e a menor lacuna do grupo de 6 linhas.
#:
#: A FOTO DO VIOLÃO passa com razão **1,6** (lacunas 32,27,26,25,40) — o limite exato — e dela
#: vieram recortes de "partitura" na coleta. Apertei para 1,3 e MEDI o custo nos mesmos 34
#: quadros: painel em **33/34** com 1,6 e em **26/34** com 1,3 — **7 quadros (21%) perderiam a
#: notação** para consertar um caso de lixo. **Reprovado**: negócio ruim, com o número na mão.
#: A constante fica (para não voltar a ser argumento fixo escondido) e o valor fica em 1,6.
TOLERANCIA_ESPACAMENTO = 1.6


def espacamento_regular(linhas_y: list[int], tolerancia: float | None = None) -> bool:
    """As linhas estão igualmente espaçadas? (senão não é uma pauta de cordas)"""
    if tolerancia is None:
        tolerancia = TOLERANCIA_ESPACAMENTO
    """As linhas estão igualmente espaçadas? (senão não é uma pauta de cordas)

    Medido no `sky guitar` (`(henze) nocturno`, t=228 s): sem esta checagem o detector
    aceitava `[138, 154, 170, 185, 202, 342]` — as **5 linhas da partitura mais 1 linha da
    tablatura**, 140 px abaixo. Espaçamentos: 16, 16, 15, 17, **140**. Isso não é uma pauta:
    é um remendo, e foi ele que fez 61 % do lido virar bolinha de nota e número de digitação.

    A origem do remendo está no `tabseg.achar_cordas`: quando não encontra 6 linhas
    regulares, ele **cai para os picos mais fortes** (aviso "espaçamento irregular"). O
    aviso existia — e o portão do painel o ignorava.

    Args:
        linhas_y: y das linhas detectadas.
        tolerancia: razão máxima entre o maior e o menor intervalo.

    Returns:
        True se o espaçamento for regular dentro da tolerância.
    """
    if len(linhas_y) < 2:
        return False
    lacunas = [b - a for a, b in itertools.pairwise(linhas_y)]
    if min(lacunas) <= 0:
        return False
    return max(lacunas) / min(lacunas) <= tolerancia


#: Linha é "forte" se sua tinta for pelo menos esta fração da mais forte do grupo.
FRACAO_LINHA_FORTE = 0.5


def forcas_das_linhas(roi: np.ndarray, linhas_y: list[int]) -> list[float]:
    """Força (fração de tinta na linha) de cada linha do grupo, no recorte.

    Medida no perfil horizontal da máscara de tinta (união das máscaras do `segmentar`),
    com 2 px de folga para cada lado da linha.

    Args:
        roi: recorte da faixa (BGR ou cinza).
        linhas_y: y das linhas, relativas ao recorte.

    Returns:
        Uma força por linha, na mesma ordem de ``linhas_y``.
    """
    perfil = _uniao_mascaras(roi).mean(axis=1)
    return [
        float(perfil[max(0, y - 2) : min(len(perfil), y + 3)].max()) for y in linhas_y
    ]


def e_pauta(roi: np.ndarray, linhas_y: list[int]) -> bool:
    """O grupo de 6 linhas é, na verdade, uma pauta de 5 linhas mais uma linha fraca?

    Medido na rodada 0007 (iwaki VN18, VN20, FP38): o `segmentar` acha as 5 linhas da
    pauta fortes (força ~0,86) e uma 6ª linha fraca (~0,38, viga ou haste). Essa 6ª linha
    passa no teste de espaçamento regular porque a pauta tem espaçamento constante. A TAB
    de verdade tem as 6 cordas fortes (0,75 a 0,94 nos quadros conferidos). Regra: se
    exatamente 5 linhas forem fortes, o grupo é pauta, não tablatura.

    Args:
        roi: recorte da faixa.
        linhas_y: y das 6 linhas, relativas ao recorte.

    Returns:
        True se houver 5 linhas fortes (a faixa vizinha com 6 fortes deve ser preferida).
    """
    forcas = forcas_das_linhas(roi, linhas_y)
    if not forcas:
        return False
    corte = FRACAO_LINHA_FORTE * max(forcas)
    fortes = sum(1 for f in forcas if f >= corte)
    return fortes == 5


#: Fração da linha mais forte do recorte a partir da qual uma linha de tinta conta como
#: linha de pauta ou corda. Medido no FN05 (sky guitar, t=117,15): pauta e TAB ficam
#: em 0,93 a 0,99 da mais forte, e o ruído de notas e hastes em 0,30 a 0,39.
FRACAO_LINHA_PAUTA = 0.6


def linhas_fortes(roi: np.ndarray, fracao: float = FRACAO_LINHA_PAUTA) -> list[float]:
    """Centros das linhas horizontais fortes do recorte, de cima para baixo.

    Usa a mesma máscara de união de ``forcas_das_linhas``: uma linha forte é um trecho
    contínuo de linhas do perfil com tinta de pelo menos ``fracao`` da mais forte.

    Args:
        roi: recorte da faixa (BGR ou cinza).
        fracao: fração da linha mais forte que uma linha precisa atingir.

    Returns:
        Y (relativo ao recorte) do centro de cada linha forte.
    """
    if roi.size == 0:
        return []
    perfil = _uniao_mascaras(roi).mean(axis=1)
    if perfil.max() <= 0:
        return []
    forte = perfil >= fracao * perfil.max()
    centros: list[float] = []
    y = 0
    while y < len(forte):
        if forte[y]:
            j = y
            while j + 1 < len(forte) and forte[j + 1]:
                j += 1
            centros.append((y + j) / 2)
            y = j + 1
        else:
            y += 1
    return centros


def aparar_pauta(
    quadro: np.ndarray, rect: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """Corta a caixa do painel para só a TAB quando ela traz uma pauta de 5 linhas em cima.

    Medido no FN05 (sky guitar, t=117,15, 2026-10-10, dono: "cobre a tablatura e tambem a
    partitura, o quadrado deveria ser menor"): a caixa ia de y=710 a 1080 e cobria a pauta
    (5 linhas fortes, y 720 a 786, passo 16,5) e a TAB (6 cordas, y 916 a 1039, passo 24,6).

    A regra só ESTREITA a caixa, e só quando acha, dentro dela, um grupo de 6 linhas
    fortes regularmente espaçadas (passo na faixa do acervo) com pelo menos 5 linhas fortes
    acima. Nesse caso a caixa passa a ir de uma corda acima da TAB a uma corda abaixo dela.
    Caixa sem pauta em cima fica como estava.

    Args:
        quadro: quadro BGR inteiro.
        rect: caixa do painel no quadro, ``(x0, y0, x1, y1)``.

    Returns:
        A caixa aparada (a mesma ``rect`` se não houver pauta em cima da TAB).
    """
    x0, y0, x1, y1 = rect
    roi = quadro[y0:y1, x0:x1]
    ys = [round(v) for v in linhas_fortes(roi)]
    escolhido: tuple[list[int], float] | None = None
    for i in range(len(ys) - 5):
        grupo = ys[i : i + 6]
        passo = float(np.median([b - a for a, b in itertools.pairwise(grupo)]))
        if not (PASSO_MINIMO_PX <= passo <= PASSO_MAXIMO_PX):
            continue
        if not espacamento_regular(grupo):
            continue
        acima = [v for v in ys[:i] if grupo[0] - v > passo]
        if len(acima) < 5:
            continue
        escolhido = (grupo, passo)  # o último (mais embaixo) é a TAB
    if escolhido is None:
        return rect
    grupo, passo = escolhido
    margem = round(passo)
    topo = max(0, grupo[0] - margem)
    base = min(roi.shape[0], grupo[-1] + margem)
    return (x0, y0 + topo, x1, y0 + base)


#: Fração da largura que uma corda de TAB cobre, sem interrupção a não ser pelos algarismos.
FRACAO_CORRIDA_CORDA = 0.5

#: Mínimo de linhas horizontais contínuas para a caixa ser tablatura (6 cordas; uma pode
#: falhar por contraste). O braço do violão visto na diagonal dá 0 ou 1.
MIN_CORDAS_CONTINUAS = 4


def cordas_continuas(roi: np.ndarray, passo: float) -> int:
    """Quantas linhas horizontais atravessam o recorte (a corda de TAB é uma delas).

    A tablatura tem 6 linhas perfeitamente horizontais que ocupam a largura do painel,
    interrompidas só por algarismos. As cordas do braço do violão são diagonais (ou, na
    vista de lado, cobertas por madeira e mão): uma linha de pixels as cruza só em trechos
    curtos. Mede-se, por linha de pixels, a maior corrida contínua de tinta (buracos de
    até ``passo`` px são fechados, para o algarismo no meio da corda) e conta-se quantos
    grupos de linhas vizinhas passam de ``FRACAO_CORRIDA_CORDA`` da largura.

    Args:
        roi: recorte BGR do painel (a caixa).
        passo: passo entre cordas, em px (largura do buraco tolerado).

    Returns:
        Número de linhas horizontais contínuas (0 se o recorte é vazio).
    """
    if roi.size == 0:
        return 0
    tinta = _uniao_mascaras(roi).astype(np.uint8)
    largura = tinta.shape[1]
    fechada = cv2.morphologyEx(
        tinta, cv2.MORPH_CLOSE, np.ones((1, max(3, round(passo))), np.uint8)
    )
    continuas = np.zeros(fechada.shape[0], dtype=bool)
    for y, linha in enumerate(fechada):
        bordas = np.diff(np.concatenate(([0], linha, [0])))
        comprimentos = np.flatnonzero(bordas == -1) - np.flatnonzero(bordas == 1)
        continuas[y] = (
            len(comprimentos) > 0
            and comprimentos.max() >= FRACAO_CORRIDA_CORDA * largura
        )
    subidas = np.diff(np.concatenate(([0], continuas.astype(np.int8))))
    return int(np.count_nonzero(subidas == 1))


def criar(
    nome: str,
    y0: int,
    y1: int,
    roi: np.ndarray,
    grade: Grade,
    min_glifos: int = MIN_GLIFOS,
    x0: int = 0,
) -> Candidato | None:
    """Monta um candidato a partir de uma grade JÁ segmentada.

    Existe para quem precisa medir as faixas de qualquer jeito (a varredura mede
    picos e cursor em todas) e não quer pagar `segmentar` duas vezes.

    Args:
        nome: nome da faixa.
        y0: topo da faixa no quadro.
        y1: base da faixa no quadro.
        roi: recorte da faixa.
        grade: resultado de ``segmentar(roi)``.
        min_glifos: mínimo de glifos para aceitar a faixa.
        x0: deslocamento em x do ``roi`` no quadro.

    Returns:
        O candidato, ou None se a faixa não tem 6 cordas nem glifos suficientes.
    """
    if len(grade.linhas_y) != 6 or len(grade.glifos) < min_glifos:
        return None
    if not espacamento_regular(grade.linhas_y):
        return None  # 5 linhas de partitura + 1 de tablatura não é pauta de cordas
    if e_pauta(roi, grade.linhas_y):
        return None  # 5 linhas fortes + 1 fraca (viga/haste): é pauta, não tablatura
    u = uniformidade(roi)
    return Candidato(
        nome=nome,
        y0=y0,
        y1=y1,
        roi=roi,
        grade=grade,
        uniformidade=u,
        score=(round(u, 3), grade.glifos_centrados),
        x0=x0,
    )


def escolher_rapido(frame: np.ndarray) -> Candidato | None:
    """Como `escolher`, mas sem pagar `segmentar` em faixa que não serve.

    Medido num quadro real (1920x1080): `segmentar` custa **52 ms** na faixa da
    tablatura, **190 ms** na do meio e **758 ms** na faixa do braço — porque ali a
    cascata de máscaras é tentada inteira e falha. Na reserva a ordem é por **papel
    branco** (C1, rodada 0007: a uniformidade punha o braço à frente da TAB densa).
    Mede-se a fração de papel das três faixas (barato) e roda-se `segmentar` **em ordem
    decrescente de papel, parando na primeira que serve**: o custo cai nos vídeos em que
    a primeira ou a segunda faixa já serve.

    Args:
        frame: quadro inteiro.

    Returns:
        O melhor candidato, ou None.
    """
    medidas: list[tuple[float, str, int, int, np.ndarray]] = []
    for nome, y0, y1 in FAIXAS:
        y1 = min(y1, frame.shape[0])
        if y1 - y0 < 60:
            continue
        roi = frame[y0:y1, :]
        medidas.append((papel_branco(roi), nome, y0, y1, roi))
    for _papel, nome, y0, y1, roi in sorted(medidas, key=lambda m: -m[0]):
        try:
            g = segmentar(roi)
        except Exception:
            continue
        # `criar` concentra as regras de aceitação (6 linhas, glifos e ESPAÇAMENTO
        # REGULAR). Construir o candidato direto aqui foi um erro medido: o conserto do
        # espaçamento não pegava neste caminho, e o pipeline continuava aceitando
        # 5 linhas de partitura + 1 de tablatura.
        c = criar(nome, y0, y1, roi, g)
        if c is not None:
            return c
    return None


def e_tablatura(c: Candidato) -> bool:
    """O candidato tem as cordas de uma TAB (linhas horizontais contínuas)?

    Mede ``cordas_continuas`` na faixa das 6 cordas (com 1,5 passo de folga, como a caixa
    do produto). Com ``MIN_CORDAS_CONTINUAS`` em 0 o portão fica aberto (comparação).

    Args:
        c: candidato já refinado.

    Returns:
        False para o braço do violão (cordas diagonais ou cobertas); True para TAB.
    """
    if MIN_CORDAS_CONTINUAS <= 0:
        return True
    linhas = list(c.grade.linhas_y)
    folga = round(1.5 * c.passo)
    faixa = c.roi[max(0, min(linhas) - folga) : max(linhas) + folga + 1]
    return cordas_continuas(faixa, c.passo) >= MIN_CORDAS_CONTINUAS


def _primeira_tablatura(grupos: list[list[Candidato]]) -> Candidato | None:
    """Primeiro candidato (refinado) que é TAB e tem passo na faixa do acervo.

    Args:
        grupos: listas de candidatos, em ordem de preferência.

    Returns:
        O candidato refinado, ou None se nenhum passar.
    """
    for grupo in grupos:
        for cand in grupo:
            cand = refinar(cand)
            if PASSO_MINIMO_PX <= cand.passo <= PASSO_MAXIMO_PX and e_tablatura(cand):
                return cand
    return None


def _por_mascara(frame: np.ndarray) -> list[Candidato]:
    """Candidatos por máscara (grupos fortes de 6 cordas), do mais liso ao menos liso."""
    return [c for _u, c in sorted(candidatos_por_mascara(frame), key=lambda t: -t[0])]


def _tablatura_no_lugar_do_braco(
    frame: np.ndarray, min_glifos: int
) -> Candidato | None:
    """Procura, no quadro, um candidato que seja TAB quando o escolhido era o braço.

    Ordem: os demais candidatos do quadro inteiro (por uniformidade), depois os grupos
    fortes por máscara (a via que acha a TAB estreita ou colada no vídeo). Só entra quem
    passa em ``e_tablatura``.

    Args:
        frame: quadro inteiro.
        min_glifos: mínimo de glifos do caminho principal.

    Returns:
        O candidato (já refinado) ou None se nenhum for TAB.
    """
    do_quadro = sorted(
        candidatos_quadro(frame, min_glifos=min_glifos), key=lambda c: c.score
    )[::-1]
    return _primeira_tablatura([do_quadro, _por_mascara(frame)])


def escolher_ou_mascara(frame: np.ndarray) -> Candidato | None:
    """``escolher`` e, se ele não achar nada, a TAB por máscara (leitura do produto).

    O `kenneth acoustic` (t=88 s do `end of beginning`) tem o braço na horizontal e a TAB
    embaixo: nenhuma faixa fixa serve e `escolher` devolve None, mas a via por máscara
    acha a TAB. Fica fora de `escolher` para não mudar os demais chamadores.

    Args:
        frame: quadro inteiro.

    Returns:
        O candidato, ou None.
    """
    esc = escolher(frame)
    if esc is not None:
        return esc
    return _primeira_tablatura([_por_mascara(frame)])


def escolher(frame: np.ndarray, min_glifos: int = MIN_GLIFOS) -> Candidato | None:
    """Escolhe a faixa que é painel de tablatura (ou None se não houver).

    O critério é a uniformidade do fundo primeiro e os glifos centrados depois —
    invertido em relação ao critério antigo, que preferia o braço do violão.

    Depois da escolha vem o portão das cordas contínuas (``e_tablatura``) e do passo: se a
    faixa escolhida é o braço do violão ou tem passo fora de 14-55 px (medido no `south
    american music` e no `kenneth acoustic`: a faixa da TAB perdia para a do braço ou para
    uma faixa de passo 6), procura-se uma TAB de verdade no quadro. Sem alternativa, o
    braço vira None e a TAB de passo fora da faixa fica como estava. Quem já era TAB com
    passo válido não muda.

    Args:
        frame: quadro inteiro.
        min_glifos: mínimo de glifos para aceitar a faixa.

    Returns:
        O melhor candidato, ou None.
    """
    esc = melhor(candidatos_quadro(frame, min_glifos=min_glifos))
    if esc is None:
        # reserva: as três faixas fixas (cortam o painel em vídeo com partitura, mas
        # ainda acham os canais em que a tablatura cabe inteira numa faixa)
        esc = (
            escolher_rapido(frame)
            if min_glifos == MIN_GLIFOS
            else melhor(candidatos(frame, min_glifos))
        )
    if esc is None:
        return None
    esc = refinar(esc)
    passo_ok = PASSO_MINIMO_PX <= esc.passo <= PASSO_MAXIMO_PX
    eh_tab = e_tablatura(esc)
    if eh_tab and passo_ok:
        return esc
    alternativa = _tablatura_no_lugar_do_braco(frame, min_glifos)
    if alternativa is not None:
        return alternativa
    # sem alternativa: o braço vira "sem painel"; a TAB de passo fora da faixa fica como
    # estava (quem chama já a recusa)
    return esc if eh_tab else None


# ---------------------------------------------------------------------------------
# TAB ESCURA (cifra club): caminho ADITIVO, só para quadro sem candidato do HEAD
# ---------------------------------------------------------------------------------

NOME_MASCARA_CLARA = "contraste_claro_k21_d12"


def _grupos_regulares(
    picos: list[int],
    altura: int,
    passo_min: float,
    passo_max: float,
    tolerancia: float,
    nome: str,
) -> list[tuple[str, float, int, int, list[int]]]:
    """Janelas de 6 picos consecutivos, regulares e com passo na faixa do acervo.

    Args:
        picos: y dos picos de UMA máscara, em ordem.
        altura: altura do quadro (para limitar a faixa).
        passo_min: passo mínimo aceitável, em px.
        passo_max: passo máximo aceitável, em px.
        tolerancia: razão máxima entre a maior e a menor lacuna do grupo.
        nome: nome da máscara que achou os picos.

    Returns:
        ``(nome, passo, y0, y1, cordas)`` de cada grupo aceito: ``cordas`` são as 6 linhas
        relativas a ``y0``; a faixa ``[y0, y1)`` leva a margem de uma corda.
    """
    achados: list[tuple[str, float, int, int, list[int]]] = []
    for i in range(len(picos) - 5):
        grupo = picos[i : i + 6]
        passo = float(np.median([b - a for a, b in itertools.pairwise(grupo)]))
        if not (passo_min <= passo <= passo_max):
            continue
        if not espacamento_regular(grupo, tolerancia=tolerancia):
            continue
        margem = round(passo)  # round() de float já devolve int (regra 8)
        y0 = max(0, grupo[0] - margem)
        y1 = min(altura, grupo[-1] + margem)
        if y1 - y0 < 60:
            continue
        achados.append((nome, passo, y0, y1, [v - y0 for v in grupo]))
    return achados


def _grade_do_grupo(
    roi: np.ndarray, nome: str, cordas: list[int], passo: float
) -> Grade:
    """Grade de uma faixa cujas 6 cordas JÁ foram achadas pela máscara ``nome``.

    Por que não `segmentar(roi)`: a busca de cordas dele usa fração de tinta 0,30, e a
    TAB escura (máscara `contraste_claro`, cordas com tinta 0,29-0,31) não chega lá: a
    faixa dava `linhas=0`. Aqui as cordas vêm do grupo regular já achado, e o resto segue
    o `segmentar`: a grade pela máscara e depois o delimitador de tokens.

    Args:
        roi: recorte da faixa (BGR).
        nome: nome da máscara que achou as cordas (``mascaras_candidatas``).
        cordas: as 6 linhas, relativas ao recorte.
        passo: passo entre cordas, em px.

    Returns:
        A grade, com os glifos já delimitados.
    """
    tinta = dict(mascaras_candidatas(roi))[nome]
    g = _segmentar_de_mascara(tinta, 6, list(cordas), passo)
    g.glifos, recusados = delimitar_tokens(
        g.glifos,
        g.passo,
        g.linhas_y,
        extensao=extensao_das_linhas(roi, g.linhas_y),
        tinta=tinta,
        cinza=cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),
    )
    g.recusados = recusados
    return g


#: Fundo de TAB escura: cinza mediano da faixa até este valor (medido: TAB escura 26; painel
#: claro 84 a 97; video escuro não passou no `criar`, ver _diag/feat.py).
FUNDO_ESCURO_MAXIMO = 50.0
#: Contraste mediano das cordas: cinza na linha menos cinza 4 a 7 px acima (medido: TAB
#: escura 13,7 a 21,5 nos 15 rotulados; o mínimo dos grupos de painel claro foi 50 e o do
#: VP16 com fundo 97 passava só por isso).
CONTRASTE_LINHA_MINIMO = 12.0


def candidatos_claros_escuros(frame: np.ndarray) -> list[tuple[float, Candidato]]:
    """Grupos de 6 cordas claras sobre fundo ESCURO, achados SÓ na máscara `contraste_claro`.

    Só entra grupo cuja faixa tem fundo escuro (cinza mediano <= FUNDO_ESCURO_MAXIMO) e
    cujas cordas são mais claras que o fundo acima delas (contraste mediano >=
    CONTRASTE_LINHA_MINIMO). Painel claro não passa por aqui: quem atende painel claro é o
    `escolher` do HEAD.

    Args:
        frame: quadro inteiro (BGR).

    Returns:
        ``(uniformidade, candidato)`` de cada grupo escuro que `criar` aceita.
    """
    cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mascara = dict(mascaras_candidatas(frame))[NOME_MASCARA_CLARA]
    picos: list[int] = []
    for fracao in (0.30, 0.15):
        for _v, y in picos_de_linha(mascara, fracao_min=fracao):
            y = int(y)
            if not picos or all(abs(y - p) > 2 for p in picos):
                picos.append(y)
    picos.sort()
    achados: list[tuple[float, Candidato]] = []
    for nome, passo, y0, y1, cordas in _grupos_regulares(
        picos,
        frame.shape[0],
        PASSO_MINIMO_PX,
        PASSO_MAXIMO_PX,
        TOLERANCIA_ESPACAMENTO,
        NOME_MASCARA_CLARA,
    ):
        roi = frame[y0:y1, :]
        if float(np.median(cinza[y0:y1, :])) > FUNDO_ESCURO_MAXIMO:
            continue
        if _contraste_das_cordas(cinza, cordas, y0) < CONTRASTE_LINHA_MINIMO:
            continue
        try:
            g = _grade_do_grupo(roi, nome, cordas, passo)
        except Exception:  # nunca derrubar a varredura por uma faixa ruim
            continue
        c = criar(f"y{y0}", y0, y1, roi, g)
        if c is not None:
            achados.append((c.uniformidade, c))
    return achados


def _contraste_das_cordas(cinza: np.ndarray, cordas: list[int], y0: int) -> float:
    """Mediana, sobre as 6 cordas, de (cinza na linha) menos (cinza 4 a 7 px acima).

    Args:
        cinza: quadro em cinza (float32).
        cordas: y das 6 cordas, relativos a ``y0``.
        y0: topo da faixa no quadro.

    Returns:
        O contraste mediano (positivo quando a corda é mais clara que o fundo acima).
    """
    largura = cinza.shape[1]
    difs = []
    for c in cordas:
        y = y0 + c
        linha = cinza[max(0, y - 1) : y + 2, 200 : largura - 200].mean()
        acima = cinza[max(0, y - 7) : max(0, y - 3), 200 : largura - 200].mean()
        difs.append(float(linha - acima))
    return float(np.median(difs))


# ---------------------------------------------------------------------------------
# TAB POR MÁSCARA (aditivo): grupos de 6 cordas fortes, uma máscara de cada vez
# ---------------------------------------------------------------------------------

#: Pico FORTE do perfil de tinta (fração 0,30), usado por máscara. Medido nos quadros dos
#: casos do dono (2026-10-11): as cordas da TAB ficam em 0,6 a 0,99 da máscara, e o ruído,
#: em 0,15 a 0,25. O `candidatos_quadro` do HEAD junta os picos de TODAS as máscaras a 0,15
#: e isso quebra a janela de 6 cordas (caso `guitar dell'arte` 273 s: a TAB em 949 a 1043 e
#: os picos fracos 961, 980 e 992 intercalados). Esta via só roda onde o HEAD não acha nada.
PICO_FORTE_MASCARA = 0.30

#: Deriva vertical máxima das cordas, em fração do passo. Corda de TAB é horizontal; a
#: corda do BRAÇO do violão, vista de lado, é diagonal (caso `guitar dell'arte` 273 s).
DERIVA_MAXIMA_PASSOS = 0.5


def deriva_das_cordas(tinta: np.ndarray, cordas: list[int], passo: float) -> float:
    """Quanto a corda mais inclinada sobe ou desce ao longo da faixa, em px.

    Para cada corda, o centro de massa vertical da tinta é medido em 12 fatias de largura
    iguais, dentro de uma janela de ``passo / 4`` em torno da linha; uma reta é ajustada por
    mínimos quadrados e a deriva é o desvio de y entre as bordas da faixa.

    Args:
        tinta: máscara booleana ou uint8 da faixa (mesma máscara que achou as cordas).
        cordas: y das 6 cordas, relativas à faixa.
        passo: passo entre cordas, em px.

    Returns:
        A maior deriva entre as cordas medidas (0 se nenhuma tiver tinta em fatias suficientes).
    """
    largura = tinta.shape[1]
    raio = max(2, round(passo / 4))
    fatias = np.array_split(np.arange(largura), 12)
    maior = 0.0
    for c in cordas:
        xs: list[float] = []
        ys: list[float] = []
        atual = float(c)  # a janela acompanha a corda fatia a fatia
        for fatia in fatias:
            x0, x1 = int(fatia[0]), int(fatia[-1]) + 1
            topo = max(0, round(atual) - raio)
            base = round(atual) + raio + 1
            soma = tinta[topo:base, x0:x1].sum(axis=1).astype(np.float64)
            if soma.sum() <= 0:
                continue
            yy = np.arange(topo, topo + len(soma))
            xs.append((x0 + x1 - 1) / 2)
            atual = float((soma * yy).sum() / soma.sum())
            ys.append(atual)
        if len(xs) < 4:
            continue
        inclinacao = float(np.polyfit(xs, ys, 1)[0])
        maior = max(maior, abs(inclinacao) * (xs[-1] - xs[0]))
    return maior


#: Mínimo de glifos para um grupo da via por máscara. Medido: o diagrama de acorde (grade de
#: 6 cordas e 4 trastes) do `kenneth acoustic` (t=66 s) tem 9 glifos e uniformidade maior que a
#: TAB verdadeira do mesmo quadro (22 a 25 glifos); o piso de 12 separa os dois nos quadros
#: medidos. O piso geral (MIN_GLIFOS) fica para o caminho do HEAD.
MIN_GLIFOS_MASCARA = 12


def candidatos_por_mascara(
    frame: np.ndarray, min_glifos: int = MIN_GLIFOS_MASCARA
) -> list[tuple[float, Candidato]]:
    """Grupos de 6 cordas fortes e horizontais, achados em cada máscara SEPARADAMENTE.

    Para cada máscara da cascata do `segmentar`, os picos são os de ``PICO_FORTE_MASCARA``;
    grupos de 6 regulares com passo do acervo viram faixas, e a faixa passa por `criar`
    (glifos, espaçamento e não-pauta) e pelo teste de deriva.

    Args:
        frame: quadro inteiro (BGR).
        min_glifos: mínimo de glifos para aceitar a faixa.

    Returns:
        ``(uniformidade, candidato)`` de cada faixa aceita; pode haver a mesma faixa em
        mais de uma máscara (quem chama escolhe pela ordem).
    """
    altura = frame.shape[0]
    achados: list[tuple[float, Candidato]] = []
    vistos: set[tuple[str, int, int]] = set()
    for nome, mascara in mascaras_candidatas(frame):
        for picos in _picos_em_janelas(mascara):
            for _n, passo, y0, y1, cordas in _grupos_regulares(
                picos,
                altura,
                PASSO_MINIMO_PX,
                PASSO_MAXIMO_PX,
                TOLERANCIA_ESPACAMENTO,
                nome,
            ):
                if (nome, y0, y1) in vistos:
                    continue
                vistos.add((nome, y0, y1))
                c = _candidato_do_grupo(frame, nome, y0, y1, cordas, passo, min_glifos)
                if c is not None:
                    achados.append((c.uniformidade, c))
    return achados


#: Largura da janela em que se acham os picos fortes, por máscara, em px. O perfil de
#: tinta é média sobre a LARGURA do quadro: uma TAB estreita (vídeo vertical, letterbox)
#: cai abaixo do pico forte. Medido: a TAB do `kenneth acoustic` (vertical, ~600 px de
#: 1920) tem picos de 0,6 na janela e 0,2 na média do quadro.
JANELA_PICOS_PX = 480


def _picos_em_janelas(mascara: np.ndarray) -> list[list[int]]:
    """Picos fortes (fração 0,30) de cada janela horizontal da máscara.

    Args:
        mascara: máscara de tinta do quadro inteiro.

    Returns:
        Uma lista de y (ordenados) por janela; janelas se sobrepõem em metade.
    """
    largura = mascara.shape[1]
    passo = JANELA_PICOS_PX // 2
    saida: list[list[int]] = []
    for x0 in range(0, max(1, largura - JANELA_PICOS_PX) + 1, passo):
        sub = mascara[:, x0 : x0 + JANELA_PICOS_PX]
        saida.append(
            sorted(
                int(y) for _v, y in picos_de_linha(sub, fracao_min=PICO_FORTE_MASCARA)
            )
        )
    return saida


def _candidato_do_grupo(
    frame: np.ndarray,
    nome: str,
    y0: int,
    y1: int,
    cordas: list[int],
    passo: float,
    min_glifos: int,
) -> Candidato | None:
    """Candidato de um grupo de 6 cordas achado numa máscara, ou None se não passa.

    Args:
        frame: quadro inteiro (BGR).
        nome: máscara que achou as cordas.
        y0: topo da faixa no quadro.
        y1: base da faixa no quadro.
        cordas: y das 6 cordas, relativos a ``y0``.
        passo: passo entre cordas, em px.
        min_glifos: mínimo de glifos.

    Returns:
        O candidato, ou None (deriva alta, glifos insuficientes, pauta, espaçamento).
    """
    # estreita em x à extensão das cordas: a faixa de largura cheia mistura as barras
    # pretas do vídeo vertical e o fundo mediano sai 0 (medido no caso 10)
    cheio = frame[y0:y1, :]
    ex0, ex1 = extensao_das_linhas(cheio, list(cordas))
    ex0 = max(0, ex0 - round(passo))
    ex1 = min(cheio.shape[1], ex1 + round(passo))
    roi = cheio[:, ex0:ex1]
    if roi.shape[1] < 3 * passo:
        return None
    tinta = dict(mascaras_candidatas(roi))[nome]
    if deriva_das_cordas(tinta, cordas, passo) > DERIVA_MAXIMA_PASSOS * passo:
        return None
    try:
        g = _grade_do_grupo(roi, nome, cordas, passo)
    except Exception:  # nunca derrubar a varredura por uma faixa ruim
        return None
    return criar(f"y{y0}", y0, y1, roi, g, min_glifos=min_glifos, x0=ex0)
