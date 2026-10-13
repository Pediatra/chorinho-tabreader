"""Recortes de pauta (5 linhas) de quadros reais, para a trilha "partitura" (P1).

Monta o conjunto de conferência do comparativo de leitores de partitura (OMR): 20
quadros no total. Doze vêm dos três vídeos com gabarito de tablatura conferido pelo dono
(origem ``ouro``); oito vêm de outros canais, sorteados da amostra da P0
(``data/saida/partitura/p0/amostra.jsonl``, origem ``p0``).

Para cada quadro, ``tab.partitura_pauta.achar_pautas`` acha as pautas e cada pauta vira um
recorte PNG em resolução nativa, sem nenhum processamento. Além dos recortes, saem:

- ``indice.json``: uma entrada por recorte, e uma por quadro sem pauta (``sem_pauta``);
- ``contexto_NN.jpg``: quadros inteiros com a caixa de cada recorte em vermelho, para
  conferir de onde o recorte saiu;
- ``recortes_NN.jpg``: os recortes empilhados, para conferir o que entrou em cada um.

Regra de recorte (``caixa_do_recorte``): horizontalmente, 2 entrelinhas de margem de cada
lado da pauta (a clave fica antes de ``x0``). Verticalmente, 4 entrelinhas acima da 1ª
linha e abaixo da 5ª (linhas suplementares, digitação, ligaduras), limitadas pela
estrutura horizontal vizinha. Se a vizinha é outra pauta, o corte vai ao ponto médio entre
as duas. Se é tablatura (ou o retângulo dela no censo), o corte fica uma entrelinha antes.
Estruturas são linhas longas achadas por ``estruturas_horizontais``.

Uso:
    python -m tab.partitura_recortes
"""

from __future__ import annotations

import json
import math
import random
import time
import unicodedata
from dataclasses import dataclass, field, replace
from pathlib import Path

import cv2
import numpy as np

from tab.cache import ModoCache, caminho_do_quadro, ler_quadro, pasta_do_video
from tab.caminhos import OURO_VIDEO, SAIDA, acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import (
    FRAC_FRACA,
    Pauta,
    _abrir,
    _mascaras_de_tinta,
    achar_pautas,
)

#: Seed do sorteio dos quadros B (o sorteio é determinístico).
SEMENTE = 0

#: Amostra da P0: uma linha JSON por vídeo, com os 12 quadros do censo de cada um.
AMOSTRA_P0 = SAIDA / "partitura" / "p0" / "amostra.jsonl"

#: Saída da P1: recortes, índice e folhas de conferência.
PASTA_SAIDA = SAIDA / "partitura" / "p1" / "recortes"

#: Vídeos ouro: nome do JSON em ``OURO_VIDEO`` e ids das telas usadas (None = todas).
OURO = (
    ("greensleeves_guia_de_estudio_partitura_tab_pdf", None),
    ("south_american_music_easy_guitar_tutorial_with_sheet_and_tab", None),
    (
        "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
        (1, 3, 5, 7, 9),
    ),
)

#: Canais dos quadros B, na ordem em que os recortes são numerados.
CANAIS_B = (
    "sky guitar",
    "iwaki",
    "serge kottelat",
    "transcriptor",
    "tv on guitar",
    "paolo d'angelo",
    "ギタロー ⧸ guitarous",
)

#: Quantos vídeos sortear por canal (os canais fora deste dicionário sorteiam 1).
VIDEOS_POR_CANAL = {"sky guitar": 2}

#: Classe do censo exigida num quadro B: pauta e tablatura no mesmo quadro.
CLASSE_B = "pauta+tab"

#: Margem horizontal do recorte, em entrelinhas, de cada lado da pauta.
MARGEM_X_ENTRELINHAS = 2

#: Margem vertical do recorte, em entrelinhas, acima da 1ª e abaixo da 5ª linha.
MARGEM_Y_ENTRELINHAS = 4

#: Margem vertical abaixo da 5ª linha, em entrelinhas: notas graves com linhas
#: suplementares descem mais que as agudas. Continua limitada pela vizinha de baixo.
MARGEM_Y_BAIXO_ENTRELINHAS = 6

#: Folga mínima (px) entre a pauta e uma linha para a linha contar como vizinha.
FOLGA_MIN_PX = 3.0

#: Estrutura horizontal só limita o recorte se tem pelo menos esta fração da extensão da
#: pauta. Linha de tablatura e de outra pauta passam; barra de nota e linha suplementar não.
FRACAO_ESTRUTURA_VIZINHA = 0.5

#: Corte antes da tablatura, em entrelinhas (meia entrelinha, para não cortar as cifras
#: que ficam logo acima das cordas).
MARGEM_TAB_ENTRELINHAS = 0.5

