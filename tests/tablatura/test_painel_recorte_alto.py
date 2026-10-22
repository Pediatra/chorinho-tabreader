"""O recorte alto do detector (rodada 0210): mais folga acima da corda 1 e abaixo da 6."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from tab.tablatura.ataque import r4 as ataque_r4
from tab.tablatura.leitura import detector_tab
from tab.tablatura.leitura.painel import FOLGA_DETECTOR_PASSOS, recorte_alto


def _quadro_e_candidato(y0: int = 100, altura: int = 70, x0: int = 30):
    """Quadro com valores distintos por linha e um candidato que é recorte cru dele."""
    quadro = (np.arange(300)[:, None] % 251 * np.ones((1, 200))).astype(np.uint8)
    roi = quadro[y0 : y0 + altura, x0 : x0 + 120]
    grade = SimpleNamespace(linhas_y=[10.0, 20.0, 30.0, 40.0, 50.0, 60.0], passo=10.0)
    return quadro, SimpleNamespace(y0=y0, x0=x0, roi=roi, grade=grade, passo=10.0)


def test_folga_igual_a_do_detector() -> None:
    """A folga do recorte é a que o detector lê."""
    assert FOLGA_DETECTOR_PASSOS == detector_tab.MARGEM_PASSOS


def test_recorte_cresce_na_vertical_e_desloca_as_linhas() -> None:
    """De 1 para 2,5 passos de cada lado; mesmas colunas; linhas no novo recorte."""
    quadro, c = _quadro_e_candidato()
    roi, linhas = recorte_alto(quadro, c)
    assert linhas[0] == pytest.approx(25.0)
    assert roi.shape[0] - linhas[-1] == pytest.approx(25.0)
    assert roi.shape[1] == c.roi.shape[1]
    assert np.array_equal(roi, quadro[85:185, 30:150])


def test_recorte_para_na_borda_do_quadro() -> None:
    """Perto do topo do quadro, cresce só até a borda."""
    quadro, c = _quadro_e_candidato(y0=5)
    roi, linhas = recorte_alto(quadro, c)
    assert linhas[0] == pytest.approx(15.0)
    assert np.array_equal(roi[: int(linhas[0])], quadro[0:15, 30:150])


def test_roi_que_nao_e_recorte_cru_fica_como_esta() -> None:
    """Via por máscara (roi transformado): devolve o roi e as linhas sem mexer."""
    quadro, c = _quadro_e_candidato()
    c.roi = 255 - c.roi
    roi, linhas = recorte_alto(quadro, c)
    assert roi is c.roi
    assert linhas == c.grade.linhas_y


def test_ler_tela_recusa_recorte_desconhecido() -> None:
    """ler_tela só aceita os recortes de RECORTES."""
    with pytest.raises(ValueError, match="recorte"):
        ataque_r4.ler_tela(None, None, 0.0, recorte="largo")
