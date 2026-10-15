"""Detector de pauta de 5 linhas em quadros de vídeo-aula (trilha "partitura").

A pauta é um grupo de 5 linhas horizontais longas, equiespaçadas e com a mesma extensão.
A tablatura tem 6 linhas no mesmo formato: por isso um grupo de 5 é rejeitado quando há
uma 6ª linha a uma entrelinha de distância, sobreposta horizontalmente. Não usa aprendizado:
é geometria determinística sobre a máscara de tinta.

Passos (ver ``achar_pautas``):

1. máscara de tinta nas duas polaridades (escuro em claro e claro em escuro), por
   limiar adaptativo;
2. abertura morfológica horizontal, que apaga cabeças de nota, hastes, texto e diagonais;
3. perfil de linhas de pixel: linhas fortes (muita tinta) e fracas (tinta média);
4. grupos de 5 linhas fortes consecutivas com espaçamento regular;
   depois, grupos de 4 linhas fortes livres em que a 5ª, faltante (linha dividida
   entre duas linhas de pixel e apagada pela abertura, ou na borda), é completada por
   espaçamento e tem de passar no teste de crista (``_completar_grupos_de_quatro``);
5. teste de crista no cinza: cada linha tem de ser mais escura (ou mais clara, na
   polaridade clara) que as linhas vizinhas a ``ceil(espessura / 2) + CRISTA_FOLGA``
   px. Fundo branco entre duas linhas escuras não é crista;
6. rejeição de grupo com 6ª linha a uma entrelinha, sobreposta: pela lista de linhas
   (se a linha for fina o bastante) ou pela janela da máscara aberta (se a linha for grossa
   ou borrada, e por isso descartada no passo 3). Só na polaridade do próprio grupo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

#: Tamanho (px) da vizinhança do limiar adaptativo (deve ser ímpar).
BLOCO_ADAPTATIVO = 31

#: Subtraído da média local no limiar: quanto a tinta precisa ser mais escura que a vizinhança.
C_ADAPTATIVO = 10

#: Comprimento mínimo da linha horizontal, como fração da largura do quadro.
FRAC_ABERTURA = 0.04

#: Comprimento mínimo absoluto (px) da linha horizontal da abertura.
ABERTURA_MIN_PX = 40

#: Linha de pixel é "forte" com contagem de tinta >= esta fração da largura.
FRAC_FORTE = 0.15

#: Linha de pixel é "fraca" com contagem de tinta >= esta fração da largura.
FRAC_FRACA = 0.05

#: Espessura máxima (px) de uma linha; faixa mais grossa não é linha de pauta. Era 4: a
#: Gymnopédie (robert lunn), com entrelinha de 20 px, tem linhas de 4 a 5 px e era perdida.
ESPESSURA_MAX = 6

#: Folga (px) da comparação de espessura (``_espessura_limite``): uma linha é "parecida"
#: com a pauta de espessura mediana ``t`` até ``t + ESPESSURA_FOLGA``. Medido no acervo:
#: barra de colcheias de 5 a 6 px junto de linhas de 2 a 3 px (iwaki, sky guitar) fica de
#: fora; a 6ª linha borrada da tab (5 px, linhas de 3 px) e a Gymnopédie (4 a 5 px) ficam.
ESPESSURA_FOLGA = 2

#: Intervalo mínimo e máximo (px) entre duas linhas consecutivas de uma pauta.
ENTRE_MIN = 5
ENTRE_MAX = 40

#: Tolerância dos intervalos: max(TOL_ABS, TOL_REL * mediana).
TOL_ABS = 1.5
TOL_REL = 0.12

#: Sobreposição horizontal mínima das 5 linhas, como fração da menor extensão.
SOBREP_GRUPO = 0.70

#: Extensão horizontal comum mínima, como fração da largura do quadro.
EXT_MIN_FRAC = 0.20

#: Sobreposição mínima (fração do comprimento da 6ª linha, ou da extensão da pauta na
#: janela) para a 6ª linha contar como tablatura.
SOBREP_TAB = 0.50

#: Folga (px) além da meia espessura da linha até as vizinhas do teste de crista: a
#: vizinha fica a ``ceil(espessura / 2) + CRISTA_FOLGA`` px (3 px para linha de 2 px).
CRISTA_FOLGA = 2

#: Diferença mínima de cinza (níveis, 0-255) entre a linha e cada vizinha, para ser crista.
#: Linha de tablatura cinza (120) em fundo branco passa com folga; fundo branco entre duas
#: linhas escuras, não.
CRISTA_DELTA = 20

#: Fração mínima das colunas da pauta em que a linha tem de ser crista (0,5 = a maioria).
CRISTA_FRAC = 0.5

#: Pautas com todas as 5 ys a até esta distância (px) são a mesma pauta.
DUPLICATA_PX = 2

#: Linhas por pauta.
N_LINHAS = 5


@dataclass(frozen=True)
class Pauta:
    """Uma pauta de 5 linhas achada num quadro.

    Attributes:
        ys: y central de cada linha, de cima para baixo.
        entrelinha: mediana dos 4 intervalos, em px.
        x0: início horizontal comum das 5 linhas.
        x1: fim horizontal comum das 5 linhas.
    """

    ys: tuple[int, int, int, int, int]
    entrelinha: float
    x0: int
    x1: int

    @property
    def caixa(self) -> tuple[int, int, int, int]:
        """Caixa da pauta, do topo da primeira linha à base da última.

        Returns:
            ``(x0, y0, x1, y1)`` com ``y0 = ys[0]`` e ``y1 = ys[4]``.
        """
        return (self.x0, self.ys[0], self.x1, self.ys[4])


@dataclass(frozen=True)
class _Linha:
    """Linha horizontal achada no perfil de pixels.

    Attributes:
        y: centro vertical, em px.
        x0: primeira coluna com tinta.
        x1: última coluna com tinta.
        forte: se a contagem de tinta chega a ``FRAC_FORTE`` da largura.
        escura: se a linha veio da máscara de tinta escura (False: clara).
        espessura: linhas de pixel do núcleo da linha.
    """

    y: float
    x0: int
    x1: int
    forte: bool
    escura: bool
    espessura: int = 1


def achar_pautas(quadro: np.ndarray) -> list[Pauta]:
    """Acha as pautas de 5 linhas de um quadro, ordenadas por y.

    Args:
        quadro: quadro BGR (3 canais) ou cinza (1 canal), ``uint8``.

    Returns:
        As pautas achadas, da mais alta para a mais baixa. Lista vazia se não há pauta.
    """
    cinza = quadro if quadro.ndim == 2 else cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
    largura = cinza.shape[1]
    abertas = [_abrir(mascara, largura) for mascara in _mascaras_de_tinta(cinza)]
    linhas_por_polaridade = [
        _linhas_da_abertura(aberta, largura, escura=(k == 0))
        for k, aberta in enumerate(abertas)
    ]
    encontradas: list[Pauta] = []
    for linhas, aberta in zip(linhas_por_polaridade, abertas, strict=True):
        encontradas.extend(_grupos_de_cinco(linhas, aberta, cinza, largura))
    encontradas.sort(key=lambda pauta: pauta.ys[0])
    return _sem_duplicatas(encontradas)


def classe_do_quadro(n_pautas: int, tem_tab: bool) -> str:
    """Classifica um quadro pela presença de pauta e de tablatura.

    Args:
        n_pautas: quantas pautas o detector achou no quadro.
        tem_tab: se o censo marcou tablatura no quadro.

    Returns:
        ``"pauta+tab"``, ``"so_pauta"``, ``"so_tab"`` ou ``"nenhum"``.
    """
    if n_pautas > 0 and tem_tab:
        return "pauta+tab"
    if n_pautas > 0:
        return "so_pauta"
    if tem_tab:
        return "so_tab"
    return "nenhum"


def classe_do_video(classes_dos_quadros: list[str]) -> str:
    """Classifica um vídeo pelo melhor achado entre seus quadros.

    A ordem de precedência é ``pauta+tab``, ``so_pauta``, ``so_tab`` e ``nenhum``:
    basta um quadro com pauta para o vídeo ter pauta.

    Args:
        classes_dos_quadros: as classes de cada quadro (``classe_do_quadro``).

    Returns:
        A classe do vídeo.
    """
    for classe in ("pauta+tab", "so_pauta", "so_tab"):
        if classe in classes_dos_quadros:
            return classe
    return "nenhum"


def _mascaras_de_tinta(cinza: np.ndarray) -> list[np.ndarray]:
    """Máscaras de tinta escura em fundo claro e de tinta clara em fundo escuro.

    Args:
        cinza: quadro em tons de cinza, ``uint8``.

    Returns:
        Duas máscaras ``uint8`` (255 = tinta): a escura primeiro, depois a clara.
    """
    escura = cv2.adaptiveThreshold(
        cinza,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        BLOCO_ADAPTATIVO,
        C_ADAPTATIVO,
    )
    clara = cv2.adaptiveThreshold(
        cv2.bitwise_not(cinza),
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        BLOCO_ADAPTATIVO,
        C_ADAPTATIVO,
    )
    return [escura, clara]


def _abrir(mascara: np.ndarray, largura: int) -> np.ndarray:
    """Abertura morfológica horizontal: só sobrevivem traços longos na horizontal.

    Args:
        mascara: máscara de tinta, ``uint8`` (255 = tinta).
        largura: largura do quadro, em px.

    Returns:
        A máscara aberta, ``uint8``.
    """
    comprimento = max(ABERTURA_MIN_PX, round(FRAC_ABERTURA * largura))
    nucleo = cv2.getStructuringElement(cv2.MORPH_RECT, (comprimento, 1))
    return cv2.morphologyEx(mascara, cv2.MORPH_OPEN, nucleo)


def _linhas_da_mascara(
    mascara: np.ndarray, largura: int, escura: bool = True
) -> list[_Linha]:
    """Linhas horizontais longas de uma máscara de tinta (abre a máscara antes).

    Args:
        mascara: máscara de tinta, ``uint8`` (255 = tinta).
        largura: largura do quadro, em px.
        escura: polaridade da máscara (True: tinta escura).

    Returns:
        As linhas fortes e fracas, de cima para baixo.
    """
    return _linhas_da_abertura(_abrir(mascara, largura), largura, escura)


def _linhas_da_abertura(aberta: np.ndarray, largura: int, escura: bool) -> list[_Linha]:
    """Linhas horizontais de uma máscara já aberta, pelo perfil de pixels.

    Args:
        aberta: máscara aberta (``_abrir``), ``uint8``.
        largura: largura do quadro, em px.
        escura: polaridade da máscara (True: tinta escura).

    Returns:
        As linhas fortes e fracas, de cima para baixo.
    """
    contagem = np.count_nonzero(aberta, axis=1)
    limiar_forte = FRAC_FORTE * largura
    limiar_fraca = FRAC_FRACA * largura
    linhas: list[_Linha] = []
    for a, b in _sequencias(np.flatnonzero(contagem >= limiar_fraca)):
        # A espessura é medida no núcleo da sequência (linhas de pixel com pelo menos
        # metade da contagem máxima dela). Um objeto lateral de contagem constante
        # (chave, colchete) engrossa a sequência, mas não o núcleo da linha de pauta.
        limiar_nucleo = 0.5 * contagem[a : b + 1].max()
        for ia, ib in _sequencias(np.flatnonzero(contagem[a : b + 1] >= limiar_nucleo)):
            inicio, fim = a + ia, a + ib
            if fim - inicio + 1 > ESPESSURA_MAX:
                continue
            colunas = np.flatnonzero(aberta[inicio : fim + 1].any(axis=0))
            linhas.append(
                _Linha(
                    y=(inicio + fim) / 2,
                    x0=int(colunas[0]),
                    x1=int(colunas[-1]),
                    forte=bool(contagem[inicio : fim + 1].max() >= limiar_forte),
                    escura=escura,
                    espessura=fim - inicio + 1,
                )
            )
    return linhas


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


def _grupos_de_cinco(
    linhas: list[_Linha],
    aberta: np.ndarray,
    cinza: np.ndarray,
    largura: int,
) -> list[Pauta]:
    """Procura pautas entre as linhas fortes de uma polaridade, pulando as já usadas.

    Primeiro passada de grupos de 5 linhas fortes consecutivas; depois, passada de
    grupos de 4 com a 5ª linha completada (``_completar_grupos_de_quatro``), só entre as
    linhas fortes que a primeira passada não usou.

    A checagem da 6ª linha usa só a polaridade do grupo: a 6ª linha de uma tablatura escura
    é tinta escura. A faixa que o limiar adaptativo desenha nos espaços entre linhas juntas,
    na máscara da polaridade oposta, geraria rejeições falsas de pautas reais.

    Args:
        linhas: linhas fortes e fracas da polaridade em análise, de cima para baixo.
        aberta: máscara aberta da mesma polaridade (para a janela da 6ª linha).
        cinza: quadro em tons de cinza (para o teste de crista).
        largura: largura do quadro, em px.

    Returns:
        As pautas aceitas, de cima para baixo.
    """
    fortes = [linha for linha in linhas if linha.forte]
    pautas: list[Pauta] = []
    i = 0
    while i + N_LINHAS <= len(fortes):
        pauta = _pauta_do_grupo(fortes[i : i + N_LINHAS], largura)
        grupo = fortes[i : i + N_LINHAS]
        espessuras = [linha.espessura for linha in grupo]
        mediana = round(float(np.median(espessuras)))
        if (
            pauta is not None
            and max(espessuras) <= _espessura_limite(mediana)
            and _linhas_sao_crista(grupo, pauta, cinza)
            and not _ha_sexta_linha(pauta, linhas, largura, mediana)
            and not _ha_sexta_na_janela(pauta, aberta)
        ):
            pautas.append(pauta)
            i += N_LINHAS
        else:
            i += 1
    novas = _completar_grupos_de_quatro(linhas, aberta, cinza, largura, pautas)
    return sorted([*pautas, *novas], key=lambda pauta: pauta.ys[0])


def _completar_grupos_de_quatro(
    linhas: list[_Linha],
    aberta: np.ndarray,
    cinza: np.ndarray,
    largura: int,
    pautas_aceitas: list[Pauta],
) -> list[Pauta]:
    """Completa pautas de 4 linhas fortes achadas, com a 5ª linha faltante.

    Considera só as linhas fortes que nenhuma pauta de ``pautas_aceitas`` usou. Anda por
    janelas de 4 linhas livres consecutivas (em ordem de y); numa janela aceita, pula as 4
    linhas inteiras. Uma janela é aceita quando ``_completar_janela`` acha a pauta.

    Args:
        linhas: linhas fortes e fracas da polaridade em análise, de cima para baixo.
        aberta: máscara aberta da mesma polaridade (para a janela da 6ª linha).
        cinza: quadro em tons de cinza (para o teste de crista).
        largura: largura do quadro, em px.
        pautas_aceitas: pautas já aceitas pela passada de 5 linhas nesta polaridade.

    Returns:
        As pautas completadas, de cima para baixo.
    """
    usadas = {y for pauta in pautas_aceitas for y in pauta.ys}
    livres = [linha for linha in linhas if linha.forte and round(linha.y) not in usadas]
    novas: list[Pauta] = []
    i = 0
    while i + N_LINHAS - 1 <= len(livres):
        pauta = _completar_janela(
            livres[i : i + N_LINHAS - 1], linhas, aberta, cinza, largura
        )
        if pauta is not None:
            novas.append(pauta)
            i += N_LINHAS - 1
        else:
            i += 1
    return novas


def _completar_janela(
    janela: list[_Linha],
    linhas: list[_Linha],
    aberta: np.ndarray,
    cinza: np.ndarray,
    largura: int,
) -> Pauta | None:
    """Tenta completar uma janela de 4 linhas fortes numa pauta de 5.

    A 5ª linha vem de ``_linhas_faltantes``. Só é candidata a que, com as 4, forma uma
    pauta geometricamente válida e passa no teste de crista. Exatamente uma candidata
    tem de passar; depois disso valem os mesmos testes do laço de 5 linhas
    (``_pauta_do_grupo``, espessura, crista, 6ª linha).

    Args:
        janela: as 4 linhas fortes livres, de cima para baixo.
        linhas: linhas fortes e fracas da polaridade (para a 6ª linha).
        aberta: máscara aberta da mesma polaridade.
        cinza: quadro em tons de cinza.
        largura: largura do quadro, em px.

    Returns:
        A pauta de 5 linhas, ou ``None`` se a janela não vira pauta.
    """
    escura = janela[0].escura
    espessura = round(float(np.median([linha.espessura for linha in janela])))
    x0 = max(linha.x0 for linha in janela)
    x1 = min(linha.x1 for linha in janela)
    passam: list[tuple[list[_Linha], Pauta]] = []
    for y in _linhas_faltantes([linha.y for linha in janela]):
        nova = _Linha(y=y, x0=x0, x1=x1, forte=True, escura=escura, espessura=espessura)
        grupo = sorted([*janela, nova], key=lambda linha: linha.y)
        pauta = _pauta_do_grupo(grupo, largura)
        if pauta is not None and _linha_e_crista(nova, pauta, cinza):
            passam.append((grupo, pauta))
    if len(passam) != 1:
        return None
    grupo, pauta = passam[0]
    espessuras = [linha.espessura for linha in grupo]
    mediana = round(float(np.median(espessuras)))
    if max(espessuras) > _espessura_limite(mediana):
        return None
    if not _linhas_sao_crista(grupo, pauta, cinza):
        return None
    if _ha_sexta_linha(pauta, linhas, largura, mediana):
        return None
    if _ha_sexta_na_janela(pauta, aberta):
        return None
    return pauta


def _linhas_faltantes(ys: list[float]) -> list[float]:
    """Candidatas a 5ª linha de um grupo de 4 linhas, pelo espaçamento.

    Com os três intervalos ``d`` do grupo:

    - caso borda: os três estão a até ``tol`` da mediana ``e``; candidatas
      ``ys[0] - e`` (acima) e ``ys[3] + e`` (abaixo);
    - caso meio: exatamente um intervalo está a até ``2 * tol`` de ``2e`` e os outros dois
      a até ``tol`` de ``e`` (``e`` é a média dos dois simples); candidata única, o ponto
      médio do intervalo duplo.

    Fora desses casos não há candidata. ``tol = max(TOL_ABS, TOL_REL * e)``.

    Args:
        ys: as 4 posições verticais, de cima para baixo.

    Returns:
        As candidatas a y da 5ª linha (lista vazia se o espaçamento não basta).
    """
    d = [ys[1] - ys[0], ys[2] - ys[1], ys[3] - ys[2]]
    e = float(np.median(d))
    if all(abs(x - e) <= max(TOL_ABS, TOL_REL * e) for x in d):
        return [ys[0] - e, ys[3] + e]
    meios: list[float] = []
    for k in range(3):
        simples = [d[j] for j in range(3) if j != k]
        e_simples = (simples[0] + simples[1]) / 2
        tol = max(TOL_ABS, TOL_REL * e_simples)
        if all(abs(s - e_simples) <= tol for s in simples) and (
            abs(d[k] - 2 * e_simples) <= 2 * tol
        ):
            meios.append((ys[k] + ys[k + 1]) / 2)
    return meios if len(meios) == 1 else []


def _espessura_limite(espessura: int) -> int:
    """Espessura máxima de uma linha para ainda ser "parecida" com as da pauta.

    Linhas da pauta e da tablatura têm espessura parecida entre si (1 a 5 px, conforme a
    escala); barra de colcheias tem 5 a 6 px junto de linhas de 2 a 3 px.

    Args:
        espessura: espessura mediana das linhas de referência, em px.

    Returns:
        ``espessura + ESPESSURA_FOLGA`` px.
    """
    return espessura + ESPESSURA_FOLGA


def _pauta_do_grupo(grupo: list[_Linha], largura: int) -> Pauta | None:
    """Testa se 5 linhas consecutivas formam uma pauta (geometria apenas).

    Args:
        grupo: as 5 linhas, de cima para baixo.
        largura: largura do quadro, em px.

    Returns:
        A pauta, ou ``None`` se o grupo não tem espaçamento regular, sobreposição
        horizontal ou extensão suficientes.
    """
    ys = [linha.y for linha in grupo]
    intervalos = np.diff(ys)
    if np.any(intervalos < ENTRE_MIN) or np.any(intervalos > ENTRE_MAX):
        return None
    mediana = float(np.median(intervalos))
    tolerancia = max(TOL_ABS, TOL_REL * mediana)
    if np.any(np.abs(intervalos - mediana) > tolerancia):
        return None
    x0 = max(linha.x0 for linha in grupo)
    x1 = min(linha.x1 for linha in grupo)
    menor = min(linha.x1 - linha.x0 for linha in grupo)
    if x1 - x0 < SOBREP_GRUPO * menor:
        return None
    if x1 - x0 < EXT_MIN_FRAC * largura:
        return None
    y0, y1, y2, y3, y4 = (round(float(y)) for y in ys)
    return Pauta(ys=(y0, y1, y2, y3, y4), entrelinha=mediana, x0=x0, x1=x1)


def _linhas_sao_crista(grupo: list[_Linha], pauta: Pauta, cinza: np.ndarray) -> bool:
    """Diz se cada uma das 5 linhas é uma crista de tinta no cinza.

    Para a linha escura, cada coluna da pauta tem de ser ``CRISTA_DELTA`` mais escura que
    as linhas a ``ceil(espessura / 2) + CRISTA_FOLGA`` px acima e abaixo; para a clara,
    mais clara. A linha passa se a fração de colunas que cumprem isso for pelo menos ``CRISTA_FRAC``.

    Args:
        grupo: as 5 linhas da pauta, de cima para baixo.
        pauta: a pauta candidata (define as colunas testadas).
        cinza: quadro em tons de cinza.

    Returns:
        True se todas as 5 linhas são crista.
    """
    return all(_linha_e_crista(linha, pauta, cinza) for linha in grupo)


def _linha_e_crista(linha: _Linha, pauta: Pauta, cinza: np.ndarray) -> bool:
    """Teste de crista de uma linha (ver ``_linhas_sao_crista``).

    Args:
        linha: a linha a testar.
        pauta: define as colunas ``[x0, x1]`` testadas.
        cinza: quadro em tons de cinza.

    Returns:
        True se a linha é crista na maioria das colunas.
    """
    y = round(linha.y)
    altura = cinza.shape[0]
    distancia = math.ceil(linha.espessura / 2) + CRISTA_FOLGA
    if y - distancia < 0 or y + distancia >= altura:
        return False
    colunas = slice(pauta.x0, pauta.x1 + 1)
    centro = cinza[y, colunas].astype(np.int32)
    acima = cinza[y - distancia, colunas].astype(np.int32)
    abaixo = cinza[y + distancia, colunas].astype(np.int32)
    if linha.escura:
        passa = (centro <= acima - CRISTA_DELTA) & (centro <= abaixo - CRISTA_DELTA)
    else:
        passa = (centro >= acima + CRISTA_DELTA) & (centro >= abaixo + CRISTA_DELTA)
    return float(np.mean(passa)) >= CRISTA_FRAC


def _ha_sexta_linha(
    pauta: Pauta, linhas: list[_Linha], largura: int, espessura_pauta: int
) -> bool:
    """Diz se há uma 6ª linha (pela lista de linhas) a uma entrelinha: é tablatura.

    A 6ª linha tem de ter a mesma extensão mínima de uma linha de pauta (``EXT_MIN_FRAC``
    da largura): objeto curto (chave, colchete, texto) não conta como corda.

    Args:
        pauta: a pauta candidata.
        linhas: linhas (fortes e fracas) da polaridade da pauta.
        largura: largura do quadro, em px.
        espessura_pauta: espessura mediana das 5 linhas da pauta.

    Returns:
        True se alguma linha está acima da primeira ou abaixo da última, a uma
        entrelinha de distância, com espessura parecida com a da pauta, e cobre pelo menos
        ``SOBREP_TAB`` do seu comprimento (linha forte) ou da extensão da pauta (fraca).
    """
    tolerancia = max(TOL_ABS, TOL_REL * pauta.entrelinha)
    for linha in linhas:
        acima = pauta.ys[0] - linha.y
        abaixo = linha.y - pauta.ys[4]
        a_uma_entrelinha = (
            abs(acima - pauta.entrelinha) <= tolerancia
            or abs(abaixo - pauta.entrelinha) <= tolerancia
        )
        if not a_uma_entrelinha:
            continue
        comprimento = linha.x1 - linha.x0
        if comprimento < EXT_MIN_FRAC * largura:
            continue
        # Barra de colcheias (6 px) a uma entrelinha não é corda: a 6ª linha tem de ter
        # espessura parecida com a das linhas da pauta.
        if linha.espessura > _espessura_limite(espessura_pauta):
            continue
        sobreposicao = min(linha.x1, pauta.x1) - max(linha.x0, pauta.x0)
        # Linha forte (corda de tab, mesmo coberta de algarismos) basta cobrir a si mesma;
        # linha fraca (barras de colcheia em sequência) tem de cobrir metade da pauta.
        referencia = comprimento if linha.forte else pauta.x1 - pauta.x0
        if sobreposicao >= SOBREP_TAB * referencia:
            return True
    return False


def _ha_sexta_na_janela(pauta: Pauta, aberta: np.ndarray) -> bool:
    """Diz se há tinta a uma entrelinha da pauta, na máscara aberta: é tablatura.

    Cobre a 6ª linha que a lista de linhas perdeu (grossa ou borrada, descartada pela
    espessura máxima). Olha uma janela de altura ``2 * tol + 1`` em torno de
    ``ys[0] - entrelinha`` (acima) e ``ys[4] + entrelinha`` (abaixo), restrita às colunas
    da pauta, e conta as colunas com algum pixel de tinta.

    Args:
        pauta: a pauta candidata.
        aberta: máscara aberta da polaridade da pauta.

    Returns:
        True se alguma janela tem tinta em pelo menos ``SOBREP_TAB`` da extensão da pauta.
    """
    e = pauta.entrelinha
    tol = math.ceil(max(TOL_ABS, TOL_REL * e))
    extensao = pauta.x1 - pauta.x0
    altura = aberta.shape[0]
    for centro in (pauta.ys[0] - e, pauta.ys[4] + e):
        lo = max(0, round(centro) - tol)
        hi = min(altura - 1, round(centro) + tol)
        if lo > hi:
            continue
        janela = aberta[lo : hi + 1, pauta.x0 : pauta.x1 + 1]
        if np.count_nonzero(np.any(janela > 0, axis=0)) >= SOBREP_TAB * extensao:
            return True
    return False


def _sem_duplicatas(pautas: list[Pauta]) -> list[Pauta]:
    """Remove pautas repetidas (as duas polaridades podem achar a mesma).

    Args:
        pautas: pautas ordenadas por y.

    Returns:
        As pautas, sem repetição de até ``DUPLICATA_PX`` px em todas as linhas.
    """
    unicas: list[Pauta] = []
    for pauta in pautas:
        repetida = any(
            max(abs(a - b) for a, b in zip(pauta.ys, outra.ys, strict=True))
            <= DUPLICATA_PX
            for outra in unicas
        )
        if not repetida:
            unicas.append(pauta)
    return unicas
