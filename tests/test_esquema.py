"""Testes do esquema ``chorinho/video@1`` (``tab.esquema.validar``).

A forma do JSON é a mesma nos três caminhos (com posição, com cor e sem marcador): o
que muda é o conteúdo de ``t_ini`` e ``tempo``. Os casos são montados pelas funções
reais de ``tab.video`` (``entradas_da_nota`` e ``montar_v1``), então o teste acompanha o
que o motor emite de verdade.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

import tab.transcrever as cli
from tab.caminhos import SAIDA
from tab.esquema import ESQUEMA, validar
from tab.video import entradas_da_nota, montar_v1

_MEDIDO_POSICAO = {
    "medido": True,
    "observador": "posicao",
    "motivo": None,
    "coerencia": 0.97,
    "cobertura": 0.92,
}
_MEDIDO_COR = {
    "medido": True,
    "observador": "cor_acende",
    "motivo": None,
    "coerencia": 0.96,
    "cobertura": 0.95,
}
_SEM_MARCADOR = {
    "medido": False,
    "observador": None,
    "motivo": "posicao: 3 amostras com faixa; cor: nenhum destaque",
    "coerencia": None,
    "cobertura": None,
}


def _dados(tempo_exibicao: dict, passagens: list) -> dict:
    """Um vídeo com uma tela, uma exibição e duas colunas, montado como o motor faz.

    Args:
        tempo_exibicao: bloco ``tempo`` da exibição.
        passagens: passagens da exibição (``{"coluna", "t_ini"}``).

    Returns:
        O JSON ``chorinho/video@1`` montado por ``tab.video.montar_v1``.
    """
    exibicao = {
        "t0": 10.0,
        "t1": 20.0,
        "tempo": tempo_exibicao,
        "observadores": {},
        "passagens": passagens,
        "amostras": 12,
    }
    medido = tempo_exibicao["medido"]
    tela = {
        "id": 1,
        "painel": [70, 296, 1854, 446],
        "passo": 21.6,
        "modo": "paginado",
        "barlines_x": [480, 1010],
        "exibicoes": [exibicao],
        "tempo": {"medido": medido, "motivo": None if medido else "sem marcador"},
        "leitura": "ok",
    }
    notas: list[dict] = []
    for coluna, corda, casa in [(1, 2, 0), (2, 3, 5)]:
        base = {
            "tela": 1,
            "coluna": coluna,
            "corda": corda,
            "x_quadro": 200 + 40 * coluna,
            "x_centro_quadro": 210.0 + 40 * coluna,
            "compasso": 1,
            "casa": casa,
            "tecnica": None,
            "confianca": 0.99,
        }
        notas.extend(entradas_da_nota(base, [exibicao]))
    nao_notas = [
        {
            "tela": 1,
            "coluna": 2,
            "corda": 1,
            "x_quadro": 300,
            "x_centro_quadro": 306.0,
            "classe": "harmonico",
            "confianca": 0.7,
            "simbolo_cru": {"png": "abc.png", "classe": "harmonico"},
        }
    ]
    return montar_v1(
        video={
            "arquivo": "sky guitar/teste.mp4",
            "canal": "sky guitar",
            "duracao_s": 60.0,
            "codec": "h264",
        },
        gerado_por={
            "modelo": "artefatos/oficial_3/glifo_sint.pt",
            "commit": "abc1234",
            "imagem": "quadro",
            "em": "2026-10-10T12:00:00",
        },
        telas_v1=[tela],
        notas=notas,
        nao_notas=nao_notas,
    )


def _caminho_posicao() -> dict:
    return _dados(
        _MEDIDO_POSICAO,
        [[{"coluna": 1, "t_ini": 11.0}, {"coluna": 2, "t_ini": 12.5}]],
    )


def _caminho_cor() -> dict:
    return _dados(
        _MEDIDO_COR,
        [[{"coluna": 1, "t_ini": 11.2}, {"coluna": 2, "t_ini": 13.0}]],
    )


def _caminho_sem_marcador() -> dict:
    return _dados(_SEM_MARCADOR, [])


def _formas(dados: dict) -> dict:
    """As chaves de cada bloco do JSON (o contrato de forma, sem valores).

    Passagens e ``t_ini`` mudam de conteúdo por design quando não há tempo; o que tem
    de ser igual é a estrutura de cada registro.
    """
    return {
        "raiz": sorted(dados),
        "video": sorted(dados["video"]),
        "gerado_por": sorted(dados["gerado_por"]),
        "tela": sorted(dados["telas"][0]),
        "tempo_tela": sorted(dados["telas"][0]["tempo"]),
        "exibicao": sorted(dados["telas"][0]["exibicoes"][0]),
        "tempo_exibicao": sorted(dados["telas"][0]["exibicoes"][0]["tempo"]),
        "nota": sorted(dados["notas"][0]),
        "nao_nota": sorted(dados["nao_notas"][0]),
        "resumo": sorted(dados["resumo"]),
    }


@pytest.mark.parametrize(
    "caminho", [_caminho_posicao, _caminho_cor, _caminho_sem_marcador]
)
def test_os_tres_caminhos_validam(caminho) -> None:
    """Com posição, com cor e sem marcador, o JSON é válido e a régua do esquema passa."""
    assert validar(caminho()) == []


def test_forma_e_a_mesma_nos_tres_caminhos() -> None:
    """A forma (chaves e tipos) não muda com o observador; só os valores mudam."""
    formas = [
        _formas(c()) for c in (_caminho_posicao, _caminho_cor, _caminho_sem_marcador)
    ]
    assert formas[0] == formas[1] == formas[2]


def test_sem_marcador_nao_inventa_tempo() -> None:
    """Sem tempo medido, toda nota sai com ``t_ini`` nulo e nenhuma passagem existe."""
    dados = _caminho_sem_marcador()
    assert all(n["t_ini"] is None and n["exibicao"] is None for n in dados["notas"])
    assert dados["resumo"]["notas_com_tempo"] == 0
    assert dados["telas"][0]["exibicoes"][0]["passagens"] == []


def test_esquema_errado_e_recusado() -> None:
    dados = _caminho_posicao()
    dados["esquema"] = "chorinho/video@0"
    assert any("esquema" in e for e in validar(dados))


def test_bloco_faltando_e_recusado() -> None:
    dados = _caminho_posicao()
    del dados["resumo"]
    assert any("resumo" in e for e in validar(dados))


def test_raiz_que_nao_e_objeto_nao_levanta() -> None:
    assert validar([]) == ["raiz não é um objeto"]


def test_t_ini_fora_da_exibicao_e_recusado() -> None:
    dados = _caminho_posicao()
    dados["telas"][0]["exibicoes"][0]["passagens"][0][0]["t_ini"] = 25.0
    dados["notas"][0]["t_ini"] = 25.0
    erros = validar(dados)
    assert any("fora de" in e for e in erros)


def test_t_ini_sem_exibicao_e_recusado() -> None:
    dados = _caminho_posicao()
    dados["notas"][0]["exibicao"] = None
    assert any("sem exibicao" in e for e in validar(dados))


def test_nota_com_t_ini_que_a_passagem_nao_tem_e_recusada() -> None:
    dados = _caminho_posicao()
    dados["notas"][0]["t_ini"] = 11.7
    assert any("difere do da passagem" in e for e in validar(dados))


def test_medido_false_sem_motivo_e_recusado() -> None:
    dados = _caminho_sem_marcador()
    dados["telas"][0]["exibicoes"][0]["tempo"]["motivo"] = ""
    assert any("medido false sem motivo" in e for e in validar(dados))


def test_sem_tempo_com_passagens_e_recusado() -> None:
    dados = _caminho_sem_marcador()
    dados["telas"][0]["exibicoes"][0]["passagens"] = [[{"coluna": 1, "t_ini": 11.0}]]
    assert any("sem tempo medido mas com passagens" in e for e in validar(dados))


def test_onsets_decrescentes_sao_recusados() -> None:
    dados = _caminho_posicao()
    passagem = dados["telas"][0]["exibicoes"][0]["passagens"][0]
    passagem[0]["t_ini"], passagem[1]["t_ini"] = 13.0, 11.0
    assert any("onsets decrescem" in e for e in validar(dados))


def test_casa_e_corda_fora_do_intervalo_sao_recusadas() -> None:
    dados = _caminho_posicao()
    dados["notas"][0]["casa"] = 30
    dados["notas"][1]["corda"] = 7
    erros = validar(dados)
    assert any("casa 30" in e for e in erros)
    assert any("corda 7" in e for e in erros)


def test_resumo_que_nao_bate_e_recusado() -> None:
    dados = _caminho_posicao()
    dados["resumo"]["notas"] = 999
    assert any("resumo.notas" in e for e in validar(dados))


def test_nota_repetida_na_mesma_passagem_e_recusada() -> None:
    dados = _caminho_posicao()
    dados["notas"].append(copy.deepcopy(dados["notas"][0]))
    dados["resumo"]["notas"] = len(dados["notas"])
    dados["resumo"]["notas_com_tempo"] = sum(
        1 for n in dados["notas"] if n["t_ini"] is not None
    )
    assert any("repetida" in e for e in validar(dados))


def test_entrada_malformada_nao_levanta_excecao() -> None:
    dados = _caminho_posicao()
    dados["notas"][0]["tela"] = [1]
    dados["notas"][1]["passagem"] = {"x": 1}
    dados["telas"][0]["exibicoes"][0]["passagens"][0][0]["t_ini"] = "a"
    assert validar(dados)


def _rodar_cli(monkeypatch, dados: dict, destino: Path) -> int:
    """Roda a CLI com o motor trocado por ``dados``, sem vídeo e sem modelo."""
    monkeypatch.setattr(cli, "transcrever_video", lambda *a, **k: dados)
    monkeypatch.setattr(
        sys, "argv", ["tab.transcrever", "video.mp4", "--json", str(destino)]
    )
    return cli.main()


def test_cli_recusa_esquema_invalido_e_nao_grava(monkeypatch, tmp_path) -> None:
    """Falha alta: erro de esquema sai com código 1 e nenhum JSON é gravado."""
    dados = _caminho_posicao()
    dados["notas"][0]["t_ini"] = 99.0
    destino = tmp_path / "saida.json"
    assert _rodar_cli(monkeypatch, dados, destino) == 1
    assert not destino.exists()


def test_cli_grava_o_json_quando_o_esquema_passa(monkeypatch, tmp_path) -> None:
    destino = tmp_path / "sub" / "saida.json"
    assert _rodar_cli(monkeypatch, _caminho_posicao(), destino) == 0
    assert validar(json.loads(destino.read_text(encoding="utf-8"))) == []


_REAL = SAIDA / "fase5" / "mvp.json"


@pytest.mark.skipif(not _REAL.exists(), reason="saída real ausente nesta cópia")
def test_saida_real_do_motor_valida() -> None:
    """O JSON que o motor gravou no retrato (Fase 5) passa no esquema, sem erro."""
    dados = json.loads(_REAL.read_text(encoding="utf-8"))
    assert dados["esquema"] == ESQUEMA
    assert validar(dados) == []
