"""Testes da leitura do modelo para a ferramenta (tab.ataque_divergencia)."""

import json

import pytest

from tab import ataque_divergencia as ad
from tab import ouro_video


@pytest.mark.parametrize(
    ("dono", "modelo", "esperado"),
    [
        ("nao", "sim", "nao_viu"),
        ("sim", "nao", "viu_mais"),
        ("sim", "nao_sei", "duvida"),
        ("sim", "sim", None),
        ("nao", "nao", None),
        ("nao", "nao_sei", None),
        ("nao_sei", "sim", None),
        ("sim", None, None),
    ],
)
def test_divergencia(dono: str, modelo: str | None, esperado: str | None) -> None:
    """Só três casos viram marca: não viu, viu a mais e dúvida em nota atacada."""
    assert ad.divergencia(dono, modelo) == esperado


def test_onde_ler_usa_indice_quando_existe(tmp_path, monkeypatch) -> None:
    """Com ``indice.json`` (lote de vários vídeos), cada tela tem o seu vídeo e instante."""
    monkeypatch.setattr(ad.caminhos, "acervo", lambda: tmp_path / "acervo")
    (tmp_path / "indice.json").write_text(
        json.dumps([{"id": 3, "video": "canal/v.mp4", "t": 12.5}]), encoding="utf-8"
    )
    assert ad.onde_ler(tmp_path) == {3: (tmp_path / "acervo" / "canal/v.mp4", 12.5)}


def test_onde_ler_sem_indice_usa_pre(tmp_path, monkeypatch) -> None:
    """Sem índice: o vídeo do ``pre.json`` e o ``quadro_ref_s`` de cada tela."""
    monkeypatch.setattr(ad.caminhos, "acervo", lambda: tmp_path / "acervo")
    pre = {"video": "canal/v.mp4", "telas": [{"id": 1, "quadro_ref_s": 4.0}]}
    (tmp_path / "pre.json").write_text(json.dumps(pre), encoding="utf-8")
    assert ad.onde_ler(tmp_path) == {1: (tmp_path / "acervo" / "canal/v.mp4", 4.0)}


def test_pagina_busca_a_leitura_do_modelo() -> None:
    """A página busca o arquivo que o módulo grava e espelha os três tipos."""
    assert f'fetch("/{ad.ARQUIVO}")' in ouro_video.PAGINA
    for tipo in ("nao_viu", "viu_mais", "duvida"):
        assert tipo in ouro_video.PAGINA
