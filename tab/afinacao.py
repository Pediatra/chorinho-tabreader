"""Candidatos a texto de afinação/capotraste no começo dos vídeos.

O dono do projeto levantou duas hipóteses: (1) a afinação pode mudar de vídeo para
vídeo e às vezes aparece escrita na tela; (2) no `shin izumi` o começo costuma trazer
o compasso (`4/4`) e o capotraste (`fret capo (casa)`).

**Não há OCR instalado e não se instala nada.** Este módulo não lê o texto: ele acha
**candidatos** — blocos com estrutura de texto (vários componentes pequenos, de altura
parecida, alinhados na mesma base, com contraste alto contra o fundo local) — e grava o
recorte ampliado **4x** em ``data/saida/afinacao/<canal>/<t>s_<n>.png`` para leitura
humana. O ``resumo.json`` diz, por canal, quantos vídeos tiveram candidato, em que
instantes e com que score.

Medição que mudou o desenho (2026-10-09, quadros reais 1920x1080): o texto que
interessa **não** está na metade superior do quadro.

- ``shin izumi`` (t=3 s): ``Capo fret 4`` em y≈0,81 da altura, ``♩= 78`` em y≈0,70 e
  ``4/4`` em y≈0,84 — a partitura ocupa o terço de baixo;
- ``iwaki`` (t=3 s): ``⑥=D`` (sexta corda em ré = drop D) em y≈0,62, no cabeçalho da
  tablatura.

Por isso a banda padrão é o **quadro inteiro** (``--frac-topo 1.0``). ``--frac-topo
0.5`` restaura a restrição da metade superior e, medido, **perde os dois casos acima**.
O que continua limitado é a altura do bloco (componente entre 1 % e 8,5 % da altura do
quadro; bloco até 10 %), para não pegar título gigante nem painel de tablatura.

Uso:
    python -m tab.afinacao amostrar --canais "shin izumi" iwaki --por-canal 5
"""

from __future__ import annotations

import argparse
import json
import os
import unicodedata
from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .caminhos import SAIDA, acervo
from .inventario import amostrar as amostrar_acervo
from .inventario import ler_quadro
from .varredura import duracao_s

#: Instantes fixos amostrados (segundos): só o começo do vídeo, onde o cabeçalho fica.
INSTANTES_S: tuple[float, ...] = (3.0, 8.0, 15.0, 30.0, 45.0)

#: Banda vertical procurada, como fração da altura. 1.0 = quadro inteiro (ver docstring).
FRAC_TOPO = 1.0

#: Quanto vale um componente para ser caractere: fração da altura do quadro.
ALTURA_MIN_FRAC = 0.010
ALTURA_MAX_FRAC = 0.085

#: Altura do bloco inteiro, como fração da altura do quadro.
ALTURA_BLOCO_FRAC = 0.10

#: Contraste mínimo (diferença ao fundo local, em níveis de cinza) para virar tinta.
LIMIAR_TINTA = 35

#: Kernel do fundo local (fechamento/abertura) para separar tinta de fundo.
KERNEL_FUNDO = 15

#: Mínimo de componentes para um bloco ser "linha de texto" — `⑥=D` tem 3.
MIN_COMPONENTES = 3

#: Largura mínima do bloco, em px e como fração da largura do quadro.
LARGURA_MIN_PX = 30
LARGURA_MIN_FRAC = 0.02

#: Bloco largo demais é linha de partitura/tablatura, não texto (aspecto = largura/altura).
ASPECTO_MAX = 35.0

#: Coerência interna de uma linha de texto (coeficiente de variação, 0 = perfeito).
CV_ALTURA_MAX = 0.50
CV_BASE_MAX = 0.55

#: Espaço médio entre caracteres, em múltiplos da largura mediana (texto é apertado).
RAZAO_GAP_MAX = 2.5

#: Separação de Otsu (bimodalidade) mínima do recorte e contraste mínimo (níveis de cinza).
BIMODAL_MIN = 0.55
CONTRASTE_MIN = 45.0

#: Fração da largura do bloco que uma linha contínua de tinta pode cobrir.
#: Corda de tablatura, linha de partitura e barra de ligação cobrem o bloco inteiro;
#: texto de verdade não — é o portão que separa "2 (2)" (tablatura) de "Capo fret 4".
LINHA_CONTINUA_FRAC = 0.6

#: IoU a partir do qual dois blocos são o mesmo (supressão dentro do quadro).
IOU_NMS = 0.30

