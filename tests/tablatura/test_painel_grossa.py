"""Linha grossa (barra de borda) não é corda: o grupo que a tem sai da escolha.

Caso medido no Gymnopédie (tela 10, t=136,5 s): o grupo ``[899..1043]`` tem 6 cordas de
3 px, e o grupo ``[928..1072]`` tem 5 dessas cordas mais uma barra preta de 10 px. Os
dois são regulares e têm passo na faixa; o errado ganhava por uniformidade porque o
recorte dele inclui a barra. A imagem abaixo reproduz essa geometria, sem acervo.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.tablatura.leitura.painel import candidatos_quadro, linhas_grossas

CORDAS = [200, 229, 258, 287, 316, 345]
# 29 px abaixo da sexta corda: forma grupo regular com as cinco do meio
BARRA_Y = 374


def _quadro(com_barra: bool) -> np.ndarray:
    """Papel claro, 6 cordas finas, algarismos sobre as cordas e (opcional) barra grossa."""
    img = np.full((480, 1200, 3), 245, np.uint8)
    for y in CORDAS:
        cv2.line(img, (20, y), (1180, y), (30, 30, 30), 3)
    for j, x in enumerate(range(100, 1100, 90)):
        cv2.putText(
            img,
            str(j % 8),
            (x, CORDAS[j % 6] + 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (20, 20, 20),
            2,
        )
    if com_barra:
        # barra preta de borda: 10 px de altura, atravessa o quadro inteiro
        img[BARRA_Y - 5 : BARRA_Y + 5, :] = 15
    return img


def test_linha_de_barra_e_grossa_e_corda_nao_e() -> None:
    quadro = _quadro(com_barra=True)
    assert linhas_grossas(quadro, 0, 480, [*CORDAS[1:], BARRA_Y])
    assert not linhas_grossas(quadro, 0, 480, CORDAS)


def test_grupo_com_barra_nao_e_escolhido() -> None:
    quadro = _quadro(com_barra=True)
    achados = candidatos_quadro(quadro, min_glifos=1)
    grupos = [[c.y0 + y for y in c.grade.linhas_y] for c in achados]
    assert grupos, "nenhum candidato: o teste não mede nada"
    for linhas in grupos:
        assert not any(abs(y - BARRA_Y) <= 3 for y in linhas), linhas
    assert any(
        all(abs(a - b) <= 2 for a, b in zip(sorted(linhas), CORDAS, strict=True))
        for linhas in grupos
    ), grupos


def test_sem_barra_as_seis_cordas_continuam_valendo() -> None:
    quadro = _quadro(com_barra=False)
    achados = candidatos_quadro(quadro, min_glifos=1)
    grupos = [[c.y0 + y for y in c.grade.linhas_y] for c in achados]
    assert any(
        len(linhas) == 6
        and all(abs(a - b) <= 2 for a, b in zip(sorted(linhas), CORDAS, strict=True))
        for linhas in grupos
    ), grupos
