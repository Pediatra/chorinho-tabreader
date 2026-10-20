"""Testes do rótulo de ataque com a faixa "não sei" (rodada 0205)."""

import pytest

from tab.ataque_rotulo import LIMIAR_NAO, LIMIAR_SIM, rotular
from tab.detector_tab import TECNICAS_MODELO
from tab.video import transcrever_video


def _nota(x: float, corda: int = 1, **probs: float) -> dict:
    p = [0.0] * len(TECNICAS_MODELO)
    for t, v in probs.items():
        p[TECNICAS_MODELO.index({"barra": "/", "contra": "\\"}.get(t, t))] = v
    return {"corda": corda, "x_centro_quadro": x, "tecnica_p": p}


def test_sem_sinal_e_sim_com_sinal_forte_e_nao() -> None:
    notas = [_nota(10.0), _nota(40.0, h=LIMIAR_NAO + 0.2)]
    assert rotular(notas, 20.0) == [("sim", "normal"), ("nao", "h")]


def test_sinal_fraco_e_nao_sei() -> None:
    notas = [_nota(10.0), _nota(40.0, p=(LIMIAR_SIM + LIMIAR_NAO) / 2)]
    assert rotular(notas, 20.0)[1] == ("nao_sei", "tinta_sem_explicacao")


def test_harmonico_nao_conta_como_tecnica_sem_ataque() -> None:
    assert rotular([_nota(10.0, harm=0.9)], 20.0) == [("sim", "normal")]


def test_slide_sem_origem_e_entrada_e_com_origem_e_ligado() -> None:
    sozinho = [_nota(100.0, barra=0.9)]
    assert rotular(sozinho, 20.0) == [("sim", "slide_entrada")]
    ligado = [_nota(70.0), _nota(100.0, barra=0.9)]
    assert rotular(ligado, 20.0)[1] == ("nao", "slide_ligado")
    outra_corda = [_nota(70.0, corda=2), _nota(100.0, barra=0.9)]
    assert rotular(outra_corda, 20.0)[1] == ("sim", "slide_entrada")


def test_motivo_e_a_tecnica_mais_forte() -> None:
    nota = _nota(40.0, h=0.3, orn=0.8)
    assert rotular([_nota(10.0), nota], 20.0)[1] == ("nao", "mordente")


def test_video_recusa_rotulo_com_pesos_nao_calibrados(tmp_path) -> None:
    with pytest.raises(ValueError, match="rotulo_ataque"):
        transcrever_video(
            "nao_existe.mp4",
            leitor_notas="rede",
            detector=tmp_path / "outro.pt",
            rotulo_ataque=True,
        )