#: IoU (com folga de 10 px) para juntar o mesmo texto achado em instantes diferentes.
IOU_MESMO_TEXTO = 0.35

#: Quantos candidatos guardar por instante.
TOP_K = 3

#: Score mínimo para guardar um candidato. Medido: 0,00 mantém 222 candidatos em 30
#: vídeos (o dono do projeto lê todos); 0,65 corta ~35 % — os fracos são tablatura e
#: madeira, mas ``⑥=D`` (drop D) fica com 0,65 e não pode cair.
SCORE_MIN = 0.0

#: Aumento do recorte gravado e margem de contexto, em px.
AMPLIACAO = 4
MARGEM_PX = 5


@dataclass(frozen=True)
class Bloco:
    """Um bloco candidato a texto, com as medidas que o sustentaram.

    Attributes:
        x0: borda esquerda no quadro.
        y0: borda superior no quadro.
        x1: borda direita no quadro.
        y1: borda inferior no quadro.
        n: número de componentes (caracteres prováveis).
        altura: altura média dos componentes, em px.
        cv_altura: coeficiente de variação das alturas (0 = todas iguais).
        cv_base: coeficiente de variação das bases (0 = alinhadas).
        razao_gap: espaço mediano entre componentes, em larguras medianas.
        bimodal: separação de Otsu do recorte (0..1).
        contraste: diferença p5–p95 de cinza no recorte.
        score: nota final 0..1.
    """

    x0: int
    y0: int
    x1: int
    y1: int
    n: int
    altura: float
    cv_altura: float
    cv_base: float
    razao_gap: float
    bimodal: float
    contraste: float
    score: float


def normalizar(nome: str) -> str:
    """Chave tolerante de nome de canal (sem acento, sem pontuação, minúsculo).

    Existe porque o dono do projeto escreve ``guitar dell'arte`` e a pasta no acervo é
    ``guitar dell ́arte`` (apóstrofo combinante): exigir a grafia exata perderia o canal.

    Args:
        nome: nome de canal ou de pasta.

    Returns:
        Apenas letras e dígitos, minúsculos.
    """
    decomposto = unicodedata.normalize("NFD", nome)
    return "".join(c for c in decomposto if c.isalnum()).lower()


def quadro_em(
    caminho: str, t_s: float, duracao: float | None = None
) -> tuple[np.ndarray | None, str]:
    """Quadro no instante ``t_s``, pelo leitor único do projeto (trata AV1).

    ``tab.inventario.ler_quadro`` posiciona por FRAÇÃO da duração (e cai para o ffmpeg
    quando o OpenCV não decodifica AV1, 44 % do acervo); aqui a fração é derivada do
    instante pedido.

    Args:
        caminho: arquivo de vídeo.
        t_s: instante em segundos.
        duracao: duração já medida (evita um ``ffprobe`` por instante).

    Returns:
        ``(quadro, via)``; ``(None, "falhou")`` se não houver quadro.
    """
    dur = duracao if duracao is not None else duracao_s(caminho)
    if dur <= 0:
        return None, "falhou"
    frac = min(0.99, max(0.0, t_s / dur))
    return ler_quadro(caminho, frac)


def _mascaras_tinta(cinza: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Separa tinta escura e tinta clara do fundo local.

    Fechamento e abertura com o mesmo kernel estimam o fundo nas duas polaridades: o
    que sobra é o que está bem mais escuro (texto preto em papel branco) ou bem mais
    claro (texto branco em vídeo preto) que a vizinhança.

    Args:
        cinza: quadro em tons de cinza.

    Returns:
        ``(tinta_escura, tinta_clara)``, ambas binárias 0/255.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_FUNDO, KERNEL_FUNDO))
    fundo_escuro = cv2.morphologyEx(cinza, cv2.MORPH_CLOSE, kernel)
    fundo_claro = cv2.morphologyEx(cinza, cv2.MORPH_OPEN, kernel)
    delta_escuro = cv2.subtract(fundo_escuro, cinza)
    delta_claro = cv2.subtract(cinza, fundo_claro)
    _, tinta_escura = cv2.threshold(delta_escuro, LIMIAR_TINTA, 255, cv2.THRESH_BINARY)
    _, tinta_clara = cv2.threshold(delta_claro, LIMIAR_TINTA, 255, cv2.THRESH_BINARY)
    return tinta_escura, tinta_clara


