"""Gerador do braço sintético (M21, fase A): fonte S, com rótulo exato.

Um braço plano é desenhado no plano, em milímetros: u ao longo do braço (escala de 650
mm, nut em 0) e v a largura (43 mm no nut e 56 mm no traste 12, linear). Os trastes
ficam nas posições das 12 notas. A homografia leva o plano à imagem 1920 x 1080: rotação
no plano, inclinação fora do plano, espelhamento horizontal e escala com vão de 8 a 40
px entre cordas vizinhas no nut.

A aparência segue o violão real (rodada 1021, revisão do coordenador): madeira escura
em HSV (matiz 0 a 30, saturação 0,15 a 0,6, valor 0,08 a 0,35), com 10 % de madeira
clara; cordas finas de 1 a 3 px, com sombra e brilho de 1 px; trastes prateados de 1 a
2 px (15 % dourados); borda de 2 a 4 px; tampo em HSV. Cordas e trastes são desenhados
em 4x e reduzidos, para o antialias ficar fino.

As cordas são marcadas só no braço, do nut até a junção com o corpo: traste 12 no
clássico e traste 14 no aço. O rótulo sai da própria homografia, então é exato. A mão
(oclusão) é pele real recortada de quadros do acervo; ela cobre o braço, e os rótulos
não mudam (o dono também estima os trastes sob a mão). Depois vem a degradação
(desfoque, ruído, brilho, contraste e JPEG).

O registro segue o formato do gabarito (``braco``, ``nut``, ``corda1``, ``corda6`` e
``trastes`` contíguos a partir do 1), para ``tab.maos_braco_tempo.marcas_do_registro``.

Os fundos são quadros de vídeos do acervo que NÃO estão na M11b. ``videos_proibidos``
e ``conferir_fora_m11b`` fazem essa barreira, e ela levanta erro em vez de seguir.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
from pathlib import Path

import cv2
import numpy as np

from tab.comum.caminhos import GABARITO_BRACO_M11B, MAOS_M21, acervo
from tab.maos.braco.cadeia import PARAMETROS_PADRAO, ler_trecho
from tab.maos.braco.faixa import aplicar_matriz
from tab.maos.braco.regra import s_do_traste

#: Comprimento de escala, em mm (o plano é em mm).
ESCALA_MM = 650.0
#: Último traste desenhado (o clássico tem 19).
TRASTES_MAXIMO = 19
#: Casa da junção com o corpo, por classe.
TRASTE_JUNCAO = {"classico": 12, "aco": 14}
CLASSES = ("classico", "aco")
#: Larguras do braço, em mm (no nut e no traste 12; linear entre elas).
LARGURA_NUT_MM = 43.0
LARGURA_TRASTE_12_MM = 56.0
#: Margem entre a corda externa e a borda do braço, em mm.
MARGEM_CORDA_MM = 3.0
#: Vão entre cordas vizinhas no nut, em mm.
VAO_NUT_MM = (LARGURA_NUT_MM - 2.0 * MARGEM_CORDA_MM) / 5.0
#: Quanto as cordas continuam sobre o corpo, depois da junção, em mm.
EXTENSAO_SOBRE_CORPO_MM = 25.0
#: Tamanho do corpo simples depois da junção, em mm.
COMPRIMENTO_CORPO_MM = 120.0
LARGURA_CORPO_MM = 90.0
#: Nut (osso): espessura em mm.
ESPESSURA_NUT_MM = 2.5
#: Dimensões da imagem (largura, altura).
DIMENSOES = (1920, 1080)
#: Distância focal do modelo de câmera, em px.
DISTANCIA_FOCAL = 3000.0
#: Limites do sorteio da vista.
ROTACAO_NO_PLANO_GRAUS = 40.0
INCLINACAO_GRAUS = 30.0
VAO_PX = (8.0, 40.0)
#: Trastes que precisam ficar dentro do quadro, além do nut.
TRASTES_MINIMOS_NO_QUADRO = 8
#: Tentativas de sorteio de vista antes de desistir.
TENTATIVAS_VISTA = 200
#: Resolução da textura do plano, em px por mm.
RESOLUCAO_TEXTURA = 3.0
#: Casas com ponto de incrustação (só no aço).
CASAS_COM_PONTO = (3, 5, 7, 9, 12, 15)
#: Extensões de vídeo do acervo.
EXTENSOES_VIDEO = (".mp4",)
#: Quadros de fundo: nome do índice e arquivo de cada um.
ARQUIVO_INDICE_FUNDOS = "indice.json"

#: Superamostragem para o antialias das linhas finas (cordas e trastes).
FATOR_SUPERAMOSTRAGEM = 4
#: Madeira em HSV: matiz em graus, saturação e valor (0 a 1).
FAIXA_MATIZ_MADEIRA = (0.0, 30.0)
FAIXA_SATURACAO_MADEIRA = (0.15, 0.6)
FAIXA_VALOR_MADEIRA_ESCURA = (0.08, 0.35)
FAIXA_VALOR_MADEIRA_CLARA = (0.35, 0.6)
PROBABILIDADE_MADEIRA_CLARA = 0.10
#: Grão fino ao longo do braço: amplitude em valor, e desfoque (x, y) em px do plano.
AMPLITUDE_GRAO = 0.04
SIGMA_GRAO_X_PX = (6.0, 14.0)
#: Tampo do corpo em HSV, e a boca escura opcional.
FAIXA_MATIZ_TAMPO = (15.0, 35.0)
FAIXA_SATURACAO_TAMPO = (0.3, 0.7)
FAIXA_VALOR_TAMPO = (0.45, 0.85)
AMPLITUDE_GRAO_TAMPO = 0.02
SIGMA_GRAO_TAMPO_PX = (20.0, 40.0)
PROBABILIDADE_BOCA = 0.5
RAIO_BOCA_MM = 22.0
#: Traste: espessura em px (na escala de 1920) e sobressaída além da escala, em mm.
ESPESSURA_TRASTE_PX = (1.0, 2.0)
SOBRESSAIDA_TRASTE_MM = 0.8
PROBABILIDADE_TRASTE_DOURADO = 0.15
#: Borda da escala, em px, mais clara ou mais escura que a madeira.
LARGURA_BORDA_PX = (2.0, 4.0)
#: Pele real: faixa de Cr e Cb no YCrCb, e a área do componente (fração do quadro).
PELE_CR = (135, 175)
PELE_CB = (85, 135)
FRACAO_AREA_PELE = (0.03, 0.25)
#: Mão: escala relativa ao recorte natural, na oclusão geral.
ESCALA_MAO_GERAL = (0.6, 1.6)
#: Probabilidade de haver uma mão cobrindo 2 a 4 casas, e número de oclusões.
PROBABILIDADE_MAO_COBRE_CASAS = 0.6
CASAS_COBERTAS = (2, 3, 4)


def trastes_no_plano(n_maximo: int = TRASTES_MAXIMO) -> list[float]:
    """Posição de cada traste ao longo do braço, no plano, em mm.

    Args:
        n_maximo: último traste.

    Returns:
        ``[t_0, ..., t_n_maximo]``, com ``t_0`` (nut) igual a 0.
    """
    return [ESCALA_MM * s_do_traste(n) for n in range(n_maximo + 1)]


def _largura_em(u: float) -> float:
    """Largura do braço na posição ``u`` (mm), linear entre o nut e o traste 12.

    Args:
        u: posição ao longo do braço, em mm.

    Returns:
        Largura em mm.
    """
    t12 = trastes_no_plano(12)[12]
    return LARGURA_NUT_MM + (LARGURA_TRASTE_12_MM - LARGURA_NUT_MM) * u / t12


def _corda_em(indice: int, u: float) -> float:
    """Posição transversal (mm) da corda ``indice`` (0 a 5) na posição ``u``.

    Args:
        indice: corda, de 0 (corda 1) a 5 (corda 6).
        u: posição ao longo do braço, em mm.

    Returns:
        Coordenada ``v`` em mm.
    """
    largura = _largura_em(u)
    return (
        -largura / 2.0 + MARGEM_CORDA_MM + indice * (largura - 2 * MARGEM_CORDA_MM) / 5
    )


def _rotacao_z(teta: float) -> np.ndarray:
    """Rotação em torno do eixo Z (no plano do braço).

    Args:
        teta: ângulo em radianos.

    Returns:
        Matriz 3x3.
    """
    c, s = math.cos(teta), math.sin(teta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _rodrigues(eixo: np.ndarray, angulo: float) -> np.ndarray:
    """Rotação de ``angulo`` radianos em torno de ``eixo`` (fórmula de Rodrigues).

    Args:
        eixo: vetor 3D unitário.
        angulo: ângulo em radianos.

    Returns:
        Matriz 3x3.
    """
    x, y, z = eixo
    k = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + math.sin(angulo) * k + (1.0 - math.cos(angulo)) * (k @ k)


def _homografia_plano(rot: np.ndarray, distancia: float, espelho: bool) -> np.ndarray:
    """Homografia do plano do braço (mm) para a imagem (px).

    Args:
        rot: rotação 3x3 da vista.
        distancia: distância da câmera ao plano, em mm.
        espelho: se o braço é espelhado no eixo horizontal (cabeça à direita).

    Returns:
        Homografia 3x3 que recebe ``(u, v, 1)`` em mm.
    """
    k = np.array(
        [
            [DISTANCIA_FOCAL, 0.0, DIMENSOES[0] / 2.0],
            [0.0, DISTANCIA_FOCAL, DIMENSOES[1] / 2.0],
            [0.0, 0.0, 1.0],
        ]
    )
    a = np.column_stack([rot[:, 0], rot[:, 1], [0.0, 0.0, distancia]])
    mirror = np.diag([-1.0, 1.0, 1.0]) if espelho else np.eye(3)
    return k @ a @ mirror


def _calibrar_vista(
    rot: np.ndarray, espelho: bool, vao_alvo: float
) -> tuple[np.ndarray, float] | None:
    """Acha a distância da câmera que dá o vão pedido no nut.

    Args:
        rot: rotação 3x3 da vista.
        espelho: espelhamento horizontal.
        vao_alvo: vão desejado entre cordas vizinhas no nut, em px.

    Returns:
        ``(homografia, distancia)``, ou ``None`` se algum canto do plano fica atrás da
        câmera.
    """
    distancia = DISTANCIA_FOCAL * VAO_NUT_MM / vao_alvo
    for _ in range(4):
        h = _homografia_plano(rot, distancia, espelho)
        pontos = aplicar_matriz(h, [[0.0, _corda_em(0, 0.0)], [0.0, _corda_em(1, 0.0)]])
        vao = float(np.linalg.norm(pontos[1] - pontos[0]))
        distancia *= vao / vao_alvo
    h = _homografia_plano(rot, distancia, espelho)
    z_cantos = (
        h[2]
        @ np.array(
            [
                [-10.0, -50.0, 1.0],
                [-10.0, 50.0, 1.0],
                [600.0, -50.0, 1.0],
                [600.0, 50.0, 1.0],
            ]
        ).T
    )
    if np.any(z_cantos <= 0.0):
        return None
    return h, distancia


def _sortear_vista(rng: random.Random, jf: int) -> tuple[np.ndarray, float]:
    """Sorteia a vista do braço: rotação, inclinação, espelho, vão e posição.

    A posição garante o nut dentro do quadro e pelo menos ``TRASTES_MINIMOS_NO_QUADRO``
    trastes dentro. Sem sucesso em ``TENTATIVAS_VISTA`` sorteios, levanta erro.

    Args:
        rng: gerador do chamador.
        jf: último traste visível (junção com o corpo).

    Returns:
        ``(homografia, vao)``: a homografia total (mm para a imagem) e o vão no nut,
        em px.

    Raises:
        RuntimeError: se nenhuma vista cumpre as condições.
    """
    largura, altura = DIMENSOES
    trastes = [[t, 0.0] for t in trastes_no_plano(jf)[1:]]
    for _ in range(TENTATIVAS_VISTA):
        teta = math.radians(
            rng.uniform(-ROTACAO_NO_PLANO_GRAUS, ROTACAO_NO_PLANO_GRAUS)
        )
        tau = math.radians(rng.uniform(0.0, INCLINACAO_GRAUS))
        psi = rng.uniform(0.0, 2.0 * math.pi)
        espelho = rng.random() < 0.5
        vao_alvo = rng.uniform(*VAO_PX)
        nut_x = rng.uniform(0.15, 0.85) * largura
        nut_y = rng.uniform(0.15, 0.85) * altura
        eixo_inclinacao = np.array([math.cos(psi), math.sin(psi), 0.0])
        rot = _rodrigues(eixo_inclinacao, tau) @ _rotacao_z(teta)
        calibrada = _calibrar_vista(rot, espelho, vao_alvo)
        if calibrada is None:
            continue
        h_plano, _ = calibrada
        ancora = aplicar_matriz(h_plano, [[0.0, 0.0]])[0]
        translacao = np.array(
            [
                [1.0, 0.0, nut_x - ancora[0]],
                [0.0, 1.0, nut_y - ancora[1]],
                [0.0, 0.0, 1.0],
            ]
        )
        h = translacao @ h_plano
        pontos = aplicar_matriz(h, trastes)
        dentro = (
            (pontos[:, 0] >= 0)
            & (pontos[:, 0] < largura)
            & (pontos[:, 1] >= 0)
            & (pontos[:, 1] < altura)
        )
        if int(dentro.sum()) >= TRASTES_MINIMOS_NO_QUADRO:
            vao = float(
                np.linalg.norm(
                    aplicar_matriz(h, [[0.0, _corda_em(1, 0.0)]])[0]
                    - aplicar_matriz(h, [[0.0, _corda_em(0, 0.0)]])[0]
                )
            )
            return h, vao
    raise RuntimeError("nenhuma vista do braço cumpre o quadro")


def _bgr_de_hsv(matiz: float, saturacao: float, valor: float) -> tuple[int, int, int]:
    """Cor BGR (0 a 255) de uma cor em HSV (matiz em graus, saturação e valor de 0 a 1).

    Args:
        matiz: matiz em graus (0 a 360).
        saturacao: saturação de 0 a 1.
        valor: valor (brilho) de 0 a 1.

    Returns:
        Tupla BGR de inteiros.
    """
    hsv = np.array([[[matiz, saturacao, valor]]], dtype=np.float32)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0] * 255.0
    return tuple(round(float(c)) for c in np.clip(bgr, 0, 255))


def _textura_hsv(
    rng: random.Random,
    altura: int,
    largura: int,
    matiz: tuple[float, float],
    saturacao: tuple[float, float],
    valor: tuple[float, float],
    amplitude: float,
    sigma_x: tuple[float, float],
) -> np.ndarray:
    """Textura de madeira em HSV, com grão fino ao longo do braço e faixas suaves.

    O matiz e a saturação são sorteados uma vez por textura. O valor varia com grão de
    amplitude ``amplitude`` (ruído desfocado mais no eixo horizontal, ao longo do braço).

    Args:
        rng: gerador do chamador.
        altura: altura da textura em px.
        largura: largura da textura em px.
        matiz: intervalo do matiz, em graus.
        saturacao: intervalo da saturação (0 a 1).
        valor: intervalo do valor (0 a 1).
        amplitude: amplitude do grão no valor (0 a 1).
        sigma_x: intervalo do desfoque horizontal do grão, em px.

    Returns:
        Imagem BGR uint8 ``(altura, largura, 3)``.
    """
    matiz_sorteado = rng.uniform(*matiz)
    saturacao_sorteada = rng.uniform(*saturacao)
    valor_sorteado = rng.uniform(*valor)
    gerador = np.random.default_rng(rng.randrange(2**32))
    ruido = gerador.standard_normal((altura, largura)).astype(np.float32)
    ruido = cv2.GaussianBlur(ruido, (0, 0), sigmaX=rng.uniform(*sigma_x), sigmaY=0.6)
    ruido = np.clip(ruido / (float(ruido.std()) + 1e-6), -1.0, 1.0)
    faixas = np.sin(
        2.0 * math.pi * np.arange(altura) / rng.uniform(2.5, 7.0)
        + rng.uniform(0.0, 2.0 * math.pi)
    )
    mapa_valor = np.clip(
        valor_sorteado + amplitude * ruido + 0.25 * amplitude * faixas[:, None],
        0.0,
        1.0,
    )
    hsv = np.empty((altura, largura, 3), dtype=np.float32)
    hsv[..., 0] = matiz_sorteado
    hsv[..., 1] = saturacao_sorteada
    hsv[..., 2] = mapa_valor
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return np.clip(bgr * 255.0, 0, 255).astype(np.uint8)


def _linha_suave(
    img: np.ndarray,
    p0: np.ndarray,
    p1: np.ndarray,
    cor: tuple[int, int, int],
    espessura: float,
    alpha: float = 1.0,
) -> None:
    """Linha antialias, desenhada em 4x num recorte e reduzida para a imagem.

    Cada linha é desenhada na máscara em resolução de ``FATOR_SUPERAMOSTRAGEM`` vezes e
    reduzida por área, o que dá cobertura fracionária (antialias) mesmo para espessuras
    de 1 px. A cor é mesclada pela cobertura, vezes ``alpha``.

    Args:
        img: imagem BGR uint8, alterada no lugar.
        p0: ponto inicial ``(x, y)``, em px.
        p1: ponto final ``(x, y)``, em px.
        cor: cor BGR da linha.
        espessura: espessura em px (pode ser fracionária).
        alpha: opacidade da linha, de 0 a 1.
    """
    k = FATOR_SUPERAMOSTRAGEM
    altura, largura = img.shape[:2]
    xs = (float(p0[0]), float(p1[0]))
    ys = (float(p0[1]), float(p1[1]))
    margem = espessura + 3.0
    x0 = max(0, math.floor(min(xs) - margem))
    x1 = min(largura, math.ceil(max(xs) + margem))
    y0 = max(0, math.floor(min(ys) - margem))
    y1 = min(altura, math.ceil(max(ys) + margem))
    if x1 <= x0 or y1 <= y0:
        return
    w, h = x1 - x0, y1 - y0
    a = (round((xs[0] - x0) * k), round((ys[0] - y0) * k))
    b = (round((xs[1] - x0) * k), round((ys[1] - y0) * k))
    mascara = np.zeros((h * k, w * k), dtype=np.uint8)
    cv2.line(mascara, a, b, 255, max(1, round(espessura * k)))
    cobertura = cv2.resize(mascara, (w, h), interpolation=cv2.INTER_AREA)
    m = (cobertura.astype(np.float32) / 255.0 * alpha)[..., None]
    roi = img[y0:y1, x0:x1].astype(np.float32)
    cor_arr = np.array(cor, dtype=np.float32)
    img[y0:y1, x0:x1] = np.clip(roi * (1.0 - m) + cor_arr * m, 0, 255).astype(np.uint8)


def _desenhar_objeto(
    rng: random.Random,
    h: np.ndarray,
    jf: int,
    classe: str,
    vao: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Desenha o braço e o corpo no quadro, e devolve a cor e a máscara.

    A textura do plano é feita em mm e levada à imagem por ``h``. Borda, trastes,
    pontos e cordas são desenhados na imagem, com antialias em 4x.

    Args:
        rng: gerador do chamador.
        h: homografia total (mm para px).
        jf: último traste visível.
        classe: ``classico`` ou ``aco``.
        vao: vão no nut, em px (define a espessura e o tamanho dos pontos).

    Returns:
        ``(cor, mascara)``: imagem BGR uint8 e máscara uint8 (255 onde há objeto), na
        resolução da imagem.
    """
    r = RESOLUCAO_TEXTURA
    u0, v_meia = -10.0, LARGURA_CORPO_MM / 2.0 + 5.0
    u_junta = trastes_no_plano(jf)[jf]
    u1 = u_junta + COMPRIMENTO_CORPO_MM
    largura_c = round((u1 - u0) * r)
    altura_c = round(2.0 * v_meia * r)

    def para_canvas(pontos: list[tuple[float, float]]) -> np.ndarray:
        """Pontos em mm para pixels do canvas do plano."""
        return np.array(
            [[(u - u0) * r, (v + v_meia) * r] for u, v in pontos], dtype=np.int32
        )

    valor_madeira = (
        FAIXA_VALOR_MADEIRA_CLARA
        if rng.random() < PROBABILIDADE_MADEIRA_CLARA
        else FAIXA_VALOR_MADEIRA_ESCURA
    )
    cor = _textura_hsv(
        rng,
        altura_c,
        largura_c,
        FAIXA_MATIZ_MADEIRA,
        FAIXA_SATURACAO_MADEIRA,
        valor_madeira,
        AMPLITUDE_GRAO,
        SIGMA_GRAO_X_PX,
    )
    mascara = np.zeros((altura_c, largura_c), dtype=np.uint8)

    pescoco = [
        (0.0, -_largura_em(0.0) / 2.0),
        (u_junta, -_largura_em(u_junta) / 2.0),
        (u_junta, _largura_em(u_junta) / 2.0),
        (0.0, _largura_em(0.0) / 2.0),
    ]
    cv2.fillPoly(mascara, [para_canvas(pescoco)], 255)
    media_madeira = cor[mascara > 0].mean(axis=0)

    corpo = [
        (u_junta, -LARGURA_CORPO_MM / 2.0),
        (u1, -LARGURA_CORPO_MM / 2.0),
        (u1, LARGURA_CORPO_MM / 2.0),
        (u_junta, LARGURA_CORPO_MM / 2.0),
    ]
    mascara_corpo = np.zeros_like(mascara)
    cv2.fillPoly(mascara_corpo, [para_canvas(corpo)], 255)
    tampo = _textura_hsv(
        rng,
        altura_c,
        largura_c,
        FAIXA_MATIZ_TAMPO,
        FAIXA_SATURACAO_TAMPO,
        FAIXA_VALOR_TAMPO,
        AMPLITUDE_GRAO_TAMPO,
        SIGMA_GRAO_TAMPO_PX,
    )
    cor[mascara_corpo > 0] = tampo[mascara_corpo > 0]
    mascara = np.maximum(mascara, mascara_corpo)
    if rng.random() < PROBABILIDADE_BOCA:
        centro_boca = para_canvas([(u_junta + 55.0, 0.0)])[0]
        cv2.circle(
            cor,
            (int(centro_boca[0]), int(centro_boca[1])),
            round(RAIO_BOCA_MM * r),
            _bgr_de_hsv(0.0, 0.2, 0.05),
            -1,
        )

    nut = [
        (-ESPESSURA_NUT_MM, -_largura_em(0.0) / 2.0),
        (0.0, -_largura_em(0.0) / 2.0),
        (0.0, _largura_em(0.0) / 2.0),
        (-ESPESSURA_NUT_MM, _largura_em(0.0) / 2.0),
    ]
    cor_osso = tuple(int(rng.uniform(200.0, 235.0)) for _ in range(3))
    cv2.fillPoly(cor, [para_canvas(nut)], cor_osso)
    cv2.fillPoly(mascara, [para_canvas(nut)], 255)

    m_canvas = np.array([[1.0 / r, 0.0, u0], [0.0, 1.0 / r, -v_meia], [0.0, 0.0, 1.0]])
    h_canvas = h @ m_canvas
    cor_img = cv2.warpPerspective(
        cor, h_canvas, DIMENSOES, flags=cv2.INTER_LINEAR, borderValue=0
    )
    mascara_img = cv2.warpPerspective(
        mascara, h_canvas, DIMENSOES, flags=cv2.INTER_LINEAR, borderValue=0
    )
    _desenhar_borda(rng, cor_img, h, pescoco, media_madeira)
    _desenhar_trastes(rng, cor_img, h, jf, classe, vao)
    _desenhar_cordas(rng, cor_img, h, jf, classe)
    return cor_img, mascara_img


