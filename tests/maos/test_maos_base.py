"""Testes da parte pura da base das mãos (rodada 1049, ``tab.maos.base``)."""

from __future__ import annotations

import math

import numpy as np

from tab.maos.base import (
    braco_do_previsto,
    caixa_em,
    distancia_na_celula,
    eventos,
    intervalos,
    janela,
    recortar_reta,
    resumo,
    som_por_coluna,
    trilhas,
    vazio,
)
from tab.maos.esquema import validar_json


def _produto() -> dict:
    """Produto mínimo: uma tela com duas exibições e três notas.

    Returns:
        ``chorinho/video@1`` reduzido.
    """
    return {
        "telas": [
            {
                "id": 1,
                "painel": [0, 0, 100, 50],
                "exibicoes": [{"t0": 10.0, "t1": 12.0}, {"t0": 12.5, "t1": 14.0}],
            }
        ],
        "notas": [
            {
                "tela": 1,
                "exibicao": 0,
                "coluna": 1,
                "passagem": 2,
                "corda": 3,
                "casa": 2,
                "t_ini": 10.5,
            },
            {
                "tela": 1,
                "exibicao": 0,
                "coluna": 1,
                "passagem": 1,
                "corda": 3,
                "casa": 2,
                "t_ini": 11.5,
            },
            {
                "tela": 1,
                "exibicao": 0,
                "coluna": 2,
                "passagem": 1,
                "corda": 1,
                "casa": 0,
                "t_ini": 11.0,
            },
        ],
    }


def test_intervalos_fundem_com_folga() -> None:
    """Exibições a menos de 2 s viram um intervalo, cortado na duração."""
    assert intervalos(_produto(), 14.5) == [(9.0, 14.5)]


def test_caixa_em_so_dentro_da_exibicao() -> None:
    """A caixa é o painel da tela exibida; fora das exibições, None."""
    assert caixa_em(_produto(), 11.0) == [0.0, 0.0, 100.0, 50.0]
    assert caixa_em(_produto(), 12.2) is None


def test_trilhas_quebram_depois_da_lacuna() -> None:
    """O mesmo lado seguido é uma trilha; depois de > 0,5 s sem a mão, outra."""
    pts = np.array([0.0, 0.1, 0.2, 0.9, 1.0])
    presente = np.array([[1, 0], [1, 1], [0, 1], [1, 1], [1, 0]], dtype=bool)
    saida = trilhas(presente, pts)
    assert saida[:, 0].tolist() == [0, 0, -1, 1, 1]
    assert saida[:, 1].tolist() == [-1, 2, 2, 3, -1]


def test_recortar_reta_mantem_a_reta_dentro() -> None:
    """A reta recortada fica no quadro e continua sobre a mesma reta."""
    reta = recortar_reta(np.array([-50.0, 10.0]), np.array([150.0, 10.0]), 100, 50)
    assert reta is not None
    assert reta[:, 1].tolist() == [10.0, 10.0]
    assert math.isclose(reta[:, 0].min(), 0.0, abs_tol=1e-9)
    assert math.isclose(reta[:, 0].max(), 99.0)
    assert recortar_reta(np.array([0.0, -5.0]), np.array([10.0, -5.0]), 100, 50) is None