def _caixas(mascara: np.ndarray, altura: int) -> list[tuple[int, int, int, int]]:
    """Componentes com cara de caractere: pequenos, nem linha, nem bloco sólido.

    Args:
        mascara: máscara binária de tinta.
        altura: altura do quadro (o tamanho aceito é relativo a ela).

    Returns:
        Lista de ``(x, y, w, h)`` no referencial do quadro.
    """
    alt_min = max(7, int(ALTURA_MIN_FRAC * altura))
    alt_max = max(20, int(ALTURA_MAX_FRAC * altura))
    quantos, _rotulos, stats, _centros = cv2.connectedComponentsWithStats(mascara, 8)
    caixas: list[tuple[int, int, int, int]] = []
    for i in range(1, quantos):
        x, y, w, h, area = (int(v) for v in stats[i])
        if h < alt_min or h > alt_max or w < 3:
            continue
        if area < 12 or area > 0.9 * w * h:
            continue
        razao = w / h
        if razao < 0.15 or razao > 2.5:
            continue
        caixas.append((x, y, w, h))
    return caixas


def _agrupar_linhas(
    caixas: list[tuple[int, int, int, int]],
) -> list[list[tuple[int, int, int, int]]]:
    """Agrupa componentes que dividem a mesma faixa vertical (mesma linha de base).

    Args:
        caixas: componentes aceitos.

    Returns:
        Uma lista de linhas, cada uma com seus componentes.
    """
    linhas: list[list[tuple[int, int, int, int]]] = []
    for caixa in sorted(caixas, key=lambda b: (b[1], b[0])):
        for linha in linhas:
            topo = min(b[1] for b in linha)
            base = max(b[1] + b[3] for b in linha)
            altura_linha = float(np.median([b[3] for b in linha]))
            sobreposicao = min(caixa[1] + caixa[3], base) - max(caixa[1], topo)
            if sobreposicao >= 0.6 * min(caixa[3], altura_linha):
                linha.append(caixa)
                break
        else:
            linhas.append([caixa])
    return linhas


def _cortar_grupos(
    linha: list[tuple[int, int, int, int]],
) -> list[list[tuple[int, int, int, int]]]:
    """Corta a linha nos buracos grandes (uma frase pode ter mais de um bloco).

    Args:
        linha: componentes da mesma linha, em ordem qualquer.

    Returns:
        Grupos contíguos, cada um candidato a um bloco de texto.
    """
    ordenada = sorted(linha, key=lambda b: b[0])
    largura_mediana = float(np.median([b[2] for b in ordenada]))
    grupos: list[list[tuple[int, int, int, int]]] = [[ordenada[0]]]
    anterior = ordenada[0]
    for caixa in ordenada[1:]:
        gap = caixa[0] - (anterior[0] + anterior[2])
        if gap > 3.0 * largura_mediana:
            grupos.append([])
        grupos[-1].append(caixa)
        anterior = caixa
    return grupos


def _bimodalidade(cinza: np.ndarray) -> float:
    """Separação de Otsu (0..1): o recorte tem duas populações bem separadas?

    Texto sobre fundo liso dá perto de 1; madeira, sombra e gradiente dão baixo — é o
    que separa "linha de texto" de "textura do braço do violão".

    Args:
        cinza: recorte em tons de cinza.

    Returns:
        Variância entre classes dividida pela variância total.
    """
    if cinza.size < 4:
        return 0.0
    limiar, _ = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    escuros = cinza[cinza <= limiar]
    claros = cinza[cinza > limiar]
    variancia = float(cinza.var())
    if escuros.size == 0 or claros.size == 0 or variancia < 1e-6:
        return 0.0
    media = float(cinza.mean())
    entre = (
        escuros.size * (float(escuros.mean()) - media) ** 2
        + claros.size * (float(claros.mean()) - media) ** 2
    ) / cinza.size
    return float(min(1.0, entre / variancia))


