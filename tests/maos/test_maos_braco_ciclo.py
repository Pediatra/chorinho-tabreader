"""Testes do ciclo de revisão do braço (rodadas 1026 e 1027): sem acervo e sem GPU."""

from __future__ import annotations

import numpy as np
import pytest

from tab.comum.caminhos import (
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    MAOS_M26,
    MAOS_M27,
)
from tab.maos.braco.ciclo import (
    MARCA_SETE_CORDAS,
    OBS_NAO_SINALIZADO,
    OBS_SEM_BRACO,
    OBS_SINALIZADO,
    RODADAS,
    _sem_resposta,
    como_foi_rotulado,
    conferir_numeracao,
    criterio,
    escolher_videos,
    fracoes_instantes,
    itens_do_sorteio,
    marcas_do_previsto,
    medir_quadros,
    ordenar_por_sinalizado,
    registro_previsto,
    trastes_visiveis,
)
from tab.maos.braco.gabarito import registro_em_branco
from tab.maos.braco.tempo import marcas_do_registro


def _previsto(sinalizado: bool = False, deslocamento: float = 0.0) -> dict:
    """Entrada de previsto.json com 3 trastes em ordem do nut para fora.

    Args:
        sinalizado: se a regra mandou o quadro para revisão.
        deslocamento: soma em x dos trastes (para fazer uma previsão errada).

    Returns:
        Entrada no formato de ``previsto_do_resultado``.
    """
    return {
        "arquivo": "sky guitar/video.mp4",
        "achou": True,
        "sinalizado": sinalizado,
        "motivo": None,
        "S1": 0.1,
        "S2": 0.1,
        "S3": 0.1,
        "nut": [100.0, 200.0],
        "corda1": [[0.0, 150.0], [600.0, 120.0]],
        "corda6": [[0.0, 260.0], [600.0, 240.0]],
        "trastes": [
            {"numero": 1, "ponto": [200.0 + deslocamento, 205.0]},
            {"numero": 2, "ponto": [300.0 + deslocamento, 210.0]},
            {"numero": 3, "ponto": [390.0 + deslocamento, 215.0]},
        ],
    }


DIMENSOES = (1920, 1080)


def _sem_braco() -> dict:
    """Entrada de previsto.json sem braço achado.

    Returns:
        Entrada com ``achou`` falso e as marcas vazias.
    """
    return {
        "arquivo": "sky guitar/outro.mp4",
        "achou": False,
        "sinalizado": True,
        "motivo": "sem pico",
        "S1": None,
        "S2": None,
        "S3": None,
        "nut": None,
        "corda1": None,
        "corda6": None,
        "trastes": None,
    }


def test_fracoes_instantes_vao_de_015_a_085_igualmente_espacadas() -> None:
    fracoes = fracoes_instantes()
    assert len(fracoes) == 8
    assert fracoes[0] == pytest.approx(0.15)
    assert fracoes[-1] == pytest.approx(0.85)
    passos = np.diff(fracoes)
    assert np.allclose(passos, passos[0])


def test_escolher_videos_respeita_exclusao_e_e_reproduzivel() -> None:
    candidatos = [f"sky guitar/v{k:02d}.mp4" for k in range(30)]
    excluidos = set(candidatos[:10])
    escolhidos = escolher_videos(candidatos, excluidos, semente=20261026)
    assert len(escolhidos) == 8
    assert len(set(escolhidos)) == 8
    assert not set(escolhidos) & excluidos
    assert escolher_videos(candidatos, excluidos, semente=20261026) == escolhidos


def test_escolher_videos_recusa_quando_falta_video() -> None:
    candidatos = ["sky guitar/a.mp4", "sky guitar/b.mp4"]
    with pytest.raises(ValueError):
        escolher_videos(candidatos, set(), semente=20261026, n=8)


def test_itens_do_sorteio_tem_oito_instantes_por_video() -> None:
    itens = itens_do_sorteio(
        ["sky guitar/a.mp4", "sky guitar/b.mp4"],
        {"sky guitar/a.mp4": 1000.0, "sky guitar/b.mp4": 500.0},
    )
    assert len(itens) == 16
    primeiros = [item["t"] for item in itens[:8]]
    assert primeiros[0] == pytest.approx(150.0)
    assert primeiros[-1] == pytest.approx(850.0)
    assert all(item["arquivo"] == "sky guitar/a.mp4" for item in itens[:8])
    assert all(item["tab"] is None for item in itens)


def test_ordenar_por_sinalizado_poe_sinalizados_primeiro_sem_mudar_a_ordem() -> None:
    ids = ["q01", "q02", "q03", "q04"]
    sinalizados = {"q01": False, "q02": True, "q03": False, "q04": True}
    assert ordenar_por_sinalizado(ids, sinalizados) == ["q02", "q04", "q01", "q03"]


