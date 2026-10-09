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

from .tabseg import Grade, binarizar, picos_de_linha, segmentar

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
PASSO_MAXIMO_PX = 45.0


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
    tinta = binarizar(frame)
    picos = [int(y) for _v, y in picos_de_linha(tinta)]
    if len(picos) < 6:
        return []
    # 1) grupos de 6 linhas regulares — só geometria, sem custo de segmentação
    faixas: list[tuple[float, int, int]] = []
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
        faixas.append((passo, y0, y1))
    # 2) uniformidade do fundo é barata (medida: 38 ms) e ordena quem merece segmentação
    ordenadas: list[tuple[float, int, int]] = []
    vistos: list[int] = []
    for passo, y0, y1 in faixas:
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


def extensao_das_linhas(
    roi: np.ndarray, linhas_y: list[int], espessura: int = 2, minimo: int = 4
) -> tuple[int, int]:
    """Onde as linhas de corda existem TODAS juntas, em x.

    O painel é um **retângulo**, não uma tira de largura total. Medido no `sky guitar`
    (t=88 s): a tablatura ocupa x≈20–520 e o resto da faixa `meio` é vídeo do braço —
    os trastes e cordas entravam como "glifos" e o painel rendia 36 tokens, 19 deles
    lixo, com os algarismos em confiança média 0,466.

    Duas tentativas antes desta, as duas medidas e descartadas:

    1. exigir tinta em QUALQUER linha: o braço também tem tinta nas mesmas alturas (as
       cordas dele têm espaçamento parecido), e o recorte parou em 882 px onde a
       tablatura tem ~520;
    2. usar a uniformidade do fundo por coluna: o trecho mais liso do quadro é a
       **margem vazia** ao lado da tablatura, e o recorte ia para 240 px de papel em
       branco.

    O que separa é exigir que **quase todas** as cordas estejam presentes na mesma
    coluna — na tablatura as 6 linhas são contínuas, no braço não.

    Args:
        roi: recorte da faixa.
        linhas_y: y das linhas detectadas (relativas ao recorte).
        espessura: meia-espessura, em px, da faixa de linha considerada.
        minimo: quantas das linhas precisam estar presentes na coluna.

    Returns:
        ``(x0, x1)`` do maior trecho contíguo válido.
    """
    cinza = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, tinta = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if tinta.mean() > 127:  # fundo claro: a linha é escura
        tinta = 255 - tinta
    contagem = np.zeros(roi.shape[1], dtype=np.int16)
    for ly in linhas_y:
        a, b = max(0, ly - espessura), min(tinta.shape[0], ly + espessura + 1)
        if b > a:
            contagem += (tinta[a:b, :] > 127).any(axis=0).astype(np.int16)
    ativo = contagem >= minimo
    if not ativo.any():
        return 0, roi.shape[1]
    # maior trecho contíguo, tolerando buracos de até 2% da largura
    tolerancia = max(4, int(0.02 * roi.shape[1]))
    melhor = (0, 0)
    inicio = None
    buraco = 0
    for x, a in enumerate(ativo):
        if a:
            if inicio is None:
                inicio = x
            buraco = 0
        elif inicio is not None:
            buraco += 1
            if buraco > tolerancia:
                if x - buraco - inicio > melhor[1] - melhor[0]:
                    melhor = (inicio, x - buraco)
                inicio = None
    if inicio is not None and len(ativo) - inicio > melhor[1] - melhor[0]:
        melhor = (inicio, len(ativo))
    return int(melhor[0]), int(melhor[1])


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
    novo = criar(c.nome, c.y0, c.y1, recorte, grade, min_glifos=1)
    if novo is None:
        return c
    return novo


def melhor(achados: list[Candidato]) -> Candidato | None:
    """O melhor candidato da lista (uniformidade primeiro, centrados depois).

    Args:
        achados: candidatos já medidos.

    Returns:
        O melhor, ou None se a lista estiver vazia.
    """
    return max(achados, key=lambda c: c.score) if achados else None


def espacamento_regular(linhas_y: list[int], tolerancia: float = 1.6) -> bool:
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


def criar(
    nome: str,
    y0: int,
    y1: int,
    roi: np.ndarray,
    grade: Grade,
    min_glifos: int = MIN_GLIFOS,
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

    Returns:
        O candidato, ou None se a faixa não tem 6 cordas nem glifos suficientes.
    """
    if len(grade.linhas_y) != 6 or len(grade.glifos) < min_glifos:
        return None
    if not espacamento_regular(grade.linhas_y):
        return None  # 5 linhas de partitura + 1 de tablatura não é pauta de cordas
    u = uniformidade(roi)
    return Candidato(
        nome=nome,
        y0=y0,
        y1=y1,
        roi=roi,
        grade=grade,
        uniformidade=u,
        score=(round(u, 3), grade.glifos_centrados),
    )


def escolher_rapido(frame: np.ndarray) -> Candidato | None:
    """Como `escolher`, mas sem pagar `segmentar` em faixa que não serve.

    Medido num quadro real (1920x1080): `segmentar` custa **52 ms** na faixa da
    tablatura, **190 ms** na do meio e **758 ms** na faixa do braço — porque ali a
    cascata de máscaras é tentada inteira e falha. Como a regra decidida é
    *uniformidade primeiro*, dá para medir o fundo das três faixas (38 ms cada) e
    rodar `segmentar` **em ordem decrescente de uniformidade, parando na primeira que
    serve**: o resultado é o mesmo e o custo cai ~4x nos vídeos em que a primeira ou a
    segunda faixa já serve.

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
        medidas.append((uniformidade(roi), nome, y0, y1, roi))
    for _uniform, nome, y0, y1, roi in sorted(medidas, key=lambda m: -m[0]):
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


def escolher(frame: np.ndarray, min_glifos: int = MIN_GLIFOS) -> Candidato | None:
    """Escolhe a faixa que é painel de tablatura (ou None se não houver).

    O critério é a uniformidade do fundo primeiro e os glifos centrados depois —
    invertido em relação ao critério antigo, que preferia o braço do violão.

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
    return refinar(esc) if esc is not None else None