def _score(
    n: int,
    cv_altura: float,
    cv_base: float,
    razao_gap: float,
    bimodal: float,
    contraste: float,
) -> float:
    """Nota 0..1 do bloco: muitos caracteres, iguais, alinhados, bimodal e contrastado.

    Args:
        n: número de componentes.
        cv_altura: variação das alturas.
        cv_base: variação das bases.
        razao_gap: espaço mediano em larguras medianas.
        bimodal: separação de Otsu.
        contraste: diferença p5–p95 de cinza.

    Returns:
        Nota entre 0 e 1.
    """
    nota = (
        0.30 * min(1.0, n / 10.0)
        + 0.20 * (1.0 - min(1.0, cv_altura / CV_ALTURA_MAX))
        + 0.20 * (1.0 - min(1.0, cv_base / CV_BASE_MAX))
        + 0.15 * (1.0 - min(1.0, razao_gap / RAZAO_GAP_MAX))
        + 0.10 * min(1.0, bimodal)
        + 0.05 * min(1.0, contraste / 160.0)
    )
    return round(float(min(1.0, max(0.0, nota))), 3)


def _linha_continua(mascara: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> bool:
    """O bloco é atravessado por uma corrida longa de tinta?

    Um bloco com números de tablatura pode passar por todos os outros portões (poucos
    componentes, mesma altura, mesma base); o que o denuncia é a **corda** que o corta.
    Quando a corda é contínua dentro do bloco — como nas fileiras do `tv on guitar` e nas
    barras de ligação da partitura — uma erosão horizontal de 60 % da largura do bloco
    ainda encontra tinta e o bloco cai.

    Limite medido: quando a corda é **interrompida** pelos algarismos (desenhada atrás
    deles e visível só nos vãos), a corrida máxima cai para ~0,2 da largura e o portão
    não pega — o fragmento ``2 —(2)—`` do `tv on guitar` continua sendo candidato. Está
    registrado como limitação conhecida no relatório da rodada.

    Args:
        mascara: máscara de tinta que gerou o grupo.
        x0: borda esquerda do bloco.
        y0: borda superior do bloco.
        x1: borda direita do bloco.
        y1: borda inferior do bloco.

    Returns:
        True se alguma linha do bloco tiver uma corrida de tinta longa.
    """
    largura = x1 - x0
    if largura < 8:
        return False
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(8, int(LINHA_CONTINUA_FRAC * largura)), 1)
    )
    recorte = mascara[y0:y1, x0:x1]
    return bool(cv2.erode(recorte, kernel).any())


def _medir_bloco(
    cinza: np.ndarray,
    mascara: np.ndarray,
    grupo: list[tuple[int, int, int, int]],
    altura: int,
    largura: int,
) -> Bloco | None:
    """Mede o grupo e devolve o bloco, ou None se não parecer texto.

    Args:
        cinza: quadro (banda procurada) em tons de cinza.
        mascara: máscara de tinta que gerou o grupo.
        grupo: componentes do grupo.
        altura: altura do quadro.
        largura: largura do quadro.

    Returns:
        O bloco medido, ou None se algum portão reprovar.
    """
    if len(grupo) < MIN_COMPONENTES:
        return None
    x0 = min(b[0] for b in grupo)
    y0 = min(b[1] for b in grupo)
    x1 = max(b[0] + b[2] for b in grupo)
    y1 = max(b[1] + b[3] for b in grupo)
    largura_bloco = x1 - x0
    altura_bloco = y1 - y0
    if largura_bloco < max(LARGURA_MIN_PX, int(LARGURA_MIN_FRAC * largura)):
        return None
    if altura_bloco < 7 or altura_bloco > int(ALTURA_BLOCO_FRAC * altura):
        return None
    if largura_bloco / altura_bloco > ASPECTO_MAX:
        return None
    if _linha_continua(mascara, x0, y0, x1, y1):
        return None

    alturas = np.array([b[3] for b in grupo], dtype=np.float64)
    bases = np.array([b[1] + b[3] for b in grupo], dtype=np.float64)
    cv_altura = float(alturas.std() / max(1.0, alturas.mean()))
    cv_base = float(bases.std() / max(1.0, alturas.mean()))
    ordenado = sorted(grupo, key=lambda b: b[0])
    gaps = [
        ordenado[i + 1][0] - (ordenado[i][0] + ordenado[i][2])
        for i in range(len(ordenado) - 1)
    ]
    largura_mediana = float(np.median([b[2] for b in grupo]))
    razao_gap = float(np.median(gaps) / max(1.0, largura_mediana)) if gaps else 0.0
    if cv_altura > CV_ALTURA_MAX or cv_base > CV_BASE_MAX:
        return None
    if razao_gap < 0.0 or razao_gap > RAZAO_GAP_MAX:
        return None

    recorte = cinza[y0:y1, x0:x1]
    if recorte.size < 16:
        return None
    bimodal = _bimodalidade(recorte)
    contraste = float(np.percentile(recorte, 95) - np.percentile(recorte, 5))
    if bimodal < BIMODAL_MIN or contraste < CONTRASTE_MIN:
        return None

    return Bloco(
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        n=len(grupo),
        altura=round(float(alturas.mean()), 1),
        cv_altura=round(cv_altura, 3),
        cv_base=round(cv_base, 3),
        razao_gap=round(razao_gap, 3),
        bimodal=round(bimodal, 3),
        contraste=round(contraste, 1),
        score=_score(len(grupo), cv_altura, cv_base, razao_gap, bimodal, contraste),
    )