def _desenhar_borda(
    rng: random.Random,
    img: np.ndarray,
    h: np.ndarray,
    pescoco: list[tuple[float, float]],
    cor_madeira: np.ndarray,
) -> None:
    """Borda de 2 a 4 px em volta da escala, mais clara ou mais escura que a madeira.

    Args:
        rng: gerador do chamador.
        img: imagem BGR, alterada no lugar.
        h: homografia total (mm para px).
        pescoco: quatro cantos da escala, em mm, em ordem de contorno.
        cor_madeira: cor média da madeira (BGR, 0 a 255).
    """
    espessura = rng.uniform(*LARGURA_BORDA_PX)
    if rng.random() < 0.5:
        cor = np.clip(cor_madeira * 1.7 + 35.0, 0, 255)
    else:
        cor = np.clip(cor_madeira * 0.45, 0, 255)
    cor_int = tuple(int(c) for c in cor)
    cantos = aplicar_matriz(h, np.array(pescoco, dtype=float))
    for i in range(len(pescoco)):
        _linha_suave(img, cantos[i], cantos[(i + 1) % len(pescoco)], cor_int, espessura)


def _desenhar_trastes(
    rng: random.Random,
    img: np.ndarray,
    h: np.ndarray,
    jf: int,
    classe: str,
    vao: float,
) -> None:
    """Fios dos trastes, finos e prateados (15 % dourados), com brilho de 1 px.

    No aço, também os pontos de casa, por cima.

    Args:
        rng: gerador do chamador.
        img: imagem BGR, alterada no lugar.
        h: homografia total (mm para px).
        jf: último traste visível.
        classe: ``classico`` ou ``aco``.
        vao: vão no nut, em px (tamanho dos pontos de casa).
    """
    dourado = rng.random() < PROBABILIDADE_TRASTE_DOURADO
    cor_fio = (90, 175, 215) if dourado else (205, 210, 215)
    espessura = rng.uniform(*ESPESSURA_TRASTE_PX)
    trastes = trastes_no_plano(jf)
    for n in range(1, jf + 1):
        u = trastes[n]
        meia = _largura_em(u) / 2.0 + SOBRESSAIDA_TRASTE_MM
        pa, pb = aplicar_matriz(h, [[u, -meia], [u, meia]])
        _linha_suave(img, pa, pb, cor_fio, espessura)
        _linha_suave(
            img,
            pa + np.array([0.0, -1.0]),
            pb + np.array([0.0, -1.0]),
            (250, 250, 250),
            1.0,
            0.5,
        )
    if classe == "aco":
        raio = max(2, round(vao / VAO_NUT_MM))
        for n in CASAS_COM_PONTO:
            if n > jf:
                continue
            u = (trastes[n - 1] + trastes[n]) / 2.0
            centro = aplicar_matriz(h, [[u, 0.0]])[0]
            cv2.circle(
                img,
                (round(float(centro[0])), round(float(centro[1]))),
                raio,
                (235, 240, 240),
                -1,
                cv2.LINE_AA,
            )


