"""Testes da rodada 1029 do ciclo: escolha de pesos, exclusões e fallback. Sem GPU e sem acervo."""

from __future__ import annotations

import dataclasses
import json

import pytest

from tab import maos_braco_ciclo as ciclo
from tab.maos_braco_ciclo import (
    ARQUIVO_ESCOLHA,
    ESTAGIO1,
    ESTAGIO2,
    RODADAS,
    Pesos,
    arquivos_da_1027_e_m11b,
    combinacoes_existentes,
    escolher_combinacao,
    escolher_pesos,
    excluidos_da_rodada,
    pesos_da_rodada,
    pesos_do_documento,
    registro_previsto,
)


def _linha(
    estagio1: str,
    estagio2: str,
    falsos: int,
    certos: int,
    sinalizados: int,
    soma: int,
) -> dict:
    """Uma linha da tabela de combinações, com os campos do critério.

    Args:
        estagio1: nome do localizador.
        estagio2: nome do detector.
        falsos: falsos não sinalizados.
        certos: certos não sinalizados.
        sinalizados: quadros sinalizados.
        soma: soma das sementes.

    Returns:
        Dicionário no formato de ``avaliar_combinacao``.
    """
    return {
        "estagio1": estagio1,
        "estagio2": estagio2,
        "soma_sementes": soma,
        "medidos": 29,
        "falsos_passam_n": falsos,
        "entregue_certo": certos,
        "sinalizados": sinalizados,
    }


def test_escolhe_o_de_menos_falsos_nao_sinalizados():
    tabela = [
        _linha("L3_todos_s1", "A4_100_todos_s1", 2, 20, 3, 2),
        _linha("L3_todos_s2", "A4_100_todos_s2", 1, 5, 9, 4),
    ]
    assert escolher_combinacao(tabela)["estagio1"] == "L3_todos_s2"


def test_desempate_pelos_mais_certos_nao_sinalizados():
    tabela = [
        _linha("L3_todos_s1", "A4_100_todos_s1", 1, 5, 4, 2),
        _linha("L3_todos_s2", "A4_100_todos_s2", 1, 7, 4, 4),
    ]
    assert escolher_combinacao(tabela)["estagio1"] == "L3_todos_s2"


def test_desempate_pelos_menos_sinalizados_e_depois_pela_soma_das_sementes():
    tabela = [
        _linha("L3_todos_s1", "A4_100_todos_s1", 1, 7, 5, 2),
        _linha("L3_todos_s2", "A4_100_todos_s2", 1, 7, 3, 4),
    ]
    assert escolher_combinacao(tabela)["estagio1"] == "L3_todos_s2"
    empate = [
        _linha("L3_todos_s1", "A4_100_todos_s3", 1, 7, 3, 4),
        _linha("L3_todos_s2", "A4_100_todos_s1", 1, 7, 3, 3),
    ]
    assert escolher_combinacao(empate)["estagio1"] == "L3_todos_s2"


def test_tabela_vazia_recusa():
    with pytest.raises(ValueError):
        escolher_combinacao([])


def test_combinacoes_so_com_pesos_que_existem(tmp_path):
    for nome in ("L3_todos_s1", "L3_todos_s3", "A4_100_todos_s2", "A4_100_todos_s3"):
        (tmp_path / f"{nome}.pt").write_bytes(b"")
        (tmp_path / f"{nome}.json").write_text("{}", encoding="utf-8")
    (tmp_path / "L3_todos_s2.pt").write_bytes(b"")  # sem .json: não conta
    assert combinacoes_existentes(tmp_path) == [
        ("L3_todos_s1", "A4_100_todos_s2"),
        ("L3_todos_s1", "A4_100_todos_s3"),
        ("L3_todos_s3", "A4_100_todos_s2"),
        ("L3_todos_s3", "A4_100_todos_s3"),
    ]


def test_sem_nenhum_l3_ou_a4_cai_no_fallback_sem_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr(ciclo, "combinacoes_existentes", lambda diretorio=None: [])

    def proibido(*_args, **_kwargs):
        raise AssertionError("sem combinações não deve rodar a GPU")

    monkeypatch.setattr(ciclo, "avaliar_combinacao", proibido)
    escolha = escolher_pesos(True, False, tmp_path)
    assert escolha["estagio1"] == ESTAGIO1
    assert escolha["estagio2"] == ESTAGIO2
    assert escolha["tabela"] == []
    assert escolha["p2"] is True and escolha["p3"] is False
    gravado = json.loads((tmp_path / ARQUIVO_ESCOLHA).read_text(encoding="utf-8"))
    assert gravado["estagio1"] == ESTAGIO1 and "fallback" in gravado["fonte"]