#: Extensão horizontal: uma linha é "presente" numa coluna se o cinza ali difere do fundo
#: (média das duas linhas de intervalo) por pelo menos este valor (níveis, 0-255).
CRISTA_DELTA_EXT = 20

#: Extensão horizontal: coluna é boa se tem pelo menos este número de linhas da pauta.
MIN_LINHAS_COLUNA = 3

#: Extensão horizontal: buraco tolerado, em entrelinhas (clave, cabeças, chave).
TOLERANCIA_BURACO = 3.0

#: Largura (px) de cada quadro inteiro nas folhas de contexto.
LARGURA_CONTEXTO = 960

#: Largura máxima (px) de cada recorte na folha de recortes (só reduz, nunca amplia).
LARGURA_MAX_RECORTE = 1800

#: Células por página da folha de contexto (2 x 2).
CELULAS_POR_PAGINA = 4

#: Recortes por página da folha de recortes (empilhados).
RECORTES_POR_PAGINA = 5

#: Espessura (px, em resolução nativa) e cor BGR da caixa do recorte no quadro.
ESPESSURA_CAIXA = 3
COR_CAIXA = (0, 0, 255)

#: Altura (px) da faixa de legenda, e espaço (px) entre blocos das folhas.
ALTURA_LEGENDA = 36
ESPACO = 16

#: Qualidade do JPEG das folhas de conferência.
QUALIDADE_JPEG = 90


@dataclass(frozen=True)
class FonteQuadro:
    """Um quadro a processar e de onde ele veio.

    Attributes:
        origem: ``"ouro"`` (gabarito conferido) ou ``"p0"`` (amostra do censo).
        canal: nome do canal (no ouro, o primeiro trecho do caminho do vídeo).
        video: caminho do vídeo, relativo ao acervo.
        t: instante do quadro, em segundos.
        chave: chave de retomada do vídeo (só p0).
        indice_quadro: posição do quadro em ``quadros`` da amostra (só p0).
        tela: id da tela do gabarito (só ouro).
        rect: caixa ``(x0, y0, x1, y1)`` da tablatura no censo, se o quadro tem (só p0).
    """

    origem: str
    canal: str
    video: str
    t: float
    chave: str | None = None
    indice_quadro: int | None = None
    tela: int | None = None
    rect: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class Recorte:
    """Um recorte de pauta pronto para gravar.

    Attributes:
        id: identificador ``R01``, ``R02``...
        imagem: recorte BGR em resolução nativa, contíguo.
        legenda: texto ASCII (id, canal, instante, entrelinha).
    """

    id: str
    imagem: np.ndarray
    legenda: str


@dataclass
class Celula:
    """Um quadro inteiro com as caixas dos seus recortes, para a folha de contexto.

    Attributes:
        legenda: texto ASCII da célula (ids, canal, instante).
        imagem: quadro BGR em resolução nativa.
        caixas: caixas ``(x0, y0, x1, y1)`` dos recortes, em coordenadas do quadro.
    """

    legenda: str
    imagem: np.ndarray
    caixas: list[tuple[int, int, int, int]] = field(default_factory=list)


def canal_ascii(texto: str) -> str:
    """Versão ASCII de um nome de canal, para legendas (OpenCV não desenha o resto).

    Tira os acentos (decompõe e descarta as marcas combinantes) e troca cada caractere
    não ASCII restante, como o japonês e o ``⧸``, por ``?``.

    Args:
        texto: nome do canal, em Unicode.

    Returns:
        O nome em ASCII.
    """
    saida: list[str] = []
    for caractere in unicodedata.normalize("NFKD", texto):
        if unicodedata.combining(caractere):
            continue
        saida.append(caractere if ord(caractere) < 128 else "?")
    return "".join(saida)


def carregar_amostra(caminho: Path) -> list[dict]:
    """Lê a amostra da P0 (uma linha JSON por vídeo).

    Args:
        caminho: arquivo ``amostra.jsonl``.

    Returns:
        Uma ``dict`` por vídeo, na ordem do arquivo.
    """
    with caminho.open(encoding="utf-8") as arquivo:
        return [json.loads(linha) for linha in arquivo if linha.strip()]


