"""Testes dos alvos de técnica do R4a (rodada 0202)."""

from tab.ataque_r4 import alvos_da_tela, modelo_da_dobra, tecnica_alvo


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
