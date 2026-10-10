"""MusicXML: o produto que o dono do projeto pediu, com as inferências declaradas.

O que se afere aqui é o **formato e as decisões**, não a acurácia: se a duração é
inferida, se nota que não é algarismo não vira nota, e se a afinação vira `staff-tuning`
de verdade. O alvo declarado é o esqueleto entregue pelo dono (score-partwise 4.0,
clef TAB linha 5, 6 linhas, `technical/string`+`fret`).
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from tab.esquema import ESQUEMA
from tab.musicxml import TICKS_COMPASSO, exportar, midi_da_corda, pitch_de_midi


def test_midi_e_pitch_da_corda() -> None:
    """Corda 5, casa 3 é Dó 3 — exatamente o exemplo que o dono do projeto entregou."""
    assert midi_da_corda(5, 3) == 48
    assert pitch_de_midi(48) == ("C", 0, 3)
    assert midi_da_corda(6, 0) == 40  # E2, corda grave solta
    assert midi_da_corda(1, 0) == 64  # E4, corda aguda solta
    assert midi_da_corda(9, 0) is None  # corda que não existe


def _transcricao() -> dict:
    return {
        "passo": 30.0,
        "notas": [
            {
                "ordem": 1,
                "corda": 5,
                "casa": "3",
                "tecnica": None,
                "compasso": 1,
                "t_ini": 0.0,
                "confianca": 0.9,
            },
            {
                "ordem": 2,
                "corda": 4,
                "casa": "2",
                "tecnica": "harmonico",
                "compasso": 1,
                "t_ini": 2.0,
                "confianca": 0.8,
            },
            {
                "ordem": 3,
                "corda": 3,
                "casa": "junk",
                "tecnica": None,
                "compasso": 1,
                "t_ini": 3.0,
                "confianca": 0.0,
            },
            {
                "ordem": 4,
                "corda": 2,
                "casa": "12",
                "tecnica": None,
                "compasso": 2,
                "t_ini": 4.0,
                "confianca": 0.7,
            },
        ],
    }


def test_xml_e_valido_e_tem_o_esqueleto_pedido() -> None:
    """O arquivo abre, e traz clef TAB, 6 linhas, staff-tuning e technical."""
    xml, _ = exportar(_transcricao(), titulo="teste")
    raiz = ET.fromstring(xml)
    assert raiz.tag == "score-partwise"
    assert raiz.get("version") == "4.0"
    assert raiz.findtext("part-list/score-part/part-name") == "Guitarra (Tab)"
    assert raiz.findtext("part/measure/attributes/clef/sign") == "TAB"
    assert raiz.findtext("part/measure/attributes/clef/line") == "5"
    detalhes = raiz.find("part/measure/attributes/staff-details")
    assert detalhes is not None
    assert detalhes.findtext("staff-lines") == "6"
    assert len(detalhes.findall("staff-tuning")) == 6

    primeira = raiz.find("part/measure/note")
    tecnico = primeira.find("notations/technical")
    assert tecnico.findtext("string") == "5"
    assert tecnico.findtext("fret") == "3"
    assert primeira.findtext("pitch/step") == "C"
    assert primeira.findtext("pitch/octave") == "3"


def test_nota_que_nao_e_algarismo_nao_vira_nota() -> None:
    """`junk` não pode virar pitch: "sem nota inventada" é critério de pronto."""
    xml, relatorio = exportar(_transcricao(), titulo="teste")
    assert relatorio["notas_exportadas"] == 3
    assert relatorio["notas_nao_exportadas"] == 1
    assert relatorio["motivo_nao_exportada"] == ["junk"]
    assert xml.count("<note>") == 3


def test_duracao_inferida_e_declarada_como_inferida() -> None:
    """As durações vêm do intervalo entre onsets, e o relatório diz isso."""
    xml, relatorio = exportar(_transcricao(), titulo="teste")
    assert relatorio["pulso_s"] == 2.0
    assert relatorio["bpm_derivado_do_pulso"] == 30.0
    assert "INFERIDA" in relatorio["duracao"]
    raiz = ET.fromstring(xml)
    duracoes = [n.findtext("duration") for n in raiz.findall("part/measure/note")]
    assert duracoes[:2] == ["1024", "1024"]  # 2 s de pulso = um pulso = 1024 ticks


def test_tecnica_conhecida_vira_elemento_e_desconhecida_nao() -> None:
    """Técnica mapeada entra em `notations/technical`; o resto fica só no JSON."""
    xml, _ = exportar(_transcricao(), titulo="teste")
    assert "<harmonic" in xml.replace(" ", "").replace("/>", ">")
    assert "hammer-on" not in xml


def test_sem_tempo_o_exportador_nao_inventa_pulso() -> None:
    """Sem onset não há pulso: o relatório declara e usa 1 s como suposição."""
    r = {"notas": [{"ordem": 1, "corda": 1, "casa": "0", "compasso": 1}]}
    xml, relatorio = exportar(r, titulo="sem_tempo")
    assert relatorio["pulso_s"] is None
    assert relatorio["bpm_derivado_do_pulso"] is None
    assert ET.fromstring(xml).find("part/measure/note") is not None


def test_tempo_degenerado_nao_vira_ritmo() -> None:
    """144 notas no MESMO instante não é ritmo: o exportador tem de declarar.

    Medido nesta noite num vídeo do `sky guitar`: o cursor não foi encontrado, o
    pipeline carimbou todas as notas no mesmo instante e o arquivo sairia com ritmo
    falso. É a mesma classe do erro histórico "323 notas com tempo" (eram 3 instantes).
    """
    r = {
        "notas": [
            {"ordem": i + 1, "corda": 1, "casa": "3", "compasso": 1, "t_ini": 468.57}
            for i in range(10)
        ]
    }
    _, relatorio = exportar(r, titulo="degenerado")
    assert relatorio["tempo_medido"] is False
    assert relatorio["instantes_distintos"] == 1
    assert relatorio["pulso_s"] is None
    assert "NÃO medida" in relatorio["duracao"]


def test_tempo_bom_e_aceito() -> None:
    """Com onsets distintos, o tempo é dado como medido (inferido na duração)."""
    r = {
        "notas": [
            {"ordem": i + 1, "corda": 1, "casa": "3", "compasso": 1, "t_ini": i * 0.5}
            for i in range(10)
        ]
    }
    _, relatorio = exportar(r, titulo="bom")
    assert relatorio["tempo_medido"] is True
    assert relatorio["instantes_distintos"] == 10
    assert relatorio["pulso_s"] == 0.5


def _nv(
    tela: int,
    coluna: int,
    corda: int,
    casa: int,
    x: float,
    t: float | None = None,
    passagem: int = 1,
) -> dict:
    """Uma entrada do v1 com ``x_quadro``, que a ordem por x precisa."""
    return {
        "tela": tela,
        "passagem": passagem,
        "exibicao": None if t is None else 0,
        "coluna": coluna,
        "corda": corda,
        "casa": casa,
        "x_quadro": x,
        "compasso": 1,
        "tecnica": None,
        "confianca": 0.9,
        "t_ini": t,
    }


def _v1_telas(notas: list[dict], telas: list[dict]) -> dict:
    """JSON v1 com telas (barras e passo) para a exportação de partitura."""
    return {
        "esquema": ESQUEMA,
        "video": {},
        "telas": telas,
        "nao_notas": [],
        "notas": notas,
    }


def _tela(id_: int, barras: list[int], passo: float = 20.0) -> dict:
    """Uma tela com barras; os campos que ``exportar`` lê."""
    return {"id": id_, "passo": passo, "barlines_x": barras}


def _fretes(raiz: ET.Element) -> list[str]:
    """Casas na ordem em que saem no XML."""
    return [f.text for f in raiz.iter("fret")]


def test_v1_ordem_e_de_partitura_nao_de_tempo() -> None:
    """Tela 2 com t_ini ANTERIOR à tela 1 continua depois da tela 1.

    É o relato do dono: a parte final da primeira tela aparecia no começo porque o
    primeiro t_ini a punha na frente. A ordem é tela (id) e coluna (x).
    """
    telas = [_tela(1, [10, 300, 600]), _tela(2, [10, 300, 600])]
    notas = [
        _nv(2, 1, 1, 0, 50, t=5.0),
        _nv(1, 2, 2, 1, 120, t=20.0),
        _nv(1, 1, 3, 2, 50, t=30.0),
        _nv(1, 1, 3, 2, 50, t=2.0, passagem=2),  # mesma nota, passagem antiga
    ]
    xml, rel = exportar(_v1_telas(notas, telas))
    raiz = ET.fromstring(xml)
    # tela 1 (col 1: corda 3 casa 2; col 2: corda 2 casa 1), depois tela 2 (corda 1 casa 0)
    assert _fretes(raiz) == ["2", "1", "0"]
    assert rel["notas_exportadas"] == 3
    assert rel["tempo_usado"] is False


def test_v1_compasso_segue_a_barra_da_tela() -> None:
    """Primeiro compasso = colunas antes da 1a barra útil; uma barra por compasso.

    Tela com barras 10, 300, 600 e notas em x 50, 120 (compasso 1) e 350 (compasso 2).
    """
    telas = [_tela(1, [10, 300, 600])]
    notas = [
        _nv(1, 1, 1, 0, 50),
        _nv(1, 2, 2, 0, 120),
        _nv(1, 3, 3, 0, 350),
    ]
    xml, rel = exportar(_v1_telas(notas, telas))
    raiz = ET.fromstring(xml)
    medidas = raiz.findall("part/measure")
    assert len(medidas) == 2
    assert [len(m.findall("note")) for m in medidas] == [2, 1]
    assert rel["compassos"] == 2
    assert rel["compassos_por_tela"] == {1: 2}


def test_v1_compasso_2_4_declarado_e_duracao_uniforme() -> None:
    """2/4 declarado, cada compasso soma 2048 ticks e as colunas dividem igual."""
    telas = [_tela(1, [10, 300, 600])]
    notas = [_nv(1, c, 1, 0, 50 + 20 * c) for c in range(1, 5)]
    xml, rel = exportar(_v1_telas(notas, telas))
    raiz = ET.fromstring(xml)
    assert raiz.find(".//time/beats").text == "2"
    assert raiz.find(".//time/beat-type").text == "4"
    somas = [
        sum(
            int(n.findtext("duration"))
            for n in m.findall("note")
            if n.find("chord") is None
        )
        for m in raiz.findall("part/measure")
    ]
    assert somas == [TICKS_COMPASSO]
    assert "NÃO medida" in rel["duracao"]
    decl = {
        c.get("name"): c.text
        for c in raiz.findall("identification/miscellaneous/miscellaneous-field")
    }
    assert "2/4 é DECLARADA" in decl["compasso"]
    assert "UMA vez" in decl["repeticoes"]


def test_v1_acorde_fica_na_mesma_coluna_e_soma_uma_vez() -> None:
    """Notas da mesma coluna viram ``chord`` e dividem o mesmo intervalo do compasso."""
    telas = [_tela(1, [10, 600])]
    notas = [
        _nv(1, 1, 1, 0, 50),
        _nv(1, 1, 2, 1, 50),
        _nv(1, 2, 3, 2, 150),
        _nv(1, 3, 4, 3, 250),
    ]
    xml, _ = exportar(_v1_telas(notas, telas))
    raiz = ET.fromstring(xml)
    assert len(raiz.findall(".//chord")) == 1
    cabecas = [n for n in raiz.findall(".//note") if n.find("chord") is None]
    assert len(cabecas) == 3


def test_v1_barra_que_e_traco_duplo_e_fundida() -> None:
    """Duas barras a 4 px (traço duplo) viram uma; a segunda não cria compasso."""
    telas = [_tela(1, [10, 300, 304, 600])]
    notas = [_nv(1, 1, 1, 0, 150), _nv(1, 2, 2, 0, 450)]
    xml, rel = exportar(_v1_telas(notas, telas))
    assert len(ET.fromstring(xml).findall("part/measure")) == 2
    assert rel["telas"][1]["fundidas"] == 1


def test_v1_haste_lida_como_barra_e_removida() -> None:
    """Segmento de 1 a 3 notas e largura < metade da mediana sai (haste).

    Medido na tela 1 do `retrato brasileiro`: barra em 1181 entre 1012 e 1440, com 3 notas
    de um lado, 169 px, contra 420 a 470 px dos outros compassos.
    """
    barras = [94, 592, 1012, 1181, 1440, 1841]
    telas = [_tela(1, barras)]
    notas = [
        _nv(1, 1, 1, 0, 200),
        _nv(1, 2, 2, 0, 400),
        _nv(1, 3, 3, 0, 700),
        _nv(1, 4, 4, 0, 800),
        _nv(1, 5, 5, 0, 1050),
        _nv(1, 6, 6, 0, 1100),
        _nv(1, 7, 1, 0, 1150),
        _nv(1, 8, 2, 0, 1300),
        _nv(1, 9, 3, 0, 1500),
        _nv(1, 10, 4, 0, 1600),
    ]
    xml, rel = exportar(_v1_telas(notas, telas))
    medidas = ET.fromstring(xml).findall("part/measure")
    # 4 compassos: 94-592, 592-1012, 1012-1440 (com a haste de 1181 fora), 1440-1841
    assert len(medidas) == 4
    assert [len(m.findall("note")) for m in medidas] == [2, 2, 4, 2]
    assert rel["telas"][1]["hastes_removidas"] == [1181]
    assert rel["notas_exportadas"] == 10


def test_v1_nota_que_nao_e_algarismo_nao_vira_nota() -> None:
    """Casa fora dos algarismos não entra no XML (e é contada)."""
    telas = [_tela(1, [10, 600])]
    notas = [_nv(1, 1, 1, 0, 50), {**_nv(1, 2, 2, 0, 150), "casa": "junk"}]
    xml, rel = exportar(_v1_telas(notas, telas))
    assert xml.count("<note>") == 1
    assert rel["notas_nao_exportadas"] == 1
    assert rel["motivo_nao_exportada"] == ["junk"]


def test_v1_tela_sem_barra_vira_um_compasso_declarado() -> None:
    """Sem barra, a tela é um compasso só, e o relatório diz que não havia barra."""
    telas = [_tela(1, [])]
    notas = [_nv(1, 1, 1, 0, 50), _nv(1, 2, 2, 0, 150)]
    _, rel = exportar(_v1_telas(notas, telas))
    assert rel["telas"][1]["sem_barra"] is True
    assert rel["compassos"] == 1