def escolher_quadros_b(
    amostra: list[dict],
    canais: tuple[str, ...] | list[str],
    semente: int = SEMENTE,
    videos_por_canal: dict[str, int] | None = None,
) -> list[tuple[dict, int]]:
    """Sorteia os quadros B: vídeos por canal e, em cada um, o quadro de menor ``frac``.

    Só entram vídeos do canal com pelo menos um quadro de classe ``pauta+tab``. Os vídeos
    são ordenados por ``chave``, e ``random.Random(semente)`` (um gerador novo por canal)
    sorteia ``videos_por_canal[canal]`` deles (1 por padrão). Dentro de cada vídeo escolhido
    fica o quadro ``pauta+tab`` de menor ``frac``.

    Args:
        amostra: linhas da amostra da P0 (``carregar_amostra``).
        canais: canais a sortear, na ordem de numeração.
        semente: seed do ``random.Random``.
        videos_por_canal: quantos vídeos por canal; ``None`` usa ``VIDEOS_POR_CANAL``.

    Returns:
        Pares ``(linha do vídeo, índice do quadro em quadros)``, na ordem dos canais.

    Raises:
        ValueError: se um canal tem menos vídeos elegíveis do que o pedido.
    """
    quantidades = VIDEOS_POR_CANAL if videos_por_canal is None else videos_por_canal
    escolhidos: list[tuple[dict, int]] = []
    for canal in canais:
        elegiveis = sorted(
            (
                linha
                for linha in amostra
                if linha["canal"] == canal
                and any(q["classe"] == CLASSE_B for q in linha["quadros"])
            ),
            key=lambda linha: linha["chave"],
        )
        k = quantidades.get(canal, 1)
        if len(elegiveis) < k:
            raise ValueError(
                f"canal {canal!r}: {len(elegiveis)} vídeos elegíveis, pedidos {k}"
            )
        gerador = random.Random(semente)
        for linha in gerador.sample(elegiveis, k):
            quadros = linha["quadros"]
            indices = [i for i, q in enumerate(quadros) if q["classe"] == CLASSE_B]
            escolhido = min(indices, key=lambda i: quadros[i]["frac"])
            escolhidos.append((linha, escolhido))
    return escolhidos


def fontes_ouro() -> list[FonteQuadro]:
    """Os quadros das telas do gabarito de tablatura (origem ``ouro``).

    Returns:
        Uma ``FonteQuadro`` por tela listada em ``OURO``, na ordem do gabarito.

    Raises:
        ValueError: se uma tela pedida não existe no gabarito.
    """
    fontes: list[FonteQuadro] = []
    for nome, ids in OURO:
        dados = json.loads((OURO_VIDEO / f"{nome}.json").read_text(encoding="utf-8"))
        video = dados["video"]
        telas = {int(tela["id"]): tela for tela in dados["telas"]}
        pedidas = list(telas) if ids is None else list(ids)
        for id_tela in pedidas:
            if id_tela not in telas:
                raise ValueError(f"{nome}: tela {id_tela} não existe no gabarito")
            tela = telas[id_tela]
            fontes.append(
                FonteQuadro(
                    origem="ouro",
                    canal=Path(video).parts[0],
                    video=video,
                    t=float(tela["quadro_ref_s"]),
                    tela=id_tela,
                )
            )
    return fontes


def fontes_b(escolhidos: list[tuple[dict, int]]) -> list[FonteQuadro]:
    """Converte os quadros B sorteados em ``FonteQuadro`` (origem ``p0``).

    Args:
        escolhidos: pares ``(linha do vídeo, índice do quadro)`` de ``escolher_quadros_b``.

    Returns:
        Uma ``FonteQuadro`` por par, na mesma ordem.
    """
    fontes: list[FonteQuadro] = []
    for linha, indice in escolhidos:
        quadro = linha["quadros"][indice]
        rect = tuple(int(v) for v in quadro["rect"]) if quadro["rect"] else None
        fontes.append(
            FonteQuadro(
                origem="p0",
                canal=linha["canal"],
                video=linha["arquivo"],
                t=float(quadro["t"]),
                chave=linha["chave"],
                indice_quadro=indice,
                rect=rect,
            )
        )
    return fontes


def ler_fonte(fonte: FonteQuadro) -> tuple[np.ndarray, str]:
    """Lê o quadro de uma fonte: do cache do censo se existe, senão do vídeo.

    O quadro de origem ``p0`` está no cache como ``presenca_NN.png`` (NN é o índice em
    ``quadros``). Se o arquivo falta, o quadro é lido do vídeo com ``leitor.quadro_em``,
    no mesmo instante. O quadro de origem ``ouro`` sempre vem do vídeo.

    Args:
        fonte: o quadro a ler.

    Returns:
        O quadro BGR e a origem da leitura (``"cache"`` ou ``"video"``).

    Raises:
        RuntimeError: se o ffmpeg não consegue ler o quadro do vídeo.
    """
    if fonte.origem == "p0" and fonte.chave is not None:
        pasta = pasta_do_video(fonte.chave, ModoCache())
        arquivo = caminho_do_quadro(pasta, f"presenca_{fonte.indice_quadro:02d}", "png")
        if arquivo.exists():
            return ler_quadro(arquivo), "cache"
    quadro = quadro_em(str(acervo() / fonte.video), fonte.t)
    if quadro is None:
        raise RuntimeError(f"ffmpeg não leu {fonte.video} em t={fonte.t}")
    return quadro, "video"