def _desenhar_cordas(
    rng: random.Random,
    img: np.ndarray,
    h: np.ndarray,
    jf: int,
    classe: str,
) -> None:
    """Seis cordas de 1 a 3 px (crescente da 1 para a 6), com sombra e brilho de 1 px.

    No clássico, as três agudas são de nylon translúcido, mais claras e mais finas; as
    graves são bronze. No aço, as seis são metálicas, cinza-claras.

    Args:
        rng: gerador do chamador.
        img: imagem BGR, alterada no lugar.
        h: homografia total (mm para px).
        jf: último traste visível.
        classe: ``classico`` ou ``aco``.
    """
    u_fim = trastes_no_plano(jf)[jf] + EXTENSAO_SOBRE_CORPO_MM
    tom_aco = rng.uniform(-12.0, 12.0)
    for indice in range(6):
        espessura = 1.0 + 2.0 * indice / 5.0
        if classe == "classico" and indice < 3:
            cor, alpha = (238, 240, 240), 0.7
            espessura *= 0.8
        elif classe == "classico":
            cor, alpha = (70, 140, 190), 0.95
        else:
            cor = tuple(int(np.clip(c + tom_aco, 0, 255)) for c in (200, 205, 210))
            alpha = 0.9
        a = aplicar_matriz(h, [[0.0, _corda_em(indice, 0.0)]])[0]
        b = aplicar_matriz(h, [[u_fim, _corda_em(indice, u_fim)]])[0]
        _linha_suave(img, a + 1.0, b + 1.0, (0, 0, 0), espessura, 0.3)
        _linha_suave(img, a, b, cor, espessura, alpha)
        _linha_suave(
            img,
            a + np.array([-1.0, 0.0]),
            b + np.array([-1.0, 0.0]),
            (255, 255, 255),
            1.0,
            0.4,
        )


