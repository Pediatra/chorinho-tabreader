"""Testes da medição das variantes da regra da mão direita, com gabarito sintético."""

from __future__ import annotations

from tab.maos_regra_direita_medir import (
    VARIANTE_ATUAL,
    avaliar_variante,
    grade_variantes,
    validar_deixando_video_de_fora,
)


def _d(corda: int, t: float, dono: str) -> dict:
    """Entrada ``dedos`` do gabarito: corda, casa fixa, tempo e dono."""
    return {"corda": corda, "casa": 0, "t_ini": t, "palpite": "", "dono": dono}


def _gabarito_sintetico() -> list[dict]:
    """Dois compassos em dois vídeos. Um acerto em tudo no 1, um erro e uma ligada no 2."""
    return [
        {
            "video": "video A",
            "confirmado": True,
            # regra: 3@0 -> i, 3@0.5 -> m: os dois donos batem
            "dedos": [_d(3, 0.0, "i"), _d(3, 0.5, "m")],
        },
        {
            "video": "video B",
            "confirmado": True,
            # regra: 1@0 -> a (dono m: erro); 6@0.5 é ligada (dono l): fora da conta
            "dedos": [_d(1, 0.0, "m"), _d(6, 0.5, "l")],
        },
    ]


def test_grade_tem_32_variantes_com_a_atual():
    grade = grade_variantes()
    assert len(grade) == 32
    assert VARIANTE_ATUAL in grade


def test_avaliar_conta_so_notas_que_nao_sao_ligadas():
    resultado = avaliar_variante(_gabarito_sintetico(), VARIANTE_ATUAL)
    assert resultado["acertos"] == 2
    assert resultado["total"] == 3
    assert resultado["ligadas"] == 1
    assert resultado["por_video"] == {
        "video A": {"acertos": 2, "total": 2},
        "video B": {"acertos": 0, "total": 1},
    }
    assert resultado["matriz"]["m"]["a"] == 1
    assert resultado["matriz"]["i"]["i"] == 1


def test_validacao_deixando_um_video_de_fora_soma_fora_da_amostra():
    resultados = [
        avaliar_variante(_gabarito_sintetico(), v) for v in grade_variantes()[:2]
    ]
    validacao = validar_deixando_video_de_fora(resultados)
    # as duas variantes têm o mesmo resultado aqui: cada vídeo é medido uma vez
    assert validacao["total"] == 3
    assert validacao["acertos"] == 2