def _sequencias(indices: np.ndarray) -> list[tuple[int, int]]:
    """Agrupa índices consecutivos em intervalos ``(inicio, fim)``, inclusivos.

    Args:
        indices: índices inteiros em ordem crescente.

    Returns:
        Os intervalos de índices consecutivos.
    """
    if indices.size == 0:
        return []
    quebras = np.flatnonzero(np.diff(indices) > 1)
    inicios = np.concatenate(([0], quebras + 1))
    fins = np.concatenate((quebras, [indices.size - 1]))
    return [
        (int(indices[i]), int(indices[j])) for i, j in zip(inicios, fins, strict=True)
    ]


@dataclass(frozen=True)
class Estrutura:
    """Uma linha horizontal achada no quadro.

    Attributes:
        y: y central da faixa, em px.
        x0: primeira coluna com tinta da faixa.
        x1: última coluna com tinta da faixa.
    """

    y: float
    x0: int
    x1: int


def _cinza(quadro: np.ndarray) -> np.ndarray:
    """Quadro em tons de cinza (aceita BGR ou cinza).

    Args:
        quadro: quadro BGR (3 canais) ou cinza (1 canal), ``uint8``.

    Returns:
        Imagem cinza, ``uint8``.
    """
    return quadro if quadro.ndim == 2 else cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)


def _tinta_escura(cinza: np.ndarray) -> bool:
    """Diz se a tinta do quadro é escura (fundo claro), pela mediana do quadro.

    Args:
        cinza: quadro em tons de cinza.

    Returns:
        True se a mediana do cinza é de fundo claro (tinta escura).
    """
    return float(np.median(cinza)) >= 128


def estruturas_horizontais(quadro: np.ndarray) -> list[Estrutura]:
    """Linhas horizontais longas do quadro, com a extensão de cada uma.

    Usa a máscara de tinta da polaridade do fundo, aberta na horizontal como em
    ``achar_pautas``: linha de pauta, de tablatura ou traço longo sobrevive; texto, cabeça
    de nota e haste somem. Uma linha é uma faixa de linhas de pixel com contagem de tinta de
    pelo menos ``FRAC_FRACA`` da largura. A extensão é a das colunas com tinta na faixa.

    Args:
        quadro: quadro BGR (3 canais) ou cinza (1 canal), ``uint8``.

    Returns:
        Uma ``Estrutura`` por faixa, de cima para baixo.
    """
    cinza = _cinza(quadro)
    largura = cinza.shape[1]
    # Uma polaridade só, pela cor de fundo: a máscara da polaridade oposta marca o fundo
    # entre linhas densas como tinta (é o que o detector evita por polaridade).
    escura, clara = _mascaras_de_tinta(cinza)
    aberta = _abrir(escura if _tinta_escura(cinza) else clara, largura)
    contagem = np.count_nonzero(aberta, axis=1)
    estruturas: list[Estrutura] = []
    for inicio, fim in _sequencias(np.flatnonzero(contagem >= FRAC_FRACA * largura)):
        colunas = np.flatnonzero(aberta[inicio : fim + 1].any(axis=0))
        estruturas.append(
            Estrutura(
                y=(inicio + fim) / 2,
                x0=int(colunas[0]),
                x1=int(colunas[-1]),
            )
        )
    return estruturas


def _colunas_com_linhas(cinza: np.ndarray, pauta: Pauta, escura: bool) -> np.ndarray:
    """Para cada coluna, quantas das 5 linhas da pauta estão presentes ali.

    Uma linha está presente na coluna x se o mínimo do cinza em ``[y-1, y+1]`` (tinta
    escura) é ``<= ref - CRISTA_DELTA``, com ``ref`` a média do cinza nas linhas de
    intervalo ``y - e/2`` e ``y + e/2``. Para tinta clara, a comparação é invertida.

    Args:
        cinza: quadro em tons de cinza.
        pauta: a pauta (define as 5 linhas e a entrelinha).
        escura: polaridade da tinta.

    Returns:
        Vetor ``int`` com uma contagem (0 a 5) por coluna.
    """
    altura = cinza.shape[0]
    e = pauta.entrelinha
    meia = round(e / 2)
    presentes = np.zeros(cinza.shape[1], dtype=np.int64)
    for y in pauta.ys:
        ya = min(max(y - meia, 0), altura - 1)
        yb = min(max(y + meia, 0), altura - 1)
        ref = (cinza[ya].astype(np.int32) + cinza[yb].astype(np.int32)) / 2
        faixa = cinza[max(y - 1, 0) : min(y + 2, altura)].astype(np.int32)
        if escura:
            presente = faixa.min(axis=0) <= ref - CRISTA_DELTA_EXT
        else:
            presente = faixa.max(axis=0) >= ref + CRISTA_DELTA_EXT
        presentes += presente.astype(np.int64)
    return presentes


