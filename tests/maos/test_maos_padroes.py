"""Testes da ferramenta dos padrões da mão direita (M5), formato 2: confirmação e servidor."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tab.maos.padroes import (
    confirmar_compasso,
    criar_servidor,
    gabarito_novo,
    mesclar_gabarito,
    ordem_da_pagina,
    ordem_dos_pendentes,
    progresso,
    proximo_pendente,
    validar_dedos,
    validar_obs,
    vista_do_item,
)


def _notas(*cordas_casas_tempos):
    """Notas do compasso: (corda, casa, t_ini) em tuplas."""
    return [{"corda": c, "casa": k, "t_ini": t} for c, k, t in cordas_casas_tempos]


# Compasso com uma nota só em cada ataque: o palpite da regra é o padrão da corda.
NOTAS_A = _notas((3, 4, 1.0), (3, 5, 1.5), (3, 6, 2.0))  # i, m, a
NOTAS_B = _notas((6, 0, 1.0), (4, 0, 1.0), (3, 2, 1.0))  # p, i(exceção), m

ITENS = [
    {
        "id": "c01",
        "video": "v1.mp4",
        "tela": 1,
        "compasso": 2,
        "exibicao": 0,
        "janela": [0.7, 3.0],
        "n_notas": 3,
        "notas": NOTAS_A,
        "na_pagina": True,
    },
    {
        "id": "c02",
        "video": "v1.mp4",
        "tela": 1,
        "compasso": 3,
        "exibicao": 0,
        "janela": [0.7, 3.0],
        "n_notas": 3,
        "notas": NOTAS_B,
        "na_pagina": False,
    },
    {
        "id": "c03",
        "video": "v2.mp4",
        "tela": 4,
        "compasso": 5,
        "exibicao": 1,
        "janela": [0.7, 3.0],
        "n_notas": 3,
        "notas": NOTAS_A,
        "na_pagina": True,
    },
]


# ---------------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------------


def test_validar_dedos_aceita_lista_do_tamanho_das_notas():
    assert validar_dedos(["p", "i", "m"], 3) == ["p", "i", "m"]


@pytest.mark.parametrize(
    ("donos", "n"),
    [
        (["p", "i"], 3),  # tamanho errado
        (["p", "i", "x"], 3),  # dedo fora do vocabulário
        ("pim", 3),  # não é lista
        (["p", "?", "m"], 3),  # "?" não existe aqui: o dono confirma ou troca
        (["p", "L", "m"], 3),  # maiúscula não é o valor "l"
    ],
)
def test_validar_dedos_recusa_o_que_nao_bate(donos, n):
    with pytest.raises(ValueError):
        validar_dedos(donos, n)


def test_validar_dedos_aceita_l_ligada():
    assert validar_dedos(["p", "l", "m"], 3) == ["p", "l", "m"]


def test_confirmar_com_l_grava_ligada_e_conta_como_troca():
    gab = gabarito_novo(ITENS, 1)
    reg = confirmar_compasso(gab, "c01", NOTAS_A, ["i", "l", "a"], None, "agora")
    assert reg["dedos"][1]["dono"] == "l"
    assert reg["dedos"][1]["palpite"] == "m"  # a regra nunca dá "l"
    assert reg["alteradas"] == 1


def test_validar_obs_limpa_vazio_e_limita_tamanho():
    assert validar_obs("  ") is None
    assert validar_obs(None) is None
    assert validar_obs(" ok ") == "ok"
    with pytest.raises(ValueError):
        validar_obs("x" * 501)
    with pytest.raises(ValueError):
        validar_obs(3)


# ---------------------------------------------------------------------------------
# Confirmação, progresso e página
# ---------------------------------------------------------------------------------


def test_confirmar_sem_trocar_da_alteradas_zero_e_grava_palpite():
    gab = gabarito_novo(ITENS, 1)
    reg = confirmar_compasso(gab, "c01", NOTAS_A, ["i", "m", "a"], None, "agora")
    assert reg["confirmado"] is True
    assert reg["alteradas"] == 0
    assert [d["palpite"] for d in reg["dedos"]] == ["i", "m", "a"]
    assert reg["dedos"][0]["dono"] == "i" and reg["dedos"][0]["regra"]
    assert reg["respondido_em"] == "agora"


def test_confirmar_conta_trocas_contra_o_palpite():
    gab = gabarito_novo(ITENS, 1)
    reg = confirmar_compasso(gab, "c02", NOTAS_B, ["p", "m", "m"], "rápido", "agora")
    # palpite da regra: p, i (exceção do bordão), m. Trocou a 2ª (i -> m)
    assert reg["alteradas"] == 1
    assert reg["obs"] == "rápido"


def test_confirmar_recusa_dedo_invalido_sem_mexer_no_gabarito():
    gab = gabarito_novo(ITENS, 1)
    with pytest.raises(ValueError):
        confirmar_compasso(gab, "c01", NOTAS_A, ["i", "x", "a"], None, "agora")
    assert gab["itens"]["c01"]["confirmado"] is False
    assert gab["itens"]["c01"]["dedos"] == []


def test_ordem_da_pagina_so_tem_os_marcados():
    assert ordem_da_pagina(ITENS) == ["c01", "c03"]


def test_ordem_dos_pendentes_tira_os_confirmados_na_ordem_do_indice():
    gab = gabarito_novo(ITENS, 1)
    assert ordem_dos_pendentes(ITENS, gab) == ["c01", "c02", "c03"]
    confirmar_compasso(gab, "c02", NOTAS_B, ["p", "i", "m"], None, "agora")
    assert ordem_dos_pendentes(ITENS, gab) == ["c01", "c03"]


def test_criar_servidor_recusa_pagina_desconhecida(tmp_path: Path):
    with pytest.raises(ValueError):
        criar_servidor(tmp_path, tmp_path / "g.json", pagina="todas")


def test_progresso_conta_so_a_pagina():
    gab = gabarito_novo(ITENS, 1)
    confirmar_compasso(gab, "c01", NOTAS_A, ["i", "m", "a"], None, "agora")
    assert progresso(gab, ["c01", "c03"]) == (1, 2)


def test_proximo_pendente_da_a_volta_e_nao_devolve_o_atual():
    gab = gabarito_novo(ITENS, 1)
    ordem = ["c01", "c03"]
    assert proximo_pendente(ordem, gab, "c01") == "c03"
    assert proximo_pendente(ordem, gab, "c03") == "c01"
    confirmar_compasso(gab, "c01", NOTAS_A, ["i", "m", "a"], None, "agora")
    confirmar_compasso(gab, "c03", NOTAS_A, ["i", "m", "a"], None, "agora")
    assert proximo_pendente(ordem, gab, "c01") is None


def test_vista_do_item_traz_palpite_e_regra_por_nota():
    vista = vista_do_item(ITENS[1])
    assert [n["palpite"] for n in vista["notas"]] == ["p", "i", "m"]
    assert vista["notas"][1]["regra"]
    assert "dedos" not in vista


# ---------------------------------------------------------------------------------
# Mesclagem: nunca apaga confirmação
# ---------------------------------------------------------------------------------


def test_mesclar_preserva_confirmacao_do_disco():
    existente = gabarito_novo(ITENS, 1)
    confirmar_compasso(existente, "c01", NOTAS_A, ["i", "a", "a"], "ok", "agora")
    novo = mesclar_gabarito(gabarito_novo(ITENS, 1), existente)
    assert novo["itens"]["c01"]["confirmado"] is True
    assert novo["itens"]["c01"]["dedos"][1]["dono"] == "a"
    assert novo["itens"]["c01"]["alteradas"] == 1
    assert novo["itens"]["c03"]["confirmado"] is False


def test_mesclar_recusa_formato_antigo_sem_migrar():
    with pytest.raises(ValueError):
        mesclar_gabarito(gabarito_novo(ITENS, 1), {"formato": 1, "itens": {}})


def test_mesclar_recusa_confirmacao_de_outro_compasso():
    existente = gabarito_novo(ITENS, 1)
    confirmar_compasso(existente, "c01", NOTAS_A, ["i", "m", "a"], None, "agora")
    existente["itens"]["c01"]["compasso"] = 99
    with pytest.raises(ValueError):
        mesclar_gabarito(gabarito_novo(ITENS, 1), existente)


# ---------------------------------------------------------------------------------
# Servidor (HTTP real, em pasta temporária, sem acervo)
# ---------------------------------------------------------------------------------


@pytest.fixture
def servidor(tmp_path: Path):
    """Servidor sobre uma pasta de teste; devolve (url, caminho do gabarito)."""
    pasta = tmp_path / "padroes"
    (pasta / "c01").mkdir(parents=True)
    (pasta / "c01" / "clipe.mp4").write_bytes(bytes(range(256)) * 4)
    (pasta / "indice.json").write_text(
        json.dumps({"semente": 1, "itens": ITENS}), encoding="utf-8"
    )
    ouro = tmp_path / "padroes_direita.json"
    ouro.write_text(json.dumps(gabarito_novo(ITENS, 1)), encoding="utf-8")
    srv = criar_servidor(pasta, ouro, porta=0, host="127.0.0.1")
    fio = threading.Thread(target=srv.serve_forever, daemon=True)
    fio.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", ouro
    srv.shutdown()
    srv.server_close()


def _post(url: str, corpo: dict) -> dict:
    """POST JSON em ``/confirmar``; devolve a resposta decodificada."""
    pedido = urllib.request.Request(
        url + "/confirmar",
        data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(pedido) as resp:
        return json.loads(resp.read())


def test_servidor_grava_no_disco_e_avanca_para_o_pendente(servidor):
    url, ouro = servidor
    resp = _post(url, {"id": "c01", "dedos": ["i", "m", "a"], "obs": None})
    assert resp["alteradas"] == 0
    assert resp["confirmados"] == 1 and resp["total"] == 2
    assert resp["proximo"] == "c03"
    gravado = json.loads(ouro.read_text(encoding="utf-8"))
    assert gravado["itens"]["c01"]["confirmado"] is True


def test_servidor_conta_trocas_e_mantem_os_valores(servidor):
    url, ouro = servidor
    resp = _post(url, {"id": "c01", "dedos": ["i", "a", "a"], "obs": "troquei"})
    assert resp["alteradas"] == 1
    gravado = json.loads(ouro.read_text(encoding="utf-8"))
    dedos = gravado["itens"]["c01"]["dedos"]
    assert [d["dono"] for d in dedos] == ["i", "a", "a"]
    assert gravado["itens"]["c01"]["obs"] == "troquei"


def test_servidor_recusa_dedo_invalido_sem_gravar(servidor):
    url, ouro = servidor
    pedido = urllib.request.Request(
        url + "/confirmar",
        data=json.dumps({"id": "c01", "dedos": ["i", "z", "a"]}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as erro:
        urllib.request.urlopen(pedido)
    assert erro.value.code == 400
    assert (
        json.loads(ouro.read_text(encoding="utf-8"))["itens"]["c01"]["confirmado"]
        is False
    )


def test_servidor_lista_so_os_da_pagina(servidor):
    url, _ = servidor
    with urllib.request.urlopen(url + "/itens.json") as resp:
        ids = [it["id"] for it in json.loads(resp.read())["itens"]]
    assert ids == ["c01", "c03"]


def test_servidor_entrega_o_video_com_range(servidor):
    url, _ = servidor
    pedido = urllib.request.Request(
        url + "/c01/clipe.mp4", headers={"Range": "bytes=10-19"}
    )
    with urllib.request.urlopen(pedido) as resp:
        assert resp.status == 206
        assert resp.headers["Content-Type"] == "video/mp4"
        assert resp.headers["Content-Range"] == "bytes 10-19/1024"
        assert resp.read() == bytes(range(10, 20))


def test_servidor_entrega_o_video_inteiro_sem_range(servidor):
    url, _ = servidor
    with urllib.request.urlopen(url + "/c01/clipe.mp4") as resp:
        assert resp.status == 200
        assert len(resp.read()) == 1024


def test_servidor_recusa_host_estranho(servidor):
    url, _ = servidor
    pedido = urllib.request.Request(
        url + "/gabarito.json", headers={"Host": "evil.example"}
    )
    with pytest.raises(urllib.error.HTTPError) as erro:
        urllib.request.urlopen(pedido)
    assert erro.value.code == 403


def test_servidor_pendentes_mantem_a_lista_fixa_ao_confirmar(tmp_path: Path):
    pasta = tmp_path / "padroes"
    pasta.mkdir()
    (pasta / "indice.json").write_text(
        json.dumps({"semente": 1, "itens": ITENS}), encoding="utf-8"
    )
    gab = gabarito_novo(ITENS, 1)
    confirmar_compasso(gab, "c01", NOTAS_A, ["i", "m", "a"], None, "agora")
    ouro = tmp_path / "padroes_direita.json"
    ouro.write_text(json.dumps(gab), encoding="utf-8")
    srv = criar_servidor(pasta, ouro, porta=0, host="127.0.0.1", pagina="pendentes")
    fio = threading.Thread(target=srv.serve_forever, daemon=True)
    fio.start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        with urllib.request.urlopen(url + "/itens.json") as resp:
            antes = [it["id"] for it in json.loads(resp.read())["itens"]]
        assert antes == ["c02", "c03"]
        resp = _post(url, {"id": "c02", "dedos": ["p", "i", "m"], "obs": None})
        assert resp["alteradas"] == 0
        assert resp["confirmados"] == 1 and resp["total"] == 2
        with urllib.request.urlopen(url + "/itens.json") as resp:
            depois = [it["id"] for it in json.loads(resp.read())["itens"]]
        assert depois == ["c02", "c03"]
    finally:
        srv.shutdown()
        srv.server_close()
