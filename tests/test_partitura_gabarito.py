"""Testes da ferramenta de conferência da partitura (sem acervo, sem rede, sem GPU)."""

from __future__ import annotations

import copy
import http.client
import json
import threading
from pathlib import Path

import pytest

from tab.partitura_gabarito import (
    aplicar_resposta,
    criar_servidor,
    eventos_da_leitura,
    gabarito_vazio,
    ler_partitura,
    marcar_concordancia,
    progresso,
    proximo_pendente,
    validar_faltando,
    validar_obs,
)

MUSICXML_BASE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
        <key><fifths>1</fifths></key>
        <time><beats>2</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration>
        <voice>1</voice><type>quarter</type>
        <tie type="start"/><notations><tied type="start"/></notations></note>
      <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
        <voice>1</voice><type>quarter</type></note>
      <note><rest/><duration>2</duration><voice>1</voice><type>quarter</type></note>
      <backup><duration>4</duration></backup>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration>
        <voice>2</voice><type>half</type></note>
    </measure>
    <measure number="2">
      <note><grace/><pitch><step>F</step><octave>4</octave><alter>1</alter></pitch>
        <voice>1</voice><type>eighth</type></note>
      <note><pitch><step>B</step><octave>3</octave><alter>-1</alter></pitch>
        <duration>2</duration><voice>1</voice><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
"""

MUSICXML_CLAVE_8_EMBAIXO = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <clef><sign>G</sign><line>2</line><clef-octave-change>-1</clef-octave-change></clef>
      </attributes>
      <note><pitch><step>F</step><octave>3</octave><alter>1</alter></pitch>
        <duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
"""


def _gravar(caminho: Path, texto: str) -> Path:
    """Grava um texto em ``caminho`` e devolve o próprio caminho."""
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def _sim(midi: int | None, t: float, idx: int = 0, **extra: object) -> dict:
    """Símbolo mínimo de leitura, como o de ``ler_partitura``."""
    base = {
        "idx": idx,
        "compasso": "1",
        "t": t,
        "t_global": t,
        "pausa": midi is None,
        "midi": midi,
        "nome": None,
        "figura": "quarter",
        "pontuada": False,
        "duracao": 1.0,
        "acorde": False,
        "voz": "1",
        "ligadura_inicio": False,
        "ligadura_fim": False,
        "graca": False,
    }
    base.update(extra)
    return base


def _item(numeros: tuple[str, ...] = ("1",)) -> dict:
    """Item de conferência com dois símbolos por compasso (idx 0 e 1)."""
    compassos = []
    for numero in numeros:
        simbolos = []
        for k in range(2):
            simbolo = _sim(60 + k, float(k), idx=k + 10 * int(numero))
            simbolo["compasso"] = numero
            simbolos.append(simbolo)
        compassos.append({"numero": numero, "duracao": 2.0, "simbolos": simbolos})
    return {
        "id": "R01",
        "origem": "ouro",
        "canal": "canal de teste",
        "video": "v.mp4",
        "tela": 1,
        "fonte": "audiveris/x2",
        "png": "data/saida/partitura/p1/recortes/R01.png",
        "musicxml": "",
        "clave": None,
        "armadura": None,
        "compasso_formula": None,
        "compassos": compassos,
        "n_compassos": len(compassos),
        "n_notas": 2 * len(compassos),
        "n_pausas": 0,
        "discordancias": 0,
    }


def _dados(numero: str, donos: list[tuple[int, str]], **extra: object) -> dict:
    """Corpo de POST para o compasso ``numero`` do item de ``_item``."""
    corpo: dict = {
        "recorte": "R01",
        "compasso": numero,
        "simbolos": [{"idx": idx, "dono": dono} for idx, dono in donos],
    }
    corpo.update(extra)
    return corpo


# ---------------------------------------------------------------------------------
# Parser do MusicXML
# ---------------------------------------------------------------------------------


