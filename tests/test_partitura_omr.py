"""Testes da avaliação de OMR (funções puras; MusicXML e notas sintéticos; sem acervo)."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import cv2
import numpy as np
import pytest

from tab.partitura_avaliar import (
    NotaXML,
    alinhar,
    contar,
    eventos_da_biblioteca,
    ler_musicxml,
    referencia_do_recorte,
)
from tab.partitura_omr import (
    Cabecalho,
    armadura_do_video,
    comando,
    compor_cabecalho,
    herdar_armadura,
    herdar_condicao,
    preparar_entrada,
)

MUSICXML_VOZES = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>2</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration>
        <type>quarter</type></note>
      <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
        <type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave><alter>1</alter></pitch>
        <duration>4</duration><type>half</type><dot/></note>
      <note><rest/><duration>2</duration><type>quarter</type></note>
      <backup><duration>8</duration></backup>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>8</duration>
        <type>whole</type></note>
    </measure>
    <measure number="2">
      <attributes><divisions>4</divisions></attributes>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration>
        <type>quarter</type></note>
      <note><grace/><pitch><step>B</step><octave>4</octave></pitch>
        <type>eighth</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration>
        <type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
"""


def _escrever(tmp_path: Path, conteudo: str) -> Path:
    """Grava um MusicXML de teste e devolve o caminho."""
    caminho = tmp_path / "saida.musicxml"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def _nota(t: float, midi: int, ornamento: bool = False) -> NotaXML:
    """Nota sintética para os testes de agrupamento."""
    return NotaXML(
        parte=1,
        compasso="1",
        t=t,
        midi=midi,
        duracao=0.0 if ornamento else 1.0,
        tipo=None,
        pontuada=False,
        ornamento=ornamento,
        pauta=1,
    )


def test_parser_acorde_backup_divisions_e_graca(tmp_path: Path) -> None:
    """Acorde no mesmo instante, duas vozes com backup, divisions e graça."""
    partitura = ler_musicxml(_escrever(tmp_path, MUSICXML_VOZES))
    assert partitura.partes == 1
    assert partitura.compassos == 2
    por_midi = {(n.midi, n.compasso): n for n in partitura.notas}

    # Compasso 1: C4 no tempo 0; E4 é acorde com C4 (mesmo instante, não avança).
    assert por_midi[(60, "1")].t == 0.0
    assert por_midi[(64, "1")].t == 0.0
    # D#4 começa depois da nota de 1 tempo (C4 ocupou 1 semínima, no divisions=2).
    assert por_midi[(63, "1")].t == 1.0
    assert por_midi[(63, "1")].duracao == 2.0
    assert por_midi[(63, "1")].tipo == "half"
    # Backup de 4 semínimas volta ao zero: a voz 2 (G3) começa com o compasso.
    assert por_midi[(55, "1")].t == 0.0
    assert por_midi[(55, "1")].duracao == 4.0

    # Compasso 2 começa no máximo atingido no compasso 1 (4 semínimas), com divisions=4.
    assert por_midi[(69, "2")].t == 4.0
    assert por_midi[(69, "2")].duracao == 1.0
    # Nota de graça: duração 0, marcada, e não avança o tempo da nota seguinte.
    assert por_midi[(71, "2")].ornamento is True
    assert por_midi[(71, "2")].duracao == 0.0
    assert por_midi[(72, "2")].t == 5.0


def test_eventos_agrupam_por_instante_e_ignoram_graca(tmp_path: Path) -> None:
    """Notas no mesmo instante formam um evento; graça não entra na sequência."""
    partitura = ler_musicxml(_escrever(tmp_path, MUSICXML_VOZES))
    eventos = eventos_da_biblioteca(partitura.notas)
    assert eventos == [
        frozenset({60, 64, 55}),  # t=0: C4, E4 (acorde) e G3 (voz 2)
        frozenset({63}),  # t=1: D#4
        frozenset({69}),  # t=4: A4
        frozenset({72}),  # t=5: C5 (B4 de graça fora)
    ]


def test_oitava_de_clave_aplicada_e_transposicao_so_alerta(tmp_path: Path) -> None:
    """Clave com 8 embaixo volta para a escrita; transposição só vira alerta."""
    xml = MUSICXML_VOZES.replace(
        "<attributes><divisions>2</divisions></attributes>",
        "<attributes><divisions>2</divisions>"
        "<transpose><octave-change>-1</octave-change></transpose>"
        "<clef><clef-octave-change>-1</clef-octave-change></clef></attributes>",
        1,
    )
    partitura = ler_musicxml(_escrever(tmp_path, xml))
    assert len(partitura.alertas) == 2
    # C4 soado em clave de sol 8vb é escrito como C5 na clave de sol simples.
    assert partitura.notas[0].midi == 72


