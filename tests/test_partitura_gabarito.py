"""Testes da ferramenta de conferência da partitura (sem acervo, sem rede, sem GPU)."""

from __future__ import annotations

import http.client
import json
import struct
import threading
from pathlib import Path

import pytest

from tab.partitura_gabarito import (
    _tamanho_png,
    aplicar_resposta,
    carregar_gabarito,
    chaves_notacoes,
    criar_servidor,
    eventos_da_leitura,
    gabarito_vazio,
    ler_partitura,
    main,
    marcar_concordancia,
    preparar,
    preparar_sem_produto,
    progresso,
    proximo_pendente_recorte,
    validar_faltando,
    validar_notacoes_recorte,
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


MUSICXML_NOTACOES = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration>
        <voice>1</voice><type>quarter</type>
        <accidental>sharp</accidental><dot/><dot/>
        <notations>
          <fermata type="upright"/>
          <articulations><staccato/></articulations>
          <technical><fingering>2</fingering></technical>
          <slur type="start" number="1"/>
        </notations></note>
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
        "notacoes": [],
    }
    base.update(extra)
    return base


def _item(id_: str = "R01", numeros: tuple[str, ...] = ("1",)) -> dict:
    """Item de conferência: dois símbolos por compasso (idx 10·n e 10·n+1).

    A imagem de teste tem 200x100 pixels.
    """
    compassos = []
    for numero in numeros:
        simbolos = []
        for k in range(2):
            simbolo = _sim(60 + k, float(k), idx=k + 10 * int(numero))
            simbolo["compasso"] = numero
            simbolos.append(simbolo)
        compassos.append({"numero": numero, "duracao": 2.0, "simbolos": simbolos})
    return {
        "id": id_,
        "origem": "ouro",
        "canal": "canal de teste",
        "video": "v.mp4",
        "tela": 1,
        "fonte": "audiveris/x2_margem",
        "png": f"data/saida/partitura/p1/recortes/{id_}.png",
        "musicxml": "",
        "clave": None,
        "armadura": None,
        "compasso_formula": None,
        "compassos": compassos,
        "largura_png": 200,
        "altura_png": 100,
        "n_compassos": len(compassos),
        "n_notas": 2 * len(compassos),
        "n_pausas": 0,
        "discordancias": 0,
    }


def _corpo(id_: str, donos: list[tuple[int, str]], **extra: object) -> dict:
    """Corpo de POST para o recorte ``id_``: todos os ``(idx, dono)`` dele."""
    corpo: dict = {
        "recorte": id_,
        "simbolos": [{"idx": idx, "dono": dono} for idx, dono in donos],
    }
    corpo.update(extra)
    return corpo


def _todos(id_: str, numeros: tuple[str, ...] = ("1",), dono: str = "certo") -> list:
    """Lista ``(idx, dono)`` cobrindo todos os símbolos de ``_item(id_, numeros)``."""
    return [(k + 10 * int(n), dono) for n in numeros for k in range(2)]


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


def test_notacoes_fermata_staccato_dedilhado_slur_acidente_e_pontos(
    tmp_path: Path,
) -> None:
    lido = ler_partitura(_gravar(tmp_path / "n.musicxml", MUSICXML_NOTACOES))
    nota = lido["compassos"][0]["simbolos"][0]
    assert nota["notacoes"] == [
        "acidente:sharp",
        "ponto",
        "ponto",
        "fermata",
        "staccato",
        "fingering:2",
        "slur-start",
    ]
    assert nota["pontuada"] is True


def test_ligadura_repetida_em_tie_e_tied_conta_uma_vez(tmp_path: Path) -> None:
    lido = ler_partitura(_gravar(tmp_path / "b2.musicxml", MUSICXML_BASE))
    dou = next(s for s in lido["compassos"][0]["simbolos"] if s["midi"] == 60)
    assert dou["notacoes"] == ["tie-start"]


def test_chaves_notacoes_desambiguam_repeticao() -> None:
    nomes = ["ponto", "ponto", "fermata", "ponto"]
    assert chaves_notacoes(nomes) == ["ponto", "ponto#2", "fermata", "ponto#3"]
    assert chaves_notacoes([]) == []


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


