"""Testes do detector de pauta (imagens sintéticas, sem acervo nem GPU)."""

from __future__ import annotations

import cv2
import numpy as np

from tab.partitura_pauta import (
    achar_pautas,
    classe_do_quadro,
    classe_do_video,
)

ALTURA = 1080
LARGURA = 1920


def _quadro_branco() -> np.ndarray:
    """Quadro branco 1080x1920, ``uint8``.

    Returns:
        Imagem BGR toda branca.
    """
    return np.full((ALTURA, LARGURA, 3), 255, np.uint8)


def _desenhar_linhas(
    img: np.ndarray,
    y0: int,
    entrelinha: int,
    n: int = 5,
    x0: int = 200,
    x1: int = 1700,
    espessura: int = 2,
    cor: int = 0,
) -> None:
    """Desenha ``n`` linhas horizontais equiespaçadas.

    Args:
        img: imagem onde desenhar (alterada no lugar).
        y0: y da primeira linha.
        entrelinha: distância em px entre linhas consecutivas.
        n: quantas linhas.
        x0: início horizontal.
        x1: fim horizontal.
        espessura: espessura em px.
        cor: intensidade (0 = preto).
    """
    for k in range(n):
        y = y0 + k * entrelinha
        cv2.line(img, (x0, y), (x1, y), (cor, cor, cor), espessura)


def _desenhar_cabecas(img: np.ndarray, y0: int, entrelinha: int, n: int = 30) -> None:
    """Desenha cabeças de nota cheias e hastes verticais sobre a pauta.

    Args:
        img: imagem onde desenhar (alterada no lugar).
        y0: y da primeira linha da pauta.
        entrelinha: entrelinha da pauta.
        n: quantas notas.
    """
    for k in range(n):
        x = 260 + k * 45
        y = y0 + (k % 5) * entrelinha
        cv2.circle(img, (x, y), 8, (0, 0, 0), -1)
        cv2.line(img, (x + 8, y), (x + 8, y - 60), (0, 0, 0), 2)


def test_uma_pauta_simples() -> None:
    """Cinco linhas limpas: uma pauta, com entrelinha e ys corretos."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 20)
    pautas = achar_pautas(img)
    assert len(pautas) == 1
    pauta = pautas[0]
    assert abs(pauta.entrelinha - 20) <= 1
    for medido, esperado in zip(pauta.ys, [300, 320, 340, 360, 380], strict=True):
        assert abs(medido - esperado) <= 1
    assert pauta.caixa[1] == pauta.ys[0]
    assert pauta.caixa[3] == pauta.ys[4]


def test_pauta_com_cabecas_de_nota_e_hastes() -> None:
    """Cabeças e hastes não quebram nem duplicam a pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 20)
    _desenhar_cabecas(img, 300, 20)
    assert len(achar_pautas(img)) == 1


def test_seis_linhas_equiespacadas_sao_tablatura() -> None:
    """Seis linhas iguais são tablatura: nenhuma pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 20, n=6)
    assert achar_pautas(img) == []


def test_sexta_linha_curta_ainda_e_tablatura() -> None:
    """A 6ª linha com 40% da largura ainda conta, pelo passo 5."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 20, n=5)
    # 6ª linha a uma entrelinha abaixo da última, com 40% da largura.
    cv2.line(img, (200, 400), (200 + int(0.40 * LARGURA), 400), (0, 0, 0), 2)
    assert achar_pautas(img) == []


def test_duas_pautas_ordenadas() -> None:
    """Duas pautas separadas: duas, em ordem de y."""
    img = _quadro_branco()
    _desenhar_linhas(img, 600, 20)
    _desenhar_linhas(img, 200, 20)
    pautas = achar_pautas(img)
    assert len(pautas) == 2
    assert pautas[0].ys[0] < pautas[1].ys[0]
    assert abs(pautas[0].ys[0] - 200) <= 1
    assert abs(pautas[1].ys[0] - 600) <= 1


def test_linhas_curtas_nao_sao_pauta() -> None:
    """Linhas de 150 px não passam o mínimo de extensão: nenhuma pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 20, x0=800, x1=950)
    assert achar_pautas(img) == []


def test_polaridade_invertida() -> None:
    """Fundo preto com linhas brancas: uma pauta."""
    img = np.zeros((ALTURA, LARGURA, 3), np.uint8)
    _desenhar_linhas(img, 300, 20, cor=255)
    assert len(achar_pautas(img)) == 1


def test_ruido_nao_e_pauta() -> None:
    """Ruído uniforme com semente fixa não gera pauta."""
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(ALTURA, LARGURA, 3), dtype=np.uint8)
    assert achar_pautas(img) == []


def test_entrelinha_oito() -> None:
    """Entrelinha pequena (8 px): uma pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 8)
    assert len(achar_pautas(img)) == 1