def test_alinhar_insercao_delecao_e_troca() -> None:
    """Inserção, deleção e troca saem como operações no alinhamento."""
    insercao = alinhar([frozenset({60})], [frozenset({60}), frozenset({64})])
    assert ("fal", -1, 1) in insercao
    delecao = alinhar(
        [frozenset({60}), frozenset({62}), frozenset({64})],
        [frozenset({60}), frozenset({64})],
    )
    assert [op for op, _, _ in delecao] == ["casa", "inv", "casa"]
    # Troca de dois eventos sem alturas em comum: o par é casado (erro de altura).
    troca = alinhar(
        [frozenset({60}), frozenset({64})], [frozenset({64}), frozenset({60})]
    )
    assert [op for op, _, _ in troca] == ["casa", "casa"]


def test_contagem_a_mao_exato_e_classe() -> None:
    """Exemplo feito à mão: uma altura errada (64 x 65), uma inventada, e classe."""
    ref = [frozenset({60, 65}), frozenset({62})]
    lib = [frozenset({60, 64}), frozenset({62}), frozenset({70})]
    exato, pares = contar(lib, ref, "exato")
    assert exato == {
        "referencia": 3,
        "certas": 2,
        "altura_errada": 1,
        "faltando": 0,
        "inventada": 1,
    }
    assert pares == [(64, 65)]

    # 60 da biblioteca contra 72 da referência: erro de oitava. No exato é altura
    # errada; na classe (mod 12) é certa.
    oitava_lib = [frozenset({60})]
    oitava_ref = [frozenset({72})]
    assert contar(oitava_lib, oitava_ref, "exato")[0]["altura_errada"] == 1
    classe, _ = contar(oitava_lib, oitava_ref, "classe")
    assert classe["certas"] == 1
    assert classe["altura_errada"] == 0


def test_referencia_agrupa_por_x_e_respeita_janela() -> None:
    """Notas do ouro: altura escrita = soada + 12; agrupamento por x; janela da caixa."""
    notas = [
        {"corda": 1, "casa": 0, "x_centro_quadro": 100.0},  # E4 soa 64, escrito 76
        {"corda": 6, "casa": "0", "x_centro_quadro": 103.0},  # E2 soa 40, escrito 52
        {"corda": 2, "casa": "3", "x_centro_quadro": 200.0},  # B3 soa 62, escrito 74
        {"corda": 1, "casa": 0, "x_centro_quadro": 500.0},  # fora da janela
    ]
    assert referencia_do_recorte(notas, 0.0, 300.0) == [
        frozenset({76, 52}),
        frozenset({74}),
    ]


def test_preparar_entrada_x2_amplia_2x_e_nativo_copia(tmp_path: Path) -> None:
    """A condição x2 dobra o tamanho; nativo copia os bytes sem alterar."""
    origem = tmp_path / "origem.png"
    cv2.imwrite(str(origem), np.full((5, 10, 3), 200, dtype=np.uint8))
    x2 = preparar_entrada(origem, "x2", tmp_path / "x2" / "entrada.png")
    assert cv2.imread(str(x2)).shape[:2] == (10, 20)
    nativo = preparar_entrada(origem, "nativo", tmp_path / "nat" / "entrada.png")
    assert nativo.read_bytes() == origem.read_bytes()


def test_comando_de_cada_biblioteca() -> None:
    """Argumentos de linha de comando de cada biblioteca."""
    entrada = Path("/app/x/entrada.png")
    pasta = Path("/app/x")
    assert comando("homr", entrada, pasta) == ["/opt/omr/bin/homr", str(entrada)]
    assert comando("oemer", entrada, pasta)[:3] == [
        "/opt/omr/bin/oemer",
        "-o",
        str(pasta),
    ]
    audiveris = comando("audiveris", entrada, pasta)
    assert audiveris[1:5] == ["-batch", "-export", "-output", str(pasta)]


def test_preparar_entrada_x3_e_x4_ampliam(tmp_path: Path) -> None:
    """x3 e x4 ampliam 3x e 4x, com o mesmo tamanho de linha de base."""
    origem = tmp_path / "origem.png"
    cv2.imwrite(str(origem), np.full((5, 10, 3), 200, dtype=np.uint8))
    x3 = preparar_entrada(origem, "x3", tmp_path / "x3" / "entrada.png")
    assert cv2.imread(str(x3)).shape[:2] == (15, 30)
    x4 = preparar_entrada(origem, "x4", tmp_path / "x4" / "entrada.png")
    assert cv2.imread(str(x4)).shape[:2] == (20, 40)