def test_parser_pausa_acorde_backup_ligadura_e_graca(tmp_path: Path) -> None:
    lido = ler_partitura(_gravar(tmp_path / "a.musicxml", MUSICXML_BASE))
    primeiro, segundo = lido["compassos"]
    assert [c["numero"] for c in lido["compassos"]] == ["1", "2"]
    assert primeiro["duracao"] == 2.0

    dou = next(s for s in primeiro["simbolos"] if s["midi"] == 60)
    assert dou["ligadura_inicio"] is True
    assert dou["nome"] == "C4"

    acorde = next(s for s in primeiro["simbolos"] if s["midi"] == 64)
    assert acorde["acorde"] is True
    assert acorde["t"] == 0.0

    pausa = next(s for s in primeiro["simbolos"] if s["pausa"])
    assert pausa["midi"] is None
    assert pausa["nome"] is None
    assert pausa["t"] == 1.0

    voz2 = next(s for s in primeiro["simbolos"] if s["voz"] == "2")
    assert voz2["t"] == 0.0
    assert voz2["duracao"] == 2.0
    assert voz2["figura"] == "half"

    grace = next(s for s in segundo["simbolos"] if s["graca"])
    assert grace["duracao"] == 0.0
    assert grace["midi"] == 66
    assert grace["nome"] == "F#4"

    bemol = next(s for s in segundo["simbolos"] if s["nome"] == "Bb3")
    assert bemol["midi"] == 58
    assert bemol["t"] == 0.0
    assert bemol["t_global"] == 2.0

    assert lido["clave"] == {"sign": "G", "line": 2, "octave_change": 0}
    assert lido["armadura"] == 1
    assert lido["compasso_formula"] == {"beats": 2, "beat_type": 4}


def test_clave_com_8_embaixo_soma_12_na_altura_escrita(tmp_path: Path) -> None:
    lido = ler_partitura(_gravar(tmp_path / "c.musicxml", MUSICXML_CLAVE_8_EMBAIXO))
    nota = lido["compassos"][0]["simbolos"][0]
    # Soa F#3 (54); escrito é F#4 (66), como em tab.partitura_avaliar.
    assert nota["midi"] == 66
    assert nota["nome"] == "F#4"
    assert lido["clave"]["octave_change"] == -1


def test_sustenido_e_bemol_no_nome(tmp_path: Path) -> None:
    lido = ler_partitura(_gravar(tmp_path / "b.musicxml", MUSICXML_BASE))
    nomes = {s["nome"] for c in lido["compassos"] for s in c["simbolos"] if s["nome"]}
    assert "F#4" in nomes
    assert "Bb3" in nomes


def test_eventos_da_leitura_ignora_pausa_e_graca(tmp_path: Path) -> None:
    lido = ler_partitura(_gravar(tmp_path / "e.musicxml", MUSICXML_BASE))
    simbolos = [s for c in lido["compassos"] for s in c["simbolos"]]
    eventos = eventos_da_leitura(simbolos)
    assert eventos[0] == frozenset({55, 60, 64})
    assert frozenset({58}) in eventos
    assert all(66 not in e for e in eventos)


def test_ler_partitura_recusa_raiz_errada(tmp_path: Path) -> None:
    arquivo = _gravar(tmp_path / "x.musicxml", "<outra/>")
    with pytest.raises(ValueError, match="score-partwise"):
        ler_partitura(arquivo)


# ---------------------------------------------------------------------------------
# Concordância
# ---------------------------------------------------------------------------------


def test_concordancia_um_concorda_outro_discorda() -> None:
    lib = [_sim(60, 0.0, idx=0), _sim(64, 1.0, idx=1)]
    outra = [frozenset({60}), frozenset({65})]
    marcar_concordancia(lib, outra, "homr_concorda")
    assert lib[0]["homr_concorda"] is True
    assert lib[1]["homr_concorda"] is False


def test_concordancia_sem_outra_leitura_fica_none() -> None:
    lib = [_sim(60, 0.0, idx=0), _sim(None, 1.0, idx=1)]
    marcar_concordancia(lib, None, "tab_concorda")
    assert lib[0]["tab_concorda"] is None
    assert lib[1]["tab_concorda"] is None


def test_concordancia_nota_que_a_outra_nao_casa_discorda() -> None:
    lib = [_sim(60, 0.0, idx=0), _sim(62, 1.0, idx=1)]
    outra = [frozenset({60})]
    marcar_concordancia(lib, outra, "homr_concorda")
    assert lib[0]["homr_concorda"] is True
    assert lib[1]["homr_concorda"] is False


def test_pausa_e_graca_nao_entram_na_concordancia() -> None:
    graca = _sim(70, 0.0, idx=0, graca=True)
    lib = [graca, _sim(None, 1.0, idx=1), _sim(60, 2.0, idx=2)]
    marcar_concordancia(lib, [frozenset({60})], "homr_concorda")
    assert graca["homr_concorda"] is None
    assert lib[1]["homr_concorda"] is None
    assert lib[2]["homr_concorda"] is True


