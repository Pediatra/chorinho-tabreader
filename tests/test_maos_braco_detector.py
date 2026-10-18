"""Detector do braço (``tab.maos_braco_detector``): alvo, pós-processamento e rede.

Sem GPU e sem acervo: os mapas são desenhados em memória, e a rede é a de produção com
pesos aleatórios, só para conferir formas.
"""

from __future__ import annotations

import random

import numpy as np
import pytest
import torch

from tab import maos_braco_detector as det
from tab.maos_braco_faixa import aplicar_matriz, eixo_da_faixa, matriz_da_faixa
from tab.maos_braco_regra import s_do_traste
from tab.maos_braco_tempo import Marcas

#: Nut e cordas do braço sintético (px, na faixa de 1024 x 192).
NUT_X = 46.0
CORDA1 = [[NUT_X, 64.0], [1000.0, 64.0]]
CORDA6 = [[NUT_X, 128.0], [1000.0, 128.0]]
#: Escala das casas no braço sintético: t(n) = NUT_X + ESCALA * s(n).
ESCALA = 1200.0


def _rotulo_sintetico(maior: int = 9) -> dict:
    """Rótulo na faixa de um braço sintético com trastes 1 a ``maior``.

    Args:
        maior: último traste marcado.

    Returns:
        Dicionário no formato de ``rotulo_na_faixa``.
    """
    trastes = [[0, NUT_X, 96.0]]
    for n in range(1, maior + 1):
        trastes.append([n, NUT_X + ESCALA * s_do_traste(n), 96.0])
    return {
        "corda1": CORDA1,
        "corda6": CORDA6,
        "trastes": trastes,
        "trastes_previstos": None,
    }


def _mapas_oraculo(rotulo: dict) -> np.ndarray:
    """Probabilidades perfeitas, como as da V1: sigmoide alta na crista.

    Args:
        rotulo: rótulo na faixa.

    Returns:
        Array float32 ``(3, 192, 1024)``.
    """
    g = det.mapas_alvo(rotulo)
    return (1.0 / (1.0 + np.exp(-(det.LOGIT_CRISTA * g + det.LOGIT_FUNDO)))).astype(
        np.float32
    )


def test_mapas_alvo_tem_crista_nas_cordas_e_nos_trastes() -> None:
    """A crista vale 1 sobre a corda e sobre o traste, e cai longe deles."""
    alvo = det.mapas_alvo(_rotulo_sintetico())
    assert alvo.shape == (4, 192, 1024)
    assert alvo[0, 64, 500] == pytest.approx(1.0)
    assert alvo[1, 128, 500] == pytest.approx(1.0)
    assert alvo[0, 10, 500] < 1e-6
    x_traste = round(NUT_X + ESCALA * s_do_traste(3))
    assert alvo[2, 96, x_traste] == pytest.approx(1.0, abs=0.02)
    assert alvo[2, 96, x_traste + 30] < 0.01
    # Emenda 2: o nut tem canal próprio, e o canal de trastes não tem o nut.
    assert alvo[3, 96, round(NUT_X)] == pytest.approx(1.0, abs=0.02)
    assert alvo[2, 96, round(NUT_X)] < 1e-3


def test_mapas_alvo_sem_nut_levanta_erro() -> None:
    """Sem o nut (número 0) não há alvo."""
    rotulo = _rotulo_sintetico()
    rotulo["trastes"] = rotulo["trastes"][1:]
    with pytest.raises(ValueError):
        det.mapas_alvo(rotulo)


def test_espelhar_segue_os_pixels_e_nao_troca_canais() -> None:
    """Na imagem espelhada, a crista da corda 1 vai para a linha 191 - 64."""
    alvo = det.mapas_alvo(_rotulo_sintetico())
    faixa = np.zeros((192, 1024, 3), dtype=np.uint8)
    faixa_e, alvo_e = det.espelhar(faixa, alvo)
    assert faixa_e.shape == faixa.shape
    assert np.argmax(alvo_e[0, :, 500]) == 191 - 64
    assert np.argmax(alvo_e[1, :, 500]) == 191 - 128
    assert np.array_equal(alvo_e[2], alvo[2][::-1])