def test_preparar_entrada_binaria_so_tem_preto_e_branco(tmp_path: Path) -> None:
    """x2_binaria: cinza, 2x e Otsu; a saída só tem 0 e 255 e o dobro do tamanho."""
    origem = tmp_path / "origem.png"
    imagem = np.zeros((10, 12, 3), dtype=np.uint8)
    imagem[:, :6] = (250, 240, 200)  # fundo claro
    imagem[:, 6:] = (20, 30, 40)  # tinta escura
    cv2.imwrite(str(origem), imagem)
    binaria = preparar_entrada(origem, "x2_binaria", tmp_path / "b" / "entrada.png")
    lido = cv2.imread(str(binaria), cv2.IMREAD_GRAYSCALE)
    assert lido.shape == (20, 24)
    assert set(np.unique(lido).tolist()) <= {0, 255}
    assert lido[0, 0] == 255 and lido[0, 23] == 0


def test_cabecalho_soma_largura_e_alinha_a_primeira_linha(tmp_path: Path) -> None:
    """Cabeçalho colado: largura soma, linhas da pauta alinhadas, branco onde falta."""
    destino = np.full((20, 30, 3), 255, dtype=np.uint8)
    destino[5, :, :] = (0, 0, 0)  # 1ª linha da pauta do destino, na linha 5
    destino[7, 0, :] = (0, 0, 255)  # marca de conteúdo do destino
    origem_cab = np.full((40, 50, 3), 255, dtype=np.uint8)
    origem_cab[10, :, :] = (0, 0, 0)  # 1ª linha da pauta do cabeçalho, na linha 10
    origem_cab[30, 0:5, :] = (255, 0, 0)  # marca só no cabeçalho
    cab_path = tmp_path / "R05.png"
    cv2.imwrite(str(cab_path), origem_cab)
    cabecalho = Cabecalho(imagem=cab_path, x_fim=12, linha_origem=10, linha_destino=5)
    tela = compor_cabecalho(destino, cabecalho)
    # acima = 5 (a pauta do destino desce 5 linhas); altura = max(5+20, 40) = 40
    assert tela.shape == (40, 42, 3)
    assert tela[10, 0].tolist() == [0, 0, 0]  # linha da pauta do cabeçalho
    assert tela[10, 12].tolist() == [0, 0, 0]  # mesma linha, no destino (linha 5)
    assert tela[10, 11].tolist() == [0, 0, 0]  # a faixa colada termina em x=11
    assert tela[30, 0].tolist() == [255, 0, 0]  # marca só do cabeçalho
    assert tela[12, 12].tolist() == [0, 0, 255]  # marca do destino (linha 7 -> 12)
    assert tela[25, 0].tolist() == [255, 255, 255]  # abaixo do cabeçalho? não: vazio
    assert tela[39, 12].tolist() == [255, 255, 255]  # abaixo do destino: branco
    # preparar_entrada soma a largura e dobra tudo na x2
    dest_path = tmp_path / "R06.png"
    cv2.imwrite(str(dest_path), destino)
    saida = preparar_entrada(
        dest_path, "x2_cabecalho", tmp_path / "c" / "entrada.png", cabecalho
    )
    assert cv2.imread(str(saida)).shape[:2] == (80, 84)
    # sem cabeçalho, x2_cabecalho é x2 pura
    pura = preparar_entrada(dest_path, "x2_cabecalho", tmp_path / "p" / "entrada.png")
    assert cv2.imread(str(pura)).shape[:2] == (40, 60)


def _partitura_sem_armadura(*compassos: str, atributos: str = "") -> str:
    """MusicXML mínimo sem armadura; cada argumento é o conteúdo de um compasso."""
    corpo = ""
    for i, conteudo in enumerate(compassos, start=1):
        cabeca = ""
        if i == 1:
            cabeca = f"<attributes><divisions>1</divisions>{atributos}</attributes>"
        corpo += f'<measure number="{i}">{cabeca}{conteudo}</measure>'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<score-partwise version="4.0"><part-list><score-part id="P1">'
        "<part-name>G</part-name></score-part></part-list>"
        f'<part id="P1">{corpo}</part></score-partwise>'
    )