def _iou(a: Bloco, b: Bloco, folga: int = 0) -> float:
    """Interseção sobre união de dois blocos, com folga opcional em px."""
    x0 = max(a.x0 - folga, b.x0 - folga)
    y0 = max(a.y0 - folga, b.y0 - folga)
    x1 = min(a.x1 + folga, b.x1 + folga)
    y1 = min(a.y1 + folga, b.y1 + folga)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    area_a = (a.x1 - a.x0) * (a.y1 - a.y0)
    area_b = (b.x1 - b.x0) * (b.y1 - b.y0)
    return inter / max(1.0, float(area_a + area_b - inter))


def _suprimir(blocos: list[Bloco], top_k: int) -> list[Bloco]:
    """Tira blocos sobrepostos e devolve só os ``top_k`` melhores.

    Args:
        blocos: blocos já ordenados por score decrescente.
        top_k: quantos manter.

    Returns:
        Blocos mantidos.
    """
    mantidos: list[Bloco] = []
    for bloco in blocos:
        if all(_iou(bloco, m) < IOU_NMS for m in mantidos):
            mantidos.append(bloco)
        if len(mantidos) >= top_k:
            break
    return mantidos


def candidatos(
    frame: np.ndarray, frac_topo: float = FRAC_TOPO, top_k: int = TOP_K
) -> list[Bloco]:
    """Blocos com estrutura de texto na banda procurada do quadro.

    Portões, todos medidos antes de entrar: componentes pequenos e estreitos (nem linha
    de corda, nem traste), altura parecida e base alinhada, espaço apertado entre eles,
    bloco bimodal e contrastado, altura de bloco razoável e banda vertical respeitada.

    Args:
        frame: quadro inteiro (BGR).
        frac_topo: fração da altura do quadro procurada a partir do topo.
        top_k: quantos blocos devolver.

    Returns:
        Blocos ordenados por score decrescente (no máximo ``top_k``).
    """
    if frame is None or frame.size == 0:
        return []
    altura = int(frame.shape[0])
    largura = int(frame.shape[1])
    corte = round(min(1.0, max(0.05, frac_topo)) * altura)
    cinza = cv2.cvtColor(frame[:corte], cv2.COLOR_BGR2GRAY)

    achados: list[Bloco] = []
    for mascara in _mascaras_tinta(cinza):
        for linha in _agrupar_linhas(_caixas(mascara, altura)):
            for grupo in _cortar_grupos(linha):
                bloco = _medir_bloco(cinza, mascara, grupo, altura, largura)
                if bloco is not None:
                    achados.append(bloco)
    achados.sort(key=lambda b: -b.score)
    return _suprimir(achados, top_k)


def _procurar_blocos(
    video: str,
    instantes: tuple[float, ...] = INSTANTES_S,
    frac_topo: float = FRAC_TOPO,
    top_k: int = TOP_K,
    duracao: float | None = None,
) -> tuple[list[tuple[float, Bloco]], dict[float, np.ndarray], list[str]]:
    """Lê os instantes pedidos e devolve os blocos, os quadros e as vias usadas.

    Args:
        video: arquivo de vídeo.
        instantes: instantes fixos, em segundos.
        frac_topo: fração da altura procurada.
        top_k: quantos blocos por instante.
        duracao: duração já medida.

    Returns:
        ``(achados, quadros, vias)``; ``achados`` é ``(t, bloco)`` na ordem de leitura.
    """
    dur = duracao if duracao is not None else duracao_s(video)
    achados: list[tuple[float, Bloco]] = []
    quadros: dict[float, np.ndarray] = {}
    vias: list[str] = []
    for t in instantes:
        if dur > 0 and t >= dur - 0.5:
            continue
        frame, via = quadro_em(video, t, dur)
        vias.append(via)
        if frame is None:
            continue
        quadros[t] = frame
        for bloco in candidatos(frame, frac_topo, top_k):
            achados.append((float(t), bloco))
    return achados, quadros, vias