def test_registro_previsto_relido_pela_ferramenta_da_as_mesmas_marcas() -> None:
    previsto = _previsto()
    base = registro_em_branco("chave|1|2")
    registro = registro_previsto(base, previsto, False, DIMENSOES)
    conferir_numeracao(registro, previsto, DIMENSOES)
    registro["braco"] = "sim"
    marcas = marcas_do_registro(registro)
    assert marcas is not None
    previsao = marcas_do_previsto(previsto)
    assert np.array_equal(marcas.nut, previsao.nut)
    assert np.array_equal(marcas.corda1, previsao.corda1)
    assert np.array_equal(marcas.corda6, previsao.corda6)
    assert sorted(marcas.trastes) == [1, 2, 3]
    for numero in (1, 2, 3):
        assert np.array_equal(marcas.trastes[numero], previsao.trastes[numero])


def test_registro_previsto_grava_braco_vazio_e_observacao() -> None:
    base = registro_em_branco("chave|1|2")
    achado = registro_previsto(base, _previsto(sinalizado=True), True, DIMENSOES)
    assert achado["braco"] is None
    assert achado["obs"] == OBS_SINALIZADO
    assert achado["trastes_previstos"] == achado["trastes"]
    nao_sinalizado = registro_previsto(base, _previsto(), False, DIMENSOES)
    assert nao_sinalizado["obs"] == OBS_NAO_SINALIZADO
    sem = registro_previsto(base, _sem_braco(), True, DIMENSOES)
    assert sem["obs"] == OBS_SEM_BRACO
    assert sem["nut"] is None and sem["trastes"] is None and sem["corda1"] is None


def test_conferir_numeracao_recusa_traste_fora_de_ordem() -> None:
    previsto = _previsto()
    previsto["trastes"][0], previsto["trastes"][2] = (
        previsto["trastes"][2],
        previsto["trastes"][0],
    )
    registro = registro_previsto(registro_em_branco("c"), _previsto(), False, DIMENSOES)
    with pytest.raises(ValueError):
        conferir_numeracao(registro, previsto, DIMENSOES)


def test_sem_resposta_recusa_gabarito_respondido() -> None:
    gabarito = {"quadros": {"q01": {**registro_em_branco("c"), "respondido_em": "x"}}}
    with pytest.raises(ValueError):
        _sem_resposta(gabarito)
    _sem_resposta({"quadros": {"q01": registro_em_branco("c")}})


def _gabarito_final() -> dict:
    """Gabarito final de teste: um quadro por caso da medida.

    Returns:
        Gabarito com q01 (certo), q02 e q03 (braço ``nao``), q04 (braço ``sim`` sem
        previsão), q05 (``7 cordas``) e q06 (sem resposta).
    """
    certo = registro_previsto(registro_em_branco("c1"), _previsto(), False, DIMENSOES)
    certo["braco"] = "sim"
    nao_1 = registro_previsto(registro_em_branco("c2"), _previsto(), False, DIMENSOES)
    nao_1["braco"] = "nao"
    nao_2 = registro_previsto(registro_em_branco("c3"), _previsto(), True, DIMENSOES)
    nao_2["braco"] = "nao"
    sem_previsao = registro_previsto(
        registro_em_branco("c4"), _previsto(), True, DIMENSOES
    )
    sem_previsao["braco"] = "sim"
    sete = registro_em_branco("c5")
    sete["braco"] = "nao"
    sete["obs"] = MARCA_SETE_CORDAS
    vazio = registro_em_branco("c6")
    return {
        "quadros": {
            "q01": certo,
            "q02": nao_1,
            "q03": nao_2,
            "q04": sem_previsao,
            "q05": sete,
            "q06": vazio,
        }
    }