def test_escolha_usa_a_tabela_e_grava_o_json(tmp_path, monkeypatch):
    combos = [("L3_todos_s1", "A4_100_todos_s1"), ("L3_todos_s2", "A4_100_todos_s2")]
    monkeypatch.setattr(ciclo, "combinacoes_existentes", lambda diretorio=None: combos)
    monkeypatch.setattr(ciclo, "_quadros_m11b", lambda: ([], {}))
    falsos = {"L3_todos_s1": 3, "L3_todos_s2": 1}

    def falsa(estagio1, estagio2, _itens, _registros):
        return _linha(estagio1, estagio2, falsos[estagio1], 5, 4, 2)

    monkeypatch.setattr(ciclo, "avaliar_combinacao", falsa)
    escolha = escolher_pesos(False, True, tmp_path)
    assert escolha["estagio1"] == "L3_todos_s2"
    assert escolha["estagio2"] == "A4_100_todos_s2"
    assert len(escolha["tabela"]) == 2
    assert escolha["p2"] is False and escolha["p3"] is True


def test_pesos_1026_e_1027_seguem_fixos():
    assert pesos_da_rodada("1026") == Pesos(ESTAGIO1, ESTAGIO2)
    assert pesos_da_rodada("1027") == Pesos(ESTAGIO1, ESTAGIO2)


def test_prever_1029_sem_escolha_falha_com_mensagem_clara(tmp_path, monkeypatch):
    monkeypatch.setitem(
        RODADAS, "1029", dataclasses.replace(RODADAS["1029"], pasta=tmp_path)
    )
    with pytest.raises(ValueError, match="escolher-pesos"):
        pesos_da_rodada("1029")


def test_pesos_1029_vem_do_json(tmp_path, monkeypatch):
    monkeypatch.setitem(
        RODADAS, "1029", dataclasses.replace(RODADAS["1029"], pasta=tmp_path)
    )
    escolha = {
        "estagio1": "L3_todos_s2",
        "estagio2": "A4_100_todos_s3",
        "p2": True,
        "p3": False,
    }
    (tmp_path / ARQUIVO_ESCOLHA).write_text(json.dumps(escolha), encoding="utf-8")
    assert pesos_da_rodada("1029") == Pesos(
        "L3_todos_s2", "A4_100_todos_s3", True, False
    )


def test_bloco_de_pesos_so_leva_as_opcoes_ligadas():
    assert pesos_do_documento(Pesos(ESTAGIO1, ESTAGIO2)) == {
        "estagio1": ESTAGIO1,
        "estagio2": ESTAGIO2,
        "conjunta": True,
    }
    ligado = pesos_do_documento(Pesos(ESTAGIO1, ESTAGIO2, p2=True, p3=True))
    assert ligado["um_braco"] is True
    assert ligado["consenso"] == "S4"


def test_exclui_a_1027_e_a_m11b_na_1029(tmp_path):
    m27 = tmp_path / "indice27.json"
    m27.write_text(
        json.dumps({"quadros": [{"arquivo": "canal/a.mp4"}]}), encoding="utf-8"
    )
    m11b = tmp_path / "chaves.json"
    m11b.write_text(
        json.dumps({"videos": [{"arquivo": "canal/b.mp4"}]}), encoding="utf-8"
    )
    assert arquivos_da_1027_e_m11b(m27, m11b) == {"canal/a.mp4", "canal/b.mp4"}


def test_excluidos_da_1029_somam_as_amostras_e_a_1027(monkeypatch):
    monkeypatch.setattr(ciclo, "arquivos_ja_usados", lambda: {"antigo.mp4"})
    monkeypatch.setattr(ciclo, "arquivos_da_1027_e_m11b", lambda: {"m27.mp4"})
    assert excluidos_da_rodada("1029") == {"antigo.mp4", "m27.mp4"}
    assert excluidos_da_rodada("1026") == {"antigo.mp4"}


def test_registro_previsto_zera_o_capotraste():
    base = {"chave": "k", "capo": [10.0, 20.0]}
    previsto = {"achou": False}
    registro = registro_previsto(base, previsto, False, (1280, 720))
    assert registro["capo"] is None
    assert base["capo"] == [10.0, 20.0]


