"""O detector de afinação/capotraste: acha texto, não inventa em fundo liso.

Testes sintéticos, sem acervo: um quadro com "texto" desenhado tem de gerar candidato,
um quadro liso ou de textura (madeira) **não**. Os quadros reais que motivaram o desenho
estão descritos em `tab/afinacao.py` (`Capo fret 4` no `shin izumi`, `⑥=D` no `iwaki`).
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.tablatura.censo.afinacao import (
    Bloco,
    agrupar,
    candidatos,
    normalizar,
    rotulo_instante,
)
from tab.tablatura.leitura.painel import uniformidade


def _liso(altura: int = 720, largura: int = 1280) -> np.ndarray:
    """Fundo de cor sólida, sem nada para o detector achar."""
    return np.full((altura, largura, 3), 240, np.uint8)


def _com_texto(altura: int = 720, largura: int = 1280) -> np.ndarray:
    """Fundo liso com uma linha de texto escura, tipo cabeçalho de partitura."""
    img = _liso(altura, largura)
    cv2.putText(
        img,
        "Standard tuning EADGBE",
        (60, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (25, 25, 25),
        2,
        cv2.LINE_AA,
    )
    return img


def _madeira(altura: int = 720, largura: int = 1280, semente: int = 0) -> np.ndarray:
    """Textura de madeira com veio: o falso positivo que a medição tem de recusar."""
    rng = np.random.default_rng(semente)
    base = rng.integers(60, 210, (altura, largura), dtype=np.uint8)
    veio = cv2.GaussianBlur(base, (0, 0), 1.0)
    cinza = np.clip(veio.astype(np.int16) + np.linspace(-45, 45, largura), 0, 255)
    return cv2.cvtColor(cinza.astype(np.uint8), cv2.COLOR_GRAY2BGR)


def _avaliada(blocos: list[Bloco], caixa: tuple[int, int, int, int]) -> bool:
    """Algum bloco cobre a caixa dada (interseção não vazia)?"""
    x0, y0, x1, y1 = caixa
    return any(
        min(b.x1, x1) > max(b.x0, x0) and min(b.y1, y1) > max(b.y0, y0) for b in blocos
    )


def test_texto_desenhado_gera_candidato() -> None:
    """Uma linha de texto no quadro tem de virar candidato, na região do texto."""
    blocos = candidatos(_com_texto())
    assert blocos, "nenhum candidato numa imagem com texto"
    assert _avaliada(blocos, (60, 90, 560, 130))
    assert max(b.score for b in blocos) > 0.6


def test_imagem_lisa_nao_gera_candidato() -> None:
    """Fundo de cor sólida não pode gerar candidato nenhum."""
    assert candidatos(_liso()) == []


def test_imagem_escura_lisa_nao_gera_candidato() -> None:
    """O mesmo no escuro (o `sky guitar` é fundo preto com texto claro)."""
    assert candidatos(np.zeros((720, 1280, 3), np.uint8)) == []


def test_textura_de_madeira_nao_gera_candidato() -> None:
    """Madeira com veio tem tinta de sobra, mas não tem estrutura de texto.

    É o caso medido no `paolo d'angelo`/`violaodecria`: o braço do violão já enganou o
    detector de painel duas vezes.
    """
    assert candidatos(_madeira()) == []


def test_texto_claro_em_fundo_escuro_gera_candidato() -> None:
    """Texto branco sobre preto (a polaridade oposta) também é texto."""
    img = np.zeros((720, 1280, 3), np.uint8)
    cv2.putText(
        img,
        "Tuning: Drop D",
        (80, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )
    blocos = candidatos(img)
    assert blocos and _avaliada(blocos, (80, 110, 420, 150))


def test_linha_continua_atravessando_o_bloco_e_recusada() -> None:
    """Um bloco cortado por uma corda/linha contínua não é texto (é tablatura)."""
    img = _liso()
    cv2.putText(
        img,
        "2 0 3 2",
        (200, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (25, 25, 25),
        2,
        cv2.LINE_AA,
    )
    caixa = (200, 170, 400, 210)
    assert _avaliada(candidatos(img), caixa), (
        "sem a corda, os algarismos são candidatos"
    )
    cv2.line(img, (120, 196), (520, 196), (25, 25, 25), 2)
    assert not _avaliada(candidatos(img), caixa)


def test_tablatura_sintetica_nao_gera_candidato() -> None:
    """6 cordas com algarismos em cima **não** são texto: é a própria tablatura.

    Sem este portão o detector acharia a linha de números em quase todo o acervo — a
    tablatura é justamente uma fileira de componentes pequenos, iguais e alinhados.
    """
    img = np.full((720, 1280, 3), 245, np.uint8)
    for i in range(6):
        cv2.line(img, (40, 300 + i * 30), (1240, 300 + i * 30), (30, 30, 30), 1)
    for j, x in enumerate(range(90, 1200, 70)):
        cv2.putText(
            img,
            str(j % 8),
            (x, 390),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (20, 20, 20),
            2,
        )
    assert candidatos(img) == []


def test_metade_superior_so_acha_texto_no_topo() -> None:
    """Com `frac_topo=0.5` o texto do rodapé fica fora e o do topo continua dentro."""
    img = _liso(720, 1280)
    cv2.putText(
        img, "Capo fret 4", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (20, 20, 20), 2
    )
    cv2.putText(
        img, "Capo fret 4", (80, 660), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (20, 20, 20), 2
    )
    topo = candidatos(img, frac_topo=0.5)
    assert _avaliada(topo, (80, 70, 360, 110))
    assert not _avaliada(topo, (80, 630, 360, 670))
    assert _avaliada(candidatos(img, frac_topo=1.0), (80, 630, 360, 670))


def test_agrupar_junta_o_mesmo_texto_em_instantes_diferentes() -> None:
    """O mesmo bloco em 3 s e 8 s é um candidato com dois instantes, não dois."""
    a = Bloco(100, 200, 400, 230, 8, 20.0, 0.1, 0.1, 0.2, 0.9, 200.0, 0.8)
    b = Bloco(104, 202, 404, 232, 8, 20.0, 0.1, 0.1, 0.2, 0.9, 200.0, 0.7)
    longe = Bloco(900, 600, 1100, 630, 5, 18.0, 0.1, 0.1, 0.2, 0.9, 200.0, 0.6)
    grupos = agrupar([(3.0, a), (8.0, b), (15.0, longe)])
    assert len(grupos) == 2
    juntos = [g for g in grupos if len(g["instantes"]) == 2]
    assert juntos and juntos[0]["instantes"] == [3.0, 8.0]
    assert juntos[0]["score"] == 0.8


def test_agrupar_nao_repete_instante() -> None:
    """Dois blocos do mesmo quadro podem cair no mesmo grupo; o instante conta 1 vez."""
    a = Bloco(100, 200, 400, 230, 8, 20.0, 0.1, 0.1, 0.2, 0.9, 200.0, 0.8)
    b = Bloco(104, 202, 404, 232, 8, 20.0, 0.1, 0.1, 0.2, 0.9, 200.0, 0.7)
    grupos = agrupar([(3.0, a), (3.0, b)])
    assert len(grupos) == 1
    assert grupos[0]["instantes"] == [3.0]


def test_normalizar_casa_com_a_pasta_do_acervo() -> None:
    """`guitar dell'arte` (como o dono escreve) casa com a pasta acentuada."""
    assert normalizar("guitar dell'arte") == normalizar("guitar dell ́arte")
    assert normalizar("mr. tabs") == "mrtabs"
    assert normalizar("sky guitar") != normalizar("shin izumi")


def test_rotulo_de_instante() -> None:
    """O nome do PNG usa o instante sem casa decimal quando ele é inteiro."""
    assert rotulo_instante(3.0) == "3"
    assert rotulo_instante(8.0) == "8"
    assert rotulo_instante(15.5) == "15.5"


def test_uniformidade_separa_texto_de_madeira() -> None:
    """A madeira é menos lisa que a imagem com texto, como no detector de painel."""
    assert uniformidade(_com_texto()) > uniformidade(_madeira())
