"""Regra das 12 notas (``tab.maos_braco_regra``): conta, recusas e recorte do quadro."""

from __future__ import annotations

import pytest

from tab import maos_braco_regra
from tab.maos_braco_geometria import ajustar, prever
from tab.maos_braco_regra import prever_trastes, s_do_traste

#: Braço horizontal: cordas 1 e 6 paralelas, eixo na reta y = 150, nut em x = 100.
CORDA1 = [[0.0, 100.0], [1000.0, 100.0]]
CORDA6 = [[0.0, 200.0], [1000.0, 200.0]]
NUT = [100.0, 150.0]
ORIGEM_X = 500.0
GRANDE = (2000, 400)

#: Modelo projetivo usado para gerar os cliques sintéticos (t a partir da origem).
A, B, C = 1200.0, -400.0, 0.3


def _t_do_modelo(n: int, c: float = C) -> float:
    """Posição ao longo do eixo do traste ``n`` segundo o modelo sintético.

    Args:
        n: número do traste.
        c: coeficiente do denominador (o padrão dá um braço bem comportado).

    Returns:
        ``t`` em px a partir da origem (``x = 500 + t``).
    """
    s = s_do_traste(n)
    return (A * s + B) / (c * s + 1.0)


def _ponto_do_traste(n: int, c: float = C) -> list[float]:
    """Clique sintético do traste ``n``: sobre o eixo (sem arredondar).

    Args:
        n: número do traste.
        c: coeficiente do denominador.

    Returns:
        ``[x, y]`` no eixo y = 150.
    """
    return [ORIGEM_X + _t_do_modelo(n, c), 150.0]


def _ancoras(*numeros: int) -> dict[int, list[float]]:
    """Dicionário de âncoras sintéticas para os números pedidos.

    Args:
        *numeros: números dos trastes âncora.

    Returns:
        ``{numero: ponto}``.
    """
    return {n: _ponto_do_traste(n) for n in numeros}


def test_s_do_traste_mede_a_escala() -> None:
    """Nut é 0; o traste 12 é a metade do comprimento."""
    assert s_do_traste(0) == 0.0
    assert s_do_traste(12) == pytest.approx(0.5)


def test_conta_bate_com_a_geometria() -> None:
    """Os trastes previstos saem iguais aos do ajuste de ``maos_braco_geometria``."""
    previsao = prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 12), GRANDE)
    ajuste = ajustar([(0, B), (5, _t_do_modelo(5)), (12, _t_do_modelo(12))], "proj")
    assert sorted(previsao) == list(range(1, 20))
    for n in range(1, 20):
        if n in (5, 12):
            continue
        x_esperado = ORIGEM_X + prever(ajuste, "proj", n)
        assert previsao[n][0] == pytest.approx(x_esperado, abs=0.06), n
        assert previsao[n][1] == pytest.approx(150.0, abs=0.06), n


def test_devolve_a_ancora_clicada_e_nao_a_prevista() -> None:
    """Nos números das âncoras o resultado é o ponto clicado, sem mexer."""
    ancoras = {5: [700.3, 150.0], 12: [1010.7, 150.0]}
    previsao = prever_trastes(NUT, CORDA1, CORDA6, ancoras, GRANDE)
    assert previsao[5] == [700.3, 150.0]
    assert previsao[12] == [1010.7, 150.0]


def test_pontos_previstos_ficam_em_1_casa_decimal() -> None:
    """Como os cliques: coordenadas arredondadas a 1 casa."""
    previsao = prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 12), GRANDE)
    for n, ponto in previsao.items():
        if n not in (5, 12):
            assert ponto == [round(ponto[0], 1), round(ponto[1], 1)]


def test_fica_de_fora_o_traste_que_sai_do_quadro() -> None:
    """Só entram os trastes com ponto dentro do quadro (0 <= x < largura)."""
    previsao = prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 12), (700, 400))
    assert sorted(previsao) == list(range(1, 13))
    assert all(0 <= p[0] < 700 for p in previsao.values())


def test_recusa_nut_ausente_ou_fora() -> None:
    """Sem pestana marcada, a regra não se aplica."""
    for nut in (None, "fora"):
        with pytest.raises(ValueError, match="pestana"):
            prever_trastes(nut, CORDA1, CORDA6, _ancoras(5, 12), GRANDE)


def test_recusa_cordas_incompletas() -> None:
    """Corda com menos de 2 pontos não define o eixo."""
    with pytest.raises(ValueError, match="corda 1"):
        prever_trastes(NUT, [[0.0, 100.0]], CORDA6, _ancoras(5, 12), GRANDE)
    with pytest.raises(ValueError, match="corda 6"):
        prever_trastes(NUT, CORDA1, None, _ancoras(5, 12), GRANDE)


def test_recusa_sem_exatamente_duas_ancoras() -> None:
    """A regra precisa de 2 âncoras, nem uma nem três."""
    with pytest.raises(ValueError, match="2 âncoras"):
        prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5), GRANDE)
    with pytest.raises(ValueError, match="2 âncoras"):
        prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 7, 12), GRANDE)


def test_recusa_ancoras_mal_espalhadas() -> None:
    """Maior número abaixo de 9, ou diferença abaixo de 5: âncoras próximas erram."""
    with pytest.raises(ValueError, match="mal espalhadas"):
        prever_trastes(NUT, CORDA1, CORDA6, _ancoras(3, 7), GRANDE)
    with pytest.raises(ValueError, match="mal espalhadas"):
        prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 9), GRANDE)


def test_recusa_ancora_fora_de_1_a_19() -> None:
    """Âncora além do último traste previsto não tem onde se apoiar."""
    with pytest.raises(ValueError, match=r"fora de 1\.\.19"):
        prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 20), GRANDE)


def test_recusa_curva_que_nao_cresce(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarda da sequência: posições que não crescem do nut para fora são recusadas.

    Com o denominador positivo a curva projetiva já é monótona, e a orientação pelas
    âncoras impede a queda; a guarda existe mesmo assim. Por isso o teste força as
    posições por ``monkeypatch``.
    """

    def _caindo(params: object, n_max: int) -> list[float]:
        return [-float(n) for n in range(n_max + 1)]

    monkeypatch.setattr(maos_braco_regra, "_posicoes_t", _caindo)
    with pytest.raises(ValueError, match="não cresce"):
        prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 12), GRANDE)


def test_recusa_polo_no_intervalo_dos_trastes() -> None:
    """Denominador c*s+1 que zera antes do traste 19: a conta não vale."""
    ancoras = {5: _ponto_do_traste(5, c=-30.0), 12: _ponto_do_traste(12, c=-30.0)}
    with pytest.raises(ValueError, match="polo"):
        prever_trastes(NUT, CORDA1, CORDA6, ancoras, GRANDE)


def test_eixo_nao_depende_da_ordem_das_cordas() -> None:
    """Trocar os pontos de uma corda não muda a previsão (o sentido é o das âncoras)."""
    direta = prever_trastes(NUT, CORDA1, CORDA6, _ancoras(5, 12), GRANDE)
    invertida = prever_trastes(
        NUT, [CORDA1[1], CORDA1[0]], [CORDA6[1], CORDA6[0]], _ancoras(5, 12), GRANDE
    )
    assert direta == invertida