def _nota_xml(step: str, octave: int, extra: str = "", alter: str = "") -> str:
    """Nota de 1 tempo com pitch; ``extra`` (ex.: accidental) vai depois do tipo."""
    alter_xml = f"<alter>{alter}</alter>" if alter else ""
    return (
        f"<note><pitch><step>{step}</step>{alter_xml}<octave>{octave}</octave></pitch>"
        f"<duration>1</duration><type>quarter</type>{extra}</note>"
    )


def _alteracoes(xml: str) -> list[str]:
    """Para cada nota com pitch, a ``step``+``octave`` e o ``alter`` (ou ``-``)."""
    saida = []
    for nota in ET.fromstring(xml).iter("note"):
        pitch = nota.find("pitch")
        if pitch is None:
            continue
        alter = pitch.findtext("alter") or "-"
        saida.append(f"{pitch.findtext('step')}{pitch.findtext('octave')}={alter}")
    return saida


def test_herdar_armadura_sustenido_cria_key_e_alter() -> None:
    """Com 1 sustenido, F sem acidente vira F#; C e B (fora da armadura) não mudam."""
    xml = _partitura_sem_armadura(
        _nota_xml("F", 4) + _nota_xml("C", 4) + _nota_xml("F", 5)
    )
    saida = herdar_armadura(xml, 1)
    assert "<key><fifths>1</fifths></key>" in saida
    assert _alteracoes(saida) == ["F4=1", "C4=-", "F5=1"]


def test_herdar_armadura_bemol_aplica_menos_um() -> None:
    """Com 2 bemóis (B e E), B e E sem acidente recebem -1; A não."""
    xml = _partitura_sem_armadura(
        _nota_xml("B", 3) + _nota_xml("E", 4) + _nota_xml("A", 4)
    )
    assert _alteracoes(herdar_armadura(xml, -2)) == ["B3=-1", "E4=-1", "A4=-"]


def test_herdar_armadura_nota_com_accidental_nao_muda() -> None:
    """Nota com <accidental>natural</accidental> mantém o próprio alter."""
    xml = _partitura_sem_armadura(
        _nota_xml("F", 4, extra="<accidental>natural</accidental>")
    )
    assert _alteracoes(herdar_armadura(xml, 1)) == ["F4=-"]


def test_herdar_armadura_segue_natural_explicito_no_compasso() -> None:
    """Depois de F natural explícito no compasso, o F seguinte não é alterado."""
    xml = _partitura_sem_armadura(
        _nota_xml("F", 4, extra="<accidental>natural</accidental>")
        + _nota_xml("F", 4)
        + _nota_xml("F", 5)
    )
    # A F5 é outra altura: sem acidente próprio, recebe a armadura.
    assert _alteracoes(herdar_armadura(xml, 1)) == ["F4=-", "F4=-", "F5=1"]


def test_herdar_armadura_proximo_compasso_volta_a_aplicar() -> None:
    """O natural explícito vale só no compasso em que aparece."""
    xml = _partitura_sem_armadura(
        _nota_xml("F", 4, extra="<accidental>natural</accidental>"),
        _nota_xml("F", 4),
    )
    assert _alteracoes(herdar_armadura(xml, 1)) == ["F4=-", "F4=1"]


def test_herdar_armadura_step_fora_da_armadura_nao_muda() -> None:
    """Com 1 sustenido, só F é alterado; C, G, D e A continuam naturais."""
    xml = _partitura_sem_armadura(
        _nota_xml("C", 4) + _nota_xml("G", 4) + _nota_xml("D", 4) + _nota_xml("A", 4)
    )
    assert _alteracoes(herdar_armadura(xml, 1)) == ["C4=-", "G4=-", "D4=-", "A4=-"]


def test_herdar_armadura_nao_aplica_duas_vezes() -> None:
    """Partitura que já tem fifths=1 volta igual: a armadura não é somada de novo."""
    xml = _partitura_sem_armadura(
        _nota_xml("F", 4, alter="1"),
        atributos="<key><fifths>1</fifths></key>",
    )
    assert herdar_armadura(xml, 1) == xml


def test_herdar_armadura_substitui_key_com_fifths_zero() -> None:
    """Key com fifths 0 é trocado pelo valor pedido, e o modo é mantido."""
    xml = _partitura_sem_armadura(
        _nota_xml("F", 4),
        atributos="<key><fifths>0</fifths><mode>major</mode></key>",
    )
    saida = herdar_armadura(xml, 1)
    assert saida.count("<key>") == 1
    assert "<fifths>1</fifths><mode>major</mode>" in saida
    assert _alteracoes(saida) == ["F4=1"]


