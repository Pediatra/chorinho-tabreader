"""Um espaço de coordenadas só: o do quadro (T1.3 do plano).

A ROI do painel é recortada em x (``painel.refinar``); o x das notas fica no espaço da
ROI e o do marcador no do QUADRO. ``Candidato.x0`` é a ponte: ``x_quadro = x0 + x_roi``.
"""

from __future__ import annotations

from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from tab.comum.caminhos import acervo
from tab.tablatura.leitura.inventario import ler_quadro
from tab.tablatura.leitura.painel import Candidato, escolher, refinar
from tab.tablatura.leitura.tabseg import segmentar
from tab.tablatura.produto import estado
from tab.tablatura.produto.colunas import Coluna

LARGURA, ALTURA = 1280, 360
X_INI, X_FIM = 300, 900
ALGARISMOS = [(str(d), 340 + 70 * k) for k, d in enumerate([3, 0, 5, 2, 4, 1, 3, 0])]


def _quadro_com_painel() -> np.ndarray:
    """Fundo liso 1280x360 com uma tablatura só em x entre 300 e 900."""
    img = np.full((ALTURA, LARGURA, 3), 245, np.uint8)
    for i in range(6):
        y = 100 + i * 20
        cv2.line(img, (X_INI, y), (X_FIM, y), (30, 30, 30), 2)
    for k, (txt, x) in enumerate(ALGARISMOS):
        y = 100 + (k % 4 + 1) * 20 + 7
        cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    return img


def test_escolher_grava_x0_e_x_quadro_cai_no_algarismo() -> None:
    """Depois de ``escolher``, ``x0 + x_roi`` de um glifo cai sobre o algarismo."""
    cand = escolher(_quadro_com_painel())
    assert cand is not None
    assert cand.x0 > 0
    assert cand.x0 <= X_INI
    alvos = [
        (x, x + cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0][0])
        for t, x in ALGARISMOS
    ]
    for x_ini, x_fim in alvos:
        assert any(
            x_ini - 2 <= cand.x0 + (tk.x0 + tk.x1) / 2 <= x_fim + 2
            for tk in cand.grade.glifos
        )
    # o x_roi sozinho NÃO cai no algarismo: é exatamente o bug que o x0 conserta
    x_roi = [(tk.x0 + tk.x1) / 2 for tk in cand.grade.glifos]
    assert min(x_roi) < ALGARISMOS[0][1] - 20


def test_refinar_soma_ao_x0_anterior() -> None:
    """``refinar`` acumula o deslocamento: ``x0 = c.x0 + x0_do_recorte``."""
    quadro = _quadro_com_painel()
    bruto = escolher(quadro)
    assert bruto is not None
    # um candidato "largo" (ROI cheia, x0 = 0) refinado tem de dar o mesmo x0
    roi = quadro[0:ALTURA, :]
    largo = Candidato(
        nome="meio",
        y0=0,
        y1=ALTURA,
        roi=roi,
        grade=segmentar(roi),
        uniformidade=1.0,
        score=(1.0, 0),
    )
    assert largo.x0 == 0
    assert refinar(largo).x0 == bruto.x0
    # e se o candidato já veio deslocado, o deslocamento soma
    deslocado = Candidato(**{**largo.__dict__, "x0": 10})
    assert refinar(deslocado).x0 == bruto.x0 + 10


def test_estado_por_cor_usa_o_deslocamento(monkeypatch: pytest.MonkeyPatch) -> None:
    """O recorte do token aceso soma ``cand.x0``; o x comparado é o do quadro."""
    quadro = np.full((200, 600, 3), 200, np.uint8)
    x0, y0 = 280, 50
    quadro[y0 + 10 : y0 + 30, x0 + 10 : x0 + 30] = (0, 0, 255)  # glifo vermelho
    tokens = [
        SimpleNamespace(x0=10, x1=30, y0=10, y1=30),
        SimpleNamespace(x0=100, x1=120, y0=10, y1=30),
        SimpleNamespace(x0=150, x1=170, y0=10, y1=30),
    ]
    cand = SimpleNamespace(y0=y0, x0=x0, grade=SimpleNamespace(glifos=tokens))
    monkeypatch.setattr(estado, "ler_quadro", lambda video, frac: (quadro, "x"))
    # x_quadro das colunas: o vermelho está em x_quadro = 280 + 20 = 300 -> coluna 1
    colunas = [Coluna(100.0, [0]), Coluna(300.0, [1]), Coluna(440.0, [2])]
    r = estado.estado_por_cor("v.mp4", cand, colunas, 2, 0.5, 0.6)
    assert r["com_destaque"] > 0
    assert list(r["onsets"]) == [1]


@pytest.mark.integration
def test_retrato_brasileiro_x0_70() -> None:
    """No `retrato brasileiro` (quadro em 0,5) o recorte em x começa em 70 px."""
    caminho = acervo() / "sky guitar" / "retrato brasileiro - tab & lesson.mp4"
    if not caminho.exists():
        pytest.skip(f"acervo ausente: {caminho}")
    quadro, _ = ler_quadro(str(caminho), 0.5)
    assert quadro is not None
    cand = escolher(quadro)
    assert cand is not None
    assert cand.x0 == 70
