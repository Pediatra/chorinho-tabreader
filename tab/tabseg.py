"""Segmentação estrutural de uma linha de TABLATURA renderizada em vídeo.

Objetivo: transformar um recorte de pauta de tablatura (tipicamente 6 cordas) em
uma grade determinística (corda x coluna) com as caixas dos glifos, SEM depender
de OCR genérico.

Desenho inspirado no Audiveris: geometria (linhas, barlines, colunas) é resolvida
por métodos *ad-hoc* determinísticos; só a identidade do símbolo vira modelo.

Famílias de renderização já verificadas nos dados reais:
  A. MuseScore/Guitar Pro, fundo claro, linhas SÓLIDAS, algarismos pretos.
  B. Livro impresso, fundo creme, pauta + TAB, algarismos pretos.
  C. Player escuro (Songsterr-like), fundo preto, algarismos claros.
  D. Player escuro com linhas TRACEJADAS (Cifra Club-like), acordes laranja.
  E. Tab ASCII de texto (Ultimate Guitar), fonte monoespaçada.

Uso:
    python -m tab.tabseg IMAGEM [--debug saida.png] [--json saida.json]
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field

import cv2
import numpy as np


@dataclass
class Glifo:
    x0: int
    y0: int
    x1: int
    y1: int
    corda: int  # 1 = corda aguda (linha de cima), 6 = grave
    coluna: int
    area: int
    partes: int = 1  # quantos componentes foram fundidos neste token
    partes_digito: int = 1  # quantas partes têm "haste" (traço vertical longo)
    # Caixas dos componentes que formaram este token. Sem isto, um `<7>` fundido
    # vira a classe `harmonico` e a CASA 7 se perde para sempre: o símbolo era
    # descartado no instante em que o token era montado, não na classificação.
    componentes: tuple[tuple[int, int, int, int], ...] = ()

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Grade:
    altura: int
    largura: int
    linhas_y: list[int] = field(default_factory=list)
    barlines_x: list[int] = field(default_factory=list)
    passo: float = 0.0
    glifos: list[Glifo] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    glifos_centrados: int = 0
    #: Quantos tokens o delimitador recusou, por motivo. Nada some em silêncio: o número
    #: que a coleta descarta tem de aparecer no relatório.
    recusados: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "altura": self.altura,
            "largura": self.largura,
            "linhas_y": self.linhas_y,
            "passo": self.passo,
            "barlines_x": self.barlines_x,
            "glifos": [asdict(g) for g in self.glifos],
            "glifos_centrados": self.glifos_centrados,
            "recusados": self.recusados,
            "avisos": self.avisos,
        }


def _para_cinza(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        if img.shape[2] == 4:  # PNG com alfa: compõe no branco
            alfa = img[:, :, 3:4].astype(np.float32) / 255.0
            rgb = img[:, :, :3].astype(np.float32)
            img = (rgb * alfa + 255.0 * (1 - alfa)).astype(np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if img.dtype != np.uint8:
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return img


def binarizar(img: np.ndarray) -> np.ndarray:
    """Tinta = True, detectando a polaridade (fundo claro ou escuro) por Otsu."""
    gray = _para_cinza(img)
    limiar, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    escuros = gray < limiar
    if escuros.mean() > 0.5:  # fundo escuro -> tinta = claro
        return gray > limiar
    return escuros


def _contraste_local(gray: np.ndarray, k: int = 21, delta: int = 12) -> np.ndarray:
    """Tinta = pixels mais ESCUROS que o fundo local (fechamento morfológico grande).

    É o que salva as famílias de traço fino e baixo contraste — player escuro
    (Songsterr/Cifra Club) e livro impresso/PDF — onde o Otsu descarta a linha por
    ela ser cinza-clara e fina.
    """
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, se)
    bg = cv2.GaussianBlur(bg, (0, 0), max(1.0, k / 4))
    d = gray.astype(np.int16) - bg.astype(np.int16)
    return d < -delta


def mascaras_candidatas(img: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """Máscaras de tinta em ordem de preferência; a primeira que validar vence."""
    gray = _para_cinza(img)
    cands = [("otsu", binarizar(gray))]
    for k, delta in ((21, 12), (31, 25)):
        cands.append((f"contraste_k{k}_d{delta}", _contraste_local(gray, k, delta)))
    # Painel ESCURO (ex.: cifra club): a tinta e a LINHA sao MAIS CLARAS que o fundo.
    # Sem esta variante a mascara pegava so os algarismos brancos e perdia as cordas
    # cinzas — foi o que travou a leitura do painel escuro por varias rodadas.
    for k, delta in ((21, 12),):
        cands.append(
            (f"contraste_claro_k{k}_d{delta}", _contraste_local_claro(gray, k, delta))
        )
    return cands


def _contraste_local_claro(
    gray: np.ndarray, k: int = 21, delta: int = 12
) -> np.ndarray:
    """Tinta = pixels mais CLAROS que o fundo local (para painel escuro)."""
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, se)
    bg = cv2.GaussianBlur(bg, (0, 0), max(1.0, k / 4))
    d = gray.astype(np.int16) - bg.astype(np.int16)
    return d > delta


# --------------------------------------------------------------------------- #
# linhas de corda
# --------------------------------------------------------------------------- #


def picos_de_linha(
    tinta: np.ndarray, fracao_min: float = 0.30, margem_borda: int = 3
) -> list[float]:
    """Picos do perfil horizontal de tinta (funciona com linha sólida e tracejada).

    Picos a menos de `margem_borda` px da borda são descartados: ali há **borda de
    quadro** (letterbox, moldura, recorte), não corda. Medido no `sky guitar`
    (`(henze) nocturno`, t=228 s): a faixa `topo` continha a partitura (5 linhas) e a
    tablatura embaixo; o detector pegou as 5 linhas da partitura MAIS a borda preta em
    `y=1`, fechou "6 cordas", passou no portão e leu 112 tokens da **partitura** — 66 % do
    que saiu era bolinha de nota e número de digitação, com confiança mediana 0,43.
    """
    h, _ = tinta.shape
    perfil = tinta.mean(axis=1)
    if h >= 3:
        perfil = np.convolve(perfil, np.ones(3) / 3, mode="same")
    picos = []
    for y in range(max(1, margem_borda), h - 1 - margem_borda):
        if (
            perfil[y] >= perfil[y - 1]
            and perfil[y] >= perfil[y + 1]
            and perfil[y] > fracao_min
        ):
            picos.append((float(perfil[y]), float(y)))
    # agrupa picos vizinhos (linha espessa gera 2-3 picos) pelo de maior perfil
    picos.sort()
    escolhidos: list[tuple[float, float]] = []
    for val, y in reversed(picos):
        if all(abs(y - ey) > 2.0 for _, ey in escolhidos):
            escolhidos.append((val, y))
    return sorted(escolhidos, key=lambda t: t[1])


def candidatos_de_cordas(
    tinta: np.ndarray, n_cordas: int = 6, max_candidatos: int = 16, top: int = 6
) -> list[tuple[list[int], float]]:
    """Todas as progressões regulares plausíveis, das mais regulares para as menos.

    Uma imagem pode conter DUAS pautas (partitura de 5 linhas em cima da tablatura de
    6). Escolher a primeira progressão regular erra — por isso devolvemos várias e a
    decisão fica com o conteúdo (ver `segmentar`).
    """
    ys = [y for _, y in picos_de_linha(tinta)]
    if len(ys) < n_cordas:
        return []
    picos = sorted(picos_de_linha(tinta), key=lambda t: -t[0])[:max_candidatos]
    ys = sorted(y for _, y in picos)
    if len(ys) < n_cordas:
        return []
    achados = []
    for comb in itertools.combinations(range(len(ys)), n_cordas):
        sel = [ys[k] for k in comb]
        difs = np.diff(sel)
        if np.any(difs < 3):
            continue
        media = float(np.mean(difs))
        erro = float(np.std(difs) / media)
        if erro > 0.22:
            continue
        achados.append((erro, media, sel))
    achados.sort(key=lambda t: (round(t[0], 3), -t[1]))
    return [([round(v) for v in sel], med) for _, med, sel in achados[:top]]


def achar_cordas(
    tinta: np.ndarray, n_cordas: int = 6, max_candidatos: int = 16
) -> tuple[list[int], float]:
    """Acha n_cordas linhas igualmente espaçadas (progressão aritmética).

    O critério de regularidade é o que separa pauta de qualquer outro conteúdo
    (texto, cabeçalho, diagrama de acorde): 6 linhas com espaçamento constante.
    """
    if tinta.shape[0] < 8:
        return [], 0.0
    picos = picos_de_linha(tinta)
    if len(picos) < n_cordas:
        return [], 0.0
    picos = sorted(picos, key=lambda t: -t[0])[:max_candidatos]
    picos.sort(key=lambda t: t[1])
    ys = [y for _, y in picos]
    if len(ys) < n_cordas:
        return [], 0.0

    melhor, melhor_chave = None, None
    for comb in itertools.combinations(range(len(ys)), n_cordas):
        sel = [ys[k] for k in comb]
        difs = np.diff(sel)
        if np.any(difs < 3):
            continue
        media = float(np.mean(difs))
        erro = float(np.std(difs) / media)
        if erro > 0.22:
            continue
        # prefere regularidade; em empate, passo maior (a TAB é a pauta mais aberta)
        chave = (round(erro, 3), -media)
        if melhor_chave is None or chave < melhor_chave:
            melhor, melhor_chave = sel, chave
    if melhor is None:
        # sem progressão regular: devolve os picos mais fortes, marcando o aviso
        sel = sorted(ys)[:n_cordas]
        return [round(v) for v in sel], 0.0
    passo = float(np.mean(np.diff(melhor)))
    return [round(v) for v in melhor], passo


def achar_barlines(tinta: np.ndarray, linhas_y: list[int]) -> list[int]:
    if not linhas_y:
        return []
    y0, y1 = max(0, linhas_y[0] - 6), min(tinta.shape[0], linhas_y[-1] + 7)
    faixa = tinta[y0:y1, :]
    col = faixa.mean(axis=0)
    minimo = 0.75
    xs, i, w = [], 0, faixa.shape[1]
    while i < w:
        if col[i] > minimo:
            j = i
            while j < w and col[j] > minimo:
                j += 1
            xs.append(int((i + j) // 2))
            i = j
        else:
            i += 1
    return xs


# --------------------------------------------------------------------------- #
# glifos
# --------------------------------------------------------------------------- #


def componentes(
    tinta: np.ndarray, area_min: int = 8
) -> list[tuple[int, int, int, int, int]]:
    n, _lab, stats, _ = cv2.connectedComponentsWithStats(
        tinta.astype(np.uint8), connectivity=8
    )
    out = []
    for k in range(1, n):
        x, y, w, h, a = stats[k]
        if a < area_min:
            continue
        out.append((int(x), int(y), int(x + w), int(y + h), int(a)))
    return out


def limpar_glifo(crop: np.ndarray, passo: float) -> np.ndarray:
    """Tira restos de corda grudados no algarismo (runs horizontais longos locais)."""
    if crop.size == 0:
        return crop
    tinta = crop < 128 if crop.mean() > 127 else crop > 127
    w = tinta.shape[1]
    run_min = max(6, int(0.55 * passo))
    if run_min >= w:
        return crop
    out = tinta.copy()
    for y in range(tinta.shape[0]):
        row = tinta[y].astype(np.int8)
        dif = np.diff(np.concatenate([[0], row, [0]]))
        idx = np.flatnonzero(dif)
        for s, e in zip(idx[0::2], idx[1::2], strict=False):
            if e - s >= run_min:
                out[y, s:e] = False
    base = np.where(tinta, 0, 255).astype(np.uint8)
    res = np.where(out, 0, 255).astype(np.uint8)
    return res if res.mean() > base.mean() else crop


#: Caixa do que pode ser SÍMBOLO ou CASA **dentro da tablatura**, em unidades de PASSO.
#: Medido em 4 canais, no QUADRO (os PNGs de auditoria são ampliados — medir neles engana):
#: algarismos ficam em largura/passo 0,12–1,39 e altura/passo 0,29–0,98; o lixo começa em
#: largura/passo **2,69** e vai a 6,97 — e o lixo é LARGO (tira de linha, trecho de texto,
#: braço do violão com as cordas em diagonal), não alto. Margem de 1,9x entre as classes.
LARGURA_MAX_PASSOS = 2.0
ALTURA_MAX_PASSOS = 2.0
ALTURA_MIN_PASSOS = 0.20
#: Quanto um token pode passar do sistema das 6 cordas, em passos (item 1 do delimitador:
#: a extração enxerga SÓ dentro da tablatura).
MARGEM_SISTEMA_PASSOS = 1.0


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


#: Nitidez mínima de um recorte para ele poder ser símbolo — variância do laplaciano.
#: Medido nos rótulos auditados, nas DUAS escalas (o ampliado 4x NEAREST infla a variância, e
#: por isso o limiar tem de ser declarado na escala em que será usado):
#:
#:     4x:  nada 4-3690 (mediana 120) | algarismo min 488   | símbolo min 430
#:     1x:  nada 22-6327 (mediana 275) | algarismo min 2030 | símbolo min 1608
#:
#: Em 1x, 600 fica 2,7x abaixo do mínimo útil e bem acima da mediana do lixo. Nos rótulos da
#: folha 1: pega ~metade do `nada` com ZERO algarismo ou símbolo morto. O `nada` é foto borrada
#: e fundo — não tem traço, então não tem alta frequência.
NITIDEZ_MINIMA = 600.0


def e_sem_nitidez(cinza: np.ndarray, g: Glifo, limiar: float = NITIDEZ_MINIMA) -> bool:
    """O recorte é borrado/fundo demais para ser símbolo?

    Args:
        cinza: imagem em tons de cinza do recorte (não a máscara).
        g: token a julgar.
        limiar: variância mínima do laplaciano.

    Returns:
        True se o token não tem nitidez de traço.
    """
    recorte = cinza[g.y0 : g.y1 + 1, g.x0 : g.x1 + 1]
    if recorte.size < 9:
        return False
    return float(cv2.Laplacian(recorte, cv2.CV_64F).var()) < limiar


def e_haste_fina(
    tinta: np.ndarray, g: Glifo, razao_max: float = 0.35, desvio_max: float = 0.06
) -> bool:
    """Haste vertical fina: material de LINHA da tablatura (barline/corda), não símbolo.

    A constância do perfil é o que separa isto de um algarismo `1`: o `1` tem bandeira e/ou
    base, então a largura de tinta varia ao longo da altura; a haste não varia.

    Medido contra os rótulos auditados pelo dono do projeto (folha 1) e contra os 72
    algarismos do gabarito, antes de entrar aqui:

    - material de linha da tablatura (`§`): pega **4 de 12** (todas as descritas como "barra");
    - algarismo: **0 de 16** rotulados e **0 de 72** do gabarito;
    - `nada`, `partitura` e `símbolo`: **0** de 20.

    Args:
        tinta: máscara booleana do recorte inteiro (True = tinta).
        g: token a julgar.
        razao_max: largura/altura máxima para ser haste.
        desvio_max: desvio do perfil de linha (fração da largura com tinta, por linha).

    Returns:
        True se o token for uma haste vertical fina de perfil constante.
    """
    recorte = tinta[g.y0 : g.y1 + 1, g.x0 : g.x1 + 1]
    if recorte.size == 0:
        return False
    altura, largura = recorte.shape
    if altura < 6 or largura < 2 or largura / float(altura) > razao_max:
        return False
    if int(recorte.sum()) < 6:
        return False
    perfil = recorte.sum(axis=1) / float(largura)
    return float(np.std(perfil)) <= desvio_max


def delimitar_tokens(
    glifos: list[Glifo],
    passo: float,
    linhas_y: list[int] | None = None,
    extensao: tuple[int, int] | None = None,
    tinta: np.ndarray | None = None,
    cinza: np.ndarray | None = None,
) -> tuple[list[Glifo], dict[str, int]]:
    """Só o que cabe DENTRO da tablatura; devolve os válidos e a contagem por motivo.

    Motivo medido, com o dono do projeto vendo a clave de sol na montagem: a coleta guardava
    como "símbolo" o braço do violão, mão, foto desfocada, nome de acorde em texto, barra
    vertical solta e tira de linha inteira. Todos com a mesma assinatura: **tamanho
    incompatível com o passo**.

    Args:
        glifos: tokens da grade, já agrupados.
        passo: distância entre cordas, em px.
        linhas_y: y das 6 cordas (para a trava vertical); None desliga essa trava.
        tinta: máscara booleana do recorte (para a haste fina); None desliga essa trava.
        cinza: tons de cinza do recorte (para a nitidez); None desliga essa trava.
        extensao: ``(x0, x1)`` onde as 6 cordas coexistem; token fora
            disso é vídeo ao lado da tablatura (medido: 21 % dos tokens numa
            amostra de 1.694 caíam fora; no gabarito, zero).

    Returns:
        ``(validos, motivos)`` — ``motivos`` conta as recusas por nome, para o relatório.
    """
    if passo <= 0:
        return list(glifos), {}
    topo = min(linhas_y) - MARGEM_SISTEMA_PASSOS * passo if linhas_y else None
    base = max(linhas_y) + MARGEM_SISTEMA_PASSOS * passo if linhas_y else None
    validos: list[Glifo] = []
    motivos: Counter = Counter()
    for g in glifos:
        altura = (g.y1 - g.y0 + 1) / passo
        largura = (g.x1 - g.x0 + 1) / passo
        if cinza is not None and e_sem_nitidez(cinza, g):
            motivos["sem_nitidez"] += 1
        elif tinta is not None and e_haste_fina(tinta, g):
            motivos["haste_fina"] += 1
        elif extensao is not None and (g.x1 < extensao[0] or g.x0 > extensao[1]):
            motivos["fora_da_extensao"] += 1
        if topo is not None and (g.y0 < topo or g.y1 > base):
            motivos["fora_do_sistema"] += 1
        elif altura > ALTURA_MAX_PASSOS:
            motivos["alto_demais"] += 1
        elif largura > LARGURA_MAX_PASSOS:
            motivos["largo_demais"] += 1
        elif altura < ALTURA_MIN_PASSOS:
            motivos["baixo_demais"] += 1
        else:
            validos.append(g)
    return validos, dict(motivos)


def segmentar(img: np.ndarray, n_cordas: int = 6, debug: str | None = None) -> Grade:
    """Tenta as máscaras em ordem e fica com a PRIMEIRA que passa no teste de estrutura.

    O teste é: exatamente n_cordas linhas com espaçamento regular (passo > 0). É ele
    que permite usar uma máscara agressiva de contraste local sem quebrar o que o Otsu
    já resolvia — e é ele que rejeita recorte que não é tablatura.
    """
    melhor: Grade | None = None
    usada: np.ndarray | None = None
    escolhida = ""
    melhor_chave: tuple | None = None
    for nome, tinta in mascaras_candidatas(img):
        cands = candidatos_de_cordas(tinta, n_cordas)
        if not cands:
            g = _segmentar_de_mascara(tinta, n_cordas)
            g.avisos.insert(0, f"mascara={nome}")
            if melhor is None:
                melhor, usada, escolhida = g, tinta, nome
            continue
        for linhas, med in cands:
            g = _segmentar_de_mascara(tinta, n_cordas, linhas, med)
            g.avisos.insert(0, f"mascara={nome}")
            # O CONTEÚDO decide qual pauta é a tablatura: algarismo de TAB fica
            # centrado na corda; cabeça de nota de partitura cai também nos espaços.
            centrados = sum(
                1
                for x in g.glifos
                if min(abs(x.cy - ly) for ly in g.linhas_y) <= 0.25 * g.passo
            )
            chave = (centrados, len(g.glifos))
            if melhor_chave is None or chave > melhor_chave:
                melhor, usada, escolhida, melhor_chave = g, tinta, nome, chave
    if melhor is None:
        g = _segmentar_de_mascara(binarizar(img), n_cordas)
        g.avisos.insert(0, "mascara=otsu")
        melhor, usada, escolhida = g, binarizar(img), "otsu"
    assert usada is not None
    melhor.glifos_centrados = int(melhor_chave[0]) if melhor_chave else 0
    grade = melhor

    # DELIMITADOR: a extração enxerga só o que cabe dentro da tablatura. Aqui, e não em
    # `_segmentar_de_mascara`, porque é aqui que a IMAGEM existe (a extensão horizontal das
    # cordas é medida nela). Antes disto a coleta guardava braço de violão, clave, texto e
    # tira de linha como "símbolo".
    grade.glifos, recusados = delimitar_tokens(
        grade.glifos,
        grade.passo,
        grade.linhas_y,
        extensao=extensao_das_linhas(img, grade.linhas_y) if grade.linhas_y else None,
        tinta=usada,
        cinza=_para_cinza(img),
    )
    grade.recusados = recusados
    if recusados:
        grade.avisos.append(
            "delimite=" + ",".join(f"{k}:{v}" for k, v in sorted(recusados.items()))
        )

    if debug:
        h, w = usada.shape
        base = cv2.cvtColor(
            np.where(usada, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR
        )
        for ly in grade.linhas_y:
            cv2.line(base, (0, ly), (w, ly), (0, 200, 0), 1)
        for bx in grade.barlines_x:
            cv2.line(base, (bx, 0), (bx, h), (0, 0, 255), 1)
        for g in grade.glifos:
            cv2.rectangle(base, (g.x0, g.y0), (g.x1, g.y1), (255, 0, 0), 1)
            cv2.putText(
                base,
                str(g.corda),
                (g.x0, max(9, g.y0 - 1)),
                cv2.FONT_HERSHEY_PLAIN,
                0.8,
                (0, 140, 255),
                1,
            )
        cv2.putText(
            base, escolhida, (4, h - 4), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 255), 1
        )
        cv2.imwrite(debug, base)
    return grade


def _pixels_de_runs_horizontais(tinta: np.ndarray, comprimento_min: int) -> np.ndarray:
    """Pixels que pertencem a um run horizontal de tinta >= comprimento_min.

    Serve para apagar a corda (estrutura longa) sem destruir o algarismo (curto).
    """
    h, _ = tinta.shape
    u8 = tinta.astype(np.int8)
    pad = np.zeros((h, 1), dtype=np.int8)
    dif = np.diff(np.concatenate([pad, u8, pad], axis=1), axis=1)
    mask = np.zeros_like(tinta)
    for y in range(h):
        idx = np.flatnonzero(dif[y])
        if idx.size == 0:
            continue
        starts, ends = idx[0::2], idx[1::2]
        for s, e in zip(starts, ends, strict=False):
            if e - s >= comprimento_min:
                mask[y, s:e] = True
    return mask


def _remover_runs(faixa: np.ndarray, run_min: int) -> np.ndarray:
    mask = _pixels_de_runs_horizontais(faixa, run_min)
    return faixa & ~mask


def _remover_rotulo(glifos: list[Glifo], largura: int, passo: float) -> list[Glifo]:
    """Descarta o rotulo "T A B" da margem esquerda.

    O rotulo NAO pode ser filtrado por posicao fixa: em varias renderizacoes ele fica
    sobre o inicio das cordas e a primeira barline detectada pode estar no MEIO da pauta
    (medido no canal iwaki: barline em x=623 e digitos reais em x=236..571 — um filtro
    por margem apagava justamente as notas). O rotulo tem assinatura propria: e um
    conjunto de letras empilhadas verticalmente (>= 3 cordas) na faixa esquerda.
    """
    if not glifos:
        return glifos
    limite_x = 0.25 * largura
    ordem = sorted(range(len(glifos)), key=lambda i: glifos[i].cx)
    grupos: list[list[int]] = []
    atual: list[int] = []
    for i in ordem:
        if atual and glifos[i].cx - glifos[atual[-1]].cx > passo * 0.6:
            grupos.append(atual)
            atual = []
        atual.append(i)
    if atual:
        grupos.append(atual)
    if not grupos:
        return glifos
    # Só o PRIMEIRO grupo pode ser o rótulo, e ele é reconhecível por ser LARGO
    # (letras fragmentadas cobrem mais de um passo de largura) enquanto um acorde
    # real ocupa a largura de um algarismo (~0,6 passo).
    g0 = grupos[0]
    x0 = min(glifos[i].x0 for i in g0)
    x1 = max(glifos[i].x1 for i in g0)
    cordas = {glifos[i].corda for i in g0}
    if x0 < limite_x and len(cordas) >= 3 and (x1 - x0) > 0.95 * passo:
        remover = set(g0)
        return [g for i, g in enumerate(glifos) if i not in remover]
    return glifos


def _glifos_por_faixa(
    tinta: np.ndarray,
    linhas_y: list[int],
    passo: float,
    lim_x: int,
    barlines_x: list[int] | None = None,
) -> list[Glifo]:
    """Extrai os glifos DENTRO da faixa de cada corda, uma corda por vez.

    Por que nao rotular componentes na imagem inteira: em tablatura com acorde
    (3-4 notas empilhadas em cordas vizinhas) os algarismos se tocam e viram UM
    componente, com centro caindo entre duas cordas. Medido no canal `tup-*`:
    110 "glifos" numa linha e so 44 % centrados na corda. Fatiar por corda resolve
    de raiz: cada algarismo tem ~0,85 do passo de altura e centra-se na linha,
    entao cabe na faixa de +-0,45 do passo.
    """
    glifos: list[Glifo] = []
    meia = 0.45 * passo
    run_min = max(6, int(0.55 * passo))
    area_min = max(6, int(passo * passo * 0.03))
    for k, ly in enumerate(linhas_y):
        a = max(0, round(ly - meia))
        b = min(tinta.shape[0], round(ly + meia) + 1)
        if b - a < 4:
            continue
        # Remove a corda SÓ nas linhas da própria corda. Apagar runs longos na faixa
        # inteira cortava os traços horizontais dos algarismos (o arco do "0", a barra
        # do "4"/"7") e devolvia glifos mutilados.
        faixa = tinta[a:b, :].copy()
        c = ly - a
        t = max(1, round(0.15 * passo))
        lo, hi = max(0, c - t), min(faixa.shape[0], c + t + 1)
        if hi > lo:
            faixa[lo:hi, :] = _remover_runs(faixa[lo:hi, :], run_min)
        _rotulos_cc, mapa_cc = cv2.connectedComponents(
            faixa.astype(np.uint8), connectivity=8
        )
        for x0, y0, x1, y1, area in componentes(faixa, area_min=area_min):
            w, h = x1 - x0, y1 - y0
            if w > 3.0 * passo or h > 1.6 * passo:
                continue  # resto de linha
            if h < 0.20 * passo or w < 0.07 * passo:
                continue  # ruido
            # barline: atravessa a faixa toda e coincide com uma coluna vertical
            if barlines_x and any(x0 - 2 <= bx <= x1 + 2 for bx in barlines_x):
                continue

            # "haste": existe uma COLUNA com traço vertical >= 60% da altura? Um
            # algarismo tem (a haste do 1, a lateral do 7); uma diagonal de slide não
            # tem nenhuma coluna com traço longo. Foi o que faltou na rodada anterior,
            # em que o slide (alto, mas espalhado) passava como se fosse dígito.
            sub = mapa_cc[y0:y1, x0:x1] > 0
            hh = max(1, sub.shape[0])
            melhor_run = 0
            for cx in range(sub.shape[1]):
                col = sub[:, cx]
                if not col.any():
                    continue
                dif = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
                idx = np.flatnonzero(dif)
                run = int((idx[1::2] - idx[0::2]).max()) if idx.size else 0
                melhor_run = max(melhor_run, run)
            tem_haste = melhor_run >= 0.60 * hh
            glifos.append(
                Glifo(
                    x0=x0,
                    y0=y0 + a,
                    x1=x1,
                    y1=y1 + a,
                    corda=k + 1,
                    coluna=0,
                    area=area,
                    partes_digito=1 if tem_haste else 0,
                )
            )
    ordem = sorted(range(len(glifos)), key=lambda i: glifos[i].cx)
    grupo, anterior = 0, None
    for i in ordem:
        cx = glifos[i].cx
        if anterior is not None and cx - anterior > passo * 0.9:
            grupo += 1
        glifos[i].coluna = grupo
        anterior = cx
    glifos = _remover_rotulo(glifos, tinta.shape[1], passo)
    glifos.sort(key=lambda g: (g.coluna, g.corda))
    return glifos


def agrupar_tokens(glifos: list[Glifo], passo: float, gap: float = 0.25) -> list[Glifo]:
    """Junta componentes vizinhos na MESMA corda em um token.

    Medido no sintético: sem isto a razão é 1,44 glifo por nota, porque `12` vira `1`+`2`
    e `<7>` vira `<`+`7`+`>`. Cada pedaço recebia o rótulo do token inteiro e a rede não
    aprendia (acurácia de treino 0,58). O intervalo entre notas distintas é >= 1 passo;
    dígitos do mesmo número ficam praticamente colados, então 0,25 passo separa os dois.
    """
    por_corda: dict[int, list[Glifo]] = collections.defaultdict(list)
    for g in glifos:
        por_corda[g.corda].append(g)
    tokens: list[Glifo] = []
    for gs in por_corda.values():
        gs.sort(key=lambda g: g.x0)
        atual = [gs[0]]
        for g in gs[1:]:
            if g.x0 - max(x.x1 for x in atual) <= gap * passo:
                atual.append(g)
            else:
                tokens.append(_fundir(atual, passo))
                atual = [g]
        tokens.append(_fundir(atual, passo))
    tokens.sort(key=lambda g: (g.coluna, g.corda))
    return tokens


def _fundir(gs: list[Glifo], passo: float = 0.0) -> Glifo:
    hastes = sum(1 for g in gs if getattr(g, "partes_digito", 1) >= 1)
    if len(gs) == 1:
        unico = gs[0]
        if not unico.componentes:
            unico.componentes = ((unico.x0, unico.y0, unico.x1, unico.y1),)
        return unico
    return Glifo(
        x0=min(g.x0 for g in gs),
        y0=min(g.y0 for g in gs),
        x1=max(g.x1 for g in gs),
        y1=max(g.y1 for g in gs),
        corda=gs[0].corda,
        coluna=min(g.coluna for g in gs),
        area=sum(g.area for g in gs),
        partes=len(gs),
        partes_digito=hastes,
        componentes=tuple((g.x0, g.y0, g.x1, g.y1) for g in gs),
    )


def _segmentar_de_mascara(
    tinta: np.ndarray,
    n_cordas: int = 6,
    linhas_y: list[int] | None = None,
    passo: float = 0.0,
) -> Grade:
    h, w = tinta.shape
    grade = Grade(altura=h, largura=w)

    if linhas_y is None:
        linhas_y, passo = achar_cordas(tinta, n_cordas)
    grade.linhas_y = linhas_y
    grade.passo = passo
    if len(linhas_y) != n_cordas:
        grade.avisos.append(f"esperava {n_cordas} cordas, achei {len(linhas_y)}")
    if not linhas_y:
        return grade
    if passo <= 0:
        passo = float(np.median(np.diff(linhas_y))) if len(linhas_y) > 1 else 20.0
        grade.passo = passo
        grade.avisos.append("espaçamento irregular entre cordas")

    grade.barlines_x = achar_barlines(tinta, linhas_y)

    lim_x = (grade.barlines_x[0] + int(passo * 2.2)) if grade.barlines_x else 0
    grade.glifos = agrupar_tokens(
        _glifos_por_faixa(tinta, linhas_y, passo, lim_x, grade.barlines_x), passo
    )
    grade.glifos_centrados = sum(
        1
        for x in grade.glifos
        if min(abs(x.cy - ly) for ly in linhas_y) <= 0.25 * passo
    )
    # DELIMITADOR: a extração enxerga só o que cabe dentro da tablatura. Antes disto a
    # coleta guardava braço de violão, clave, texto e tira de linha como "símbolo".
    grade.glifos.sort(key=lambda g: (g.coluna, g.corda))
    return grade


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("imagem")
    ap.add_argument("--cordas", type=int, default=6)
    ap.add_argument("--debug")
    ap.add_argument("--json")
    args = ap.parse_args()

    img = cv2.imread(args.imagem, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"não consegui abrir {args.imagem}", file=sys.stderr)
        return 2
    g = segmentar(img, n_cordas=args.cordas, debug=args.debug)
    d = g.to_json()
    print(
        f"linhas_y={d['linhas_y']} passo={d['passo']:.2f} barlines={d['barlines_x']} "
        f"glifos={len(d['glifos'])} avisos={d['avisos']}"
    )
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(d, fh, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
