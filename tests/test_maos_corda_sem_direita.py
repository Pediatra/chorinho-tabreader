"""Corda sem a mão direita (M8): polifonia, custo, Viterbi, D3 sem vazar e inversa."""

from __future__ import annotations

import numpy as np
import pytest

from tab.maos_braco_geometria import ajustar, prever
from tab.maos_corda_sem_direita import (
    Ataque,
    Nota,
    Pesos,
    agrupar_ataques,
    casa_mais_baixa,
    combinacoes_do_ataque,
    custo_combinacao,
    decodificar,
    inverter_casa,
    janelas_de_vizinhos,
)


def _ataque(*notas: Nota) -> Ataque:
    """Um ataque com as notas dadas (todas no mesmo instante)."""
    return Ataque(t=notas[0].t, notas=tuple(notas))


def test_polifonia_duas_notas_iguais_nao_caem_na_mesma_corda() -> None:
    """Duas notas de altura 64 no mesmo ataque nunca usam a mesma corda."""
    ataque = _ataque(Nota(0, 1.0, 1, 0), Nota(1, 1.0, 2, 5))
    combos, valida = combinacoes_do_ataque(ataque)
    assert valida
    assert combos
    for combo in combos:
        cordas = [corda for corda, _ in combo]
        assert len(set(cordas)) == len(cordas)
    assert len(combos) == 20  # 5 candidatos por nota, cordas distintas: 5 * 4


def test_ataque_inconsistente_e_contado_a_parte() -> None:
    """Sete notas de altura 64 não cabem em seis cordas: não há combinação válida."""
    ataque = _ataque(*(Nota(i, 1.0, (i % 6) + 1, 0) for i in range(7)))
    _, valida = combinacoes_do_ataque(ataque)
    assert not valida


def test_corda_solta_custa_zero_com_a_mao_longe() -> None:
    """Corda solta tem custo zero, mesmo com a janela da mão bem longe dela."""
    longe = [(10.0, 12.0)]
    assert custo_combinacao(((1, 0),), longe, Pesos()) == 0.0
    assert custo_combinacao(((1, 0), (2, 0)), longe * 2, Pesos()) == 0.0


def test_corda_presa_paga_casa_e_distancia_a_janela() -> None:
    """Nota presa paga α·casa mais β·distância à janela; dentro da janela, só α·casa."""
    pesos = Pesos(alpha=1.0, beta=3.0, gamma=5.0, delta=0.5)
    fora = custo_combinacao(((3, 9),), [(0.0, 2.0)], pesos)
    assert fora == pytest.approx(9.0 + 3.0 * 7.0)
    dentro = custo_combinacao(((3, 9),), [(8.0, 10.0)], pesos)
    assert dentro == pytest.approx(9.0)


def test_abertura_acima_de_quatro_casas_paga_gamma() -> None:
    """Presas com abertura de 5 casas pagam γ; com abertura de 4, não."""
    pesos = Pesos(alpha=0.0, beta=0.0, gamma=5.0, delta=0.0)
    sem_janela = [None, None]
    assert custo_combinacao(((1, 2), (2, 7)), sem_janela, pesos) == 5.0
    assert custo_combinacao(((1, 2), (2, 6)), sem_janela, pesos) == 0.0


def test_viterbi_prefere_continuidade_e_carrega_a_posicao_pelo_solto() -> None:
    """O Viterbi troca a casa barata do primeiro ataque pela continuidade com o terceiro.

    Ataque 1: A (casa 3, custo 3) ou B (casa 8, custo 8). Ataque 2: só cordas soltas, que
    não mudam a posição. Ataque 3: só H (casa 9, custo 9). Com δ=0 a melhor é A (3+9=12);
    com δ=2 a melhor é B (8+2·1+9=19 contra 3+2·6+9=24), porque a posição vem do primeiro
    ataque pelo solto.
    """
    primeiro = [((1, 3),), ((2, 8),)]
    solto = [((1, 0),)]
    terceiro = [((3, 9),)]
    sem_janela = [[None], [None], [None]]
    combos = [primeiro, solto, terceiro]
    janelas = sem_janela
    barato = decodificar(
        combos, janelas, Pesos(alpha=1.0, beta=0.0, gamma=0.0, delta=0.0)
    )
    assert barato[0] == ((1, 3),)
    continuo = decodificar(
        combos, janelas, Pesos(alpha=1.0, beta=0.0, gamma=0.0, delta=2.0)
    )
    assert continuo[0] == ((2, 8),)
    assert continuo[2] == ((3, 9),)


def test_casa_mais_baixa_escolhe_a_menor_casa() -> None:
    """D0: a altura 64 vai para a corda 1 solta, a casa mais baixa."""
    ataque = _ataque(Nota(0, 1.0, 2, 5))
    assert casa_mais_baixa(ataque) == ((1, 0),)


def test_d3_nao_usa_a_propria_nota_nem_o_proprio_ataque() -> None:
    """A janela D3 vem só dos vizinhos de outros ataques, presos, a até 1 s."""
    notas = [
        Nota(0, 1.0, 2, 5),  # ataque A, presa
        Nota(1, 1.0, 3, 6),  # ataque A, presa (fica de fora para a nota 0)
        Nota(2, 1.5, 1, 10),  # ataque B, presa: único vizinho de A
        Nota(3, 1.2, 1, 0),  # solta: não entra na mediana
        Nota(4, 30.0, 1, 4),  # isolada: sem vizinhos
    ]
    ataques = agrupar_ataques(notas)
    janelas = janelas_de_vizinhos(ataques)
    assert janelas[0] == (8.0, 12.0)
    assert janelas[1] == (8.0, 12.0)
    assert janelas[4] is None


def test_d3_nao_depende_da_casa_da_propria_nota() -> None:
    """Trocar a casa da nota avaliada não muda a janela dela."""
    base = [Nota(0, 1.0, 2, 5), Nota(1, 1.5, 1, 10)]
    trocada = [Nota(0, 1.0, 2, 19), Nota(1, 1.5, 1, 10)]
    assert janelas_de_vizinhos(agrupar_ataques(base))[0] == (8.0, 12.0)
    assert janelas_de_vizinhos(agrupar_ataques(trocada))[0] == (8.0, 12.0)


def test_inversa_do_modelo_projetivo_recupera_a_casa() -> None:
    """Inverter ``prever`` (modelo projetivo) devolve a casa de origem."""
    pontos = [(0, 0.0), (5, 210.0), (12, 470.0), (19, 720.0)]
    params = ajustar(pontos, "proj")
    for casa in (0, 3, 7, 12, 19):
        t = prever(params, "proj", casa)
        assert inverter_casa(np.asarray(params), t) == pytest.approx(casa, abs=1e-6)
