"""Testes do gerador de sistemas de tablatura: sem GPU e sem acervo.

Cobrem determinismo, coordenadas dentro da imagem, vocabulário dos rótulos, a
cobertura mínima das famílias (dois algarismos, "x", acorde com 3 ou mais cordas) e
a CLI que grava as duas folhas.
"""

from __future__ import annotations

import collections
import itertools
import random

import numpy as np
import pytest

from tab.sintetico import PRESETS_FONTES, _resolver_fontes
from tab.sintetico_sistema import (
    ESTRUTURA_TIPOS,
    REGIOES,
    ROTULOS,
    TECNICAS,
    gerar_sistema,
    main,
)

#: Variantes de desenho (sem rótulo) que cada 100 sementes precisa mostrar.
VARIANTES = (
    "legato_sem_letra",
    "ligadura",
    "slide_solo",
    "colcheia",
    "semicolcheia",
    "viga_dupla",
    "pausa",
    "mordente",
    "enfeite",
)


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


def test_tecnicas_novas_aparecem_em_100_sementes(fontes: list[str]) -> None:
    """Em 100 sementes aparecem bend, vib, orn e o enfeite (nota pequena)."""
    vistas: set[str] = set()
    for semente in range(100):
        _, info = gerar_sistema(random.Random(semente), fontes)
        vistas.update(str(nota["tecnica"]) for nota in info["notas"])
    assert {"bend", "vib", "orn", "enfeite", "lig"} <= vistas


def test_regioes_e_estrutura_aparecem_em_100_sementes(fontes: list[str]) -> None:
    """Em 100 sementes aparecem cada código de região e cada tipo de estrutura."""
    regioes: set[str] = set()
    estrutura: set[str] = set()
    for semente in range(100):
        _, info = gerar_sistema(random.Random(semente), fontes)
        regioes.update(r["tecnica"] for r in info["regioes"])
        estrutura.update(item["tipo"] for item in info["estrutura"])
    assert set(REGIOES) <= regioes
    assert set(ESTRUTURA_TIPOS) <= estrutura


def test_variantes_de_desenho_aparecem_em_100_sementes(fontes: list[str]) -> None:
    """Em 100 sementes aparece cada variante de desenho (legato, slide, ritmo...)."""
    vistas: set[str] = set()
    for semente in range(100):
        _, info = gerar_sistema(random.Random(semente), fontes)
        vistas.update(info["variantes"])
    assert set(VARIANTES) <= vistas


def test_regioes_dentro_da_imagem_e_cordas_validas(fontes: list[str]) -> None:
    """Toda caixa de região e de estrutura cabe na imagem; cordas 1 <= a <= b <= 6."""
    for semente in range(100):
        img, info = gerar_sistema(random.Random(semente), fontes)
        altura, largura = img.shape[:2]
        for regiao in info["regioes"]:
            x0, y0, x1, y1 = regiao["caixa"]
            assert 0 <= x0 < x1 <= largura, (semente, regiao)
            assert 0 <= y0 < y1 <= altura, (semente, regiao)
            a, b = regiao["cordas"]
            assert 1 <= a <= b <= 6, (semente, regiao)
            assert regiao["tecnica"] in REGIOES
        for item in info["estrutura"]:
            x0, y0, x1, y1 = item["caixa"]
            assert 0 <= x0 < x1 <= largura, (semente, item)
            assert 0 <= y0 < y1 <= altura, (semente, item)
            assert item["tipo"] in ESTRUTURA_TIPOS


def test_notas_vizinhas_na_mesma_corda_nao_se_encostam(fontes: list[str]) -> None:
    """Em 100 sementes, duas notas da mesma corda têm vão >= 0,3 passo.

    O par enfeite -> nota principal fica de fora (o enfeite fica a 0,45 passo).
    """
    for semente in range(100):
        _, info = gerar_sistema(random.Random(semente), fontes)
        passo = info["passo"]
        por_corda: dict[int, list[dict]] = collections.defaultdict(list)
        for nota in info["notas"]:
            por_corda[nota["corda"]].append(nota)
        for corda, notas in por_corda.items():
            notas.sort(key=lambda n: n["caixa"][0])
            for a, b in itertools.pairwise(notas):
                if a["tecnica"] == "enfeite" and b["tecnica"] == "orn":
                    continue
                vao = b["caixa"][0] - a["caixa"][2]
                assert vao >= 0.3 * passo, (semente, corda, a, b, vao, passo)
