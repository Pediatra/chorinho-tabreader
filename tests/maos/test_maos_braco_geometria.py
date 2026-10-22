"""Geometria do braço (M3b): modelo físico, eixo, previsão e resíduo do piso."""

from __future__ import annotations

import pytest

from tab.maos.braco.geometria import (
    ajustar,
    ajustar_ancoras,
    eixo_do_braco,
    larguras_locais,
    montar_geometria,
    prever,
    prever_quadro,
    residuos_piso,
    s_do_traste,
)

L = 1000.0


def _afim(n: int) -> float:
    """Posição física do traste ``n`` numa escala de 1000 px (sem perspectiva)."""
    return L * s_do_traste(n)


def _projetivo(n: int) -> float:
    """Posição com perspectiva: Möbius com denominador ``0,3 s + 1``."""
    s = s_do_traste(n)
    return 1000.0 * s / (0.3 * s + 1.0)


def _registro(numeros: list[int], t_de_n, com_nut: bool = True) -> dict:
    """Quadro sintético: eixo horizontal (y = 300), nut em x = 1800, corpo à esquerda.

    Os trastes são clicados na ordem inversa, para o numerador não depender da ordem.
    Sem nut, o traste ``1`` (ou o primeiro da lista) vira a referência.
    """
    xs = {n: 1800.0 - t_de_n(n) for n in numeros}
    trastes = [[xs[n], 300.0] for n in numeros][::-1]
    registro = {
        "braco": "sim",
        "corda1": [[700.0, 290.0], [1800.0, 290.0]],
        "corda6": [[700.0, 310.0], [1800.0, 310.0]],
        "nut": [1800.0, 300.0] if com_nut else "fora",
        "trastes": trastes,
        "traste_referencia": None,
    }
    if not com_nut:
        primeiro = min(numeros)
        registro["traste_referencia"] = {
            "ponto": [xs[primeiro], 300.0],
            "numero": primeiro,
        }
    return registro


def test_s_do_traste_referencias() -> None:
    assert s_do_traste(0) == 0.0
    assert s_do_traste(12) == pytest.approx(0.5)
    assert s_do_traste(1) == pytest.approx(1 - 2 ** (-1 / 12))


def test_eixo_e_bissetriz_das_cordas() -> None:
    origem, u = eixo_do_braco([[0.0, 0.0], [10.0, 0.0]], [[0.0, 4.0], [10.0, 4.0]])
    assert u[0] == pytest.approx(1.0)
    assert u[1] == pytest.approx(0.0)
    assert origem == pytest.approx([5.0, 2.0])


def test_afim_exato_com_duas_ancoras() -> None:
    params = ajustar([(0, 0.0), (5, _afim(5))], "afim")
    assert prever(params, "afim", 12) == pytest.approx(_afim(12))
    assert prever(params, "afim", 19) == pytest.approx(_afim(19))


def test_projetivo_recupera_perspectiva_e_afim_erra() -> None:
    ancoras = [(0, 0.0), (5, _projetivo(5)), (12, _projetivo(12))]
    params = ajustar(ancoras, "proj")
    assert prever(params, "proj", 3) == pytest.approx(_projetivo(3), abs=1e-6)
    assert prever(params, "proj", 19) == pytest.approx(_projetivo(19), abs=1e-6)
    afim = ajustar([(0, 0.0), (5, _projetivo(5))], "afim")
    assert abs(prever(afim, "afim", 19) - _projetivo(19)) > 10.0


def test_montar_com_nut_numera_e_orienta_para_o_corpo() -> None:
    registro = _registro(list(range(1, 11)), _afim)
    geo = montar_geometria("q00", registro)
    assert geo is not None
    assert geo.com_nut
    assert geo.ancora_n == 0
    assert [tr.numero for tr in geo.trastes] == list(range(1, 11))
    # t cresce para o corpo (x menor): traste n a L*s_n a partir do nut.
    for tr in geo.trastes:
        assert tr.t == pytest.approx(_afim(tr.numero), abs=1e-6)


def test_montar_sem_nut_usa_referencia_como_ancora() -> None:
    registro = _registro(list(range(1, 11)), _afim, com_nut=False)
    geo = montar_geometria("q09", registro)
    assert geo is not None
    assert not geo.com_nut
    assert geo.ancora_n == 1
    t_ref = next(tr.t for tr in geo.trastes if tr.numero == 1)
    assert t_ref == pytest.approx(0.0, abs=1e-6)
    # Mesmo modelo, agora com a origem na referência: diferenças iguais ao afim.
    t5 = next(tr.t for tr in geo.trastes if tr.numero == 5)
    assert t5 == pytest.approx(_afim(5) - _afim(1), abs=1e-6)


def test_quadro_sem_braco_fica_de_fora() -> None:
    registro = _registro(list(range(1, 11)), _afim)
    registro["braco"] = "nao"
    assert montar_geometria("q00", registro) is None


def test_prever_quadro_pula_quando_falta_ancora() -> None:
    geo = montar_geometria("q00", _registro(list(range(1, 11)), _afim))
    assert geo is not None
    larguras = larguras_locais(geo)
    assert prever_quadro(geo, larguras, "proj", (12,)) is None
    previsoes = prever_quadro(geo, larguras, "afim", (5,))
    assert previsoes is not None
    assert {p.numero for p in previsoes} == set(range(1, 11)) - {5}
    assert all(p.erro_px < 1e-6 for p in previsoes)


def test_residuo_do_piso_zero_com_numeracao_certa() -> None:
    geo = montar_geometria("q00", _registro(list(range(1, 13)), _projetivo))
    assert geo is not None
    residuos = residuos_piso(geo, larguras_locais(geo), "proj")
    assert max(r.erro_px for r in residuos) < 1e-6


def test_residuo_do_piso_acusa_traste_pulado() -> None:
    # Clicou-se sem o traste 4: os de 5 em diante ganham o número de 4 em diante.
    numeros = [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12]
    geo = montar_geometria("q00", _registro(numeros, _projetivo))
    assert geo is not None
    residuos = residuos_piso(geo, larguras_locais(geo), "proj")
    assert max(r.erro_fracao for r in residuos) > 0.15


def test_largura_local_e_distancia_ao_vizinho() -> None:
    geo = montar_geometria("q00", _registro(list(range(1, 6)), _afim))
    assert geo is not None
    larguras = larguras_locais(geo)
    assert larguras[1] == pytest.approx(_afim(2) - _afim(1), abs=1e-6)
    # No último traste, a largura é a distância ao anterior.
    assert larguras[5] == pytest.approx(_afim(5) - _afim(4), abs=1e-6)


def test_ajustar_ancoras_devolve_none_sem_traste() -> None:
    geo = montar_geometria("q00", _registro(list(range(1, 8)), _afim))
    assert geo is not None
    assert ajustar_ancoras(geo, "afim", (12,)) is None
    assert ajustar_ancoras(geo, "afim", (3, 7)) is not None


def test_modelo_desconhecido_levanta() -> None:
    with pytest.raises(ValueError, match="modelo desconhecido"):
        ajustar([(0, 0.0), (5, 1.0)], "quadratico")