def _pele_do_quadro(
    rng: random.Random, quadro: np.ndarray
) -> tuple[np.ndarray, np.ndarray] | None:
    """Recorte de pele real de um quadro do acervo, segmentada por cor em YCrCb.

    Pega um componente conexo de pele com área entre ``FRACAO_AREA_PELE`` do quadro,
    sorteado com ``rng``. A máscara é suavizada para a colagem.

    Args:
        rng: gerador do chamador.
        quadro: quadro BGR do acervo (fora da M11b).

    Returns:
        ``(recorte_bgr, alfa)`` (alfa float32 de 0 a 1 do mesmo tamanho), ou ``None``
        se o quadro não tem componente de pele no tamanho pedido.
    """
    ycc = cv2.cvtColor(quadro, cv2.COLOR_BGR2YCrCb)
    cr, cb = ycc[..., 1], ycc[..., 2]
    pele = (
        (cr >= PELE_CR[0])
        & (cr <= PELE_CR[1])
        & (cb >= PELE_CB[0])
        & (cb <= PELE_CB[1])
    ).astype(np.uint8)
    nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    pele = cv2.morphologyEx(pele, cv2.MORPH_OPEN, nucleo)
    pele = cv2.morphologyEx(pele, cv2.MORPH_CLOSE, nucleo)
    _, rotulos, estatisticas, _ = cv2.connectedComponentsWithStats(pele, connectivity=8)
    area_quadro = quadro.shape[0] * quadro.shape[1]
    candidatos = [
        i
        for i in range(1, len(estatisticas))
        if FRACAO_AREA_PELE[0] * area_quadro
        <= estatisticas[i, cv2.CC_STAT_AREA]
        <= FRACAO_AREA_PELE[1] * area_quadro
    ]
    if not candidatos:
        return None
    escolhido = candidatos[rng.randrange(len(candidatos))]
    x, y, largura, altura = (int(v) for v in estatisticas[escolhido, :4])
    recorte = quadro[y : y + altura, x : x + largura].copy()
    mascara = (rotulos[y : y + altura, x : x + largura] == escolhido).astype(np.float32)
    alfa = cv2.GaussianBlur(mascara, (0, 0), 2.0)
    return recorte, alfa


