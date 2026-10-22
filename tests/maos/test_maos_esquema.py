"""Testes do esquema ``chorinho/maos@1`` (``tab.maos_esquema``).

Sintéticos: sem acervo, sem GPU e sem ``data/saida``. O par válido mínimo tem três
eventos (ouro, prata e recusado sem janela) e um denso de 40 quadros em 1920x1080, com
mãos ausentes e quadros em que o braço não foi achado. Cada teste quebra uma regra
da decisão 1007 com ``copy.deepcopy`` e confere a mensagem da regra quebrada.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tab.maos.esquema import (
    ESQUEMA,
    carregar,
    main,
    nivel_esperado,
    validar_denso,
    validar_json,
    validar_par,
)

_N = 40
_LARGURA = 1920
_ALTURA = 1080


def _checagens(k1: object, k2: object, k3: object, k4: object) -> dict:
    """Checagens K1 a K4 com ``passou`` dado e um ``valor`` fixo.

    Args:
        k1: ``passou`` de K1.
        k2: ``passou`` de K2.
        k3: ``passou`` de K3.
        k4: ``passou`` de K4.

    Returns:
        O dicionário ``checagens`` de um evento.
    """
    passou = {"K1": k1, "K2": k2, "K3": k3, "K4": k4}
    return {chave: {"passou": valor, "valor": 0.5} for chave, valor in passou.items()}


def _denso_valido() -> dict[str, np.ndarray]:
    """Denso de 40 quadros: mãos com ausências, braço com quadros sem achado.

    Returns:
        As matrizes do ``.npz``, por nome, com forma e dtype da decisão 1007.
    """
    pts = np.arange(_N, dtype=np.float64) / 15.0
    origem = np.full((_N, 2), 1, dtype=np.int8)
    origem[::7, 1] = 0
    origem[3, 0] = 0
    ids = np.array([1, 2], dtype=np.int16)
    trilha = np.where(origem == 0, -1, ids).astype(np.int16)
    maos = np.full((_N, 2, 21, 3), np.nan, dtype=np.float32)
    k = np.arange(21, dtype=np.float32)
    for i in range(_N):
        for h in range(2):
            if origem[i, h] != 0:
                maos[i, h, :, 0] = 200 + 50 * h + i + 5 * k
                maos[i, h, :, 1] = 300 + 4 * k + 0.5 * i
                maos[i, h, :, 2] = 0.9
    corpo = np.empty((_N, 6, 3), dtype=np.float32)
    j = np.arange(6, dtype=np.float32)
    corpo[..., 0] = 800 + 10 * j
    corpo[..., 1] = 500 + 10 * j
    corpo[..., 2] = 0.8
    corpo[:5, 5, :] = np.nan
    achou = np.ones(_N, dtype=np.bool_)
    achou[[2, 9, 30]] = False
    sem = ~achou
    trastes = np.empty((_N, 25, 2), dtype=np.float32)
    kt = np.arange(25, dtype=np.float32)
    trastes[..., 0] = 400 + 20 * kt
    trastes[..., 1] = 950 - 10 * kt
    trastes[sem] = np.nan
    corda1 = np.broadcast_to(
        np.array([[300, 400], [1500, 420]], dtype=np.float32), (_N, 2, 2)
    ).copy()
    corda1[sem] = np.nan
    corda6 = np.broadcast_to(
        np.array([[320, 900], [1520, 930]], dtype=np.float32), (_N, 2, 2)
    ).copy()
    corda6[sem] = np.nan
    conf = np.full(_N, 0.7, dtype=np.float32)
    conf[sem] = np.nan
    caixa = np.broadcast_to(
        np.array([600, 700, 1800, 1000], dtype=np.float32), (_N, 4)
    ).copy()
    caixa[:10] = np.nan
    return {
        "pts": pts,
        "maos": maos,
        "maos_origem": origem,
        "maos_trilha": trilha,
        "corpo": corpo,
        "braco_trastes": trastes,
        "braco_corda1": corda1,
        "braco_corda6": corda6,
        "braco_conf": conf,
        "braco_achou": achou,
        "tab_caixa": caixa,
    }


def _doc_valido() -> dict:
    """JSON mínimo válido com três eventos (ouro, prata e recusado sem janela).

    Returns:
        O dicionário de ``<nome>.maos.json``, já como o leitor o veria.
    """
    ouro = {
        "tela": 1,
        "passagem": 1,
        "exibicao": 0,
        "coluna": 3,
        "corda": 2,
        "t_ini": 245.011,
        "casa": 5,
        "t_som": 245.19,
        "janela": [4, 12],
        "checagens": _checagens(True, True, True, True),
        "nivel": "ouro",
        "motivo": None,
    }
    prata = {
        "tela": 1,
        "passagem": 1,
        "exibicao": 0,
        "coluna": 4,
        "corda": 3,
        "t_ini": 246.0,
        "casa": 2,
        "t_som": 246.1,
        "janela": [12, 20],
        "checagens": _checagens(True, False, True, True),
        "nivel": "prata",
        "motivo": None,
    }
    recusado = {
        "tela": 1,
        "passagem": 1,
        "exibicao": 0,
        "coluna": 5,
        "corda": 1,
        "t_ini": 247.4,
        "casa": 7,
        "t_som": 247.5,
        "janela": None,
        "checagens": _checagens(True, None, None, True),
        "nivel": "recusado",
        "motivo": "sem janela de quadros",
    }
    return {
        "esquema": ESQUEMA,
        "produto": "data/saida/x.json",
        "produto_sha256": "a" * 64,
        "audio": "data/saida/x.audio.json",
        "audio_sha256": "b" * 64,
        "denso": "x.maos.npz",
        "denso_sha256": "c" * 64,
        "video": {
            "arquivo": "sky guitar/x.mp4",
            "fps": 29.97,
            "largura": _LARGURA,
            "altura": _ALTURA,
        },
        "gerado_por": {
            "commit": "abc1234",
            "detector_maos": "wholebody",
            "detector_braco": "gabarito",
            "parametros": {},
        },
        "violao": {"canhoto": False, "capotraste": 0, "capotraste_fonte": "canal"},
        "eventos": [ouro, prata, recusado],
        "resumo": {
            "eventos": 3,
            "ouro": 1,
            "prata": 1,
            "recusado": 1,
            "motivos": {"sem janela de quadros": 1},
        },
    }


_DOC = _doc_valido()
_DENSO = _denso_valido()


def _par() -> tuple[dict, dict[str, np.ndarray]]:
    """Cópia independente do par válido, para quebrar uma regra por teste.

    Returns:
        ``(doc, arr)`` copiados com ``copy.deepcopy``.
    """
    return copy.deepcopy(_DOC), copy.deepcopy(_DENSO)


def _ev(doc: dict, i: int) -> dict:
    """Evento ``i`` do documento, para mutar nos casos.

    Args:
        doc: o JSON.
        i: posição do evento.

    Returns:
        O dicionário do evento.
    """
    return doc["eventos"][i]


def test_par_valido_nao_tem_erro() -> None:
    """O par mínimo válido dá lista vazia (e não só o JSON ou só o denso)."""
    doc, arr = _par()
    assert validar_json(doc) == []
    assert validar_denso(arr, _LARGURA, _ALTURA) == []
    assert validar_par(doc, arr) == []


def test_nivel_esperado_combinacoes_principais() -> None:
    """Ouro, prata e recusado conforme a decisão 1007."""
    assert nivel_esperado(_checagens(True, True, True, True)) == "ouro"
    assert nivel_esperado(_checagens(True, False, True, True)) == "prata"
    assert nivel_esperado(_checagens(True, None, True, True)) == "prata"
    assert nivel_esperado(_checagens(False, True, True, True)) == "recusado"
    assert nivel_esperado(_checagens(True, True, True, None)) == "recusado"
    assert nivel_esperado(_checagens(True, True, False, True)) == "recusado"
    assert nivel_esperado(_checagens(True, True, None, True)) == "recusado"


#: (mutação, trecho esperado na mensagem). Cada mutação quebra só a regra indicada.
_CASOS_JSON = [
    pytest.param(
        lambda d, a: d.update(esquema="chorinho/maos@2"), "esquema", id="esquema"
    ),
    pytest.param(lambda d, a: d.pop("denso_sha256"), "falta o campo", id="ausente"),
    pytest.param(
        lambda d, a: d.update(produto_sha256="abc"),
        "produto_sha256",
        id="hash-curto",
    ),
    pytest.param(
        lambda d, a: d.update(denso_sha256="A" * 64),
        "denso_sha256",
        id="hash-maiusculo",
    ),
    pytest.param(
        lambda d, a: d.update(audio=None),
        "nulos juntos",
        id="audio-null-sha-nao",
    ),
    pytest.param(
        lambda d, a: d["violao"].update(canhoto="não"),
        "canhoto",
        id="canhoto-texto",
    ),
    pytest.param(
        lambda d, a: d["violao"].update(capotraste=13),
        "capotraste deve ser",
        id="capotraste-acima-de-12",
    ),
    pytest.param(
        lambda d, a: d["violao"].update(capotraste=True),
        "capotraste deve ser",
        id="capotraste-bool",
    ),
    pytest.param(
        lambda d, a: d["violao"].update(capotraste=None),
        "capotraste_fonte deve ser null",
        id="capotraste-null-com-fonte",
    ),
    pytest.param(
        lambda d, a: d["violao"].update(capotraste_fonte="outra"),
        "capotraste_fonte",
        id="fonte-desconhecida",
    ),
    pytest.param(
        lambda d, a: _ev(d, 0).update(corda=0), "corda inválido", id="corda-zero"
    ),
    pytest.param(lambda d, a: _ev(d, 0).update(casa=25), "casa inválido", id="casa-25"),
    pytest.param(
        lambda d, a: _ev(d, 0).update(casa=True), "casa inválido", id="casa-bool"
    ),
    pytest.param(
        lambda d, a: _ev(d, 0).update(t_ini="245"), "t_ini inválido", id="t-ini-texto"
    ),
    pytest.param(
        lambda d, a: _ev(d, 0).update(janela=[10, 10]),
        "janela inválido",
        id="janela-i0-igual-i1",
    ),
    pytest.param(
        lambda d, a: _ev(d, 2)["checagens"]["K3"].update(passou=True),
        "janela null, mas K3",
        id="janela-null-com-k3-true",
    ),
    pytest.param(
        lambda d, a: _ev(d, 2).update(t_som=None),
        "t_som null, mas K1",
        id="t-som-null-com-k1-true",
    ),
    pytest.param(
        lambda d, a: d["eventos"].append(copy.deepcopy(d["eventos"][0])),
        "chave repetida",
        id="chave-repetida",
    ),
    pytest.param(
        lambda d, a: _ev(d, 0)["checagens"].pop("K4"),
        "checagens devem ser exatamente",
        id="checagens-sem-k4",
    ),
    pytest.param(
        lambda d, a: _ev(d, 0)["checagens"]["K1"].update(passou="sim"),
        "K1.passou deve ser",
        id="passou-texto",
    ),
    pytest.param(
        lambda d, a: _ev(d, 0)["checagens"]["K1"].update(valor=True),
        "K1.valor deve ser",
        id="valor-bool",
    ),
    pytest.param(
        lambda d, a: _ev(d, 1).update(nivel="ouro", motivo=None),
        "mas as checagens dão 'prata'",
        id="nivel-diferente-das-checagens",
    ),
    pytest.param(
        lambda d, a: _ev(d, 1).update(nivel="bronze"),
        "nivel 'bronze' desconhecido",
        id="nivel-desconhecido",
    ),
    pytest.param(
        lambda d, a: _ev(d, 2).update(motivo="  "),
        "recusado sem motivo",
        id="motivo-vazio-no-recusado",
    ),
    pytest.param(
        lambda d, a: _ev(d, 0).update(motivo="sobrou"),
        "ouro com motivo",
        id="motivo-no-ouro",
    ),
    pytest.param(
        lambda d, a: d["resumo"].update(ouro=2), "resumo.ouro", id="resumo-ouro"
    ),
    pytest.param(
        lambda d, a: d["resumo"].update(eventos=True),
        "resumo.eventos",
        id="resumo-eventos-bool",
    ),
    pytest.param(
        lambda d, a: d["resumo"].update(motivos={"outro": 1}),
        "resumo.motivos",
        id="resumo-motivos",
    ),
    pytest.param(lambda d, a: d.pop("resumo"), "falta o campo", id="resumo-ausente"),
    pytest.param(
        lambda d, a: d.update(eventos="x"), "eventos não é lista", id="eventos-texto"
    ),
    pytest.param(
        lambda d, a: d["video"].update(largura=0),
        "video.largura",
        id="video-largura-zero",
    ),
]


def _mudar_maos_origem(arr: dict) -> None:
    """Origem 3 num quadro (valor fora de 0, 1 e 2).

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["maos_origem"][4, 0] = 3


