"""Testes unitários do P2 (um braço só) e do P3 (consenso por vídeo) da rodada 1028."""

from __future__ import annotations

import numpy as np

import tab.maos_braco_localizador as loc
from tab.maos_braco_consenso import consenso, deslocamento, mesma_tomada
from tab.maos_braco_regra import eixo_do_braco, s_do_traste

CORDA1 = [[100.0, 500.0], [1500.0, 300.0]]
CORDA6 = [[100.0, 600.0], [1500.0, 400.0]]


def _mapas_com_componentes(
    blocos: list[tuple[int, int, float]],
) -> np.ndarray:
    """Mapas (5, 384, 640) com um bloco de presença por ``(y, x, valor)``.

    Args:
        blocos: ``(y, x, soma)`` de cada componente (um quadrado de 10 px).

    Returns:
        Mapas com a presença no canal 4 e o valor no canal 0.
    """
    mapas = np.zeros((5, 384, 640), dtype=np.float32)
    for y, x, soma in blocos:
        mapas[4, y : y + 10, x : x + 10] = 0.9
        mapas[0, y : y + 10, x : x + 10] = soma / 100.0
    return mapas


def _decodificador_falso(mapas, enquadre):
    """Decodificador de teste: acha se há presença, com soma no canal 0.

    Args:
        mapas: mapas (possivelmente zerados fora do componente).
        enquadre: não usado.

    Returns:
        Dicionário no formato da decodificação conjunta.
    """
    if float(mapas[4].max()) < 0.3:
        return {"achou": False, "motivo": "sem presença", "presenca": 0.0}
    ys, xs = np.nonzero(mapas[4] > 0.5)
    return {
        "achou": True,
        "motivo": None,
        "presenca": float(mapas[4].max()),
        "pontos": np.array([[xs.min(), ys.min()]]),
        "marcas": None,
        "soma": float(mapas[0].sum()),
        "origem_y": int(ys.min()),
    }


def test_p2_componente_de_maior_soma_vence(monkeypatch):
    """Com diferença maior que 5 %, ganha o de maior soma, mesmo estando embaixo."""
    monkeypatch.setattr(loc, "decodificar_quadro_conjunto", _decodificador_falso)
    mapas = _mapas_com_componentes([(50, 100, 10.0), (300, 200, 20.0)])
    dec = loc.decodificar_quadro_um_braco(mapas, None)
    assert dec["achou"]
    assert dec["origem_y"] == 300


def test_p2_empate_menor_que_5_por_cento_ganha_o_de_cima(monkeypatch):
    """Com diferença menor que 5 %, o componente de cima ganha."""
    monkeypatch.setattr(loc, "decodificar_quadro_conjunto", _decodificador_falso)
    mapas = _mapas_com_componentes([(50, 100, 19.5), (300, 200, 20.0)])
    dec = loc.decodificar_quadro_um_braco(mapas, None)
    assert dec["origem_y"] == 50


def test_p2_um_componente_nao_muda_nada(monkeypatch):
    """Com um componente só, o resultado é o da decodificação conjunta sem mudança."""
    monkeypatch.setattr(loc, "decodificar_quadro_conjunto", _decodificador_falso)
    mapas = _mapas_com_componentes([(50, 100, 10.0)])
    esperado = _decodificador_falso(mapas, None)
    dec = loc.decodificar_quadro_um_braco(mapas, None)
    assert dec["soma"] == esperado["soma"]
    assert dec["origem_y"] == esperado["origem_y"]
    assert "componentes" not in dec


def _quadro_com_curva(numeracao_deslocada: int, id_quadro: str, video: str) -> dict:
    """Quadro com trastes 1..8 numa curva conhecida, rotulados com um deslocamento.

    Args:
        numeracao_deslocada: soma aplicada aos números que o quadro declara.
        id_quadro: id do quadro.
        video: nome do vídeo.

    Returns:
        Quadro no formato de ``consenso``.
    """
    origem, u = eixo_do_braco(CORDA1, CORDA6)
    trastes = []
    for n in range(1, 9):
        t = 1000.0 * s_do_traste(n)
        ponto = origem + u * t
        trastes.append(
            {"numero": n + numeracao_deslocada, "ponto": [float(v) for v in ponto]}
        )
    nut = [float(v) for v in origem]
    return {
        "id": id_quadro,
        "arquivo": video,
        "achou": True,
        "sinalizado": False,
        "nut": nut,
        "corda1": CORDA1,
        "corda6": CORDA6,
        "trastes": trastes,
    }


def test_p3_mesma_tomada_e_mesmo_video():
    """Dois quadros do mesmo vídeo e cordas iguais são da mesma tomada."""
    a = _quadro_com_curva(0, "a", "v1")
    b = _quadro_com_curva(0, "b", "v1")
    c = _quadro_com_curva(0, "c", "v2")
    assert mesma_tomada(a, b)
    assert not mesma_tomada(a, c)


def test_p3_deslocamento_k1_sinaliza_e_k0_nao():
    """Numeração deslocada de 1 em relação à referência dá S4; a igual não."""
    referencia = _quadro_com_curva(0, "r", "v1")
    deslocado = _quadro_com_curva(-1, "d", "v1")
    igual = _quadro_com_curva(0, "i", "v1")
    assert (
        deslocamento(deslocado, referencia) == 1
        or deslocamento(deslocado, referencia) == -1
    )
    assert deslocamento(igual, referencia) == 0
    saida = consenso([referencia, deslocado])
    assert saida["d"]["S4"] is True
    # Com só dois quadros não sinalizados não há maioria: cada um é a referência do outro.
    assert saida["r"]["S4"] is True