def _colar_mao(
    img: np.ndarray,
    recorte: np.ndarray,
    alfa: np.ndarray,
    centro: np.ndarray,
    escala: float,
    angulo: float,
) -> None:
    """Cola um recorte de pele sobre a imagem, com escala e rotação, por máscara suave.

    Args:
        img: imagem BGR, alterada no lugar.
        recorte: recorte BGR da pele.
        alfa: máscara float32 (0 a 1) do recorte.
        centro: onde centrar o recorte, ``(x, y)`` em px da imagem.
        escala: fator de escala do recorte.
        angulo: rotação em graus.
    """
    altura, largura = recorte.shape[:2]
    cx, cy = largura / 2.0, altura / 2.0
    m = cv2.getRotationMatrix2D((cx, cy), angulo, escala)
    m[0, 2] += float(centro[0]) - cx
    m[1, 2] += float(centro[1]) - cy
    dimensoes = (img.shape[1], img.shape[0])
    pele = cv2.warpAffine(recorte, m, dimensoes, flags=cv2.INTER_LINEAR, borderValue=0)
    a = cv2.warpAffine(alfa, m, dimensoes, flags=cv2.INTER_LINEAR, borderValue=0)
    a = a[..., None]
    img[:] = np.clip(
        img.astype(np.float32) * (1.0 - a) + pele.astype(np.float32) * a, 0, 255
    ).astype(np.uint8)


