"""Testes dos alvos de técnica do R4a (rodada 0202)."""

from tab.tablatura.ataque.r4 import (
    LIMIARES,
    LIMIARES_MEDIDOS,
    alvos_da_tela,
    ataque_com_regra,
    com_limiar,
    escolher_limiar,
    escolher_nao_sei,
    modelo_da_dobra,
    tecnica_alvo,
)


def _gab(ataque: str, motivo: str, casa: int = 5, esq: int | None = 3) -> dict:
    return {
        "ataque": ataque,
        "motivo": motivo,
        "casa": casa,
        "casa_vizinha_esq": esq,
        "corda": 1,
        "x_centro_quadro": 100.0,
    }


def test_tecnica_alvo_por_motivo() -> None:
    assert tecnica_alvo(_gab("nao", "h")) == "h"
    assert tecnica_alvo(_gab("nao", "p")) == "p"
    assert tecnica_alvo(_gab("nao", "prolongamento")) == "lig"
    assert tecnica_alvo(_gab("nao", "mordente")) == "orn"
    assert tecnica_alvo(_gab("sim", "sustentada")) is None
    assert tecnica_alvo(_gab("sim", "mordente_simbolo")) is None


def test_slide_sobe_ou_desce_pela_vizinha_da_esquerda() -> None:
    assert tecnica_alvo(_gab("nao", "slide_ligado", casa=5, esq=3)) == "/"
    assert tecnica_alvo(_gab("nao", "slide_ligado", casa=3, esq=5)) == "\\"
    assert tecnica_alvo(_gab("nao", "slide_ligado", casa=3, esq=None)) == "/"


def test_alvos_casam_pela_corda_e_pelo_x_no_quadro() -> None:
    cache = [
        {"corda": 1, "casa": 5, "x_roi": 90.0},
        {"corda": 2, "casa": 5, "x_roi": 90.0},
    ]
    alvos = alvos_da_tela(cache, 10.0, 20.0, [_gab("nao", "h")])
    assert alvos == [(True, "h"), (False, None)]
    assert alvos_da_tela(cache, 10.0, 20.0, []) == [(False, None), (False, None)]


def test_nome_dos_modelos() -> None:
    assert modelo_da_dobra("ger", 4, 1).parent.name == "detector_tab_v3ft_d4_ger"
    assert modelo_da_dobra("ger", 4, 2).parent.name == "detector_tab_v3ft_d4_ger_s2"
    assert modelo_da_dobra("ger", 0, 2).parent.name == "detector_tab_final_s2_ger"
    assert modelo_da_dobra("atq", 0, 1).parent.name == "detector_tab_final_atq_s1"
    assert modelo_da_dobra("atq", 3, 3).parent.name == "detector_tab_v3ft_d3_atq_s3"


def test_slide_sem_origem_e_atacado() -> None:
    def n(corda: int, x: float, tec: list[str]) -> dict:
        return {"corda": corda, "x_centro_quadro": x, "tecnica": tec}

    pred = [n(1, 100, []), n(1, 130, ["/"]), n(2, 130, ["/"]), n(3, 200, ["h"])]
    assert ataque_com_regra(pred, 1, 20.0) == "nao"  # origem a 1,5 passo
    assert ataque_com_regra(pred, 2, 20.0) == "sim"  # sem origem na corda 2
    assert ataque_com_regra(pred, 3, 20.0) == "nao"  # h não é slide
    assert ataque_com_regra(pred, 0, 20.0) == "sim"


def test_limiar_refaz_so_a_tecnica() -> None:
    p = [0.0] * 10
    p[0] = 0.3  # h
    pred = [{"corda": 1, "x_centro_quadro": 10.0, "tecnica": [], "tecnica_p": p}]
    assert com_limiar(pred, 0.25)[0]["tecnica"] == ["h"]
    assert com_limiar(pred, 0.5)[0]["tecnica"] == []
    assert pred[0]["tecnica"] == []


def test_escolher_o_menor_limiar_que_cabe_no_teto() -> None:
    def medida(alarmes: dict[float, int]) -> dict:
        return {
            "ouros": {
                "por_limiar": {
                    str(lim): {
                        "regra:sim|nao": alarmes.get(lim, 0),
                        "regra:sim|sim": 100 - alarmes.get(lim, 0),
                    }
                    for lim in LIMIARES
                }
            }
        }

    assert escolher_limiar([medida({0.1: 5, 0.15: 2, 0.2: 1})]) == 0.2


def test_nao_sei_escolhe_o_menor_limiar_com_cobertura_no_teto() -> None:
    def medida(sem_sim: dict[float, int]) -> dict:
        return {
            "ouros": {
                "por_limiar": {
                    str(lim): {
                        "regra:sim|nao": sem_sim.get(lim, 0),
                        "regra:sim|sim": 100 - sem_sim.get(lim, 0),
                    }
                    for lim in LIMIARES_MEDIDOS
                }
            }
        }

    assert escolher_nao_sei([medida({0.01: 20, 0.02: 9, 0.03: 5, 0.05: 3})]) == 0.03
    assert escolher_nao_sei([medida(dict.fromkeys(LIMIARES_MEDIDOS, 50))]) == 0.5