def test_tamanho_png_le_o_cabecalho(tmp_path: Path) -> None:
    cabecalho = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
    caminho = tmp_path / "r.png"
    caminho.write_bytes(cabecalho + struct.pack(">II", 1920, 168) + b"\x00" * 10)
    assert _tamanho_png(caminho) == (1920, 168)
    ruim = tmp_path / "ruim.png"
    ruim.write_bytes(b"GIF89a" + b"\x00" * 30)
    with pytest.raises(ValueError, match="não é PNG"):
        _tamanho_png(ruim)


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
# Validação e gabarito (formato 3: uma entrada por recorte, notações por símbolo)
# ---------------------------------------------------------------------------------


def test_estado_invalido_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    corpo = _corpo("R01", [(10, "certo"), (11, "errado")])
    with pytest.raises(ValueError, match="estado inválido"):
        aplicar_resposta(gab, itens, corpo, "t")
    assert gab["recortes"] == {}


def test_idx_faltando_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    with pytest.raises(ValueError, match="idx não batem"):
        aplicar_resposta(gab, itens, _corpo("R01", [(10, "certo")]), "t")
    assert gab["recortes"] == {}


def test_idx_errado_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    corpo = _corpo("R01", [(10, "certo"), (99, "certo")])
    with pytest.raises(ValueError, match="idx"):
        aplicar_resposta(gab, itens, corpo, "t")
    assert gab["recortes"] == {}


def test_idx_repetido_e_erro() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    with pytest.raises(ValueError, match="repetido"):
        aplicar_resposta(gab, itens, _corpo("R01", [(10, "certo"), (10, "certo")]), "t")


def test_faltando_fora_da_imagem_e_erro() -> None:
    with pytest.raises(ValueError, match="fora da imagem"):
        validar_faltando([{"x": 201, "y": 5}], 200, 100)
    with pytest.raises(ValueError, match="fora da imagem"):
        validar_faltando([{"x": 5, "y": -1}], 200, 100)
    with pytest.raises(ValueError, match="números"):
        validar_faltando([{"x": "5", "y": 5}], 200, 100)
    # Bordas incluídas: [0, largura] × [0, altura].
    assert validar_faltando([{"x": 0, "y": 0}, {"x": 200, "y": 100}], 200, 100) == [
        {"x": 0.0, "y": 0.0},
        {"x": 200.0, "y": 100.0},
    ]


def test_faltando_201_pontos_e_erro() -> None:
    pontos = [{"x": 1, "y": 1}] * 201
    with pytest.raises(ValueError, match="200 pontos"):
        validar_faltando(pontos, 200, 100)
    gab = gabarito_vazio()
    itens = {"R01": _item()}
    corpo = _corpo("R01", _todos("R01"), faltando=pontos)
    with pytest.raises(ValueError, match="200 pontos"):
        aplicar_resposta(gab, itens, corpo, "t")
    assert gab["recortes"] == {}


def test_obs_longa_e_erro() -> None:
    assert validar_obs("  nota  ") == "nota"
    with pytest.raises(ValueError, match="500"):
        validar_obs("x" * 501)


def test_resposta_gravada_formato_3_com_palpite_sem_campos_da_conferencia() -> None:
    gab = gabarito_vazio()
    assert gab["formato"] == 3
    itens = {"R01": _item()}
    corpo = _corpo(
        "R01",
        [(10, "figura_errada"), (11, "certo")],
        faltando=[{"x": 12.5, "y": 61}],
        obs="pausa trocada",
        clave_certa=False,
    )
    registro = aplicar_resposta(gab, itens, corpo, "2026-10-13T10:00:00")
    assert registro["confirmado"] is True
    assert registro["faltando"] == [{"x": 12.5, "y": 61.0}]
    assert registro["obs"] == "pausa trocada"
    assert registro["largura_png"] == 200
    assert registro["altura_png"] == 100
    assert registro["clave_certa"] is False
    assert registro["armadura_certa"] is True
    primeiro = registro["simbolos"][0]
    assert primeiro["idx"] == 10
    assert primeiro["compasso"] == "1"
    assert primeiro["dono"] == "figura_errada"
    assert "idx" not in primeiro["palpite"]
    assert primeiro["palpite"]["midi"] == 60
    assert gab["recortes"]["R01"] is registro


