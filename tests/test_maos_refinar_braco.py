"""Testes do refino da homografia pelo erro de reprojeção (M3c). Sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_calibrar_por_notas import (
    Conjunto,
    aplicar_homografia,
    coordenadas_do_braco,
    grade_do_braco,
    s_traste,
)
from tab.maos_refinar_braco import (
    ajustar_pontos,
    consenso,
    custo_robusto,
    peso_tukey,
    refinar_reprojecao,
    rho_tukey,
)

#: Homografia de teste, a mesma escala dos testes da calibração.
H_VERDADEIRA = np.array(
    [
        [820.0, 35.0, 1200.0],
        [-18.0, 760.0, 540.0],
        [4.5e-4, -2.0e-4, 1.0],
    ]
)


def _conjunto(
    n: int, frac_errada: float, semente: int, ruido_px: float = 0.3
) -> Conjunto:
    """Notas com a ponta verdadeira (com ruído) e, às vezes, uma ponta errada.

    Args:
        n: número de notas.
        frac_errada: fração das notas cuja segunda candidata é uma ponta errada.
        semente: semente do gerador.
        ruido_px: desvio do ruído nas pontas verdadeiras.

    Returns:
        Um :class:`Conjunto` com duas candidatas por nota.
    """
    rng = np.random.default_rng(semente)
    cordas = rng.integers(1, 7, size=n)
    casas = rng.integers(1, 13, size=n)
    uv = np.array(
        [
            coordenadas_do_braco(int(c), int(k))
            for c, k in zip(cordas, casas, strict=True)
        ]
    )
    verdade = aplicar_homografia(H_VERDADEIRA, uv)
    verdade = verdade + rng.normal(0.0, ruido_px, size=verdade.shape)
    falsa = rng.uniform([0.0, 0.0], [1900.0, 1000.0], size=(n, 2))
    usar_falsa = rng.random(n) < frac_errada
    cand = np.zeros((n, 2, 2))
    cand[:, 0] = verdade
    cand[:, 1] = np.where(usar_falsa[:, None], falsa, verdade + 0.5)
    return Conjunto(
        indices=np.arange(n),
        corda=cordas,
        casa=casas,
        t=np.zeros(n),
        uv=uv,
        cand=cand,
        mascara=np.ones((n, 2), dtype=bool),
    )


def _erro_entre_h(h1: np.ndarray, h2: np.ndarray) -> float:
    """Maior diferença, em px, entre duas homografias sobre a grade do braço.

    Args:
        h1: primeira homografia.
        h2: segunda homografia.

    Returns:
        Distância máxima entre as duas projeções.
    """
    a = grade_do_braco(h1)
    b = grade_do_braco(h2)
    return float(np.max(np.linalg.norm(a - b, axis=1)))


def _perturbar(H: np.ndarray, escala: float) -> np.ndarray:
    """Desloca levemente as entradas da H, sem sair de perto da verdadeira.

    Args:
        H: homografia verdadeira.
        escala: fração de cada entrada que é somada, em valor relativo.

    Returns:
        Homografia perturbada, com ``H[2, 2] = 1``.
    """
    rng = np.random.default_rng(5)
    H0 = H / H[2, 2]
    ruido = rng.normal(0.0, 1.0, size=H0.shape) * np.abs(H0) * escala
    ruido[2, 2] = 0.0
    return H0 + ruido


def test_tukey_zero_no_centro_e_constante_fora() -> None:
    """Resíduo zero custa zero e peso 1; fora de ``c`` o custo é ``c**2/6`` e o peso 0."""
    c = 0.5
    assert rho_tukey(np.array([0.0]), c)[0] == 0.0
    assert peso_tukey(np.array([0.0]), c)[0] == 1.0
    assert rho_tukey(np.array([c, 2.0, np.inf]), c) == pytest.approx(c**2 / 6)
    assert np.all(peso_tukey(np.array([c, 2.0, np.inf]), c) == 0.0)


def test_refino_reduz_erro_e_ignora_pontas_erradas() -> None:
    """Com 40 % de pontas erradas, o refino a partir de uma H perturbada volta perto da verdadeira."""
    c = _conjunto(n=150, frac_errada=0.4, semente=11)
    H0 = _perturbar(H_VERDADEIRA, escala=0.002)
    erro_inicial = _erro_entre_h(H0, H_VERDADEIRA)
    H = refinar_reprojecao(H0, c)
    assert _erro_entre_h(H, H_VERDADEIRA) < erro_inicial
    assert _erro_entre_h(H, H_VERDADEIRA) < 1.5


def test_custo_menor_para_a_homografia_verdadeira() -> None:
    """O custo robusto da H verdadeira é menor que o de uma H perturbada."""
    c = _conjunto(n=120, frac_errada=0.0, semente=3)
    verdadeira = custo_robusto(H_VERDADEIRA, c)
    perturbada = custo_robusto(_perturbar(H_VERDADEIRA, escala=0.01), c)
    assert verdadeira < perturbada


def test_custo_infinito_para_h_que_cruza_o_plano() -> None:
    """Uma H cujo denominador troca de sinal entre as notas não vale (custo inf)."""
    c = _conjunto(n=40, frac_errada=0.0, semente=4)
    H_ruim = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, -0.2]])
    assert custo_robusto(H_ruim, c) == np.inf


def test_ajustar_pontos_recupera_h_exata() -> None:
    """Pares exatos (sem ruído) levam de volta à H verdadeira, partindo de uma perturbada."""
    rng = np.random.default_rng(2)
    origem = rng.uniform(0.0, 0.5, size=(40, 2))
    origem[:, 1] = rng.uniform(0.0, 1.0, size=40)
    destino = aplicar_homografia(H_VERDADEIRA, origem)
    H = ajustar_pontos(_perturbar(H_VERDADEIRA, escala=0.003), origem, destino)
    assert _erro_entre_h(H, H_VERDADEIRA) < 1e-3


def test_ajustar_pontos_exige_quatro_pares() -> None:
    """Menos de 4 pares não define a homografia: a função recusa."""
    pontos = np.zeros((3, 2))
    with pytest.raises(ValueError):
        ajustar_pontos(H_VERDADEIRA, pontos, pontos)


def test_consenso_e_deterministico_pela_semente() -> None:
    """A mesma lista de sementes dá exatamente a mesma homografia escolhida."""
    c = _conjunto(n=80, frac_errada=0.5, semente=8)
    a = consenso(c, (1, 2, 3), iteracoes=600)
    b = consenso(c, (1, 2, 3), iteracoes=600)
    assert np.array_equal(a["H"], b["H"])
    assert a["semente"] == b["semente"]
    assert len(a["candidatos"]) == 3


def test_consenso_escolhe_o_menor_custo() -> None:
    """A H escolhida é a de menor custo robusto entre as candidatas."""
    c = _conjunto(n=80, frac_errada=0.5, semente=9)
    r = consenso(c, (4, 5), iteracoes=600)
    custos = [cand["custo"] for cand in r["candidatos"]]
    assert r["custo"] == min(custos)


def test_s_traste_coerente_com_a_grade() -> None:
    """A grade do braço tem 13 trastes por 6 cordas, e o traste 12 é o meio do braço."""
    assert s_traste(12) == pytest.approx(0.5)
    grade = grade_do_braco(H_VERDADEIRA)
    assert grade.shape == (13 * 6, 2)