def _ocluir(
    rng: random.Random,
    img: np.ndarray,
    h: np.ndarray,
    jf: int,
    fundos_mao: list[np.ndarray],
) -> list[dict]:
    """Oclusão por mão de pele real, de 0 a 2 mãos, sobre o braço.

    Com probabilidade ``PROBABILIDADE_MAO_COBRE_CASAS``, uma das mãos cobre de 2 a 4
    casas inteiras por cima das cordas. As demais caem em posições e escalas aleatórias
    sobre a escala. Se o quadro de pele não tem componente, a oclusão é pulada.

    Args:
        rng: gerador do chamador.
        img: imagem composta, alterada no lugar.
        h: homografia total (mm para px).
        jf: último traste visível.
        fundos_mao: quadros do acervo de onde sai a pele (fora da M11b), tentados em
            ordem até achar um componente de pele no tamanho pedido.

    Returns:
        Uma entrada por mão colada, com ``tipo`` e, se cobre casas, ``casas``.
    """
    cobrir = rng.random() < PROBABILIDADE_MAO_COBRE_CASAS
    total = rng.randint(1, 2) if cobrir else rng.randint(0, 2)
    trastes = trastes_no_plano(jf)
    colocadas: list[dict] = []
    for i in range(total):
        recorte = None
        for fundo_mao in fundos_mao:
            recorte = _pele_do_quadro(rng, fundo_mao)
            if recorte is not None:
                break
        if recorte is None:
            break
        bgr, alfa = recorte
        if cobrir and i == 0:
            m = rng.choice(CASAS_COBERTAS)
            k = rng.randint(1, jf - m)
            u_centro = (trastes[k] + trastes[k + m]) / 2.0
            v = rng.uniform(-0.3, 0.3) * _largura_em(u_centro)
            centro = aplicar_matriz(h, [[u_centro, v]])[0]
            a = aplicar_matriz(h, [[trastes[k], 0.0]])[0]
            b = aplicar_matriz(h, [[trastes[k + m], 0.0]])[0]
            escala = float(np.linalg.norm(b - a)) / max(bgr.shape[:2])
            colocadas.append({"tipo": "mao_cobre_casas", "casas": [k, k + m]})
        else:
            u = rng.uniform(5.0, trastes[jf] - 15.0)
            v = rng.uniform(-0.35, 0.35) * _largura_em(u)
            centro = aplicar_matriz(h, [[u, v]])[0]
            escala = rng.uniform(*ESCALA_MAO_GERAL)
            colocadas.append({"tipo": "mao"})
        _colar_mao(img, bgr, alfa, centro, escala, rng.uniform(0.0, 360.0))
    return colocadas


