"""Testes do ``tab.video`` (Fase 4): funções puras, sem GPU e sem acervo.

Cobre a montagem do JSON v1, a mediana temporal que apaga um marcador móvel, o x no
espaço do quadro (soma do ``x0`` do candidato) e as colunas e o compasso.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from tab.tablatura.ouro.avaliar_video import FORMATO_V1, ler_predicao
from tab.tablatura.produto import video
from tab.tablatura.produto.telas import Tela
from tab.tablatura.produto.video import (
    BORDA_SEM_GLIFO,
    CLASSE_ABAFADA,
    ESQUEMA,
    MOTIVO_TEMPO,
    colunas_do_quadro,
    compasso_de,
    ler_tela,
    mediana_temporal,
    montar_v1,
    tokens_da_rede,
    tokens_do_quadro,
)


def _quadro_com_faixa(k: int) -> np.ndarray:
    """Quadro branco 60x80 com uma faixa azul de 4 px em x = 5 + 8k e um bloco preto fixo."""
    quadro = np.full((60, 80, 3), 255, dtype=np.uint8)
    quadro[:, 5 + 8 * k : 5 + 8 * k + 4] = (255, 0, 0)  # faixa azul (BGR)
    # tinta fixa (algarismo), presente em todos os quadros; fora das colunas das faixas
    quadro[10:20, 60:64] = 0
    return quadro


def test_mediana_apaga_faixa_movel_e_mantem_tinta_fixa():
    quadros = [_quadro_com_faixa(k) for k in range(7)]
    mediana = mediana_temporal(quadros)
    assert mediana.dtype == np.uint8
    for k in range(7):
        faixa = mediana[:, 5 + 8 * k : 5 + 8 * k + 4]
        assert (faixa == 255).all(), f"faixa do quadro {k} sobrou na mediana"
    assert (mediana[10:20, 60:64] == 0).all(), "tinta fixa sumiu"


def test_mediana_sem_quadros_levanta_erro():
    with pytest.raises(ValueError):
        mediana_temporal([])


def test_tokens_somam_x0_do_candidato_ao_x_do_roi():
    r = {
        "notas": [
            {
                "corda": 2,
                "casa": "7",
                "x": 10,
                "x_centro": 14.5,
                "confianca": 0.9123,
                "tecnica": None,
            }
        ]
    }
    (tk,) = tokens_do_quadro(r, 300)
    assert tk["x_quadro"] == 310
    assert tk["x_centro_quadro"] == 314.5
    assert tk["classe"] == "7"
    assert tk["corda"] == 2


def _nota_rede(corda: int, rotulo: str, x: float, tecnica: list[str] | None = None):
    """Nota no formato de ``tab.detector_tab.detectar``."""
    return {
        "corda": corda,
        "rotulo": rotulo,
        "tecnica": tecnica or [],
        "x": x,
        "confianca": 0.9,
    }


def test_rede_herda_borda_esquerda_do_glifo_da_mesma_corda():
    glifos = [
        SimpleNamespace(corda=2, x0=40, x1=56),  # "12": centro da rede em 48
        SimpleNamespace(corda=3, x0=44, x1=50),  # outra corda: não conta
    ]
    (tk,) = tokens_da_rede([_nota_rede(2, "12", 48.0)], glifos, 300, passo=16.0)
    assert tk["x_quadro"] == 340
    assert tk["x_centro_quadro"] == 348.0
    assert tk["classe"] == "12"
    assert tk["tecnica"] is None


def test_rede_sem_glifo_estima_borda_pelo_passo_e_junta_tecnicas():
    (tk,) = tokens_da_rede([_nota_rede(1, "7", 100.0, ["h", "lig"])], [], 0, passo=20.0)
    assert tk["x_quadro"] == round(100.0 - BORDA_SEM_GLIFO * 20.0)
    assert tk["tecnica"] == "h+lig"


def test_rede_glifo_largo_nao_junta_duas_notas_na_mesma_coluna():
    """Slide ``2/3`` num glifo só: a segunda nota não herda a borda da primeira."""
    glifos = [SimpleNamespace(corda=1, x0=100, x1=130)]
    notas = [_nota_rede(1, "2", 107.0), _nota_rede(1, "3", 125.0)]
    tokens = tokens_da_rede(notas, glifos, 0, passo=18.0)
    assert tokens[0]["x_quadro"] == 100
    assert tokens[1]["x_quadro"] == round(125.0 - BORDA_SEM_GLIFO * 18.0)
    assert colunas_do_quadro(tokens, passo=18.0) == [1, 2]


def test_ler_tela_rede_manda_x_para_nao_notas_e_casa_para_notas(monkeypatch):
    """Leitor ``rede``: algarismo vira nota (com técnica), X vira não-nota de classe x."""
    grade = SimpleNamespace(
        linhas_y=[10, 26, 42, 58, 74, 90], barlines_x=[5, 200], glifos=[]
    )
    m = SimpleNamespace(
        passo=16.0, roi=np.zeros((100, 300, 3), np.uint8), x0=50, y0=20, grade=grade
    )
    monkeypatch.setattr(video, "escolher_ou_mascara", lambda _img: m)
    lidas = [_nota_rede(1, "3", 100.0, ["/"]), _nota_rede(2, "x", 150.0)]
    monkeypatch.setattr(video.detector_tab, "detectar", lambda *a: lidas)
    tela = Tela(id=1, painel=(0, 0, 10, 10), modo="faixa", exibicoes=[(0.0, 1.0)])
    entrada, notas, nao_notas = ler_tela(
        np.zeros((200, 400, 3), np.uint8),
        tela,
        None,
        None,
        None,
        None,
        "",
        video=None,
        detector=object(),
    )
    assert entrada["leitura"] == "ok"
    assert entrada["barlines_x"] == [55, 250]
    assert [(n["corda"], n["casa"], n["tecnica"]) for n in notas] == [(1, 3, "/")]
    assert [(n["corda"], n["classe"]) for n in nao_notas] == [(2, CLASSE_ABAFADA)]


def test_colunas_agrupam_mesmo_x_e_numeram_em_ordem():
    tokens = [
        {"x_quadro": 160},
        {"x_quadro": 100},
        {"x_quadro": 101},
        {"x_quadro": 300},
    ]
    assert colunas_do_quadro(tokens, passo=16.0) == [2, 1, 1, 3]


def test_colunas_vazias():
    assert colunas_do_quadro([], passo=16.0) == []


def test_compasso_pelas_barlines_com_primeira_como_inicio():
    barlines = [100, 200, 300]
    assert compasso_de(50, barlines) == 1
    assert compasso_de(250, barlines) == 2
    assert compasso_de(350, barlines) == 3


def _tela(tid: int, medido: bool = False) -> dict:
    tempo = {"medido": medido}
    if not medido:
        tempo["motivo"] = MOTIVO_TEMPO
    return {
        "id": tid,
        "painel": [70, 296, 1854, 446],
        "passo": 16.0,
        "modo": "estatico",
        "barlines_x": [480, 1010],
        "exibicoes": [{"t0": 10.0, "t1": 20.0}, {"t0": 30.0, "t1": 40.0}],
        "tempo": tempo,
    }


def test_montar_v1_forma_resumo_e_interop_com_a_regua():
    notas = [
        {
            "tela": 1,
            "passagem": 1,
            "coluna": 1,
            "compasso": 1,
            "corda": 2,
            "casa": 0,
            "tecnica": None,
            "confianca": 0.99,
            "x_quadro": 224,
            "x_centro_quadro": 230.5,
            "t_ini": None,
        },
        {
            "tela": 1,
            "passagem": 1,
            "coluna": 2,
            "compasso": 1,
            "corda": 5,
            "casa": 12,
            "tecnica": None,
            "confianca": 0.9,
            "x_quadro": 269,
            "x_centro_quadro": 276.0,
            "t_ini": 12.5,
        },
    ]
    nao = [
        {
            "tela": 1,
            "coluna": 2,
            "corda": 1,
            "x_quadro": 269,
            "x_centro_quadro": 276.0,
            "classe": "harmonico",
            "confianca": 0.5,
        }
    ]
    dados = montar_v1(
        video={"arquivo": "sky guitar/x.mp4", "canal": "sky guitar"},
        gerado_por={"modelo": "artefatos/oficial_3/glifo_sint.pt", "commit": "x"},
        telas_v1=[_tela(1)],
        notas=notas,
        nao_notas=nao,
    )
    assert dados["esquema"] == ESQUEMA
    assert dados["resumo"] == {
        "telas": 1,
        "exibicoes": 2,
        "notas": 2,
        "notas_com_tempo": 1,
        "instantes_distintos": 1,
        "telas_sem_tempo": 1,
        "nao_notas": 1,
    }
    assert all(isinstance(n["casa"], int) for n in dados["notas"])
    assert dados["nao_notas"][0]["classe"] == "harmonico"
    # o JSON é gravável e o leitor da régua o aceita como v1
    json.dumps(dados)
    predicao = ler_predicao(json.loads(json.dumps(dados)))
    assert predicao.formato == FORMATO_V1
    assert [n.casa for n in predicao.telas[0].notas] == [0, 12]


def test_montar_v1_tela_com_tempo_medido_conta_em_telas_sem_tempo():
    dados = montar_v1(
        video={},
        gerado_por={},
        telas_v1=[_tela(1, medido=True)],
        notas=[],
        nao_notas=[],
    )
    assert dados["resumo"]["telas_sem_tempo"] == 0
    assert dados["resumo"]["notas_com_tempo"] == 0
