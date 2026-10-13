"""Medição contra o gabarito do dono com qualquer quadro e qualquer número de trastes."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tab.maos_calibrar_por_notas import aplicar_homografia, s_traste, v_corda
from tab.maos_medicoes_braco import (
    gabarito_dono,
    gabarito_dono_q02,
    medir_contra_dono,
)

#: Homografia sintética (plano do braço -> pixels), com denominador positivo no braço.
H_SINTETICA = np.array([[1100.0, 40.0, 250.0], [15.0, 880.0, 180.0], [2e-4, 1e-5, 1.0]])


def _dono_sintetico(H: np.ndarray, n_trastes: int) -> dict[str, np.ndarray]:
    """Pontos do dono gerados pela própria H: nada deve ficar longe das retas.

    Args:
        H: homografia que gera os pontos.
        n_trastes: quantos trastes marcar (do traste 1 para cima).

    Returns:
        ``corda1``, ``corda6``, ``nut`` e ``trastes`` no formato de
        :func:`tab.maos_medicoes_braco.gabarito_dono`.
    """

    def ponto(u: float, v: float) -> np.ndarray:
        return aplicar_homografia(H, np.array([(u, v)]))[0]

    return {
        "corda1": np.array([ponto(0.1, v_corda(1)), ponto(0.3, v_corda(1))]),
        "corda6": np.array([ponto(0.1, v_corda(6)), ponto(0.3, v_corda(6))]),
        "nut": ponto(0.0, 0.5),
        "trastes": np.array([ponto(s_traste(n), 0.5) for n in range(1, n_trastes + 1)]),
    }


def test_medicao_sintetica_com_quinze_trastes_da_erro_zero() -> None:
    """Com a H que gerou os pontos, o erro é ~0 também no traste 15."""
    dono = _dono_sintetico(H_SINTETICA, 15)
    medida = medir_contra_dono(H_SINTETICA, dono)

    assert len(medida["trastes"]["casamentos"]) == 15
    assert medida["trastes"]["n_com_traste_previsto"] == 15
    assert medida["trastes"]["casamentos"][-1]["traste"] == 15
    assert medida["trastes"]["casamentos"][-1]["px"] < 1e-6
    assert medida["trastes"]["fracao_mediana_dos_casados"] < 1e-6
    assert medida["nut"]["px"] < 1e-6
    assert medida["cordas"]["corda1"]["px_media"] < 1e-6
    assert medida["cordas"]["corda6"]["px_media"] < 1e-6


def test_medicao_sintetica_com_h_errada_mede_o_erro() -> None:
    """Uma H deslocada em 5 px dá erro perto de 5 px nos pontos do dono."""
    dono = _dono_sintetico(H_SINTETICA, 15)
    H_errada = H_SINTETICA.copy()
    H_errada[0, 2] += 5.0
    medida = medir_contra_dono(H_errada, dono)
    assert 1.0 < medida["trastes"]["px_mediana_dos_casados"] < 10.0


def test_gabarito_dono_le_quadro_com_quinze_trastes(tmp_path: Path) -> None:
    """Qualquer quadro do braço é lido, com o número de trastes que ele tem."""
    caminho = tmp_path / "braco.json"
    quadro = {
        "braco": "sim",
        "corda1": [[10.0, 20.0], [30.0, 40.0]],
        "corda6": [[11.0, 21.0], [31.0, 41.0]],
        "nut": [5.0, 6.0],
        "trastes": [[float(k), 1.0] for k in range(15)],
    }
    caminho.write_text(json.dumps({"quadros": {"q16": quadro}}), encoding="utf-8")
    dono = gabarito_dono(caminho, "q16")
    assert dono["trastes"].shape == (15, 2)
    assert dono["corda1"].shape == (2, 2)


def test_gabarito_dono_q02_e_o_mesmo_que_o_quadro_q02(tmp_path: Path) -> None:
    """O atalho q02 devolve o mesmo que :func:`gabarito_dono` no quadro q02."""
    caminho = tmp_path / "braco.json"
    quadro = {
        "braco": "sim",
        "corda1": [[1.0, 2.0], [3.0, 4.0]],
        "corda6": [[5.0, 6.0], [7.0, 8.0]],
        "nut": [9.0, 10.0],
        "trastes": [[float(k), 2.0] for k in range(14)],
    }
    caminho.write_text(json.dumps({"quadros": {"q02": quadro}}), encoding="utf-8")
    atalho = gabarito_dono_q02(caminho)
    geral = gabarito_dono(caminho, "q02")
    assert atalho.keys() == geral.keys()
    for chave in geral:
        assert np.array_equal(atalho[chave], geral[chave])


def test_gabarito_dono_sem_braco_levanta_erro(tmp_path: Path) -> None:
    """Quadro sem o braço marcado não é medido."""
    caminho = tmp_path / "braco.json"
    caminho.write_text(
        json.dumps({"quadros": {"q09": {"braco": None, "trastes": []}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="q09"):
        gabarito_dono(caminho, "q09")