def _estender(ok: np.ndarray, inicio: int, passo: int, tolerancia: float) -> int:
    """Caminha de ``inicio`` no sentido ``passo`` enquanto as colunas têm linhas.

    Tolera buracos de até ``tolerancia`` colunas seguidas; para no primeiro buraco maior
    que isso e devolve a última coluna boa antes dele.

    Args:
        ok: vetor de colunas boas (``True`` = pelo menos ``MIN_LINHAS_COLUNA`` linhas).
        inicio: coluna de partida (já é boa).
        passo: -1 para a esquerda, +1 para a direita.
        tolerancia: maior buraco aceito, em colunas.

    Returns:
        A última coluna boa da caminhada.
    """
    ultima = inicio
    buraco = 0
    x = inicio
    while 0 <= x < ok.size:
        if ok[x]:
            ultima = x
            buraco = 0
        else:
            buraco += 1
            if buraco > tolerancia:
                break
        x += passo
    return ultima


def extensao_horizontal(cinza: np.ndarray, pauta: Pauta) -> tuple[int, int]:
    """Estende a pauta para os dois lados enquanto as 5 linhas continuam no cinza.

    Parte de ``x0`` e ``x1`` da pauta (início e fim comuns das linhas, da máscara aberta).
    Uma coluna é boa se ao menos ``MIN_LINHAS_COLUNA`` das 5 linhas estão presentes nela.
    Caminha para a esquerda e para a direita tolerando buracos de até ``3 * entrelinha``
    colunas (clave, cabeças de nota, chave). A extensão é a última coluna boa antes de um
    buraco maior que isso.

    Args:
        cinza: quadro em tons de cinza.
        pauta: a pauta achada por ``achar_pautas``.

    Returns:
        ``(x0, x1)``, a extensão da pauta (``x1`` inclusivo, sem margem).
    """
    escura = _tinta_escura(cinza)
    presentes = _colunas_com_linhas(cinza, pauta, escura)
    ok = presentes >= MIN_LINHAS_COLUNA
    tolerancia = TOLERANCIA_BURACO * pauta.entrelinha
    x0 = _estender(ok, pauta.x0, -1, tolerancia)
    x1 = _estender(ok, pauta.x1, +1, tolerancia)
    return x0, x1


@dataclass(frozen=True)
class Vizinha:
    """Estrutura horizontal vizinha de uma pauta, acima ou abaixo.

    Attributes:
        y: y da estrutura, em px (a base dela, se está acima; o topo, se está abaixo).
        de_pauta: True se a estrutura é linha de outra pauta do quadro; False se é
            tablatura ou outra linha horizontal (incluindo o retângulo do censo).
    """

    y: float
    de_pauta: bool


def _de_outra_pauta(y: float, outras: list[Pauta]) -> bool:
    """Diz se uma linha horizontal pertence a alguma das outras pautas do quadro.

    Args:
        y: y da linha, em px.
        outras: as demais pautas do quadro.

    Returns:
        True se ``y`` cai dentro da faixa (1ª a 5ª linha, com folga) de alguma pauta.
    """
    return any(
        outra.ys[0] - max(FOLGA_MIN_PX, outra.entrelinha / 2)
        <= y
        <= outra.ys[4] + max(FOLGA_MIN_PX, outra.entrelinha / 2)
        for outra in outras
    )


def candidatos_verticais(
    pauta: Pauta,
    estruturas: list[Estrutura],
    rect: tuple[int, int, int, int] | None,
    outras: list[Pauta] | None = None,
) -> tuple[Vizinha | None, Vizinha | None]:
    """Estrutura horizontal mais próxima acima e abaixo da pauta.

    Ignora as linhas da própria pauta (até a folga ``max(FOLGA_MIN_PX, entrelinha / 2)``
    além da 1ª e da 5ª). Só conta estrutura com extensão de pelo menos
    ``FRACAO_ESTRUTURA_VIZINHA`` da extensão da pauta: barra de nota, linha suplementar e
    texto curto não limitam o recorte; linha de tablatura e de outra pauta, sim. O
    retângulo da tablatura do censo, quando existe, entra como uma estrutura a mais (a base
    dele acima, o topo dele abaixo). Cada vizinha diz se é linha de outra pauta
    (``de_pauta``), porque a regra de corte é diferente para cada caso.

    Args:
        pauta: a pauta do recorte.
        estruturas: linhas horizontais do quadro (``estruturas_horizontais``).
        rect: caixa da tablatura no censo ``(x0, y0, x1, y1)``, ou ``None``.
        outras: as demais pautas do quadro (para marcar ``de_pauta``).

    Returns:
        ``(acima, abaixo)``: a vizinha de cima (a mais baixa entre as de cima) e a de
        baixo (a mais alta entre as de baixo); ``None`` se não há estrutura naquele lado.
    """
    outras = outras or []
    folga = max(FOLGA_MIN_PX, pauta.entrelinha / 2)
    minimo = FRACAO_ESTRUTURA_VIZINHA * (pauta.x1 - pauta.x0)
    longas = [e.y for e in estruturas if e.x1 - e.x0 >= minimo]
    acima = [y for y in longas if y < pauta.ys[0] - folga]
    abaixo = [y for y in longas if y > pauta.ys[4] + folga]
    if rect is not None:
        _, ry0, _, ry1 = rect
        if ry0 > pauta.ys[4] + folga:
            abaixo.append(float(ry0))
        if ry1 - 1 < pauta.ys[0] - folga:
            acima.append(float(ry1 - 1))
    vizinha_acima = None
    if acima:
        y_acima = max(acima)
        vizinha_acima = Vizinha(y_acima, _de_outra_pauta(y_acima, outras))
    vizinha_abaixo = None
    if abaixo:
        y_abaixo = min(abaixo)
        vizinha_abaixo = Vizinha(y_abaixo, _de_outra_pauta(y_abaixo, outras))
    return vizinha_acima, vizinha_abaixo


