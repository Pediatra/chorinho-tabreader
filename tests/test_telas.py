"""Testes de `tab/telas.py` (Fase 3): sem GPU e sem acervo.

O vídeo sintético é gerado no `tmp_path` com `cv2.VideoWriter` (mp4v): páginas A, B, A e uma
faixa colorida andando por cima (o marcador). A faixa NÃO pode gerar troca.
"""

from pathlib import Path

import cv2
import numpy as np

from tab.telas import (
    Tela,
    assinatura,
    avaliar_ouro,
    cortar_em_paginas,
    deslocamento_rolagem,
    distancia_iou,
    histograma,
    refinar_borda,
    tela_em,
    telas,
    tinta_majoritaria,
    uniao_retangulos,
)

LARGURA = 320
ALTURA = 120
FPS = 10.0
SEGUNDOS_POR_PAGINA = 6
PAINEL = (0, 0, LARGURA, ALTURA)


def _pagina(semente: int) -> np.ndarray:
    """Página BGR clara com 6 cordas e 14 algarismos grandes em lugares sorteados.

    Args:
        semente: define onde ficam os algarismos (cada página tem a sua).

    Returns:
        Imagem ``ALTURA x LARGURA``.
    """
    img = np.full((ALTURA, LARGURA, 3), 250, np.uint8)
    for k in range(6):
        y = 20 + k * 16
        cv2.line(img, (0, y), (LARGURA, y), (0, 0, 0), 1)
    rng = np.random.default_rng(semente)
    for _ in range(14):
        x = int(rng.integers(5, LARGURA - 30))
        y = int(rng.integers(30, ALTURA - 5))
        cv2.putText(
            img,
            str(int(rng.integers(0, 9))),
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 0),
            3,
        )
    return img


def _com_faixa(pagina: np.ndarray, x: int) -> np.ndarray:
    """Cópia da página com uma faixa azul pálida translúcida em ``x``.

    Args:
        pagina: página BGR.
        x: coluna esquerda da faixa.

    Returns:
        A página com o marcador.
    """
    img = pagina.copy()
    faixa = img[:, x : x + 14].astype(np.float32)
    azul = np.array([255, 150, 90], np.float32)
    img[:, x : x + 14] = (0.6 * faixa + 0.4 * azul).astype(np.uint8)
    return img


def _gerar_video(destino: Path) -> Path:
    """Grava o vídeo A, B, A (6 s cada) com a faixa andando.

    Args:
        destino: arquivo ``.mp4``.

    Returns:
        O mesmo caminho.
    """
    escritor = cv2.VideoWriter(
        str(destino), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (LARGURA, ALTURA)
    )
    paginas = [_pagina(1), _pagina(2), _pagina(1)]
    k = 0
    for pagina in paginas:
        for _ in range(int(SEGUNDOS_POR_PAGINA * FPS)):
            escritor.write(_com_faixa(pagina, (k * 7) % (LARGURA - 14)))
            k += 1
    escritor.release()
    return destino


def test_video_sintetico_duas_telas_a_com_duas_exibicoes(tmp_path: Path) -> None:
    """A, B, A com faixa andando: 2 telas; A tem 2 exibições; a faixa não gera troca."""
    video = _gerar_video(tmp_path / "abA.mp4")
    resultado = telas(str(video), detectar=lambda _q: PAINEL)
    assert len(resultado) == 2
    a, b = resultado
    assert len(a.exibicoes) == 2
    assert len(b.exibicoes) == 1
    assert a.exibicoes[0][0] < 0.6 and abs(a.exibicoes[0][1] - 6.0) <= 0.6
    assert abs(b.exibicoes[0][0] - 6.0) <= 0.6 and abs(b.exibicoes[0][1] - 12.0) <= 0.6
    assert abs(a.exibicoes[1][0] - 12.0) <= 0.6
    assert a.painel == PAINEL
    assert a.modo == "paginado"
    assert tela_em(resultado, 3.0) == a.id
    assert tela_em(resultado, 9.0) == b.id
    assert tela_em(resultado, 15.0) == a.id


def test_assinatura_apaga_a_faixa_colorida() -> None:
    """A tinta da página com faixa é (quase) a da página sem faixa."""
    pagina = _pagina(1)
    limpa, ok_limpa, colorido0 = assinatura(pagina)
    suja, ok_suja, colorido1 = assinatura(_com_faixa(pagina, 100))
    assert colorido0 == 0.0 and colorido1 > 0.03
    assert distancia_iou(limpa, suja) < 0.1
    assert distancia_iou(limpa, suja, ok_limpa, ok_suja) < 0.02
    assert distancia_iou(limpa, assinatura(_pagina(2))[0]) > 0.5


def test_assinatura_serve_a_tema_escuro() -> None:
    """Página invertida (tinta clara em fundo escuro) tem a mesma tinta."""
    pagina = _pagina(1)
    claro, _, _ = assinatura(pagina)
    escuro, _, _ = assinatura(255 - pagina)
    assert distancia_iou(claro, escuro) < 0.1