def _braco() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Um braço horizontal: nut em x=0, casas de 100 px; corda 1 em y=0, 6 em y=50.

    Returns:
        ``(trastes, corda1, corda6)``.
    """
    trastes = np.full((25, 2), np.nan)
    for k in range(5):
        trastes[k] = [100.0 * k, 25.0]
    corda1 = np.array([[0.0, 0.0], [1000.0, 0.0]])
    corda6 = np.array([[0.0, 50.0], [1000.0, 50.0]])
    return trastes, corda1, corda6


def test_celula_ao_longo_e_entre_cordas() -> None:
    """Dentro da casa 2 (100–225 px) a distância é em vãos (10 px); fora, inf."""
    trastes, c1, c6 = _braco()
    assert math.isclose(
        distancia_na_celula(trastes, c1, c6, 3, 2, np.array([150.0, 20.0])), 0.0
    )
    assert math.isclose(
        distancia_na_celula(trastes, c1, c6, 3, 2, np.array([150.0, 30.0])), 1.0
    )
    assert math.isinf(
        distancia_na_celula(trastes, c1, c6, 3, 2, np.array([240.0, 20.0]))
    )
    assert math.isinf(distancia_na_celula(trastes, c1, c6, 3, 9, np.array([0, 0])))


def test_som_vai_para_a_passagem_mais_perto() -> None:
    """O ``t_audio`` vai para a passagem de ``t_ini`` mais perto, não para a ``1``."""
    audio = {
        "colunas": [
            {"tela": 1, "exibicao": 0, "coluna": 1, "t_audio": 10.6, "confianca": 0.9},
            {"tela": 1, "exibicao": 0, "coluna": 2, "t_audio": None, "confianca": None},
        ]
    }
    som = som_por_coluna(_produto()["notas"], audio)
    assert som == {(1, 0, 1, 2): (10.6, 0.9)}


def test_janela_em_volta_do_som() -> None:
    """A janela pega os quadros a ≤ 0,5 s de ``t_som``."""
    pts = np.arange(20) / 10
    assert janela(pts, 1.0) == (5, 16)
    assert janela(pts, None) is None


def _denso_com_braco(n: int = 30) -> dict[str, np.ndarray]:
    """Denso de 3 s a 10 qps, com a mão do braço na casa 2 da corda 3 e braço entregue.

    Args:
        n: quadros.

    Returns:
        As matrizes do denso.
    """
    arr = vazio(n)
    arr["pts"] = np.arange(n) * 0.1 + 9.5
    trastes, c1, c6 = _braco()
    mao = np.zeros((21, 3))
    mao[:, :2] = [150.0, 20.0]
    mao[:, 2] = 0.9
    for i in range(n):
        arr["maos"][i, 0] = mao
        arr["maos"][i, 1] = mao
        arr["maos_origem"][i] = [1, 1]
        arr["tab_caixa"][i] = [0, 0, 100, 50]
    arr["braco_trastes"][10] = trastes
    arr["braco_corda1"][10] = c1
    arr["braco_corda6"][10] = c6
    arr["braco_achou"][10] = True
    arr["braco_conf"][10] = 1.0
    arr["maos_trilha"] = trilhas(arr["maos_origem"] > 0, arr["pts"])
    return arr


def test_eventos_ouro_com_capo_e_recusado_sem_som() -> None:
    """Com som, braço, mãos e capo conhecido: ouro; sem ``t_audio``: recusado."""
    audio = {
        "colunas": [
            {"tela": 1, "exibicao": 0, "coluna": 1, "t_audio": 10.6, "confianca": 0.9}
        ]
    }
    arr = _denso_com_braco()
    evs = eventos(_produto(), audio, arr, np.zeros(len(arr["pts"])), 0)
    assert [e["nivel"] for e in evs] == ["ouro", "recusado", "recusado"]
    assert evs[1]["motivo"] == "sem t_audio"
    sem_capo = eventos(_produto(), audio, arr, np.zeros(len(arr["pts"])), None)
    assert sem_capo[0]["nivel"] == "recusado" and sem_capo[0]["motivo"] == "K4"
    assert resumo(evs)["motivos"] == {"sem t_audio": 2}


def test_corte_na_janela_reprova_k4() -> None:
    """Uma distância acima de 0,30 entre quadros da janela reprova a K4."""
    audio = {
        "colunas": [
            {"tela": 1, "exibicao": 0, "coluna": 1, "t_audio": 10.6, "confianca": 0.9}
        ]
    }
    arr = _denso_com_braco()
    cortes_pares = np.zeros(len(arr["pts"]))
    cortes_pares[12] = 0.8
    evs = eventos(_produto(), audio, arr, cortes_pares, 0)
    assert evs[0]["checagens"]["K4"] == {"passou": False, "valor": 0.8}


def test_eventos_passam_no_validador_do_formato() -> None:
    """Os eventos e o resumo montados aqui passam no ``validar_json`` do esquema."""
    audio = {
        "colunas": [
            {"tela": 1, "exibicao": 0, "coluna": 1, "t_audio": 10.6, "confianca": 0.9}
        ]
    }
    evs = eventos(_produto(), audio, _denso_com_braco(), np.zeros(30), 0)
    doc = {
        "esquema": "chorinho/maos@1",
        "produto": "p.json",
        "produto_sha256": "0" * 64,
        "audio": None,
        "audio_sha256": None,
        "denso": "x.maos.npz",
        "denso_sha256": "0" * 64,
        "video": {"arquivo": "c/x.mp4", "fps": 30.0, "largura": 1000, "altura": 100},
        "gerado_por": {
            "commit": "x",
            "detector_maos": "m",
            "detector_braco": "b",
            "parametros": {},
        },
        "violao": {"canhoto": False, "capotraste": 0, "capotraste_fonte": "dono"},
        "eventos": evs,
        "resumo": resumo(evs),
    }
    assert validar_json(doc) == []


def test_braco_do_previsto_entregue_e_sinalizado() -> None:
    """Entregue → conf 1; sinalizado → 0; sem braço → NaN e ``achou`` falso."""
    previsto = {
        "achou": True,
        "sinalizado": False,
        "nut": [10.0, 25.0],
        "trastes": [
            {"numero": 1, "ponto": [110.0, 25.0]},
            {"numero": 2, "ponto": [5000.0, 25.0]},
        ],
        "corda1": [[0.0, 0.0], [2000.0, 0.0]],
        "corda6": [[0.0, 50.0], [2000.0, 50.0]],
    }
    trastes, c1, _, achou, conf = braco_do_previsto(previsto, 1000, 100)
    assert achou and conf == 1.0
    assert trastes[1].tolist() == [110.0, 25.0] and np.isnan(trastes[2]).all()
    assert math.isclose(c1[:, 0].max(), 999.0)
    assert braco_do_previsto(dict(previsto, sinalizado=True), 1000, 100)[4] == 0.0
    _, _, _, achou, conf = braco_do_previsto({"achou": False}, 1000, 100)
    assert not achou and math.isnan(conf)
