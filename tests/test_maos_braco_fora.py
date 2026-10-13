"""Funções puras do cálculo do braço fora do MVP (estabilidade, quadro, contagem)."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_braco_fora import achar_quadro, contar_notas, estabilidade

H_BASE = np.array([[1100.0, 40.0, 250.0], [15.0, 880.0, 180.0], [2e-4, 1e-5, 1.0]])


def test_estabilidade_de_homografias_iguais_e_zero() -> None:
    """Três conjuntos com a mesma H dão diferença zero entre todos os pares."""
    estab = estabilidade([H_BASE, H_BASE.copy(), H_BASE.copy()])
    assert [p["par"] for p in estab["entre_conjuntos"]] == ["0-1", "0-2", "1-2"]
    assert all(p["mediana_px"] < 1e-9 for p in estab["entre_conjuntos"])
    assert estab["resumo"]["mediana_px_media"] < 1e-9
    assert estab["resumo"]["mediana_px_amplitude"] < 1e-9


def test_estabilidade_mede_o_deslocamento_de_um_conjunto() -> None:
    """Um conjunto deslocado em x aparece como diferença nos pares que o incluem."""
    desloc = H_BASE.copy()
    desloc[0, 2] += 3.0
    estab = estabilidade([H_BASE, H_BASE.copy(), desloc])
    por_par = {p["par"]: p["mediana_px"] for p in estab["entre_conjuntos"]}
    assert por_par["0-1"] < 1e-9
    assert por_par["0-2"] > 1.0
    assert por_par["1-2"] > 1.0


def test_achar_quadro_devolve_a_entrada_e_falha_sem_ela() -> None:
    """O quadro pedido é achado pelo id; id ausente levanta ValueError."""
    indice = {"quadros": [{"id": "q02", "t": 1.0}, {"id": "q16", "t": 284.87}]}
    assert achar_quadro(indice, "q16")["t"] == pytest.approx(284.87)
    with pytest.raises(ValueError, match="q99"):
        achar_quadro(indice, "q99")


def test_contar_notas_conta_pisadas_instantes_e_mao_esquerda() -> None:
    """Só notas com casa > 0 entram; instantes com mão esquerda são os com pontas."""
    produto = [
        {"t_ini": 1.0, "casa": 3},
        {"t_ini": 1.0, "casa": 0},
        {"t_ini": 2.0, "casa": 5},
        {"t_ini": 2.0, "casa": 4},
        {"t_ini": 3.0, "casa": 0},
    ]
    pontas = [
        {"t_ini": 1.0, "maos": [{"lado": "esquerda"}]},
        {"t_ini": 2.0, "maos": [{"lado": "direita"}]},
    ]
    contagem = contar_notas(produto, pontas)
    assert contagem["notas_pisadas"] == 3
    assert contagem["instantes_pisados"] == 2
    assert contagem["instantes_com_mao_esquerda"] == 1
    assert contagem["instantes_pontas"] == 2
