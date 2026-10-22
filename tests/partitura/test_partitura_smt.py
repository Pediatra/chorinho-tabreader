"""Testes do runner SMT (funções puras; sem modelo e sem rede).

O teste da conversão kern -> MusicXML precisa do music21, que só existe no venv
``/opt/smt``: nas outras execuções ele é pulado, e roda com
``/opt/smt/bin/python -m pytest tests/test_partitura_smt.py``.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tab.partitura.smt import (
    MODELOS,
    acrescentar_cabecalho,
    dimensoes_pagina,
    dimensoes_sistema,
    gravar_execucao,
    juntar_tokens,
    krn_para_musicxml,
    modelo_por_id,
    normalizar_ekern,
)

KRN_TRES_SEMIMINIMAS = "**kern\n*M3/4\n*clefG2\n=1\n4c\n4d\n4e\n*-\n"


def test_juntar_tokens_troca_marcadores_como_o_trainer() -> None:
    tokens = ["**kern", "<t>", "**kern", "<b>", "4c", "<s>", "4d", "<b>", "*-"]

    assert juntar_tokens(tokens) == "**kern\t**kern\n4c 4d\n*-"


def test_dimensoes_sistema_segue_prepare_data() -> None:
    # altura mínima 256; largura no máximo 3056 antes de reduzir
    assert dimensoes_sistema(150, 1000, 1.0) == (256, 1000)
    assert dimensoes_sistema(300, 4000, 1.0) == (300, 3056)
    # câmera: reduce_ratio 0.85 nas duas dimensões (ceil de 256*0.85 = 217,6)
    assert dimensoes_sistema(150, 1000, 0.85) == (218, 850)


def test_dimensoes_pagina_sem_altura_minima() -> None:
    assert dimensoes_pagina(1000, 2000, 1.0) == (1000, 2000)
    assert dimensoes_pagina(101, 99, 0.85) == (86, 85)


def test_acrescentar_cabecalho_dois_spines() -> None:
    krn = "*clefG2\t*clefF4\n4c\t4e"

    texto, spines = acrescentar_cabecalho(krn)

    assert spines == 2
    assert texto == "**kern\t**kern\n*clefG2\t*clefF4\n4c\t4e"


def test_acrescentar_cabecalho_uma_spine() -> None:
    texto, spines = acrescentar_cabecalho("*clefG2\n4c")

    assert spines == 1
    assert texto == "**kern\n*clefG2\n4c"


def test_modelo_por_id_conhece_so_os_baixaveis() -> None:
    assert modelo_por_id("PRAIG/smt-fp-grandstaff").tipo == "pagina"
    with pytest.raises(ValueError):
        modelo_por_id("PRAIG/smt-fp-mozarteum")


def test_revisoes_sao_hashes_de_commit() -> None:
    for modelo in MODELOS:
        assert len(modelo.revisao) == 40
        int(modelo.revisao, 16)


def _registro(id_: str, ok: bool) -> dict:
    return {
        "id": id_,
        "ok": ok,
        "motivo": None if ok else "kern malformado",
        "segundos": 1.5,
        "codigo": 0,
        "saida": f"x/{id_}/saida.musicxml" if ok else None,
    }


def test_gravar_execucao_mantem_formato_e_ids_nao_rodados(tmp_path: Path) -> None:
    gravar_execucao(tmp_path, [_registro("R02", True), _registro("R01", False)])
    gravar_execucao(tmp_path, [_registro("R01", True)])

    registros = json.loads((tmp_path / "execucao.json").read_text(encoding="utf-8"))

    assert [r["id"] for r in registros] == ["R01", "R02"]
    assert registros[0]["ok"] is True
    assert set(registros[0]) == {"id", "ok", "motivo", "segundos", "codigo", "saida"}


def test_krn_para_musicxml_tres_seminimas(tmp_path: Path) -> None:
    pytest.importorskip("music21")
    destino = tmp_path / "saida.musicxml"

    resumo = krn_para_musicxml(KRN_TRES_SEMIMINIMAS, destino)

    assert len(resumo) == 1
    assert resumo[0]["notas"] == 3
    raiz = ET.parse(destino).getroot()
    assert len(raiz.findall("part")) == 1
    assert len(raiz.findall(".//note/pitch")) == 3


def test_krn_sem_nota_vira_erro(tmp_path: Path) -> None:
    pytest.importorskip("music21")

    with pytest.raises(ValueError):
        krn_para_musicxml("**kern\n*clefG2\n*-\n", tmp_path / "saida.musicxml")
    assert not (tmp_path / "saida.musicxml").exists()


def test_normalizar_ekern_troca_so_o_cabecalho() -> None:
    texto, trocou = normalizar_ekern("**ekern_1.0\t**ekern_1.0\n8FL\t16r")

    assert trocou is True
    assert texto == "**kern\t**kern\n8FL\t16r"


def test_normalizar_ekern_deixa_kern_como_esta() -> None:
    texto, trocou = normalizar_ekern("**kern\n4c")

    assert trocou is False
    assert texto == "**kern\n4c"
