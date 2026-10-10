"""MusicXML: o produto que o dono do projeto pediu, com as inferências declaradas.

O que se afere aqui é o **formato e as decisões**, não a acurácia: se a duração é
inferida, se nota que não é algarismo não vira nota, e se a afinação vira `staff-tuning`
de verdade. O alvo declarado é o esqueleto entregue pelo dono (score-partwise 4.0,
clef TAB linha 5, 6 linhas, `technical/string`+`fret`).
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from tab.esquema import ESQUEMA
from tab.musicxml import exportar, midi_da_corda, pitch_de_midi


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


def _nota(
    coluna: int, corda: int, casa: int, t: float | None, passagem: int = 1
) -> dict:
    """Uma entrada do v1 (uma passagem), com os campos que o exportador lê."""
    return {
        "tela": 1,
        "passagem": passagem,
        "exibicao": None if t is None else 0,
        "coluna": coluna,
        "corda": corda,
        "casa": casa,
        "compasso": 1,
        "tecnica": None,
        "t_ini": t,
    }


def _v1(notas: list[dict]) -> dict:
    return {
        "esquema": ESQUEMA,
        "video": {},
        "telas": [],
        "nao_notas": [],
        "notas": notas,
    }


def test_v1_notas_distintas_em_ordem_de_tempo() -> None:
    """Uma nota repetida em outra passagem conta uma vez, e a ordem é a do tempo."""
    notas = [
        _nota(1, 2, 0, 10.0),
        _nota(2, 3, 5, 11.0),
        _nota(3, 4, 2, 12.5),
        _nota(2, 3, 5, 20.0, passagem=2),
    ]
    xml, rel = exportar(_v1(notas))
    raiz = ET.fromstring(xml)
    assert [f.text for f in raiz.iter("fret")] == ["0", "5", "2"]
    assert rel["notas_exportadas"] == 3
    assert rel["tempo_medido"] is True


def test_v1_sem_tempo_declara_duracao_constante() -> None:
    """Sem onset, a ordem é de tela e coluna, e a duração constante é declarada."""
    notas = [_nota(2, 3, 5, None), _nota(1, 2, 0, None)]
    xml, rel = exportar(_v1(notas))
    raiz = ET.fromstring(xml)
    assert [f.text for f in raiz.iter("fret")] == ["0", "5"]
    assert len({d.text for d in raiz.iter("duration")}) == 1
    assert rel["tempo_medido"] is False
    assert "NÃO medida" in rel["duracao"]


def test_v1_acorde_nao_infla_o_compasso() -> None:
    """Notas do mesmo ataque viram ``chord`` e não somam tempo ao compasso.

    Quatro notas em três ataques (10, 10, 11, 12 s) com pulso de 1 s dão 3 batidas, não 4.
    """
    notas = [
        _nota(1, 1, 0, 10.0),
        _nota(1, 2, 1, 10.0),
        _nota(2, 3, 2, 11.0),
        _nota(3, 4, 3, 12.0),
    ]
    xml, rel = exportar(_v1(notas))
    raiz = ET.fromstring(xml)
    assert len(raiz.findall(".//chord")) == 1
    assert raiz.find(".//time/beats").text == "3"
    assert rel["instantes_distintos"] == 3