def procurar(
    video: str,
    instantes: tuple[float, ...] = INSTANTES_S,
    frac_topo: float = FRAC_TOPO,
    top_k: int = TOP_K,
    duracao: float | None = None,
) -> list[tuple[float, int, int, int, int, float]]:
    """Procura candidatos a texto nos instantes fixos do começo do vídeo.

    Args:
        video: arquivo de vídeo.
        instantes: instantes fixos, em segundos.
        frac_topo: fração da altura do quadro procurada.
        top_k: quantos candidatos por instante.
        duracao: duração já medida (evita ``ffprobe`` repetido).

    Returns:
        Lista de ``(t, x0, y0, x1, y1, score)``, na ordem de leitura.
    """
    achados, quadros, _vias = _procurar_blocos(
        video, instantes, frac_topo, top_k, duracao
    )
    quadros.clear()
    return [(t, b.x0, b.y0, b.x1, b.y1, b.score) for t, b in achados]


def agrupar(achados: list[tuple[float, Bloco]]) -> list[dict]:
    """Junta o mesmo texto achado em instantes diferentes (cabeçalho parado na tela).

    Sem isto o resumo traria o mesmo ``Capo fret 4`` cinco vezes (uma por instante) e o
    dono do projeto leria cinco recortes iguais em vez de um.

    Args:
        achados: pares ``(t, bloco)`` na ordem de leitura.

    Returns:
        Um registro por texto distinto, com ``instantes``, ``score`` e as medidas do
        melhor quadro — ainda sem o caminho do PNG.
    """
    grupos: list[dict] = []
    for t, bloco in sorted(achados, key=lambda a: -a[1].score):
        for grupo in grupos:
            referencia: Bloco = grupo["_bloco"]
            if _iou(bloco, referencia, folga=10) >= IOU_MESMO_TEXTO:
                # Dois blocos do MESMO quadro podem cair no mesmo grupo (a folga de
                # 10 px é maior que o IoU da supressão): o instante não se repete.
                if t not in grupo["instantes"]:
                    grupo["instantes"].append(t)
                break
        else:
            registro = asdict(bloco)
            registro["t"] = t
            registro["instantes"] = [t]
            registro["_bloco"] = bloco
            grupos.append(registro)
    for grupo in grupos:
        grupo.pop("_bloco", None)
        grupo["instantes"] = sorted(grupo["instantes"])
    return grupos


def gravar_recorte(frame: np.ndarray, bloco: Bloco, destino: str) -> None:
    """Grava o recorte do bloco ampliado 4x, com margem, para leitura humana.

    Args:
        frame: quadro inteiro de onde recortar.
        bloco: bloco candidato.
        destino: caminho do PNG.
    """
    altura, largura = frame.shape[:2]
    x0 = max(0, bloco.x0 - MARGEM_PX)
    y0 = max(0, bloco.y0 - MARGEM_PX)
    x1 = min(largura, bloco.x1 + MARGEM_PX)
    y1 = min(altura, bloco.y1 + MARGEM_PX)
    recorte = frame[y0:y1, x0:x1]
    if recorte.size == 0:
        return
    ampliado = cv2.resize(
        recorte, None, fx=AMPLIACAO, fy=AMPLIACAO, interpolation=cv2.INTER_CUBIC
    )
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    cv2.imwrite(destino, ampliado)


def rotulo_instante(t: float) -> str:
    """Rótulo de um instante para nome de arquivo: ``3.0 -> "3"``, ``3.5 -> "3.5"``."""
    return f"{t:g}"


def _caminho_png(raiz_saida: str, canal: str, t: float, indice: int) -> str:
    """Caminho do PNG do candidato ``indice`` do canal no instante ``t``."""
    return os.path.join(raiz_saida, canal, f"{rotulo_instante(t)}s_{indice}.png")


