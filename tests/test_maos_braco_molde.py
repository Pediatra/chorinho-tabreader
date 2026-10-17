"""Violão molde (medida (a) da 1009): testes sintéticos, sem acervo e sem gabarito real."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_braco_geometria import s_do_traste
from tab.maos_braco_molde import ajustar_elipse, cobertura_do_arco, medir_quadro

L = 1000.0
DIMENSOES = (1920, 1080)
#: Perspectiva suave, dentro do que a câmera faz no acervo.
HOMOGRAFIA = np.array([[1.0, 0.04, 30.0], [0.01, 0.97, 25.0], [2e-5, 1e-5, 1.0]])


def _no_quadro(x: float, y: float, h: np.ndarray | None) -> list[float]:
    """Leva um ponto sintético pela homografia (ou o deixa como está).

    Args:
        x: coordenada x sem perspectiva.
        y: coordenada y sem perspectiva.
        h: homografia 3x3, ou ``None``.

    Returns:
        ``[x, y]`` no quadro.
    """
    if h is None:
        return [float(x), float(y)]
    v = h @ np.array([x, y, 1.0])
    return [float(v[0] / v[2]), float(v[1] / v[2])]


def _registro(saddle1: tuple[float, float] = (800.0, 290.0), h=None) -> dict:
    """Braço sintético, com o nut em x = 1800 e o corpo à esquerda.

    Cordas 1 e 6 em y = 290 e y = 310 (vão = 20 / 5 = 4 px). Trastes a ``L * s(n)``
    do nut, e saddles em x = 800 (escala de 1000 px). Os trastes são clicados na ordem
    inversa, para a numeração não depender da ordem do clique.

    Args:
        saddle1: ponto do saddle 1, sem perspectiva.
        h: homografia aplicada a todos os pontos, ou ``None``.

    Returns:
        Resposta de um quadro do gabarito, com todas as partes preenchidas.
    """

    def p(x: float, y: float) -> list[float]:
        return _no_quadro(x, y, h)

    # Números consecutivos: numerar_trastes numera pela ordem, sem lacunas.
    numeros = list(range(1, 20))
    trastes = [p(1800.0 - L * s_do_traste(n), 300.0) for n in numeros][::-1]
    return {
        "braco": "sim",
        "corda1": [p(700.0, 290.0), p(1800.0, 290.0)],
        "corda6": [p(700.0, 310.0), p(1800.0, 310.0)],
        "nut": p(1800.0, 300.0),
        "trastes": trastes,
        "traste_referencia": None,
        "saddle1": p(*saddle1),
        "saddle6": p(800.0, 310.0),
        "cavalete": "oculto",
        "boca": "oculto",
        "paineis": "nao",
    }


def _medir(registro: dict) -> dict:
    """Entrada de ``medir_quadro`` para o quadro sintético.

    Args:
        registro: resposta do quadro sintético.

    Returns:
        A entrada completa do quadro.
    """
    return medir_quadro("q99", registro, "sintetico", DIMENSOES)


def test_s_saddle_e_1_sem_perspectiva() -> None:
    entrada = _medir(_registro())
    assert entrada["dentro"]
    medidas = entrada["medidas"]
    assert medidas["saddle"]["s_saddle"] == pytest.approx(1.0, abs=1e-6)
    assert medidas["retidao"]["saddle1"]["vaos"] == pytest.approx(0.0, abs=1e-6)
    assert medidas["retidao"]["saddle6"]["vaos"] == pytest.approx(0.0, abs=1e-6)
    assert medidas["ajuste_proj"]["resid_max_px"] == pytest.approx(0.0, abs=1e-4)


def test_s_saddle_e_1_com_perspectiva() -> None:
    entrada = _medir(_registro(h=HOMOGRAFIA))
    assert entrada["medidas"]["saddle"]["s_saddle"] == pytest.approx(1.0, abs=1e-3)


def test_saddle_deslocado_dois_vaos_tem_retidao_dois() -> None:
    # O vão no saddle é |saddle1 - saddle6| / 5. Com o saddle 1 afastado d da corda 1,
    # esse vão é (20 + d) / 5, e a retidão é d / vão. Dá 2,0 quando d = 40 / 3.
    d = 40.0 / 3.0
    entrada = _medir(_registro(saddle1=(800.0, 290.0 - d)))
    retidao = entrada["medidas"]["retidao"]
    assert retidao["saddle1"]["vaos"] == pytest.approx(2.0, abs=0.01)
    assert retidao["saddle6"]["vaos"] == pytest.approx(0.0, abs=1e-6)


def test_elipse_de_um_circulo_recupera_o_centro() -> None:
    angulos = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False)
    pontos = np.column_stack(
        [500.0 + 50.0 * np.cos(angulos), 400.0 + 50.0 * np.sin(angulos)]
    )
    centro, eixos, _ = ajustar_elipse(pontos)
    assert centro == pytest.approx((500.0, 400.0), abs=1e-2)
    assert eixos == pytest.approx((100.0, 100.0), abs=1e-1)
    assert cobertura_do_arco(pontos, centro) > 180.0


def test_boca_com_cinco_pontos_num_arco_de_120_graus_e_parcial() -> None:
    angulos = np.radians(np.linspace(-60.0, 60.0, 5))
    registro = _registro()
    registro["boca"] = [
        [1000.0 + 60.0 * np.cos(a), 300.0 + 60.0 * np.sin(a)] for a in angulos
    ]
    boca = _medir(registro)["medidas"]["boca"]
    assert boca["cobertura_graus"] == pytest.approx(120.0, abs=0.5)
    assert boca["arco_parcial"] is True


def test_boca_com_oito_pontos_no_circulo_inteiro_nao_e_parcial() -> None:
    angulos = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False)
    registro = _registro()
    registro["boca"] = [
        [1000.0 + 60.0 * np.cos(a), 300.0 + 60.0 * np.sin(a)] for a in angulos
    ]
    boca = _medir(registro)["medidas"]["boca"]
    assert boca["arco_parcial"] is False


def test_cavalete_sobre_o_saddle_cai_em_s_1() -> None:
    registro = _registro()
    registro["cavalete"] = [[800.0, 200.0], [800.0, 400.0]]
    cavalete = _medir(registro)["medidas"]["cavalete"]
    assert cavalete["s_cavalete"] == pytest.approx(1.0, abs=1e-6)


def test_paineis_em_caixas_ficam_de_fora_com_motivo() -> None:
    registro = _registro()
    registro["paineis"] = [
        [[0.0, 0.0], [10.0, 10.0]],
        [[20.0, 20.0], [30.0, 30.0]],
    ]
    entrada = _medir(registro)
    assert entrada["dentro"] is False
    assert entrada["medidas"] is None
    assert "painéis" in entrada["motivo_fora"]


def test_pestana_fora_do_quadro_fica_de_fora_com_motivo() -> None:
    registro = _registro()
    registro["nut"] = "fora"
    registro["traste_referencia"] = {"ponto": registro["trastes"][0], "numero": 1}
    entrada = _medir(registro)
    assert entrada["dentro"] is False
    assert "pestana" in entrada["motivo_fora"]