def test_fator_lr_aquecimento_e_cosseno() -> None:
    """Aquecimento linear até 200 passos, depois cosseno até perto de zero."""
    assert det.fator_lr(0, 3000) == pytest.approx(1 / 200)
    assert det.fator_lr(199, 3000) == pytest.approx(1.0)
    assert det.fator_lr(200, 3000) == pytest.approx(1.0)
    assert det.fator_lr(2999, 3000) < 1e-4


def test_decodificar_oraculo_recupera_nut_e_trastes() -> None:
    """Mapas perfeitos voltam com o nut e os trastes 1 a 9 no lugar certo (1 px)."""
    rotulo = _rotulo_sintetico(9)
    dec = det.decodificar(_mapas_oraculo(rotulo))
    assert dec["achou"] is True
    assert dec["nut"][0] == pytest.approx(NUT_X, abs=1.0)
    for n in range(1, 10):
        esperado = NUT_X + ESCALA * s_do_traste(n)
        assert dec["trastes"][n][0] == pytest.approx(esperado, abs=1.0)
    assert max(dec["trastes"]) == 9


def test_decodificar_sem_braco_devolve_nao_achou() -> None:
    """Mapa vazio não tem reta de corda, e a resposta é "não achou"."""
    dec = det.decodificar(np.zeros((3, 192, 1024), dtype=np.float32))
    assert dec["achou"] is False
    assert "motivo" in dec


def test_no_quadro_inverte_a_matriz_da_faixa() -> None:
    """Pontos levados à faixa e de volta ao quadro caem onde estavam."""
    marcas = Marcas(
        nut=np.array([300.0, 500.0]),
        trastes={
            1: np.array([340.0, 502.0]),
            2: np.array([378.0, 503.0]),
            3: np.array([412.0, 505.0]),
        },
        corda1=np.array([[300.0, 470.0], [900.0, 460.0]]),
        corda6=np.array([[300.0, 530.0], [900.0, 540.0]]),
    )
    matriz = matriz_da_faixa(eixo_da_faixa(marcas))
    dec = {
        "achou": True,
        "nut": aplicar_matriz(matriz, marcas.nut).tolist(),
        "trastes": {
            n: aplicar_matriz(matriz, p).tolist() for n, p in marcas.trastes.items()
        },
        "corda1": aplicar_matriz(matriz, marcas.corda1).tolist(),
        "corda6": aplicar_matriz(matriz, marcas.corda6).tolist(),
    }
    volta = det._no_quadro(dec, matriz)
    assert np.allclose(volta.nut, marcas.nut, atol=1e-6)
    assert np.allclose(volta.trastes[2], marcas.trastes[2], atol=1e-6)
    assert np.allclose(volta.corda6, marcas.corda6, atol=1e-6)


def test_unet_devolve_tres_canais_na_resolucao_da_entrada() -> None:
    """A rede (pesos aleatórios, sem download) mantém a resolução de entrada."""
    modelo = det.UNetBraco(pesos_imagenet=False)
    saida = modelo(torch.zeros(1, 3, 64, 128))
    assert tuple(saida.shape) == (1, det.CANAIS_ALVO, 64, 128)


def test_aumentar_mantem_formas() -> None:
    """Os aumentos devolvem a faixa e os mapas com as formas do treino."""
    rng = random.Random(7)
    faixa = np.random.default_rng(0).integers(0, 255, (192, 1024, 3), dtype=np.uint8)
    alvo = det.mapas_alvo(_rotulo_sintetico())
    faixa_a, alvo_a = det.aumentar(faixa, alvo, rng)
    assert faixa_a.shape == (192, 1024, 3)
    assert alvo_a.shape == (det.CANAIS_ALVO, 192, 1024)
    assert faixa_a.min() >= 0.0 and faixa_a.max() <= 1.0