def amostrar_video(
    video: str,
    canal: str,
    raiz_saida: str,
    raiz: str,
    instantes: tuple[float, ...],
    frac_topo: float,
    top_k: int,
    primeiro_indice: int,
    score_min: float = SCORE_MIN,
) -> tuple[dict, int]:
    """Amostra um vídeo, grava os recortes e devolve o registro e o próximo índice.

    Args:
        video: arquivo de vídeo.
        canal: nome do canal (vira subpasta).
        raiz_saida: raiz onde gravar os PNGs (``data/saida/afinacao``).
        raiz: raiz do acervo (para o caminho relativo do vídeo).
        instantes: instantes fixos amostrados.
        frac_topo: fração da altura procurada.
        top_k: quantos candidatos por instante.
        primeiro_indice: primeiro ``n`` livre do canal (nome do PNG é ``<t>s_<n>.png``).
        score_min: descarta bloco com score abaixo disto.

    Returns:
        ``(registro, proximo_indice)``.
    """
    dur = duracao_s(video)
    achados, quadros, vias = _procurar_blocos(
        video, instantes, frac_topo, top_k, duracao=dur
    )
    grupos = [g for g in agrupar(achados) if g["score"] >= score_min]
    altura_quadro = next(iter(quadros.values())).shape[0] if quadros else 0
    indice = primeiro_indice
    for grupo in grupos:
        t = float(grupo["t"])
        frame = quadros.get(t)
        caminho_png = _caminho_png(raiz_saida, canal, t, indice)
        if frame is not None:
            gravar_recorte(frame, bloco_do_grupo(grupo), caminho_png)
            altura_quadro = frame.shape[0]
        grupo["png"] = os.path.relpath(caminho_png, os.getcwd())
        grupo["y_rel"] = round(
            (grupo["y0"] + grupo["y1"]) / 2 / max(1, altura_quadro), 3
        )
        indice += 1
    quadros.clear()

    registro = {
        "video": os.path.relpath(video, raiz),
        "duracao_s": round(dur, 1),
        "altura": altura_quadro,
        "vias": vias,
        "n_candidatos": len(grupos),
        "candidatos": grupos,
    }
    return registro, indice


def _canais_do_acervo(raiz: str, pedidos: list[str] | None, por_canal: int, seed: int):
    """Resolve os canais pedidos (tolerante a acento) e sorteia os vídeos."""
    disponiveis = amostrar_acervo(raiz, por_canal, seed)
    if not pedidos:
        return disponiveis
    indice = {normalizar(nome): nome for nome in disponiveis}
    escolhidos: dict[str, list[str]] = {}
    for pedido in pedidos:
        chave = normalizar(pedido)
        if chave not in indice:
            print(f"AVISO: canal não encontrado no acervo: {pedido!r}", flush=True)
            continue
        escolhidos[indice[chave]] = disponiveis[indice[chave]]
    return escolhidos


def amostrar(
    raiz: str,
    canais: list[str] | None,
    por_canal: int,
    raiz_saida: str,
    instantes: tuple[float, ...] = INSTANTES_S,
    frac_topo: float = FRAC_TOPO,
    top_k: int = TOP_K,
    seed: int = 0,
    score_min: float = SCORE_MIN,
) -> dict:
    """Amostra os canais pedidos e devolve o resumo (gravando os PNGs no caminho).

    Args:
        raiz: raiz do acervo.
        canais: canais pedidos (None = todos).
        por_canal: quantos vídeos sortear por canal.
        raiz_saida: raiz dos PNGs.
        instantes: instantes fixos amostrados.
        frac_topo: fração da altura procurada.
        top_k: quantos candidatos por instante.
        seed: semente do sorteio dos vídeos.
        score_min: descarta bloco com score abaixo disto.

    Returns:
        Resumo com ``canais`` (por canal: vídeos, candidatos, PNGs) e ``parametros``.
    """
    escolhidos = _canais_do_acervo(raiz, canais, por_canal, seed)
    resumo: dict = {
        "instantes_s": list(instantes),
        "parametros": {
            "frac_topo": frac_topo,
            "top_k": top_k,
            "score_min": score_min,
            "min_componentes": MIN_COMPONENTES,
            "bimodal_min": BIMODAL_MIN,
            "contraste_min": CONTRASTE_MIN,
            "aspecto_max": ASPECTO_MAX,
            "altura_bloco_frac": ALTURA_BLOCO_FRAC,
            "iou_nms": IOU_NMS,
        },
        "canais": {},
    }
    for canal, vids in escolhidos.items():
        indice = 1
        registros: list[dict] = []
        for video in vids:
            try:
                registro, indice = amostrar_video(
                    video,
                    canal,
                    raiz_saida,
                    raiz,
                    instantes,
                    frac_topo,
                    top_k,
                    indice,
                    score_min,
                )
            except Exception as exc:  # um vídeo ruim não derruba a amostragem
                registro = {
                    "video": os.path.relpath(video, raiz),
                    "erro": f"{type(exc).__name__}: {exc}",
                    "n_candidatos": 0,
                    "candidatos": [],
                }
            registros.append(registro)
            print(
                f"  {canal[:20]:<20} {registro['video'][:44]:<44} "
                f"candidatos={registro['n_candidatos']} "
                f"vias={registro.get('vias')}",
                flush=True,
            )
        com_candidato = [r for r in registros if r["n_candidatos"] > 0]
        por_instante: dict[str, int] = {}
        melhores: list[dict] = []
        for registro in registros:
            for candidato in registro["candidatos"]:
                for t in candidato["instantes"]:
                    chave = rotulo_instante(float(t))
                    por_instante[chave] = por_instante.get(chave, 0) + 1
                melhores.append(
                    {
                        "video": registro["video"],
                        "png": candidato["png"],
                        "t": candidato["t"],
                        "instantes": candidato["instantes"],
                        "score": candidato["score"],
                        "y_rel": candidato.get("y_rel"),
                    }
                )
        # O dono do projeto lê o resumo de cima para baixo: os melhores primeiro.
        melhores.sort(key=lambda m: -m["score"])
        resumo["canais"][canal] = {
            "n_videos": len(registros),
            "n_com_candidato": len(com_candidato),
            "n_candidatos": sum(r["n_candidatos"] for r in registros),
            "instantes_com_candidato": dict(sorted(por_instante.items())),
            "melhores": melhores,
            "videos": registros,
        }
    return resumo