def test_medir_quadros_classes_e_exclusoes() -> None:
    previsto_doc = {
        "ordem": ["q01", "q02", "q03", "q04", "q05", "q06"],
        "quadros": {
            "q01": _previsto(sinalizado=False),
            "q02": _previsto(sinalizado=False),
            "q03": _previsto(sinalizado=True),
            "q04": _sem_braco(),
            "q05": _previsto(sinalizado=False),
            "q06": _previsto(sinalizado=False),
        },
    }
    gabarito = _gabarito_final()
    resultado = medir_quadros(previsto_doc, gabarito, "1027")
    ids = {linha["id"] for linha in resultado["linhas"]}
    assert ids == {"q01", "q02", "q03", "q04"}
    excluidos = {item["id"]: item["motivo"] for item in resultado["excluidos"]}
    assert excluidos["q05"] == "7 cordas"
    assert excluidos["q06"].startswith("sem resposta")
    classes = {linha["id"]: linha["classe"] for linha in resultado["linhas"]}
    assert classes["q01"] == "certo"
    assert classes["q02"] == "falso"
    assert classes["q04"] == "nao_achou"
    totais = resultado["totais"]
    assert totais["medidos"] == 4
    assert totais["com_braco"] == 2
    assert totais["entregue_certo"] == 1
    assert totais["entregue_certo_fracao"] == pytest.approx(0.5)
    assert totais["falsos_passam_n"] == 1
    assert totais["falsos_passam"] == pytest.approx(0.25)
    assert totais["sinalizados"] == 2
    assert totais["sinalizados_fracao"] == pytest.approx(0.5)
    assert "parar" in totais["criterio"]


def test_criterio_segue_a_tabela_do_preregistro() -> None:
    assert criterio(0.06, 0.1, "1027").startswith("parar")
    assert criterio(0.0, 0.6, "1027").startswith("ciclo seguro, mas caro")
    assert criterio(0.02, 0.4, "1027").startswith("o ciclo funciona")
    assert criterio(None, 0.1, "1027") == "sem medida"


def test_criterio_nomeia_a_rodada_seguinte() -> None:
    """A 1026 manda para a 1027; a 1027 manda para a 1028."""
    assert criterio(0.0, 0.1, "1027").endswith(
        "a 1027 retreina os estágios 1 e 2 com as marcas finais e mede de novo num lote novo"
    )
    assert "a 1028 retreina" in criterio(0.0, 0.1, "1028")


def test_rodadas_1026_e_1027_tem_canal_semente_pasta_e_gabarito() -> None:
    assert RODADAS["1026"].canal == "sky guitar"
    assert RODADAS["1026"].semente == 20261026
    assert RODADAS["1026"].pasta == MAOS_M26
    assert RODADAS["1026"].gabarito == GABARITO_BRACO_M26
    assert RODADAS["1026"].proxima == "1027"
    assert RODADAS["1027"].canal == "ギタロー ⧸ guitarous"
    assert RODADAS["1027"].semente == 20261027
    assert RODADAS["1027"].pasta == MAOS_M27
    assert RODADAS["1027"].gabarito == GABARITO_BRACO_M27
    assert RODADAS["1027"].proxima == "1028"


def test_como_foi_rotulado_da_1026_nao_muda() -> None:
    assert como_foi_rotulado("1026") == (
        "dono, por quadro, na ferramenta tab.maos_braco_gabarito (rodada 1026, ciclo de "
        "revisão: a previsão do detector já vem preenchida, o dono confere); coordenadas "
        "no espaço do quadro original (x_quadro = x_img / escala)"
    )


def test_trastes_visiveis_cortam_no_primeiro_fora_da_imagem() -> None:
    """O corte é no primeiro ponto fora, e tudo depois dele sai, mesmo se voltar."""
    previsto = _previsto()
    previsto["trastes"][1]["ponto"] = [2000.0, 205.0]
    visiveis = trastes_visiveis(previsto, (1920, 1080))
    assert [item["numero"] for item in visiveis] == [1]
    previsto = _previsto()
    previsto["trastes"][2]["ponto"] = [100.0, -3.0]
    visiveis = trastes_visiveis(previsto, (1920, 1080))
    assert [item["numero"] for item in visiveis] == [1, 2]
    assert len(trastes_visiveis(_previsto(), (1920, 1080))) == 3


def test_registro_previsto_corta_trastes_e_previstos_mas_nao_a_previsao() -> None:
    previsto = _previsto()
    previsto["trastes"][2]["ponto"] = [1930.0, 215.0]
    registro = registro_previsto(registro_em_branco("c"), previsto, False, DIMENSOES)
    assert len(registro["trastes"]) == 2
    assert len(registro["trastes_previstos"]) == 2
    assert len(previsto["trastes"]) == 3
    conferir_numeracao(registro, previsto, DIMENSOES)


def test_medir_quadros_criterio_usa_a_fracao_de_sinalizados() -> None:
    """Critério com a fração (1 de 2 = 0,5), não com a contagem de sinalizados."""
    previsto_doc = {
        "ordem": ["q01", "q03"],
        "quadros": {
            "q01": _previsto(sinalizado=False),
            "q03": _previsto(sinalizado=True),
        },
    }
    totais = medir_quadros(previsto_doc, _gabarito_final(), "1027")["totais"]
    assert totais["sinalizados_fracao"] == 0.5
    assert totais["criterio"].startswith("o ciclo funciona")