def _mudar_trilha(arr: dict) -> None:
    """Mão ausente (origem 0) com id de trilha 7, em vez de −1.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["maos_trilha"][3, 0] = 7


def _mudar_mao_ausente_com_pontos(arr: dict) -> None:
    """Mão com origem 0 e pontos preenchidos.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["maos"][3, 0] = 1.0


def _mudar_mao_presente_com_nan(arr: dict) -> None:
    """Mão presente com um ponto NaN.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["maos"][5, 1, 4, 0] = np.nan


def _mudar_pts_decrescente(arr: dict) -> None:
    """``pts`` na ordem inversa.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["pts"] = arr["pts"][::-1].copy()


def _mudar_braco_achou_int(arr: dict) -> None:
    """``braco_achou`` com dtype int8 em vez de bool.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["braco_achou"] = arr["braco_achou"].astype(np.int8)


def _mudar_caixa_invertida(arr: dict) -> None:
    """Caixa com x0 maior que x1 num quadro.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["tab_caixa"][20] = [1800, 700, 600, 1000]


def _mudar_caixa_pela_metade(arr: dict) -> None:
    """Caixa com y0 NaN e os outros valores finitos.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["tab_caixa"][20, 1] = np.nan


def _mudar_corda1_infinita(arr: dict) -> None:
    """Coordenada infinita na corda 1.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["braco_corda1"][6, 0, 0] = np.inf