def _degradar(rng: random.Random, img: np.ndarray) -> np.ndarray:
    """Degradação: desfoque, ruído, brilho e contraste, e JPEG com qualidade 60 a 95.

    Args:
        rng: gerador do chamador.
        img: imagem BGR uint8.

    Returns:
        Imagem BGR uint8, depois de codificar e decodificar em JPEG.
    """
    sigma = rng.uniform(0.0, 1.5)
    if sigma > 0.05:
        k = 2 * math.ceil(3.0 * sigma) + 1
        img = cv2.GaussianBlur(img, (k, k), sigma)
    ruido = rng.uniform(0.0, 6.0)
    gerador = np.random.default_rng(rng.randrange(2**32))
    comum = img.astype(np.float32) + gerador.normal(0.0, ruido, img.shape).astype(
        np.float32
    )
    alpha = rng.uniform(0.75, 1.25)
    beta = rng.uniform(-20.0, 20.0)
    img = np.clip(alpha * comum + beta, 0, 255).astype(np.uint8)
    qualidade = rng.randint(60, 95)
    _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, qualidade])
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def _arredondar(pontos: np.ndarray) -> list:
    """Pontos em lista, com 2 casas decimais.

    Args:
        pontos: array ``(N, 2)`` de pontos.

    Returns:
        Lista de ``[x, y]``.
    """
    return [[round(float(x), 2), round(float(y), 2)] for x, y in pontos]


def _no_tamanho(imagem: np.ndarray) -> np.ndarray:
    """Imagem no tamanho da cena (``DIMENSOES``), redimensionada se preciso.

    Args:
        imagem: quadro BGR de qualquer tamanho.

    Returns:
        Quadro BGR de 1920 x 1080.
    """
    if imagem.shape[:2][::-1] == DIMENSOES:
        return imagem
    return cv2.resize(imagem, DIMENSOES)


def gerar(
    rng: random.Random,
    fundo: np.ndarray,
    fundos_mao: list[np.ndarray] | None = None,
) -> tuple[np.ndarray, dict]:
    """Gera um braço sintético sobre um fundo, com o registro exato do rótulo.

    Args:
        rng: gerador do chamador (a semente é do chamador).
        fundo: quadro BGR de fundo, de qualquer tamanho (é redimensionado).
        fundos_mao: quadros do acervo de onde sai a pele da mão (fora da M11b), em
            ordem de tentativa. Se ``None``, usa só o próprio ``fundo``.

    Returns:
        ``(imagem, registro)``: imagem BGR uint8 de 1920 x 1080 e o registro no formato
        do gabarito (``braco``, ``nut``, ``corda1``, ``corda6``, ``trastes`` contíguos a
        partir do 1), mais ``classe``, ``casa_juncao`` e ``oclusoes``.
    """
    classe = rng.choice(CLASSES)
    jf = TRASTE_JUNCAO[classe]
    h, vao = _sortear_vista(rng, jf)
    base = _no_tamanho(fundo)
    maos_base = [base] if fundos_mao is None else [_no_tamanho(f) for f in fundos_mao]
    cor, mascara = _desenhar_objeto(rng, h, jf, classe, vao)
    a = mascara.astype(np.float32)[..., None] / 255.0
    img = (base.astype(np.float32) * (1.0 - a) + cor.astype(np.float32) * a).astype(
        np.uint8
    )
    oclusoes = _ocluir(rng, img, h, jf, maos_base)
    img = _degradar(rng, img)
    u_junta = trastes_no_plano(jf)[jf]
    registro = {
        "braco": "sim",
        "nut": _arredondar(aplicar_matriz(h, [[0.0, 0.0]]))[0],
        "corda1": _arredondar(
            aplicar_matriz(
                h, [[0.0, _corda_em(0, 0.0)], [u_junta, _corda_em(0, u_junta)]]
            )
        ),
        "corda6": _arredondar(
            aplicar_matriz(
                h, [[0.0, _corda_em(5, 0.0)], [u_junta, _corda_em(5, u_junta)]]
            )
        ),
        "trastes": _arredondar(
            aplicar_matriz(h, [[t, 0.0] for t in trastes_no_plano(jf)[1:]])
        ),
        "traste_referencia": None,
        "paineis": None,
        "classe": classe,
        "casa_juncao": jf,
        "oclusoes": oclusoes,
    }
    return img, registro