# ---------------------------------------------------------------------------------
# Validação e gabarito
# ---------------------------------------------------------------------------------


def test_estado_invalido_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    corpo = _dados("1", [(10, "certo"), (11, "errado")])
    with pytest.raises(ValueError, match="estado inválido"):
        aplicar_resposta(gab, itens, corpo, "t")
    assert gab["recortes"] == {}


def test_idx_errado_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    corpo = _dados("1", [(10, "certo"), (99, "certo")])
    with pytest.raises(ValueError, match="idx"):
        aplicar_resposta(gab, itens, corpo, "t")
    assert gab["recortes"] == {}


def test_idx_repetido_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    with pytest.raises(ValueError, match="repetido"):
        aplicar_resposta(gab, itens, _dados("1", [(10, "certo"), (10, "certo")]), "t")


def test_faltando_51_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    corpo = _dados("1", [(10, "certo"), (11, "certo")], faltando=51)
    with pytest.raises(ValueError, match="faltando"):
        aplicar_resposta(gab, itens, corpo, "t")
    with pytest.raises(ValueError):
        validar_faltando(True)


def test_obs_longa_e_erro() -> None:
    assert validar_obs("  nota  ") == "nota"
    with pytest.raises(ValueError, match="500"):
        validar_obs("x" * 501)


def test_resposta_gravada_com_palpite_e_sem_campos_da_conferencia() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    corpo = _dados(
        "1",
        [(10, "figura_errada"), (11, "certo")],
        faltando=1,
        obs="pausa trocada",
        clave_certa=False,
    )
    registro = aplicar_resposta(gab, itens, corpo, "2026-10-13T10:00:00")
    assert registro["confirmado"] is True
    assert registro["faltando"] == 1
    assert registro["obs"] == "pausa trocada"
    primeiro = registro["simbolos"][0]
    assert primeiro["dono"] == "figura_errada"
    assert "idx" not in primeiro["palpite"]
    assert primeiro["palpite"]["midi"] == 60
    recorte = gab["recortes"]["R01"]
    assert recorte["clave_certa"] is False
    assert recorte["armadura_certa"] is True


def test_mesclagem_preserva_compasso_ja_confirmado() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item(("3", "4"))}
    aplicar_resposta(
        gab, itens, _dados("3", [(30, "altura_errada"), (31, "certo")]), "t1"
    )
    confirmado_3 = copy.deepcopy(gab["recortes"]["R01"]["compassos"]["3"])
    aplicar_resposta(gab, itens, _dados("4", [(40, "certo"), (41, "nao_existe")]), "t2")
    assert gab["recortes"]["R01"]["compassos"]["3"] == confirmado_3
    assert gab["recortes"]["R01"]["compassos"]["4"]["confirmado"] is True


def test_reconfirmar_sobrescreve_so_o_proprio_compasso() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item(("3", "4"))}
    aplicar_resposta(gab, itens, _dados("3", [(30, "certo"), (31, "certo")]), "t1")
    aplicar_resposta(gab, itens, _dados("4", [(40, "certo"), (41, "certo")]), "t2")
    aplicar_resposta(gab, itens, _dados("3", [(30, "nao_existe"), (31, "certo")]), "t3")
    compassos = gab["recortes"]["R01"]["compassos"]
    assert compassos["3"]["simbolos"][0]["dono"] == "nao_existe"
    assert compassos["3"]["respondido_em"] == "t3"
    assert compassos["4"]["respondido_em"] == "t2"


def test_progresso_e_proximo_pendente() -> None:
    gab = gabarito_vazio()
    itens = [_item(("3", "4"))]
    aplicar_resposta(
        gab, {"R01": itens[0]}, _dados("3", [(30, "certo"), (31, "certo")]), "t"
    )
    assert progresso(itens, gab) == {
        "confirmados": 1,
        "total": 2,
        "por_recorte": {"R01": [1, 2]},
    }
    assert proximo_pendente(itens, gab, ("R01", "3")) == {
        "recorte": "R01",
        "compasso": "4",
    }
    aplicar_resposta(
        gab, {"R01": itens[0]}, _dados("4", [(40, "certo"), (41, "certo")]), "t"
    )
    assert proximo_pendente(itens, gab, ("R01", "4")) is None