def _mudar_braco_conf_sem_achou(arr: dict) -> None:
    """Confiança finita num quadro em que o braço não foi achado.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["braco_conf"][2] = 0.5


def _mudar_braco_conf_nan_com_achou(arr: dict) -> None:
    """Confiança NaN num quadro em que o braço foi achado.

    Args:
        arr: as matrizes do denso, mutadas no lugar.
    """
    arr["braco_conf"][4] = np.nan


#: (mutação do denso, trecho esperado). Cada mutação quebra só a regra indicada.
_CASOS_DENSO = [
    pytest.param(
        lambda a: a.pop("braco_conf"),
        "faltam as matrizes braco_conf",
        id="matriz-ausente",
    ),
    pytest.param(
        lambda a: a.update(extra=np.zeros(_N)),
        "desconhecidas extra",
        id="matriz-extra",
    ),
    pytest.param(
        lambda a: a.update(maos=a["maos"].astype(np.float64)),
        "maos: dtype",
        id="dtype-errado",
    ),
    pytest.param(
        lambda a: a.update(corpo=a["corpo"][:, :5]),
        "corpo: forma",
        id="forma-errada",
    ),
    pytest.param(
        lambda a: a.update(braco_conf=a["braco_conf"][:39]),
        "braco_conf: forma",
        id="N-diferente",
    ),
    pytest.param(_mudar_braco_achou_int, "braco_achou: dtype", id="achou-nao-bool"),
    pytest.param(
        _mudar_pts_decrescente,
        "não é estritamente crescente",
        id="pts-decrescente",
    ),
    pytest.param(
        lambda a: a["pts"].__setitem__(5, np.nan),
        "pts: há valores não finitos",
        id="pts-nan",
    ),
    pytest.param(_mudar_maos_origem, "valor fora de 0, 1 e 2", id="origem-3"),
    pytest.param(
        _mudar_trilha,
        "origem e trilha discordando",
        id="origem-0-com-trilha",
    ),
    pytest.param(
        _mudar_mao_ausente_com_pontos,
        "origem 0 e pontos não NaN",
        id="origem-0-com-pontos",
    ),
    pytest.param(
        _mudar_mao_presente_com_nan,
        "origem presente e algum ponto NaN",
        id="origem-presente-com-nan",
    ),
    pytest.param(
        lambda a: a["maos"][5, 1, :, 0].__setitem__(slice(None), 2100),
        "maos: 1 quadro com ponto fora do quadro",
        id="maos-fora-do-quadro",
    ),
    pytest.param(
        lambda a: a["maos"][5, 1, :, 0].__setitem__(slice(None), -200),
        "maos: 1 quadro com ponto fora do quadro",
        id="maos-fora-esquerda",
    ),
    pytest.param(
        lambda a: a["corpo"][7, 2].__setitem__(1, 1200),
        "corpo: 1 quadro com ponto fora do quadro",
        id="corpo-fora-embaixo",
    ),
    pytest.param(
        _mudar_corda1_infinita,
        "braco_corda1: 1 quadro com valor infinito",
        id="corda1-infinita",
    ),
    pytest.param(
        lambda a: a["maos"].__setitem__((5, 1, slice(None), 2), 1.5),
        "maos: 1 quadro com score fora de [0, 1]",
        id="score-maos-acima-de-1",
    ),
    pytest.param(
        lambda a: a["braco_trastes"].__setitem__((5, 3, 0), 5000),
        "braco_trastes: 1 quadro com ponto fora do quadro",
        id="trastes-fora-do-quadro",
    ),
    pytest.param(
        lambda a: a["tab_caixa"].__setitem__((20, 2), 2500),
        "tab_caixa: 1 quadro com canto fora do quadro",
        id="caixa-fora-do-quadro",
    ),
    pytest.param(
        lambda a: a["corpo"].__setitem__((7, 0, 2), -0.1),
        "corpo: 1 quadro com score fora de [0, 1]",
        id="score-corpo-negativo",
    ),
    pytest.param(
        _mudar_braco_conf_sem_achou,
        "sem braço achado e confiança não NaN",
        id="conf-sem-achou",
    ),
    pytest.param(
        _mudar_braco_conf_nan_com_achou,
        "com braço achado e confiança fora de [0, 1] ou NaN",
        id="conf-nan-com-achou",
    ),
    pytest.param(
        lambda a: a["braco_conf"].__setitem__(4, 1.2),
        "com braço achado e confiança fora de [0, 1]",
        id="conf-acima-de-1",
    ),
    pytest.param(_mudar_caixa_invertida, "x0 ≥ x1 ou y0 ≥ y1", id="caixa-invertida"),
    pytest.param(
        _mudar_caixa_pela_metade,
        "com coordenadas NaN pela metade",
        id="caixa-pela-metade",
    ),
]


@pytest.mark.parametrize(("mutar", "trecho"), _CASOS_JSON)
def test_regra_do_json(mutar: object, trecho: str) -> None:
    """Cada regra do ``.maos.json`` quebrada aparece como erro.

    Args:
        mutar: função que quebra só a regra, sobre a cópia do par.
        trecho: texto que a mensagem do erro tem de conter.
    """
    doc, arr = _par()
    mutar(doc, arr)
    erros = validar_par(doc, arr)
    assert any(trecho in erro for erro in erros), erros


@pytest.mark.parametrize(("mutar", "trecho"), _CASOS_DENSO)
def test_regra_do_denso(mutar: object, trecho: str) -> None:
    """Cada regra do ``.maos.npz`` quebrada aparece como erro.

    Args:
        mutar: função que quebra só a regra, sobre a cópia do denso.
        trecho: texto que a mensagem do erro tem de conter.
    """
    _doc, arr = _par()
    mutar(arr)
    erros = validar_denso(arr, _LARGURA, _ALTURA)
    assert any(trecho in erro for erro in erros), erros


def test_janela_passa_de_n() -> None:
    """Janela com i1 maior que N (= 40) é erro do par, não do JSON isolado."""
    doc, arr = _par()
    _ev(doc, 0)["janela"] = [30, 41]
    assert validar_json(doc) == []
    erros = validar_par(doc, arr)
    assert any("passa de N = 40" in erro for erro in erros), erros


def test_denso_contra_dimensoes_do_video() -> None:
    """Com um quadro menor no ``video``, o denso sai fora e o par acusa."""
    doc, arr = _par()
    doc["video"]["largura"] = 1280
    erros = validar_par(doc, arr)
    assert any("fora do quadro" in erro for erro in erros), erros


def test_origem_zero_em_varios_quadros_vira_uma_mensagem() -> None:
    """Uma regra violada em vários quadros gera uma mensagem, com a contagem."""
    _doc, arr = _par()
    arr["maos"][[0, 7, 14], 1] = 1.0
    erros = validar_denso(arr, _LARGURA, _ALTURA)
    assert len(erros) == 1, erros
    assert erros[0].startswith("maos: 3 quadros com origem 0"), erros[0]
    assert "(primeiro: 0)" in erros[0]


def test_entrada_malformada_nao_lanca() -> None:
    """Validadores devolvem lista de erros, e não exceção, para lixo."""
    for doc, arr in (
        (None, {}),
        ({}, {}),
        ([], None),
        (_par()[0], {"pts": np.zeros(3)}),
        (_par()[0], {"pts": np.zeros((0,))}),
    ):
        erros = validar_par(doc, arr)
        assert isinstance(erros, list)
        assert erros, (doc, arr)


def test_carregar_e_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``carregar`` lê o par; a CLI dá 0 com sha certo e 1 com sha errado."""
    doc, arr = _par()
    npz = tmp_path / "x.maos.npz"
    np.savez(npz, **arr)
    doc["denso"] = "x.maos.npz"
    doc["denso_sha256"] = hashlib.sha256(npz.read_bytes()).hexdigest()
    caminho = tmp_path / "x.maos.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")

    doc_lido, arr_lido = carregar(caminho)
    assert set(arr_lido) == set(arr)
    assert validar_par(doc_lido, arr_lido) == []

    assert main([str(caminho)]) == 0
    assert capsys.readouterr().out.strip() == "ok"

    doc["denso_sha256"] = "0" * 64
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    assert main([str(caminho)]) == 1
    assert "denso_sha256" in capsys.readouterr().out


def test_cli_rejeita_json_com_nan_e_arquivo_ausente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """NaN no JSON e arquivo inexistente são erro de leitura: código 1, sem exceção."""
    ruim = tmp_path / "ruim.maos.json"
    ruim.write_text('{"denso": "x.npz", "v": NaN}', encoding="utf-8")
    assert main([str(ruim)]) == 1
    assert main([str(tmp_path / "nao_existe.maos.json")]) == 1
    capsys.readouterr()