def test_1032_considera_a5_e_sinaliza_nut(tmp_path):
    """A 1032 escolhe também entre os A5 e sinaliza o nut suspeito."""
    for nome in ("L3_todos_s1", "A4_100_todos_s2", "A5_100_todos_s1"):
        (tmp_path / f"{nome}.pt").write_bytes(b"x")
        (tmp_path / f"{nome}.json").write_text("{}")
    assert ciclo.combinacoes_existentes(tmp_path) == [
        ("L3_todos_s1", "A4_100_todos_s2")
    ]
    assert ciclo.combinacoes_existentes(tmp_path, com_a5=True) == [
        ("L3_todos_s1", "A4_100_todos_s2"),
        ("L3_todos_s1", "A5_100_todos_s1"),
    ]
    assert "1032" in ciclo.RODADAS_COM_ESCOLHA
    assert "1032" in ciclo.RODADAS_SINAL_NUT
    previsto = {
        "achou": True,
        "nut": [10.0, 360.0],
        "corda1": [[10.0, 330.0], [1200.0, 330.0]],
        "corda6": [[10.0, 390.0], [1200.0, 390.0]],
    }
    assert ciclo.nut_suspeito_previsto(previsto, (1280, 720))
    longe = dict(previsto, nut=[200.0, 360.0])
    longe["corda1"] = [[200.0, 330.0], [1200.0, 330.0]]
    longe["corda6"] = [[200.0, 390.0], [1200.0, 390.0]]
    assert not ciclo.nut_suspeito_previsto(longe, (1280, 720))
    assert not ciclo.nut_suspeito_previsto({"achou": False}, (1280, 720))


def test_1036_herda_a_escolha_da_1032(tmp_path, monkeypatch):
    """A 1036 lê o ``escolha_pesos.json`` da pasta da 1032, sem escolher de novo."""
    monkeypatch.setitem(
        RODADAS, "1032", dataclasses.replace(RODADAS["1032"], pasta=tmp_path)
    )
    escolha = {
        "estagio1": "L3_todos_s3",
        "estagio2": "A4_100_todos_s1",
        "p2": False,
        "p3": False,
    }
    (tmp_path / ARQUIVO_ESCOLHA).write_text(json.dumps(escolha), encoding="utf-8")
    assert pesos_da_rodada("1036") == Pesos("L3_todos_s3", "A4_100_todos_s1")
    assert "1036" in ciclo.RODADAS_SINAL_NUT_V2


def test_1036_sorteia_8_videos_de_aula_com_4_quadros(tmp_path):
    """O lote da 1036: só títulos de aula, 8 vídeos e 4 instantes de 0,15 a 0,85."""
    rodada = RODADAS["1036"]
    assert (rodada.n_videos, rodada.n_instantes) == (8, 4)
    canal = tmp_path / rodada.canal
    canal.mkdir()
    for nome in ("aprenda no VIOLÃO [1].mp4", "vlog da neném [2].mp4", "solo [3].mp3"):
        (canal / nome).write_bytes(b"")
    assert ciclo._candidatos(tmp_path, rodada.canal, rodada.filtro_titulo) == [
        f"{rodada.canal}/aprenda no VIOLÃO [1].mp4"
    ]
    assert ciclo.fracoes_instantes(4) == [0.15, 0.383333, 0.616667, 0.85]
    itens = ciclo.itens_do_sorteio(["a.mp4"], {"a.mp4": 10.0}, 4)
    assert [item["t"] for item in itens] == [1.5, 3.83, 6.17, 8.5]


def test_videos_com_capo_visto(tmp_path):
    caminho = tmp_path / "triagem.json"
    caminho.write_text(
        json.dumps(
            {
                "videos": [
                    {"n": 1, "arquivo": "c/a.mp4", "capo_visto": True},
                    {"n": 2, "arquivo": "c/b.mp4", "capo_visto": False},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert ciclo.videos_com_capo_visto(caminho) == ["c/a.mp4"]
    caminho.write_text(
        json.dumps({"videos": [{"n": 1, "arquivo": "c/a.mp4", "capo_visto": None}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="sem a marca"):
        ciclo.videos_com_capo_visto(caminho)


def test_rodada_1039_usa_triagem():
    rodada = ciclo.RODADAS["1039"]
    assert rodada.canal == "shin izumi"
    assert rodada.triagem


def _grava(caminho, dados):
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


def test_pesos_da_1039_dependem_da_1037(tmp_path, monkeypatch):
    escolha = _grava(
        tmp_path / "escolha.json",
        {"estagio1": "L4_capo_s2", "estagio2": "A6_capo_s1"},
    )
    passou = {"seguranca": True, "capo": True, "sem_capo": True}
    medida = _grava(tmp_path / "medida.json", {"criterios": passou})
    assert ciclo.pesos_condicionais_1037(medida, escolha) == ciclo.Pesos(
        "L4_capo_s2", "A6_capo_s1"
    )
    antigo = ciclo.Pesos("L3_todos_s3", "A4_100_todos_s1")
    monkeypatch.setattr(ciclo, "pesos_da_rodada", lambda numero: antigo)
    _grava(medida, {"criterios": dict(passou, capo=False)})
    assert ciclo.pesos_condicionais_1037(medida, escolha) == antigo
    with pytest.raises(ValueError, match="1037 precisa medir"):
        ciclo.pesos_condicionais_1037(tmp_path / "falta.json", escolha)