def test_entrelinha_trinta_e_cinco() -> None:
    """Entrelinha grande (35 px): uma pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 200, 35)
    assert len(achar_pautas(img)) == 1


def test_classe_do_quadro() -> None:
    """Tabela de ``classe_do_quadro``."""
    assert classe_do_quadro(1, True) == "pauta+tab"
    assert classe_do_quadro(2, True) == "pauta+tab"
    assert classe_do_quadro(1, False) == "so_pauta"
    assert classe_do_quadro(0, True) == "so_tab"
    assert classe_do_quadro(0, False) == "nenhum"


def test_classe_do_video() -> None:
    """Precedência de ``classe_do_video``: pauta+tab > so_pauta > so_tab > nenhum."""
    assert classe_do_video(["nenhum", "pauta+tab", "so_pauta"]) == "pauta+tab"
    assert classe_do_video(["so_tab", "so_pauta", "nenhum"]) == "so_pauta"
    assert classe_do_video(["nenhum", "so_tab"]) == "so_tab"
    assert classe_do_video(["nenhum", "nenhum"]) == "nenhum"
    assert classe_do_video([]) == "nenhum"


def test_tab_com_primeira_linha_borrada_ainda_e_tablatura() -> None:
    """A 1ª linha grossa (espessura 5, descartada na lista) não faz 5 linhas virarem pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 20, n=1, espessura=5)
    _desenhar_linhas(img, 320, 20, n=5)
    assert achar_pautas(img) == []


def test_tab_cinza_em_fundo_branco_e_tablatura() -> None:
    """Tablatura cinza (120) em fundo branco, entrelinha 27: nenhuma pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 27, n=6, cor=120)
    assert achar_pautas(img) == []


def test_tab_com_retangulo_vertical_encostado() -> None:
    """Tablatura de 6 linhas com um bloco vertical encostado (diagrama): nenhuma pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 20, n=6)
    cv2.rectangle(img, (120, 280), (199, 400), (0, 0, 0), -1)
    assert achar_pautas(img) == []


def _bloco_lateral(img: np.ndarray, y0: int, y1: int) -> None:
    """Retângulo preto de 150x200 px encostado à esquerda da pauta, cobrindo a altura dela.

    Imita a chave ou o colchete de um sistema: contagem de tinta constante em muitas linhas
    de pixel, que engrossa a sequência de linhas no perfil.

    Args:
        img: imagem onde desenhar (alterada no lugar).
        y0: topo do bloco.
        y1: base do bloco.
    """
    cv2.rectangle(img, (50, y0), (199, y1), (0, 0, 0), -1)


def test_pauta_com_bloco_lateral_continua_pauta() -> None:
    """Pauta real ao lado de um bloco preto de 150x200 px: continua 1 pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 400, 16)
    _bloco_lateral(img, 370, 490)
    assert len(achar_pautas(img)) == 1


def test_tab_com_bloco_lateral_continua_tablatura() -> None:
    """Tablatura de 6 linhas com o mesmo bloco lateral: nenhuma pauta."""
    img = _quadro_branco()
    _desenhar_linhas(img, 400, 16, n=6)
    _bloco_lateral(img, 370, 500)
    assert achar_pautas(img) == []


def test_pauta_de_linhas_grossas() -> None:
    """Pauta grande (entrelinha 20, linhas de 5 px, como a Gymnopédie) é achada."""
    img = _quadro_branco()
    for k in range(5):  # faixas exatas de 5 px (cv2.line de espessura 5 desenha 7)
        img[298 + 20 * k : 303 + 20 * k, 200:1700] = 0
    pautas = achar_pautas(img)
    assert len(pautas) == 1
    assert abs(pautas[0].entrelinha - 20) <= 1


def test_tab_de_linhas_grossas_nao_e_pauta() -> None:
    """Tablatura de 6 linhas de 5 px continua rejeitada."""
    img = _quadro_branco()
    for k in range(6):
        img[298 + 30 * k : 303 + 30 * k, 200:1700] = 0
    assert achar_pautas(img) == []


def test_pedaco_curto_a_uma_entrelinha_nao_derruba_pauta() -> None:
    """Objeto curto (chave, 200 px) a uma entrelinha acima da pauta não é 6ª linha."""
    img = _quadro_branco()
    _desenhar_linhas(img, 300, 18)
    img[279:285, 120:320] = 0
    assert len(achar_pautas(img)) == 1


def test_barra_de_colcheias_acima_nao_derruba_pauta() -> None:
    """Barra grossa (6 px, 400 px) a uma entrelinha acima da pauta não é 6ª linha."""
    img = _quadro_branco()
    for k in range(5):  # linhas de 2 px exatos, como no acervo (cv2.line desenha 3-4)
        img[300 + 18 * k : 302 + 18 * k, 200:1700] = 0
    img[279:285, 900:1300] = 0
    assert len(achar_pautas(img)) == 1