def test_salto_pula_traste_escondido() -> None:
    """Um traste escondido (sem pico) vira um salto: o número seguinte é pulado."""
    espacos = [
        81.0,
        69.0,
        66.0,
        62.0,
        60.0,
    ]  # nut->1, 1->2, ... (com o traste 3 faltando)
    x_nut = 46.0
    posicoes = [x_nut]
    for e in espacos:
        posicoes.append(posicoes[-1] + e)
    picos = [round(x) for x in posicoes[1:]]
    picos_sem_3 = [p for i, p in enumerate(picos) if i != 2]  # tira o 3º traste
    numerados = det._numerar_por_ordem(picos_sem_3, x_nut)
    assert [n for n, _ in numerados] == [1, 2, 4, 5]


def test_pool_r_da_dobra_deixa_o_canal_k_de_fora(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Na dobra k, nenhum R do canal k entra no treino (não só o G)."""
    monkeypatch.setattr(det, "canais_g", lambda: ["a", "b", "c"])
    pool = [
        {"canal": c, "arquivo": f"{c}{i}.mp4", "caminho": "", "registro": {}}
        for c in ("a", "b", "c")
        for i in range(6)
    ]
    for dobra, canal_fora in enumerate(("a", "b", "c")):
        treino = det.pool_r_da_dobra(pool, dobra, 1.0)
        assert treino
        assert all(e["canal"] != canal_fora for e in treino)


def test_videos_da_dobra_sao_prefixos_aninhados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """25 % está dentro de 50 %, que está dentro de 100 % (mesmo sorteio)."""
    monkeypatch.setattr(det, "canais_g", lambda: ["a", "b"])
    pool = [
        {"canal": "b", "arquivo": f"v{i:02d}.mp4", "caminho": "", "registro": {}}
        for i in range(20)
    ]
    v25 = det.videos_da_dobra(pool, 0, 0.25)
    v50 = det.videos_da_dobra(pool, 0, 0.5)
    v100 = det.videos_da_dobra(pool, 0, 1.0)
    assert len(v25) == 5
    assert len(v50) == 10
    assert v25 <= v50 <= v100
    assert v100 == {f"v{i:02d}.mp4" for i in range(20)}


def test_sequencia_mistura_s_e_r_em_cada_passo() -> None:
    """Em A3, cada passo tem metade de S e metade de R, nessa ordem."""
    pool_s = [(f"s{i}.jpg", {}) for i in range(5)]
    pool_r = [
        {"caminho": f"r{i}.jpg", "registro": {}, "canal": "a", "arquivo": "v"}
        for i in range(5)
    ]
    passos = 4
    sequencia = det._sequencia(pool_s, pool_r, passos, (8, 8), "teste")
    assert len(sequencia) == passos * det.LOTE
    for passo in range(passos):
        bloco = sequencia[passo * det.LOTE : (passo + 1) * det.LOTE]
        assert all(item[0].startswith("s") for item in bloco[:8])
        assert all(item[0].startswith("r") for item in bloco[8:])


def test_sequencia_recusa_pool_vazio() -> None:
    """Pedir R sem nenhum quadro R é erro, não sequência vazia."""
    with pytest.raises(ValueError):
        det._sequencia([("s.jpg", {})], [], 2, (0, 16), "teste")


def test_ransac_acha_a_reta_com_outliers() -> None:
    """A reta do RANSAC ignora pontos fora da faixa de 2 px."""
    xs = np.arange(200, dtype=float)
    ys = 0.1 * xs + 20.0
    ys[::7] += 30.0
    mascara = det._ransac_reta(xs, ys)
    assert mascara is not None
    assert mascara[1] and not mascara[0]
    assert int(mascara.sum()) >= 150