def caixa_do_recorte(
    pauta: Pauta,
    largura: int,
    altura: int,
    acima: Vizinha | None,
    abaixo: Vizinha | None,
) -> tuple[int, int, int, int]:
    """Caixa do recorte de uma pauta, em coordenadas do quadro.

    Horizontal: ``MARGEM_X_ENTRELINHAS`` entrelinhas de cada lado de ``x0`` e ``x1``.
    Vertical: ``MARGEM_Y_ENTRELINHAS`` entrelinhas acima de ``ys[0]`` e abaixo de ``ys[4]``,
    limitadas pela vizinha de cada lado:

    - vizinha que é outra pauta: o corte fica no ponto médio entre as duas (as notas de
      uma e de outra não se misturam);
    - vizinha que é tablatura ou outra estrutura: o corte fica ``MARGEM_TAB_ENTRELINHAS``
      entrelinha antes dela (meia entrelinha). O ponto médio cortava as hastes e as notas
      da voz de baixo que descem da pauta.

    Tudo é limitado ao quadro e nunca corta a própria pauta.

    Args:
        pauta: a pauta do recorte.
        largura: largura do quadro, em px.
        altura: altura do quadro, em px.
        acima: vizinha de cima (``candidatos_verticais``), ou ``None``.
        abaixo: vizinha de baixo (``candidatos_verticais``), ou ``None``.

    Returns:
        ``(x0, y0, x1, y1)`` com ``x1`` e ``y1`` exclusivos (fatia de array: ``q[y0:y1,
        x0:x1]``).
    """
    e = pauta.entrelinha
    margem_x = round(MARGEM_X_ENTRELINHAS * e)
    margem_y = round(MARGEM_Y_ENTRELINHAS * e)
    margem_base = round(MARGEM_Y_BAIXO_ENTRELINHAS * e)
    topo = pauta.ys[0] - margem_y
    base = pauta.ys[4] + margem_base
    if acima is not None:
        if acima.de_pauta:
            topo = max(topo, math.ceil((pauta.ys[0] + acima.y) / 2))
        else:
            topo = max(topo, math.ceil(acima.y + MARGEM_TAB_ENTRELINHAS * e))
    if abaixo is not None:
        if abaixo.de_pauta:
            base = min(base, math.floor((pauta.ys[4] + abaixo.y) / 2))
        else:
            base = min(base, math.floor(abaixo.y - MARGEM_TAB_ENTRELINHAS * e))
    topo = min(topo, pauta.ys[0])
    base = max(base, pauta.ys[4])
    x0 = max(0, pauta.x0 - margem_x)
    x1 = min(largura, pauta.x1 + margem_x + 1)
    y0 = max(0, topo)
    y1 = min(altura, base + 1)
    return (x0, y0, x1, y1)


def _entrada_base(fonte: FonteQuadro, fonte_quadro: str) -> dict:
    """Campos do índice comuns a todos os recortes e quadros de uma fonte.

    Args:
        fonte: o quadro.
        fonte_quadro: ``"cache"`` ou ``"video"``, de onde o quadro foi lido.

    Returns:
        Um ``dict`` com origem, canal, vídeo, instante e os campos próprios da origem.
    """
    base: dict = {
        "origem": fonte.origem,
        "canal": fonte.canal,
        "video": fonte.video,
        "t": fonte.t,
        "fonte_quadro": fonte_quadro,
    }
    if fonte.origem == "ouro":
        base["tela"] = fonte.tela
    else:
        base["chave"] = fonte.chave
        base["indice_quadro"] = fonte.indice_quadro
        base["rect"] = list(fonte.rect) if fonte.rect is not None else None
    return base