def test_distancia_iou() -> None:
    """Idênticas 0, disjuntas 1, metade 1/3 de interseção, brancas 0, tamanho diferente."""
    a = np.zeros((4, 8), bool)
    a[:, :4] = True
    b = np.zeros((4, 8), bool)
    b[:, 4:] = True
    assert distancia_iou(a, a) == 0.0
    assert distancia_iou(a, b) == 1.0
    c = np.zeros((4, 8), bool)
    c[:, 2:6] = True
    assert abs(distancia_iou(a, c) - (1 - 8 / 24)) < 1e-9
    assert distancia_iou(np.zeros((4, 8), bool), np.zeros((4, 8), bool)) == 0.0
    grande = np.kron(a, np.ones((2, 2), bool))
    assert distancia_iou(a, grande) == 0.0


def test_cortar_em_paginas_agrupa_e_absorve_transicao() -> None:
    """A A A | B B B | A A | mistura | B B B: a mistura (1 amostra) é absorvida."""
    rng = np.random.default_rng(3)
    a, b, mix = (rng.random((20, 40)) > 0.7 for _ in range(3))
    serie = [a, a, a, b, b, b, a, a, mix, b, b, b]
    trechos, dist, rolando = cortar_em_paginas(serie, limiar=0.15)
    assert len(dist) == len(serie) - 1
    assert rolando == 0
    # a mistura (1 amostra) é absorvida pelo trecho anterior (A A)
    assert trechos == [(0, 2), (3, 5), (6, 8), (9, 11)]


def test_rolagem_so_quando_o_deslocamento_explica() -> None:
    """Padrão deslocado 3 px é rolagem e não corta; páginas diferentes cortam."""
    rng = np.random.default_rng(0)
    base = rng.random((40, 120)) > 0.7
    movida = np.roll(base, 3, axis=1)
    achado = deslocamento_rolagem(base, movida, limiar=0.5)
    assert achado is not None and abs(abs(achado[0]) - 3) < 0.7
    outra = rng.random((40, 120)) > 0.7
    assert deslocamento_rolagem(base, outra, limiar=0.5) is None
    trechos, _, rolando = cortar_em_paginas(
        [base, movida, np.roll(base, 6, axis=1)], 0.15
    )
    assert trechos == [(0, 2)]
    assert rolando == 2


def test_tinta_majoritaria_apaga_marcador_que_anda() -> None:
    """Um bloco que aparece em 1 de 3 amostras some no voto."""
    rng = np.random.default_rng(4)
    fixo = rng.random((20, 40)) > 0.7
    com_marcador = fixo.copy()
    com_marcador[:, 30:36] = True
    voto, _ = tinta_majoritaria([fixo, com_marcador, fixo])
    assert distancia_iou(voto, fixo) == 0.0


def test_refinar_borda_chega_a_resolucao() -> None:
    """Busca binária acha a borda a menos de 1 s, nos dois sentidos."""
    borda = 12.3
    ate = refinar_borda(lambda t: t >= borda, 10.0, 15.0)
    assert abs(ate - borda) <= 1.0 and ate >= borda
    de_volta = refinar_borda(lambda t: t < borda, 15.0, 10.0)
    assert abs(de_volta - borda) <= 1.0 and de_volta < borda


def test_uniao_e_histograma() -> None:
    """União de retângulos e histograma com o vale vazio."""
    assert uniao_retangulos([(1, 5, 10, 20), (0, 6, 12, 18)]) == (0, 5, 12, 20)
    h = histograma([0.0, 0.01, 0.07, 0.25, 0.9])
    assert sum(h.values()) == 5
    assert h["[0.1,0.15)"] == 0 and h["[0.15,0.2)"] == 0


def test_avaliar_ouro_mapeia_pelo_quadro_ref() -> None:
    """Correspondente = tela prevista que contém o quadro_ref do ouro."""
    previstas = [
        Tela(1, PAINEL, [(0.0, 10.0), (30.0, 40.0)]),
        Tela(2, PAINEL, [(10.0, 30.0)]),
    ]
    ouro = {
        "telas": [{"id": 1, "quadro_ref_s": 5.0}, {"id": 2, "quadro_ref_s": 35.0}],
        "instantes": [
            {"t": 2, "tela": 1},
            {"t": 33, "tela": 2},  # ouro 2 mapeia para a prevista 1: certo
            {"t": 15, "tela": 1},  # prevista 2: errado
            {"t": 50, "tela": 1},  # fora de qualquer exibição: errado
        ],
    }
    r = avaliar_ouro(ouro, previstas)
    assert r["instantes_certos"] == 2 and r["instantes"] == 4
    assert r["telas_ouro_com_prevista"] == 2
    assert r["ouro_juntadas_pelo_produto"] == {"1": [1, 2]}
    assert r["previstas_a_mais"] == 1
    assert [e["t"] for e in r["erros"]] == [15, 50]
