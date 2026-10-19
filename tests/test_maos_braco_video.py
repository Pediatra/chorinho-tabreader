"""Testes da rodada 1030 (vídeo inteiro e nut fora): sem GPU e sem acervo."""

from __future__ import annotations

import numpy as np

from tab.maos_braco_ciclo import aplicar_consenso
from tab.maos_braco_detector import CANAL_CORDA1, CANAL_CORDA6, CANAL_NUT
from tab.maos_braco_faixa import matriz_da_faixa
from tab.maos_braco_regra import s_do_traste
from tab.maos_braco_video import (
    _ajustar_b_livre,
    contar_transicoes,
    corrigir_pela_tomada,
    eixo_sem_nut,
    geometria_sem_nut,
    hipoteses,
    melhor_numeracao,
    nome_jsonl,
    numero_decidido,
    numero_do_primeiro,
    nut_ausente,
)

IDENTIDADE = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
LARGURA_FAIXA = 1024
ALTURA_FAIXA = 192


def _mapas(inicio: int, nut_valor: float, nut_x: int = 300) -> np.ndarray:
    """Mapas sintéticos da faixa: cordas horizontais em y=60 e y=120 a partir de ``inicio``.

    Args:
        inicio: primeira coluna em que as cordas aparecem.
        nut_valor: valor do canal do nut na coluna ``nut_x``.
        nut_x: coluna do nut.

    Returns:
        Array ``(4, 192, 1024)``.
    """
    mapas = np.zeros((4, ALTURA_FAIXA, LARGURA_FAIXA), dtype=np.float32)
    mapas[CANAL_CORDA1, 60, inicio:] = 0.9
    mapas[CANAL_CORDA6, 120, inicio:] = 0.9
    mapas[CANAL_NUT, 60:121, nut_x] = nut_valor
    return mapas


def test_nut_ausente_quando_a_corda_toca_a_borda():
    geo = geometria_sem_nut(_mapas(inicio=0, nut_valor=0.9))
    assert geo is not None
    assert nut_ausente(geo, IDENTIDADE, (LARGURA_FAIXA, ALTURA_FAIXA))


def test_nut_presente_quando_a_corda_comeca_longe_da_borda_e_o_canal_e_forte():
    geo = geometria_sem_nut(_mapas(inicio=300, nut_valor=0.9))
    assert geo is not None
    assert not nut_ausente(geo, IDENTIDADE, (LARGURA_FAIXA, ALTURA_FAIXA))


def test_nut_ausente_quando_o_canal_do_nut_e_fraco():
    geo = geometria_sem_nut(_mapas(inicio=300, nut_valor=0.1))
    assert geo is not None
    assert nut_ausente(geo, IDENTIDADE, (LARGURA_FAIXA, ALTURA_FAIXA))


def test_eixo_sem_nut_tem_a_origem_na_ponta_mais_perto_da_borda():
    corda1 = [[300.0, 300.0], [1100.0, 300.0]]
    corda6 = [[300.0, 320.0], [1100.0, 320.0]]
    origem, u, comprimento, largura = eixo_sem_nut(corda1, corda6, 1280, 720)
    assert np.allclose(origem, [1100.0, 310.0])
    assert np.allclose(u, [-1.0, 0.0])
    assert abs(comprimento - 800.0) < 1e-9
    assert abs(largura - 20.0) < 1e-9
    matriz = matriz_da_faixa((origem, u, comprimento, largura))
    assert matriz.shape == (2, 3)


def _picos_do_modelo(primeiro: int, quantos: int, a: float, b: float, c: float):
    """Posições ``t(n)`` do modelo projetivo com b livre, para ``quantos`` trastes.

    Args:
        primeiro: número do primeiro traste visível.
        quantos: quantos trastes.
        a: parâmetro a do modelo.
        b: parâmetro b (posição do nut).
        c: parâmetro c do modelo.

    Returns:
        Lista de posições em px, crescentes.
    """
    return [
        (a * s_do_traste(n) + b) / (c * s_do_traste(n) + 1.0)
        for n in range(primeiro, primeiro + quantos)
    ]


def test_ajuste_com_b_livre_acerta_com_a_numeracao_dada():
    picos = _picos_do_modelo(primeiro=3, quantos=10, a=1100.0, b=40.0, c=0.2)
    ajuste = _ajustar_b_livre(picos, [(3 + i, x) for i, x in enumerate(picos)])
    assert ajuste is not None
    assert ajuste["pares"][0][0] == 3
    assert ajuste["inliers"] == 10
    assert ajuste["residuo"] < 1e-6