def processar_quadro(
    fonte: FonteQuadro,
    quadro: np.ndarray,
    fonte_quadro: str,
    primeiro_numero: int,
) -> tuple[list[dict], list[Recorte], Celula]:
    """Acha as pautas de um quadro e recorta cada uma.

    Args:
        fonte: de onde veio o quadro.
        quadro: quadro BGR em resolução nativa.
        fonte_quadro: ``"cache"`` ou ``"video"``.
        primeiro_numero: número do primeiro recorte deste quadro (``R{numero:02d}``).

    Returns:
        ``(entradas do índice, recortes, célula de contexto)``. Quadro sem pauta gera uma
        entrada com ``sem_pauta`` e nenhum recorte.
    """
    altura, largura = quadro.shape[:2]
    base = _entrada_base(fonte, fonte_quadro)
    pautas = achar_pautas(quadro)
    if not pautas:
        entrada = {
            **base,
            "id": None,
            "sem_pauta": True,
            "largura_quadro": largura,
            "altura_quadro": altura,
        }
        celula = Celula(
            legenda=f"SEM PAUTA | {canal_ascii(fonte.canal)} | t={fonte.t:.2f}s",
            imagem=quadro,
        )
        return [entrada], [], celula

    estruturas = estruturas_horizontais(quadro)
    cinza = _cinza(quadro)
    entradas: list[dict] = []
    recortes: list[Recorte] = []
    caixas: list[tuple[int, int, int, int]] = []
    ids: list[str] = []
    for k, pauta_achada in enumerate(pautas):
        ex0, ex1 = extensao_horizontal(cinza, pauta_achada)
        pauta = replace(pauta_achada, x0=ex0, x1=ex1)
        outras = [p for j, p in enumerate(pautas) if j != k]
        acima, abaixo = candidatos_verticais(pauta, estruturas, fonte.rect, outras)
        x0, y0, x1, y1 = caixa_do_recorte(pauta, largura, altura, acima, abaixo)
        identificador = f"R{primeiro_numero + k:02d}"
        ids.append(identificador)
        caixas.append((x0, y0, x1, y1))
        legenda = (
            f"{identificador} | {canal_ascii(fonte.canal)} | t={fonte.t:.2f}s"
            f" | e={pauta.entrelinha:.1f}px"
        )
        recortes.append(
            Recorte(
                id=identificador,
                imagem=np.ascontiguousarray(quadro[y0:y1, x0:x1]),
                legenda=legenda,
            )
        )
        entradas.append(
            {
                **base,
                "id": identificador,
                "sem_pauta": False,
                "pauta_no_quadro": k,
                "ys": list(pauta.ys),
                "entrelinha": round(pauta.entrelinha, 2),
                "caixa_recorte": [x0, y0, x1, y1],
                "largura": x1 - x0,
                "altura": y1 - y0,
                "largura_quadro": largura,
                "altura_quadro": altura,
            }
        )
    celula = Celula(
        legenda=(f"{' '.join(ids)} | {canal_ascii(fonte.canal)} | t={fonte.t:.2f}s"),
        imagem=quadro,
        caixas=caixas,
    )
    return entradas, recortes, celula


def _paginas(itens: list, por_pagina: int) -> list[list]:
    """Divide uma lista em páginas de ``por_pagina`` itens.

    Args:
        itens: itens a paginar.
        por_pagina: itens por página.

    Returns:
        As páginas, na ordem.
    """
    return [itens[i : i + por_pagina] for i in range(0, len(itens), por_pagina)]


def _redimensionar(imagem: np.ndarray, largura: int) -> np.ndarray:
    """Redimensiona mantendo a proporção até a largura dada (só para exibição).

    Args:
        imagem: imagem BGR.
        largura: largura de saída, em px.

    Returns:
        A imagem redimensionada.
    """
    altura, largura_original = imagem.shape[:2]
    nova_altura = max(1, round(altura * largura / largura_original))
    return cv2.resize(imagem, (largura, nova_altura), interpolation=cv2.INTER_AREA)


def _desenhar_celula(celula: Celula) -> np.ndarray:
    """Quadro inteiro com as caixas em vermelho, reduzido para ``LARGURA_CONTEXTO``.

    As caixas são desenhadas em resolução nativa (espessura ``ESPESSURA_CAIXA``) e só
    depois o quadro é reduzido, como manda a folha de conferência.

    Args:
        celula: quadro e caixas.

    Returns:
        A imagem da célula, sem legenda.
    """
    imagem = celula.imagem.copy()
    for x0, y0, x1, y1 in celula.caixas:
        cv2.rectangle(imagem, (x0, y0), (x1 - 1, y1 - 1), COR_CAIXA, ESPESSURA_CAIXA)
    return _redimensionar(imagem, LARGURA_CONTEXTO)