def test_reconfirmar_sobrescreve_so_o_proprio_recorte() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item("R01"), "R02": _item("R02", ("5",))}
    aplicar_resposta(gab, itens, _corpo("R01", _todos("R01")), "t1")
    aplicar_resposta(gab, itens, _corpo("R02", _todos("R02", ("5",))), "t2")
    aplicar_resposta(
        gab,
        itens,
        _corpo("R01", [(10, "nao_existe"), (11, "certo")], obs="de novo"),
        "t3",
    )
    recortes = gab["recortes"]
    assert recortes["R01"]["simbolos"][0]["dono"] == "nao_existe"
    assert recortes["R01"]["respondido_em"] == "t3"
    assert recortes["R01"]["obs"] == "de novo"
    assert recortes["R02"]["respondido_em"] == "t2"
    assert recortes["R02"]["simbolos"][0]["dono"] == "certo"


def test_progresso_e_proximo_pendente_recorte() -> None:
    gab = gabarito_vazio()
    itens = [_item("R01"), _item("R02", ("5",))]
    aplicar_resposta(gab, {"R01": itens[0]}, _corpo("R01", _todos("R01")), "t")
    assert progresso(itens, gab) == {
        "confirmados": 1,
        "total": 2,
        "por_recorte": {"R01": True, "R02": False},
    }
    assert proximo_pendente_recorte(itens, gab, "R01") == "R02"
    aplicar_resposta(gab, {"R02": itens[1]}, _corpo("R02", _todos("R02", ("5",))), "t")
    assert proximo_pendente_recorte(itens, gab, "R02") is None


def test_carregar_gabarito_formato_1_e_2_e_erro(tmp_path: Path) -> None:
    for formato in (1, 2):
        antigo = tmp_path / f"antigo{formato}.json"
        antigo.write_text(
            json.dumps({"formato": formato, "recortes": {}}), encoding="utf-8"
        )
        with pytest.raises(ValueError, match=f"formato {formato}"):
            carregar_gabarito(antigo)
    assert carregar_gabarito(tmp_path / "nao_existe.json") == gabarito_vazio()


def _item_com_notacoes() -> dict:
    """Item de R01 em que o primeiro símbolo tem fermata e dois pontos."""
    item = _item("R01")
    item["compassos"][0]["simbolos"][0]["notacoes"] = ["fermata", "ponto", "ponto"]
    return item


def test_validar_notacoes_recusa_chave_inexistente_e_estado_invalido() -> None:
    item = _item_com_notacoes()
    simbolos = item["compassos"][0]["simbolos"]
    lista = [{"idx": 10, "dono": "certo", "notacoes": {"tie-start": "certo"}}]
    lista.append({"idx": 11, "dono": "certo"})
    with pytest.raises(ValueError, match="não existe"):
        validar_notacoes_recorte(lista, simbolos)
    lista[0]["notacoes"] = {"fermata": "talvez"}
    with pytest.raises(ValueError, match="estado de notação"):
        validar_notacoes_recorte(lista, simbolos)
    lista[0]["notacoes"] = {"ponto#3": "certo"}
    with pytest.raises(ValueError, match="não existe"):
        validar_notacoes_recorte(lista, simbolos)


def test_gravacao_formato_3_guarda_todas_as_notacoes() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item_com_notacoes()}
    corpo = _corpo("R01", _todos("R01"))
    corpo["simbolos"][0]["notacoes"] = {"fermata": "inventado", "ponto#2": "errado"}
    registro = aplicar_resposta(gab, itens, corpo, "t")
    primeiro = registro["simbolos"][0]
    assert primeiro["notacoes_dono"] == {
        "fermata": "inventado",
        "ponto": "certo",
        "ponto#2": "errado",
    }
    assert primeiro["palpite"]["notacoes"] == ["fermata", "ponto", "ponto"]
    assert "notacoes_dono" not in primeiro["palpite"]
    assert registro["simbolos"][1]["notacoes_dono"] == {}