def test_herdar_armadura_zero_e_fora_do_intervalo() -> None:
    """Armadura 0 não muda o texto; valor fora de -7..7 é erro."""
    xml = _partitura_sem_armadura(_nota_xml("F", 4))
    assert herdar_armadura(xml, 0) == xml
    with pytest.raises(ValueError):
        herdar_armadura(xml, 8)


def _leitura(fifths: int | None, clave: bool = True) -> str:
    """Leitura MusicXML com clave (opcional) e armadura (None = sem ``<key>``)."""
    clef = "<clef><sign>G</sign><line>2</line></clef>" if clave else ""
    key = "" if fifths is None else f"<key><fifths>{fifths}</fifths></key>"
    return _partitura_sem_armadura(_nota_xml("G", 4), atributos=f"{clef}{key}")


def test_armadura_do_video_pela_maioria_das_com_clave() -> None:
    """Leituras sem clave não contam: a maioria entre as com clave é 2."""
    leituras = [_leitura(2), _leitura(2), _leitura(1), _leitura(5, clave=False)]
    assert armadura_do_video(leituras) == 2


def test_armadura_do_video_sem_clave_em_nenhuma_e_none() -> None:
    """Nenhuma leitura com clave: não há armadura a herdar."""
    assert armadura_do_video([_leitura(1, clave=False), _leitura(0, False)]) is None
    assert armadura_do_video([]) is None


def test_armadura_do_video_sem_key_conta_como_zero() -> None:
    """Clave sem ``<key>`` vota 0: duas delas vencem uma com fifths 1."""
    leituras = [_leitura(None), _leitura(None), _leitura(1)]
    assert armadura_do_video(leituras) == 0


def test_armadura_do_video_empate_menor_absoluto_depois_menor() -> None:
    """Empate de 1 a 1: |-1| < |2| vence; empate de 2 e -2 fica com -2."""
    assert armadura_do_video([_leitura(3), _leitura(-1)]) == -1
    assert armadura_do_video([_leitura(2), _leitura(-2)]) == -2


def test_herdar_condicao_aplica_so_onde_falta_clave(tmp_path: Path) -> None:
    """R01 tem clave (fifths 1); R02 do mesmo vídeo não tem: recebe 1 sustenido.

    R03 é de outro vídeo, sem leitura: fica sem saída e não recebe nada.
    """
    base = tmp_path
    pasta_origem = tmp_path / "x2_margem"
    indice = [
        {"id": "R01", "video": "v1"},
        {"id": "R02", "video": "v1"},
        {"id": "R03", "video": "v2"},
    ]
    com_clave = _leitura(1)
    sem_clave = _partitura_sem_armadura(_nota_xml("F", 4))
    for id_, texto in (("R01", com_clave), ("R02", sem_clave)):
        pasta = pasta_origem / id_
        pasta.mkdir(parents=True)
        (pasta / "saida.musicxml").write_text(texto, encoding="utf-8")
    execucoes = [
        {"id": "R01", "ok": True, "saida": "x2_margem/R01/saida.musicxml"},
        {"id": "R02", "ok": True, "saida": "x2_margem/R02/saida.musicxml"},
        {"id": "R03", "ok": False, "saida": None, "motivo": "timeout 300 s"},
    ]
    destino = tmp_path / "x2_margem_herdada"
    herdada = herdar_condicao(execucoes, indice, destino, base)

    assert herdada == [
        {"id": "R01", "video": "v1", "tinha_clave": True, "fifths_aplicado": None},
        {"id": "R02", "video": "v1", "tinha_clave": False, "fifths_aplicado": 1},
        {"id": "R03", "video": "v2", "tinha_clave": False, "fifths_aplicado": None},
    ]
    saida_r02 = (destino / "R02" / "saida.musicxml").read_text(encoding="utf-8")
    assert "<fifths>1</fifths>" in saida_r02
    assert _alteracoes(saida_r02) == ["F4=1"]
    assert (destino / "R01" / "saida.musicxml").read_text(encoding="utf-8") == com_clave
    assert not (destino / "R03").exists()

    execucao = json.loads((destino / "execucao.json").read_text(encoding="utf-8"))
    assert [r["saida"] for r in execucao] == [
        "x2_margem_herdada/R01/saida.musicxml",
        "x2_margem_herdada/R02/saida.musicxml",
        None,
    ]
    assert execucao[2]["motivo"] == "timeout 300 s"
    registros = json.loads((destino / "herdada.json").read_text(encoding="utf-8"))
    assert registros == herdada
