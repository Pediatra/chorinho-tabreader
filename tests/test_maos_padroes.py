"""Testes da ferramenta dos padrões da mão direita (M5): regras, respostas e servidor."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tab.maos_padroes import (
    aplicar_acao,
    completo,
    criar_servidor,
    gabarito_novo,
    mesclar_gabarito,
    progresso,
    proximo_incompleto,
    validar_resposta,
)

ITENS = [
    {"id": "c01", "video": "v1.mp4", "tela": 1, "compasso": 2, "exibicao": 0},
    {"id": "c02", "video": "v1.mp4", "tela": 1, "compasso": 3, "exibicao": 0},
    {"id": "c03", "video": "v2.mp4", "tela": 4, "compasso": 5, "exibicao": 1},
]


def _reg(**campos) -> dict:
    """Registro com os campos dados e o resto em branco."""
    base = {"tipo": None, "sequencia": None, "alternancia": None, "apoio": None}
    base.update(campos)
    return base


def test_arpejo_so_completa_com_sequencia_e_apoio():
    assert not completo(_reg(tipo="arpejo", apoio="apoiado"))
    assert completo(_reg(tipo="arpejo", sequencia="p-i-m-a", apoio="apoiado"))


def test_tremolo_tambem_pede_sequencia():
    assert not completo(_reg(tipo="tremolo", apoio="misto"))
    assert completo(_reg(tipo="tremolo", sequencia="i-i-i", apoio="misto"))


def test_plaqueado_completa_so_com_tipo_e_apoio():
    assert completo(_reg(tipo="plaqueado", apoio="sem_apoio"))


def test_melodia_pede_alternancia_e_nao_sequencia():
    assert not completo(_reg(tipo="melodia", apoio="apoiado"))
    assert completo(_reg(tipo="melodia", alternancia="i-m", apoio="apoiado"))


def test_interrogacao_conta_como_resposta():
    assert completo(_reg(tipo="?", apoio="?"))
    assert not completo(_reg(tipo="?"))


def test_validar_normaliza_sequencia_e_limpa_vazio():
    assert validar_resposta("sequencia", " P-I-m-A ") == "p-i-m-a"
    assert validar_resposta("sequencia", "") is None
    assert validar_resposta("tipo", None) is None


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("sequencia", "x-y"),
        ("sequencia", "p--i"),
        ("tipo", "dedilhado"),
        ("apoio", "forte"),
        ("alternancia", "i-x"),
        ("campo_inexistente", "a"),
        ("tipo", 3),
        ("obs", "x" * 501),
    ],
)
def test_validar_recusa_valores_fora_do_vocabulario(campo, valor):
    with pytest.raises(ValueError):
        validar_resposta(campo, valor)


def test_proximo_incompleto_da_a_volta_e_nao_devolve_o_atual():
    gab = gabarito_novo(ITENS, 1)
    ordem = [it["id"] for it in ITENS]
    gab["itens"]["c02"] = _reg(tipo="plaqueado", apoio="misto")
    gab["itens"]["c02"].update(video="v1.mp4", tela=1, compasso=3, exibicao=0)
    assert proximo_incompleto(ordem, gab, "c01") == "c03"
    assert proximo_incompleto(ordem, gab, "c03") == "c01"
    gab["itens"]["c01"] = _reg(tipo="plaqueado", apoio="misto")
    gab["itens"]["c03"] = _reg(tipo="plaqueado", apoio="misto")
    assert proximo_incompleto(ordem, gab, "c01") is None


def test_aplicar_acao_grava_campo_e_carimbo():
    gab = gabarito_novo(ITENS, 1)
    reg = aplicar_acao(gab, "c01", "tipo", "arpejo", "2026-10-13T10:00:00")
    assert reg["tipo"] == "arpejo"
    assert reg["respondido_em"] == "2026-10-13T10:00:00"
    assert progresso(gab) == (0, 3)


def test_aplicar_acao_com_item_inexistente_levanta_keyerror():
    with pytest.raises(KeyError):
        aplicar_acao(gabarito_novo(ITENS, 1), "c99", "tipo", "arpejo", "agora")


def test_mesclar_preserva_respostas_do_disco():
    existente = gabarito_novo(ITENS, 1)
    aplicar_acao(existente, "c01", "apoio", "apoiado", "2026-10-13T10:00:00")
    novo = mesclar_gabarito(gabarito_novo(ITENS, 1), existente)
    assert novo["itens"]["c01"]["apoio"] == "apoiado"
    assert novo["itens"]["c02"]["apoio"] is None


def test_mesclar_recusa_formato_antigo():
    with pytest.raises(ValueError):
        mesclar_gabarito(gabarito_novo(ITENS, 1), {"formato": 0, "itens": {}})


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
    """POST JSON em ``/responder``; devolve a resposta decodificada."""
    pedido = urllib.request.Request(
        url + "/responder",
        data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(pedido) as resp:
        return json.loads(resp.read())


def test_servidor_grava_no_disco_e_avanca_ao_completar(servidor):
    url, ouro = servidor
    _post(url, {"id": "c01", "campo": "tipo", "valor": "arpejo"})
    resp = _post(url, {"id": "c01", "campo": "sequencia", "valor": "p-i-m-a"})
    assert resp["completo"] is False
    resp = _post(url, {"id": "c01", "campo": "apoio", "valor": "apoiado"})
    assert resp["completo"] is True
    assert resp["proximo"] == "c02"
    assert resp["completos"] == 1 and resp["total"] == 3
    gravado = json.loads(ouro.read_text(encoding="utf-8"))
    assert gravado["itens"]["c01"]["sequencia"] == "p-i-m-a"


def test_servidor_recusa_valor_invalido_sem_gravar(servidor):
    url, ouro = servidor
    pedido = urllib.request.Request(
        url + "/responder",
        data=json.dumps({"id": "c01", "campo": "tipo", "valor": "dedilhado"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as erro:
        urllib.request.urlopen(pedido)
    assert erro.value.code == 400
    assert json.loads(ouro.read_text(encoding="utf-8"))["itens"]["c01"]["tipo"] is None


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