# ---------------------------------------------------------------------------------
# Servidor (porta 0, em thread, gabarito em tmp_path)
# ---------------------------------------------------------------------------------


@pytest.fixture
def servidor(tmp_path: Path):
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(
        json.dumps({"formato": 1, "itens": [_item(("1", "2"))]}), encoding="utf-8"
    )
    ouro = tmp_path / "gabarito.json"
    srv = criar_servidor(itens_path, ouro, porta=0, host="127.0.0.1")
    fio = threading.Thread(target=srv.serve_forever, daemon=True)
    fio.start()
    try:
        yield srv.server_address[1], ouro
    finally:
        srv.shutdown()
        srv.server_close()


def _pedido(porta: int, metodo: str, caminho: str, corpo=None, host=None):
    """Faz uma requisição HTTP ao servidor de teste; ``host`` troca o cabeçalho Host."""
    conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    texto = json.dumps(corpo).encode() if corpo is not None else None
    conexao.putrequest(
        metodo, caminho, skip_host=host is not None, skip_accept_encoding=True
    )
    if host is not None:
        conexao.putheader("Host", host)
    if texto is not None:
        conexao.putheader("Content-Type", "application/json")
        conexao.putheader("Content-Length", str(len(texto)))
    conexao.endheaders(texto)
    resposta = conexao.getresponse()
    dados = resposta.read()
    conexao.close()
    return resposta.status, dados


def test_servidor_pagina_itens_salvar_e_host_recusado(servidor) -> None:
    porta, ouro = servidor

    status, pagina = _pedido(porta, "GET", "/")
    assert status == 200
    assert "Conferência da partitura" in pagina.decode("utf-8")

    status, dados = _pedido(porta, "GET", "/itens")
    assert status == 200
    corpo = json.loads(dados)
    assert corpo["itens"][0]["id"] == "R01"
    assert corpo["progresso"]["total"] == 2

    status, dados = _pedido(
        porta,
        "POST",
        "/salvar",
        _dados("1", [(10, "altura_errada"), (11, "certo")], faltando=2, obs="ok"),
    )
    assert status == 200
    assert json.loads(dados)["proximo"] == {"recorte": "R01", "compasso": "2"}
    gravado = json.loads(ouro.read_text(encoding="utf-8"))
    compasso = gravado["recortes"]["R01"]["compassos"]["1"]
    assert compasso["confirmado"] is True
    assert compasso["faltando"] == 2
    assert compasso["simbolos"][0]["dono"] == "altura_errada"

    status, _ = _pedido(
        porta, "POST", "/salvar", _dados("1", [(10, "errado"), (11, "certo")])
    )
    assert status == 400
    status, _ = _pedido(
        porta,
        "POST",
        "/salvar",
        _dados("2", [(20, "certo"), (21, "certo")], faltando=51),
    )
    assert status == 400
    status, _ = _pedido(
        porta, "POST", "/salvar", _dados("2", [(20, "certo"), (99, "certo")])
    )
    assert status == 400

    status, _ = _pedido(porta, "GET", "/", host="evil.example")
    assert status == 403
    status, _ = _pedido(
        porta,
        "POST",
        "/salvar",
        _dados("2", [(20, "certo"), (21, "certo")]),
        host="evil.example",
    )
    assert status == 403


def test_servidor_carrega_gabarito_existente_e_preserva(tmp_path: Path) -> None:
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(
        json.dumps({"formato": 1, "itens": [_item(("1", "2"))]}), encoding="utf-8"
    )
    ouro = tmp_path / "gabarito.json"
    anterior = gabarito_vazio()
    aplicar_resposta(
        anterior,
        {"R01": _item(("1", "2"))},
        _dados("1", [(10, "nao_existe"), (11, "certo")]),
        "antes",
    )
    ouro.write_text(json.dumps(anterior), encoding="utf-8")
    srv = criar_servidor(itens_path, ouro, porta=0, host="127.0.0.1")
    fio = threading.Thread(target=srv.serve_forever, daemon=True)
    fio.start()
    try:
        status, dados = _pedido(srv.server_address[1], "GET", "/itens")
        assert status == 200
        estado = json.loads(dados)["gabarito"]
        assert estado["recortes"]["R01"]["compassos"]["1"]["respondido_em"] == "antes"
    finally:
        srv.shutdown()
        srv.server_close()