def videos_proibidos() -> frozenset[str]:
    """Arquivos de vídeo que não podem entrar em S, R nem G (os da M11b).

    Lê só o campo ``chave`` de cada quadro de ``braco_m11b.json``, sem abrir as marcas.

    Returns:
        Conjunto de caminhos relativos ao acervo.
    """
    quadros = json.loads(GABARITO_BRACO_M11B.read_text(encoding="utf-8"))["quadros"]
    return frozenset(
        str(quadro["chave"]).split("|")[0]
        for quadro in quadros.values()
        if quadro.get("chave")
    )


def conferir_fora_m11b(arquivo: str, proibidos: frozenset[str]) -> None:
    """Levanta erro se o vídeo é da M11b (barreira de dados, não pode ser contornada).

    Args:
        arquivo: caminho do vídeo relativo ao acervo.
        proibidos: conjunto de ``videos_proibidos``.

    Raises:
        ValueError: se o vídeo está na M11b.
    """
    if arquivo in proibidos:
        raise ValueError(f"vídeo da M11b não pode entrar em S, R ou G: {arquivo}")


def duracao_do_video(video: Path) -> float:
    """Duração de um vídeo do acervo, em segundos, pelo ffprobe.

    Args:
        video: arquivo no acervo (só leitura).

    Returns:
        Duração em segundos.

    Raises:
        subprocess.CalledProcessError: se o ffprobe falhar.
    """
    comando = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "csv=p=0",
        str(video),
    ]
    saida = subprocess.run(comando, capture_output=True, text=True, check=True)
    return float(saida.stdout.strip())


def quadro_em(video: Path, t: float) -> np.ndarray | None:
    """Quadro do vídeo no instante ``t``, lido como o rastreador lê (ffmpeg).

    Args:
        video: arquivo no acervo (só leitura).
        t: instante em segundos.

    Returns:
        Imagem BGR, ou ``None`` se não há quadro nesse instante.
    """
    passo = PARAMETROS_PADRAO.passo_s
    gerador = ler_trecho(video, t, t + passo, passo)
    try:
        par = next(gerador, None)
    finally:
        gerador.close()
    return None if par is None else par[1]


def _videos_do_acervo() -> list[str]:
    """Todos os vídeos do acervo, como caminhos relativos e ordenados.

    Returns:
        Lista ordenada de caminhos relativos ao acervo.
    """
    raiz = acervo()
    encontrados = []
    for pasta, _subpastas, nomes in os.walk(raiz):
        for nome in nomes:
            if Path(nome).suffix.lower() in EXTENSOES_VIDEO:
                encontrados.append(str(Path(pasta, nome).relative_to(raiz)))
    return sorted(encontrados)


def fundos(n: int, rng: random.Random, pasta: Path = MAOS_M21 / "fundos") -> list[dict]:
    """Sorteia ``n`` quadros de vídeos do acervo fora da M11b, como JPEG.

    Os vídeos são embaralhados com ``rng`` e lidos em ordem até somar ``n`` quadros, a
    10 % a 90 % da duração de cada um. Se o índice já existe, é reaproveitado.

    Args:
        n: quantidade de quadros de fundo.
        rng: gerador do chamador (semente fixa).
        pasta: onde gravar os JPEG e o ``indice.json``.

    Returns:
        Uma entrada por quadro, com ``arquivo``, ``t`` e ``jpg``.

    Raises:
        RuntimeError: se não há quadros suficientes no acervo.
        ValueError: se o índice existente tem outro tamanho.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo_indice = pasta / ARQUIVO_INDICE_FUNDOS
    if arquivo_indice.exists():
        existentes = json.loads(arquivo_indice.read_text(encoding="utf-8"))["fundos"]
        if len(existentes) != n:
            raise ValueError(f"índice de fundos tem {len(existentes)}, pedidos {n}")
        return existentes
    proibidos = videos_proibidos()
    candidatos = [a for a in _videos_do_acervo() if a not in proibidos]
    entradas: list[dict] = []
    for arquivo in rng.sample(candidatos, len(candidatos)):
        if len(entradas) == n:
            break
        conferir_fora_m11b(arquivo, proibidos)
        video = acervo() / arquivo
        try:
            duracao = duracao_do_video(video)
        except subprocess.CalledProcessError:
            continue
        t = rng.uniform(0.1 * duracao, 0.9 * duracao)
        quadro = quadro_em(video, t)
        if quadro is None:
            continue
        nome = f"{len(entradas):04d}.jpg"
        cv2.imwrite(str(pasta / nome), quadro, [cv2.IMWRITE_JPEG_QUALITY, 95])
        entradas.append({"arquivo": arquivo, "t": round(t, 3), "jpg": nome})
    if len(entradas) < n:
        raise RuntimeError(f"só {len(entradas)} quadros de fundo, pedidos {n}")
    arquivo_indice.write_text(
        json.dumps({"fundos": entradas}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return entradas
