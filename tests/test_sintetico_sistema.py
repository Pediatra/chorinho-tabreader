"""Testes do gerador de sistemas de tablatura: sem GPU e sem acervo.

Cobrem determinismo, coordenadas dentro da imagem, vocabulário dos rótulos, a
cobertura mínima das famílias (dois algarismos, "x", acorde com 3 ou mais cordas) e
a CLI que grava as duas folhas.
"""

from __future__ import annotations

import collections
import random

import numpy as np
import pytest

from tab.sintetico import PRESETS_FONTES, _resolver_fontes
from tab.sintetico_sistema import ROTULOS, TECNICAS, gerar_sistema, main


@pytest.fixture(scope="module")
def fontes() -> list[str]:
    """Fontes do gerador (as Liberation Bold do pacote do container)."""
    achadas = _resolver_fontes(PRESETS_FONTES["padrao"][0])
    assert achadas, "fontes Liberation não encontradas"
    return achadas


def test_mesma_semente_mesma_imagem_e_mesmos_rotulos(fontes: list[str]) -> None:
    """O mesmo rng gera exatamente a mesma imagem e os mesmos rótulos."""
    img_a, info_a = gerar_sistema(random.Random(7), fontes)
    img_b, info_b = gerar_sistema(random.Random(7), fontes)
    assert np.array_equal(img_a, img_b)
    assert info_a == info_b


def test_sementes_diferentes_geram_imagens_diferentes(fontes: list[str]) -> None:
    """Sementes diferentes dão imagens diferentes."""
    img_a, _ = gerar_sistema(random.Random(1), fontes)
    img_b, _ = gerar_sistema(random.Random(2), fontes)
    assert not (img_a.shape == img_b.shape and np.array_equal(img_a, img_b))


def test_toda_caixa_fica_dentro_da_imagem(fontes: list[str]) -> None:
    """Toda caixa de nota cabe na imagem final, em 50 sementes."""
    for semente in range(50):
        img, info = gerar_sistema(random.Random(semente), fontes)
        altura, largura = img.shape[:2]
        for nota in info["notas"]:
            x0, y0, x1, y1 = nota["caixa"]
            assert 0 <= x0 < x1 <= largura, (semente, nota)
            assert 0 <= y0 < y1 <= altura, (semente, nota)


def test_linhas_y_igualmente_espacadas(fontes: list[str]) -> None:
    """Seis cordas, da 1 à 6, com o espaçamento do passo (tolerância de 1 px)."""
    for semente in range(50):
        _, info = gerar_sistema(random.Random(semente), fontes)
        ys = info["linhas_y"]
        assert len(ys) == 6
        assert all(isinstance(y, int) for y in ys)
        diferencas = np.diff(ys)
        assert np.all(diferencas > 0)
        assert np.all(np.abs(diferencas - info["passo"]) <= 1.0), (semente, ys)


def test_rotulos_e_tecnicas_no_vocabulario(fontes: list[str]) -> None:
    """Todo rótulo está em ROTULOS, toda técnica em TECNICAS e toda corda é 1-6."""
    for semente in range(50):
        _, info = gerar_sistema(random.Random(semente), fontes)
        for nota in info["notas"]:
            assert nota["rotulo"] in ROTULOS
            assert nota["tecnica"] in TECNICAS
            assert 1 <= nota["corda"] <= 6


def test_cobertura_das_familias_em_50_sementes(fontes: list[str]) -> None:
    """Em 50 sementes aparecem dois algarismos, "x" e coluna com 3 ou mais cordas."""
    rotulos: set[str] = set()
    colunas: collections.Counter = collections.Counter()
    for semente in range(50):
        _, info = gerar_sistema(random.Random(semente), fontes)
        por_coluna: collections.defaultdict[int, set[int]] = collections.defaultdict(
            set
        )
        for nota in info["notas"]:
            rotulos.add(nota["rotulo"])
            por_coluna[nota["x"]].add(nota["corda"])
        for cordas in por_coluna.values():
            colunas[len(cordas)] += 1
    assert any(len(rotulo) == 2 and rotulo != "x" for rotulo in rotulos)
    assert "x" in rotulos
    assert any(quantas >= 3 for quantas in colunas)


def test_cli_folha_grava_as_duas_folhas(tmp_path) -> None:
    """A CLI grava a folha e a folha com rótulos, em caminhos com pasta nova."""
    saida = tmp_path / "n1" / "folha.png"
    codigo = main(["folha", "--saida", str(saida), "--n", "4", "--semente", "0"])
    assert codigo == 0
    assert saida.exists()
    assert (tmp_path / "n1" / "folha_rotulos.png").exists()
