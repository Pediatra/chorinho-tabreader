"""Testes do sorteio do braço encadeado (M11b): sem acervo e sem GPU."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from tab.maos_braco_m11b import (
    FOLGA_S,
    FRAC_FIM,
    FRAC_INICIO,
    MARGEM_FIM_S,
    N_ALVOS,
    N_CANAIS,
    N_CANDIDATOS,
    SEMENTE,
    _quadros_gravados,
    alvos,
    canais_do_gabarito,
    candidatos,
    escolher_quadro_chave,
    lista_da_etapa1,
    montar_etapa2,
    planejar_etapa1,
    rng_do_video,
    sortear_videos,
    substituir_video,
)


def _censo(canais: int, por_canal: int = 3) -> list[dict]:
    """Censo sintético: ``canais`` canais, ``por_canal`` vídeos em cada um."""
    linhas = []
    for c in range(canais):
        for v in range(por_canal):
            arquivo = f"canal{c:02d}/video{v}.mp4"
            linhas.append(
                {
                    "canal": f"canal{c:02d}",
                    "arquivo": arquivo,
                    "chave": f"{arquivo}|1|1",
                }
            )
    return linhas


def test_sorteio_e_reproduzivel_e_tem_um_video_por_canal() -> None:
    censo = _censo(12)
    primeiro = sortear_videos(censo, set(), SEMENTE)
    segundo = sortear_videos(censo, set(), SEMENTE)
    assert primeiro == segundo
    canais = [linha["canal"] for linha in primeiro]
    assert len(canais) == N_CANAIS
    assert len(set(canais)) == N_CANAIS
    for linha in primeiro:
        assert linha["arquivo"].startswith(linha["canal"] + "/")


def test_sorteio_exclui_canais_do_gabarito() -> None:
    censo = _censo(12)
    excluir = {"canal00", "canal01", "canal02", "canal03"}
    sorteados = sortear_videos(censo, excluir, SEMENTE)
    assert len(sorteados) == N_CANAIS
    assert not {linha["canal"] for linha in sorteados} & excluir


def test_sorteio_recusa_quando_faltam_canais() -> None:
    censo = _censo(12)
    excluir = {f"canal{c:02d}" for c in range(5)}  # sobram 7 canais
    with pytest.raises(ValueError, match="canais elegíveis"):
        sortear_videos(censo, excluir, SEMENTE)


def test_canais_do_gabarito_lidos_do_indice() -> None:
    indice = {
        "quadros": [
            {"id": "q01", "canal": "sky guitar"},
            {"id": "q02", "canal": "sky guitar"},
            {"id": "q03", "canal": "iwaki"},
        ]
    }
    assert canais_do_gabarito(indice) == {"sky guitar", "iwaki"}


def test_candidatos_na_faixa_e_na_ordem_do_sorteio() -> None:
    duracao = 1000.0
    cands = candidatos(duracao, random.Random(1))
    assert len(cands) == N_CANDIDATOS
    for t in cands:
        assert FRAC_INICIO * duracao <= t <= FRAC_FIM * duracao
        assert round(t, 2) == t
    # Na ordem do sorteio, não ordenados: replica as chamadas do gerador.
    esperado_rng = random.Random(1)
    inicio, fim = FRAC_INICIO * duracao, FRAC_FIM * duracao
    esperado = [
        round(esperado_rng.uniform(inicio, fim), 2) for _ in range(N_CANDIDATOS)
    ]
    assert cands == esperado
    assert cands != sorted(cands)


def test_rng_por_video_e_estavel_e_separado_por_fase() -> None:
    a = rng_do_video("canal/x.mp4", "candidatos").random()
    b = rng_do_video("canal/x.mp4", "candidatos").random()
    c = rng_do_video("canal/x.mp4", "alvos").random()
    assert a == b
    assert a != c


def test_alvos_ordenados_dentro_do_intervalo() -> None:
    t_chave = 100.0
    duracao = 400.0
    instantes = alvos(t_chave, duracao, random.Random(7))
    assert len(instantes) == N_ALVOS
    assert instantes == sorted(instantes)
    for t in instantes:
        assert t_chave + FOLGA_S <= t <= duracao - MARGEM_FIM_S


def test_alvos_recusa_intervalo_vazio() -> None:
    with pytest.raises(ValueError, match="intervalo vazio"):
        alvos(99.0, 100.0, random.Random(7))


def test_planejar_etapa1_gera_40_candidatos_em_ordem() -> None:
    censo = _censo(12)
    sorteio = planejar_etapa1(censo, {"canal00"}, lambda arquivo: 600.0)
    assert sorteio["semente"] == SEMENTE
    assert sorteio["canais_excluidos"] == ["canal00"]
    assert len(sorteio["videos"]) == N_CANAIS
    for video in sorteio["videos"]:
        assert [c["ordem"] for c in video["candidatos"]] == list(
            range(1, N_CANDIDATOS + 1)
        )
    lista = lista_da_etapa1(sorteio)
    assert len(lista) == N_CANAIS * N_CANDIDATOS
    assert lista[0] == {
        "arquivo": sorteio["videos"][0]["arquivo"],
        "t": sorteio["videos"][0]["candidatos"][0]["t"],
    }


def test_escolhe_o_primeiro_com_braco() -> None:
    candidatos_ = [
        {"ordem": 1, "t": 10.0},
        {"ordem": 2, "t": 20.0},
        {"ordem": 3, "t": 30.0},
        {"ordem": 4, "t": 40.0},
    ]
    bracos = {10.0: "nao", 20.0: "sim", 30.0: "parcial", 40.0: "sim"}
    assert escolher_quadro_chave(candidatos_, bracos) == 20.0


def test_aceita_parcial_como_braco() -> None:
    candidatos_ = [{"ordem": 1, "t": 10.0}, {"ordem": 2, "t": 20.0}]
    assert escolher_quadro_chave(candidatos_, {10.0: "parcial", 20.0: "sim"}) == 10.0


def test_pula_nao_e_interrogacao() -> None:
    candidatos_ = [
        {"ordem": 1, "t": 10.0},
        {"ordem": 2, "t": 20.0},
        {"ordem": 3, "t": 30.0},
    ]
    bracos = {10.0: "nao", 20.0: "?", 30.0: "sim"}
    assert escolher_quadro_chave(candidatos_, bracos) == 30.0


def test_recusa_sem_resposta_antes_do_primeiro_com_braco() -> None:
    candidatos_ = [
        {"ordem": 1, "t": 10.0},
        {"ordem": 2, "t": 20.0},
        {"ordem": 3, "t": 30.0},
    ]
    bracos = {10.0: "nao", 20.0: None, 30.0: "sim"}
    with pytest.raises(ValueError, match="sem resposta"):
        escolher_quadro_chave(candidatos_, bracos)


def test_recusa_quando_nenhum_candidato_tem_braco() -> None:
    candidatos_ = [{"ordem": 1, "t": 10.0}, {"ordem": 2, "t": 20.0}]
    with pytest.raises(ValueError, match="nenhum candidato"):
        escolher_quadro_chave(candidatos_, {10.0: "nao", 20.0: "nao"})


def _sorteio_sintetico() -> dict:
    return {
        "semente": SEMENTE,
        "canais_excluidos": [],
        "videos": [
            {
                "canal": "a",
                "arquivo": "a/v.mp4",
                "chave": "a/v.mp4|1|1",
                "duracao": 400.0,
                "candidatos": [
                    {"ordem": 1, "t": 50.0},
                    {"ordem": 2, "t": 60.0},
                ],
            },
            {
                "canal": "b",
                "arquivo": "b/w.mp4",
                "chave": "b/w.mp4|1|1",
                "duracao": 400.0,
                "candidatos": [
                    {"ordem": 1, "t": 70.0},
                    {"ordem": 2, "t": 80.0},
                ],
            },
        ],
    }


def _indice_sintetico() -> dict:
    return {
        "semente": SEMENTE,
        "quadros": [
            {"id": "q01", "arquivo": "a/v.mp4", "t": 50.0},
            {"id": "q02", "arquivo": "a/v.mp4", "t": 60.0},
            {"id": "q03", "arquivo": "b/w.mp4", "t": 70.0},
            {"id": "q04", "arquivo": "b/w.mp4", "t": 80.0},
        ],
    }


def test_montar_etapa2_escolhe_chave_e_sorteia_alvos() -> None:
    gabarito = {
        "quadros": {
            "q01": {"braco": "nao"},
            "q02": {"braco": "sim"},
            "q03": {"braco": "parcial"},
            "q04": {"braco": "nao"},
        }
    }
    chaves, lista = montar_etapa2(_sorteio_sintetico(), _indice_sintetico(), gabarito)
    assert [v["t_chave"] for v in chaves["videos"]] == [60.0, 70.0]
    assert [v["braco_chave"] for v in chaves["videos"]] == ["sim", "parcial"]
    assert len(lista) == 2 * N_ALVOS
    assert {item["arquivo"] for item in lista} == {"a/v.mp4", "b/w.mp4"}
    for video in chaves["videos"]:
        assert len(video["alvos"]) == N_ALVOS
        assert all(t >= video["t_chave"] + FOLGA_S for t in video["alvos"])


def test_montar_etapa2_indica_o_video_quando_falta_resposta() -> None:
    gabarito = {
        "quadros": {
            "q01": {"braco": None},
            "q02": {"braco": "sim"},
            "q03": {"braco": "sim"},
            "q04": {"braco": "sim"},
        }
    }
    with pytest.raises(ValueError, match=r"^a/v\.mp4: candidato 1"):
        montar_etapa2(_sorteio_sintetico(), _indice_sintetico(), gabarito)


def test_quadros_gravados_conta_o_que_ja_existe(tmp_path: Path) -> None:
    ausente = tmp_path / "nao_existe.json"
    assert _quadros_gravados(ausente) == 0
    com_quadro = tmp_path / "indice.json"
    com_quadro.write_text(
        json.dumps({"semente": 1, "quadros": [{"id": "q01"}]}), encoding="utf-8"
    )
    assert _quadros_gravados(com_quadro) == 1


def test_substituir_video_troca_na_mesma_posicao_e_registra() -> None:
    censo = [
        {"canal": c, "arquivo": f"{c}/v{k}.mp4", "chave": f"{c}{k}"}
        for c in "abcdefghijk"
        for k in range(3)
    ]
    sorteio = planejar_etapa1(censo, {"a"}, lambda _arquivo: 100.0)
    saida = sorteio["videos"][2]["canal"]
    novo, lista = substituir_video(
        sorteio, saida, censo, lambda _arquivo: 100.0, "guitarra elétrica"
    )
    assert novo["videos"][2]["canal"] not in {v["canal"] for v in sorteio["videos"]}
    assert novo["videos"][2]["canal"] != "a"
    assert novo["substituicoes"][0]["saiu"]["canal"] == saida
    assert len(lista) == 5
    assert sorteio["videos"][2]["canal"] == saida
    de_novo, _ = substituir_video(sorteio, saida, censo, lambda _a: 100.0, "x")
    assert de_novo["videos"][2] == novo["videos"][2]


def test_substituir_video_recusa_canal_fora_do_sorteio() -> None:
    censo = [{"canal": c, "arquivo": f"{c}/v.mp4", "chave": c} for c in "abcdefghij"]
    sorteio = planejar_etapa1(censo, set(), lambda _arquivo: 100.0)
    with pytest.raises(ValueError, match="não está no sorteio"):
        substituir_video(sorteio, "zzz", censo, lambda _a: 100.0, "x")