def test_notacao_invalida_nao_grava_nada() -> None:
    gab = gabarito_vazio()
    itens = {"R01": _item_com_notacoes()}
    corpo = _corpo("R01", _todos("R01"))
    corpo["simbolos"][0]["notacoes"] = {"fermata": "estranho"}
    with pytest.raises(ValueError, match="estado de notação"):
        aplicar_resposta(gab, itens, corpo, "t")
    assert gab["recortes"] == {}


# ---------------------------------------------------------------------------------
# Servidor (porta 0, em thread, gabarito em tmp_path)
# ---------------------------------------------------------------------------------


def _subir(tmp_path: Path, ouro: Path):
    """Sobe o servidor com R01 e R02 em ``tmp_path`` e devolve (servidor, thread)."""
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(
        json.dumps(
            {"formato": 1, "itens": [_item("R01", ("1", "2")), _item("R02", ("5",))]}
        ),
        encoding="utf-8",
    )
    srv = criar_servidor(itens_path, ouro, porta=0, host="127.0.0.1")
    fio = threading.Thread(target=srv.serve_forever, daemon=True)
    fio.start()
    return srv


@pytest.fixture
def servidor(tmp_path: Path):
    ouro = tmp_path / "gabarito.json"
    srv = _subir(tmp_path, ouro)
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
    assert corpo["progresso"]["confirmados"] == 0

    status, _ = _pedido(
        porta, "POST", "/salvar", _corpo("R01", _todos("R01", ("1", "2")))
    )
    assert status == 200
    gravado = json.loads(ouro.read_text(encoding="utf-8"))
    assert gravado["formato"] == 3
    assert gravado["recortes"]["R01"]["confirmado"] is True
    assert len(gravado["recortes"]["R01"]["simbolos"]) == 4

    status, dados = _pedido(
        porta,
        "POST",
        "/salvar",
        _corpo(
            "R01",
            [(10, "altura_errada"), (11, "certo"), (20, "certo"), (21, "certo")],
            faltando=[{"x": 10, "y": 5}],
            obs="ok",
        ),
    )
    assert status == 200
    resposta = json.loads(dados)
    assert resposta["proximo"] == {"recorte": "R02"}
    assert resposta["progresso"]["confirmados"] == 1
    gravado = json.loads(ouro.read_text(encoding="utf-8"))
    recorte = gravado["recortes"]["R01"]
    assert recorte["faltando"] == [{"x": 10.0, "y": 5.0}]
    assert recorte["simbolos"][0]["dono"] == "altura_errada"

    # Erros: nada é gravado e o arquivo continua como estava.
    antes = ouro.read_text(encoding="utf-8")
    casos = [
        _corpo("R01", [(10, "errado"), (11, "certo"), (20, "certo"), (21, "certo")]),
        _corpo("R02", [(50, "certo")]),
        _corpo("R02", [(50, "certo"), (51, "certo")], faltando=[{"x": 300, "y": 5}]),
        _corpo("R02", [(50, "certo"), (51, "certo")], obs="x" * 501),
        _corpo("R02", [(50, "certo"), (99, "certo")]),
    ]
    for corpo in casos:
        status, _ = _pedido(porta, "POST", "/salvar", corpo)
        assert status == 400
    assert ouro.read_text(encoding="utf-8") == antes

    status, _ = _pedido(porta, "GET", "/", host="evil.example")
    assert status == 403
    status, _ = _pedido(
        porta,
        "POST",
        "/salvar",
        _corpo("R02", _todos("R02", ("5",))),
        host="evil.example",
    )
    assert status == 403


def test_servidor_carrega_gabarito_existente_e_preserva(tmp_path: Path) -> None:
    ouro = tmp_path / "gabarito.json"
    anterior = gabarito_vazio()
    aplicar_resposta(
        anterior,
        {"R01": _item("R01", ("1", "2"))},
        _corpo("R01", _todos("R01", ("1", "2"), dono="nao_existe")),
        "antes",
    )
    ouro.write_text(json.dumps(anterior), encoding="utf-8")
    srv = _subir(tmp_path, ouro)
    try:
        status, dados = _pedido(srv.server_address[1], "GET", "/itens")
        assert status == 200
        corpo = json.loads(dados)
        assert corpo["gabarito"]["recortes"]["R01"]["respondido_em"] == "antes"
        assert corpo["progresso"]["confirmados"] == 1
    finally:
        srv.shutdown()
        srv.server_close()