def folha_contexto(celulas: list[Celula], pasta: Path) -> None:
    """Grava as folhas de contexto (quadros inteiros, 4 por página, 2 x 2).

    Args:
        celulas: uma célula por quadro, na ordem da execução.
        pasta: diretório de saída.
    """
    passo_y = ALTURA_LEGENDA
    for numero, grupo in enumerate(_paginas(celulas, CELULAS_POR_PAGINA), start=1):
        desenhadas = [_desenhar_celula(celula) for celula in grupo]
        altura_celula = max(img.shape[0] for img in desenhadas)
        bloco_y = passo_y + altura_celula + ESPACO
        linhas = math.ceil(len(grupo) / 2)
        folha = np.full(
            (linhas * bloco_y, 2 * LARGURA_CONTEXTO + ESPACO, 3), 255, np.uint8
        )
        for k, (celula, img) in enumerate(zip(grupo, desenhadas, strict=True)):
            y = (k // 2) * bloco_y
            x = (k % 2) * (LARGURA_CONTEXTO + ESPACO)
            cv2.putText(
                folha,
                celula.legenda,
                (x + 8, y + ALTURA_LEGENDA - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )
            folha[y + passo_y : y + passo_y + img.shape[0], x : x + img.shape[1]] = img
        cv2.imwrite(
            str(pasta / f"contexto_{numero:02d}.jpg"),
            folha,
            [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG],
        )


def folha_recortes(recortes: list[Recorte], pasta: Path) -> None:
    """Grava as folhas de recortes (5 por página, empilhados, com o id escrito).

    Cada recorte é reduzido para no máximo ``LARGURA_MAX_RECORTE`` de largura, só para
    exibição. O PNG gravado em ``recortes/`` fica em resolução nativa.

    Args:
        recortes: recortes na ordem de numeração.
        pasta: diretório de saída.
    """
    for numero, grupo in enumerate(_paginas(recortes, RECORTES_POR_PAGINA), start=1):
        blocos = [
            _redimensionar(r.imagem, min(r.imagem.shape[1], LARGURA_MAX_RECORTE))
            for r in grupo
        ]
        largura = max(b.shape[1] for b in blocos)
        altura = sum(ALTURA_LEGENDA + b.shape[0] + ESPACO for b in blocos)
        folha = np.full((altura, largura, 3), 255, np.uint8)
        y = 0
        for recorte, bloco in zip(grupo, blocos, strict=True):
            cv2.putText(
                folha,
                recorte.legenda,
                (8, y + ALTURA_LEGENDA - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )
            folha[
                y + ALTURA_LEGENDA : y + ALTURA_LEGENDA + bloco.shape[0],
                : bloco.shape[1],
            ] = bloco
            y += ALTURA_LEGENDA + bloco.shape[0] + ESPACO
        cv2.imwrite(
            str(pasta / f"recortes_{numero:02d}.jpg"),
            folha,
            [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG],
        )


def limpar_saida(pasta: Path) -> None:
    """Apaga o que uma execução anterior deixou na pasta de saída da P1.

    Só remove os arquivos que este módulo grava (``R*.png``, ``contexto_*.jpg``,
    ``recortes_*.jpg`` e ``indice.json``).

    Args:
        pasta: diretório de saída.
    """
    for padrao in ("R*.png", "contexto_*.jpg", "recortes_*.jpg", "indice.json"):
        for arquivo in pasta.glob(padrao):
            arquivo.unlink()


def main() -> None:
    """Gera os recortes, o índice e as folhas de conferência da P1 em ``PASTA_SAIDA``."""
    inicio = time.perf_counter()
    amostra = carregar_amostra(AMOSTRA_P0)
    fontes = fontes_ouro() + fontes_b(escolher_quadros_b(amostra, CANAIS_B))
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    limpar_saida(PASTA_SAIDA)

    indice: list[dict] = []
    recortes: list[Recorte] = []
    celulas: list[Celula] = []
    for fonte in fontes:
        quadro, fonte_quadro = ler_fonte(fonte)
        entradas, novos, celula = processar_quadro(
            fonte, quadro, fonte_quadro, len(recortes) + 1
        )
        indice.extend(entradas)
        recortes.extend(novos)
        celulas.append(celula)
        for recorte in novos:
            cv2.imwrite(str(PASTA_SAIDA / f"{recorte.id}.png"), recorte.imagem)

    (PASTA_SAIDA / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    folha_contexto(celulas, PASTA_SAIDA)
    folha_recortes(recortes, PASTA_SAIDA)

    sem_pauta = [e["canal"] for e in indice if e["sem_pauta"]]
    tempo = time.perf_counter() - inicio
    print(
        f"{len(fontes)} quadros, {len(recortes)} recortes, "
        f"{len(sem_pauta)} quadros sem pauta, {tempo:.1f} s"
    )
    print(f"saída: {PASTA_SAIDA}")


if __name__ == "__main__":
    main()