def bloco_do_grupo(grupo: dict) -> Bloco:
    """Reconstrói o Bloco guardado num registro de grupo (campos geométricos)."""
    return Bloco(
        x0=grupo["x0"],
        y0=grupo["y0"],
        x1=grupo["x1"],
        y1=grupo["y1"],
        n=grupo["n"],
        altura=grupo["altura"],
        cv_altura=grupo["cv_altura"],
        cv_base=grupo["cv_base"],
        razao_gap=grupo["razao_gap"],
        bimodal=grupo["bimodal"],
        contraste=grupo["contraste"],
        score=grupo["score"],
    )


def _instantes_do_texto(argumento: list[float] | None) -> tuple[float, ...]:
    """Tuple de instantes a partir do argumento da CLI (default: ``INSTANTES_S``)."""
    return tuple(argumento) if argumento else INSTANTES_S


def main() -> int:
    """CLI: amostra canais e grava os recortes candidatos e o resumo."""
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="comando", required=True)
    amostrar_ap = sub.add_parser("amostrar", help="amostra canais e grava os PNGs")
    amostrar_ap.add_argument("--raiz", default=str(acervo()))
    amostrar_ap.add_argument("--canais", nargs="*", default=None)
    amostrar_ap.add_argument("--por-canal", type=int, default=5)
    amostrar_ap.add_argument("--saida", default=str(SAIDA / "afinacao"))
    amostrar_ap.add_argument("--seed", type=int, default=0)
    amostrar_ap.add_argument("--frac-topo", type=float, default=FRAC_TOPO)
    amostrar_ap.add_argument("--top-k", type=int, default=TOP_K)
    amostrar_ap.add_argument("--score-min", type=float, default=SCORE_MIN)
    amostrar_ap.add_argument("--instantes", type=float, nargs="*", default=None)
    args = ap.parse_args()

    if args.comando != "amostrar":
        ap.error(f"comando desconhecido: {args.comando}")

    os.makedirs(args.saida, exist_ok=True)
    resumo = amostrar(
        args.raiz,
        args.canais,
        args.por_canal,
        args.saida,
        _instantes_do_texto(args.instantes),
        args.frac_topo,
        args.top_k,
        args.seed,
        args.score_min,
    )
    destino = os.path.join(args.saida, "resumo.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(resumo, fh, ensure_ascii=False, indent=1)

    print("\n=== CANDIDATOS POR CANAL ===")
    for canal, dados in resumo["canais"].items():
        print(
            f"{canal[:26]:<28} vídeos={dados['n_videos']} "
            f"com_candidato={dados['n_com_candidato']} "
            f"candidatos={dados['n_candidatos']} "
            f"instantes={dados['instantes_com_candidato']}"
        )
    print(f"\nresumo: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