def test_servidor_recusa_gabarito_formato_1(tmp_path: Path) -> None:
    ouro = tmp_path / "gabarito.json"
    ouro.write_text(json.dumps({"formato": 1, "recortes": {}}), encoding="utf-8")
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(
        json.dumps({"formato": 1, "itens": [_item("R01")]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="formato 1"):
        criar_servidor(itens_path, ouro, porta=0, host="127.0.0.1")


def test_servidor_grava_notacoes_e_recusa_chave_errada(tmp_path: Path) -> None:
    ouro = tmp_path / "gabarito.json"
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(
        json.dumps({"formato": 1, "itens": [_item_com_notacoes()]}), encoding="utf-8"
    )
    srv = criar_servidor(itens_path, ouro, porta=0, host="127.0.0.1")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    porta = srv.server_address[1]
    try:
        corpo = _corpo("R01", _todos("R01"))
        corpo["simbolos"][0]["notacoes"] = {"fermata": "inventado"}
        status, _ = _pedido(porta, "POST", "/salvar", corpo)
        assert status == 200
        gravado = json.loads(ouro.read_text(encoding="utf-8"))
        assert gravado["formato"] == 3
        notas = gravado["recortes"]["R01"]["simbolos"][0]["notacoes_dono"]
        assert notas == {"fermata": "inventado", "ponto": "certo", "ponto#2": "certo"}

        antes = ouro.read_text(encoding="utf-8")
        ruins = [
            {"fermata": "errado", "tie-start": "certo"},
            {"ponto#3": "certo"},
            {"fermata": "talvez"},
        ]
        for notacoes in ruins:
            corpo["simbolos"][0]["notacoes"] = notacoes
            status, _ = _pedido(porta, "POST", "/salvar", corpo)
            assert status == 400
        assert ouro.read_text(encoding="utf-8") == antes
    finally:
        srv.shutdown()
        srv.server_close()


# ---------------------------------------------------------------------------------
# Vídeos sem produto (preparar --sem-produto, PNG e servidor)
# ---------------------------------------------------------------------------------

SLUG_SEM_PRODUTO = "meu_video_de_teste_longo"


def _png_do_tamanho(caminho: Path, largura: int, altura: int) -> Path:
    """Grava só o cabeçalho de um PNG com o tamanho pedido (basta para ``_tamanho_png``)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\x0dIHDR"
        + struct.pack(">II", largura, altura)
        + b"\x00" * 10
    )
    return caminho


@pytest.fixture
def sem_produto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Uma pasta de vídeo sem produto, com um recorte (P01a) e a leitura herdada.

    Devolve a pasta do vídeo; ``PASTA_SEM_PRODUTO`` aponta para o pai dela.
    """
    monkeypatch.setattr(
        "tab.partitura_gabarito.PASTA_SEM_PRODUTO", tmp_path / "sem_produto"
    )
    pasta = tmp_path / "sem_produto" / SLUG_SEM_PRODUTO
    indice = [
        {
            "id": "P01a",
            "video": "canal teste/aula.mp4",
            "pagina": 2,
            "largura": 200,
            "altura": 100,
        }
    ]
    (pasta / "recortes").mkdir(parents=True)
    (pasta / "recortes" / "indice.json").write_text(
        json.dumps(indice), encoding="utf-8"
    )
    _png_do_tamanho(pasta / "recortes" / "P01a.png", 200, 100)
    _gravar(_pasta_leitura_herdada(pasta, "P01a") / "saida.musicxml", MUSICXML_BASE)
    return pasta


def _pasta_leitura_herdada(pasta: Path, id_: str) -> Path:
    """Pasta da leitura herdada de um recorte sem produto (criada se faltar)."""
    alvo = pasta / "omr" / "audiveris" / "x2_margem_herdada" / id_
    alvo.mkdir(parents=True, exist_ok=True)
    return alvo


def test_preparar_sem_produto_item_com_id_png_fonte_e_concordancias_none(
    sem_produto: Path, tmp_path: Path
) -> None:
    saida = tmp_path / "itens.json"
    itens = preparar_sem_produto([(SLUG_SEM_PRODUTO, "P01a")], saida)

    assert len(itens) == 1
    item = itens[0]
    # SLUG[:16] + "_" + ID: "meu_video_de_tes" tem 16 caracteres.
    assert item["id"] == "meu_video_de_tes_P01a"
    assert item["origem"] == "sem_produto"
    assert item["canal"] == "canal teste"
    assert item["video"] == "canal teste/aula.mp4"
    assert item["tela"] == 2
    assert item["fonte"] == "audiveris/x2_margem_herdada"
    assert item["recorte"] == "P01a"
    # Fora da RAIZ (tmp_path), o caminho sai absoluto; dentro, sai relativo.
    assert item["pasta"] == str(sem_produto)
    assert item["png"] == str(sem_produto / "recortes" / "P01a.png")
    assert (item["largura_png"], item["altura_png"]) == (200, 100)
    assert item["clave"]["sign"] == "G"
    assert item["armadura"] == 1
    assert item["n_compassos"] == 2

    simbolos = [s for c in item["compassos"] for s in c["simbolos"]]
    assert simbolos
    assert all(s["homr_concorda"] is None for s in simbolos)
    assert all(s["tab_concorda"] is None for s in simbolos)
    assert item["discordancias"] == 0

    gravado = json.loads(saida.read_text(encoding="utf-8"))
    assert gravado["itens"][0]["id"] == "meu_video_de_tes_P01a"


def test_cli_preparar_sem_produto_grava_no_saida_informado(
    sem_produto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    saida = tmp_path / "diag" / "itens.json"
    codigo = main(
        ["preparar", "--saida", str(saida), "--sem-produto", f"{SLUG_SEM_PRODUTO}:P01a"]
    )
    assert codigo == 0
    assert json.loads(saida.read_text(encoding="utf-8"))["itens"][0]["fonte"] == (
        "audiveris/x2_margem_herdada"
    )
    saiu = capsys.readouterr().out
    assert "meu_video_de_tes_P01a" in saiu
    assert f"gravado: {saida}" in saiu


def test_cli_sem_produto_exige_slug_e_id() -> None:
    with pytest.raises(SystemExit):
        main(["preparar", "--sem-produto", "so_o_slug"])


def test_preparar_sem_produto_sem_leitura_herdada_e_erro(
    sem_produto: Path, tmp_path: Path
) -> None:
    (
        sem_produto
        / "omr"
        / "audiveris"
        / "x2_margem_herdada"
        / "P01a"
        / "saida.musicxml"
    ).unlink()
    saida = tmp_path / "itens.json"
    with pytest.raises(FileNotFoundError, match="sem leitura herdada"):
        preparar_sem_produto([(SLUG_SEM_PRODUTO, "P01a")], saida)
    assert not saida.exists()


def test_preparar_sem_produto_recorte_fora_do_indice_e_erro(
    sem_produto: Path, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match=r"não está em recortes/indice\.json"):
        preparar_sem_produto([(SLUG_SEM_PRODUTO, "P09a")], tmp_path / "itens.json")


def test_preparar_sem_produto_png_de_tamanho_errado_e_erro(
    sem_produto: Path, tmp_path: Path
) -> None:
    _png_do_tamanho(sem_produto / "recortes" / "P01a.png", 150, 100)
    with pytest.raises(ValueError, match="!= índice"):
        preparar_sem_produto([(SLUG_SEM_PRODUTO, "P01a")], tmp_path / "itens.json")


def test_preparar_sem_a_opcao_continua_igual_para_a_p1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recortes = tmp_path / "recortes"
    omr = tmp_path / "omr"
    monkeypatch.setattr("tab.partitura_gabarito.PASTA_RECORTES", recortes)
    monkeypatch.setattr("tab.partitura_gabarito.PASTA_OMR", omr)
    _png_do_tamanho(recortes / "R01.png", 200, 100)
    for pasta in (
        omr / "audiveris" / "x2_margem" / "R01",
        omr / "homr" / "nativo" / "R01",
    ):
        pasta.mkdir(parents=True)
        _gravar(pasta / "saida.musicxml", MUSICXML_BASE)
    indice = tmp_path / "indice.json"
    indice.write_text(
        json.dumps(
            [
                {
                    "id": "R01",
                    "origem": "p1",
                    "canal": "canal p1",
                    "video": "canal p1/v.mp4",
                    "tela": 1,
                    "largura": 200,
                    "altura": 100,
                }
            ]
        ),
        encoding="utf-8",
    )
    itens = preparar(indice=indice, saida=tmp_path / "itens.json")
    item = itens[0]
    assert item["id"] == "R01"
    assert item["fonte"] == "audiveris/x2_margem"
    assert "pasta" not in item and "recorte" not in item
    assert item["png"] == str(recortes / "R01.png")
    simbolos = [s for c in item["compassos"] for s in c["simbolos"]]
    # homr idêntico ao Audiveris: concorda em todas as notas; tab fica None (origem p1).
    notas = [s for s in simbolos if not s["pausa"] and not s["graca"]]
    assert notas and all(s["homr_concorda"] is True for s in notas)
    assert all(s["tab_concorda"] is None for s in simbolos)


def test_servidor_entrega_png_da_p1_e_do_sem_produto_e_recusa_o_resto(
    sem_produto: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recortes_p1 = tmp_path / "p1" / "recortes_margem"
    monkeypatch.setattr("tab.partitura_gabarito.PASTA_RECORTES", recortes_p1)
    _png_do_tamanho(recortes_p1 / "R01.png", 200, 100)
    fora = _png_do_tamanho(tmp_path / "fora" / "F01.png", 200, 100)

    sem = preparar_sem_produto([(SLUG_SEM_PRODUTO, "P01a")], tmp_path / "sem.json")[0]
    da_p1 = _item("R01")
    da_p1["png"] = str(recortes_p1 / "R01.png")
    intruso = _item("F01")
    intruso["png"] = str(fora)
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(
        json.dumps({"formato": 1, "itens": [da_p1, sem, intruso]}), encoding="utf-8"
    )

    srv = criar_servidor(itens_path, tmp_path / "gabarito.json", porta=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    porta = srv.server_address[1]
    try:
        for id_ in ("R01", "meu_video_de_tes_P01a"):
            status, dados = _pedido(porta, "GET", f"/recorte/{id_}.png")
            assert status == 200, id_
            assert dados.startswith(b"\x89PNG\r\n\x1a\n")
        status, _ = _pedido(porta, "GET", "/recorte/F01.png")
        assert status == 404
        status, _ = _pedido(porta, "GET", "/recorte/nao_existe.png")
        assert status == 404
    finally:
        srv.shutdown()
        srv.server_close()


def test_servidor_confere_recorte_sem_produto_com_id_com_sublinhado(
    sem_produto: Path, tmp_path: Path
) -> None:
    sem = preparar_sem_produto([(SLUG_SEM_PRODUTO, "P01a")], tmp_path / "sem.json")[0]
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(json.dumps({"formato": 1, "itens": [sem]}), encoding="utf-8")
    ouro = tmp_path / "gabarito.json"
    srv = criar_servidor(itens_path, ouro, porta=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    porta = srv.server_address[1]
    try:
        status, dados = _pedido(porta, "GET", "/itens")
        assert status == 200
        corpo = json.loads(dados)
        assert corpo["itens"][0]["origem"] == "sem_produto"
        assert corpo["progresso"]["total"] == 1

        simbolos = [s for c in sem["compassos"] for s in c["simbolos"]]
        status, _ = _pedido(
            porta,
            "POST",
            "/salvar",
            _corpo(sem["id"], [(s["idx"], "certo") for s in simbolos]),
        )
        assert status == 200
        gravado = json.loads(ouro.read_text(encoding="utf-8"))
        registro = gravado["recortes"][sem["id"]]
        assert registro["confirmado"] is True
        assert registro["fonte"] == "audiveris/x2_margem_herdada"
        assert all("homr_concorda" not in s["palpite"] for s in registro["simbolos"])
    finally:
        srv.shutdown()
        srv.server_close()