def test_sem_nut_o_numero_do_primeiro_e_ambiguo_em_picos_exatos():
    # O modelo com b livre é invariante a deslocar o rótulo do primeiro traste: n=3 e n=4
    # ajustam os mesmos picos. O resíduo não escolhe, então o método recusa.
    picos = _picos_do_modelo(primeiro=3, quantos=10, a=1100.0, b=40.0, c=0.2)
    melhor = melhor_numeracao(picos, com_fim=False)
    assert melhor is not None
    assert {3, 4} <= set(melhor["empatados"])
    assert numero_decidido(melhor) is None
    assert numero_do_primeiro(melhor) is not None


def test_numero_decidido_so_quando_um_numero_vence_o_empate():
    assert numero_decidido({"empatados": [3]}) == 3
    assert numero_decidido({"empatados": [3, 4]}) is None
    assert numero_decidido(None) is None


def test_hipoteses_de_primeiro_traste_sem_fim_do_braco():
    picos = _picos_do_modelo(primeiro=3, quantos=10, a=1100.0, b=40.0, c=0.2)
    origens = [h["origem"] for h in hipoteses(picos, com_fim=False)]
    assert "primeiro=3" in origens
    assert all(o.startswith("primeiro=") for o in origens)
    com_fim = [h["origem"] for h in hipoteses(picos, com_fim=True)]
    assert any(o.startswith("fim=") for o in com_fim)


def test_poucos_picos_recusam():
    assert melhor_numeracao([100.0, 150.0], com_fim=True) is None


def _quadro(
    id_q: str,
    nut: list[float],
    deslocamento: int,
    arquivo: str = "video.mp4",
) -> dict:
    """Quadro previsto com cordas fixas e 5 trastes, deslocados em ``deslocamento``.

    Args:
        id_q: id do quadro.
        nut: ponto do nut.
        deslocamento: soma aos números dos trastes (o erro de numeração).
        arquivo: vídeo do quadro.

    Returns:
        Entrada no formato de ``previsto.json``.
    """
    trastes = [
        {"numero": n + deslocamento, "ponto": [100.0 + 60.0 * n, 100.0]}
        for n in range(1, 6)
    ]
    return {
        "id": id_q,
        "arquivo": arquivo,
        "achou": True,
        "sinalizado": False,
        "motivo": None,
        "S1": None,
        "S2": None,
        "S3": None,
        "nut": nut,
        "corda1": [[100.0, 80.0], [700.0, 80.0]],
        "corda6": [[100.0, 120.0], [700.0, 120.0]],
        "trastes": trastes,
    }


def test_consenso_denso_corrige_com_k_1_e_troca_o_nut_pela_referencia():
    # Duas referências concordantes (r1, r2) e um quadro com numeração deslocada (t).
    doc = {
        "ordem": ["r1", "r2", "t"],
        "quadros": {
            "r1": _quadro("r1", nut=[100.0, 100.0], deslocamento=0),
            "r2": _quadro("r2", nut=[100.0, 100.0], deslocamento=0),
            "t": _quadro("t", nut=[90.0, 100.0], deslocamento=-1),
        },
    }
    dimensoes = {"r1": (1280, 720), "r2": (1280, 720), "t": (1280, 720)}
    novo = aplicar_consenso(doc, dimensoes)["quadros"]
    assert novo["t"]["S4"]["k"] == 1
    assert novo["t"]["S4"]["S4"] is True
    assert novo["t"]["sinalizado"] is True
    corrigidos = corrigir_pela_tomada(novo)
    assert corrigidos["r1"] is None
    assert corrigidos["r2"] is None
    corrigido = corrigidos["t"]
    assert corrigido is not None
    assert [t["numero"] for t in corrigido["trastes"]] == [1, 2, 3, 4, 5]
    assert corrigido["nut"] == [100.0, 100.0]


def test_consenso_sem_deslocamento_nao_corrige():
    doc = {
        "ordem": ["r", "t"],
        "quadros": {
            "r": _quadro("r", nut=[100.0, 100.0], deslocamento=0),
            "t": _quadro("t", nut=[100.0, 100.0], deslocamento=0),
        },
    }
    novo = aplicar_consenso(doc, {"r": (1280, 720), "t": (1280, 720)})["quadros"]
    assert novo["t"]["S4"]["S4"] is False
    assert corrigir_pela_tomada(novo)["t"] is None


def test_contar_transicoes_e_passa_so_sem_perder_certo():
    antes = [{"id": "a", "correto": True}, {"id": "b", "correto": False}]
    depois = [{"id": "a", "correto": True}, {"id": "b", "correto": True}]
    assert contar_transicoes(antes, depois)["passa_para_ciclo"] is True
    perdeu = [{"id": "a", "correto": False}, {"id": "b", "correto": True}]
    assert contar_transicoes(antes, perdeu)["passa_para_ciclo"] is False


def test_nome_do_jsonl_tem_dois_digitos():
    assert nome_jsonl(3) == "video_03.jsonl"
    assert nome_jsonl(16) == "video_16.jsonl"
