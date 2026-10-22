"""A escolha do painel: fundo liso ganha do braço do violão.

Medido num quadro real do `sky guitar` (t=88 s): a tablatura de verdade está na faixa
`meio` (uniformidade 0,888) e a faixa `base` é o braço mais a mão (0,842) — e o critério
antigo, que ordenava por glifos centrados, escolhia o braço.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.tablatura.leitura.painel import (
    aparar_pauta,
    candidatos,
    e_pauta,
    escolher,
    espacamento_regular,
    mesmas_linhas,
    papel_branco,
    uniformidade,
)


def _faixa_tablatura(semente: int = 0) -> np.ndarray:
    """Fundo liso, 6 cordas e alguns algarismos: um painel de tablatura."""
    img = np.full((300, 1200, 3), 245, np.uint8)
    for i in range(6):
        y = 60 + i * 30
        cv2.line(img, (20, y), (1180, y), (30, 30, 30), 1)
    for j, x in enumerate(range(100, 1100, 90)):
        cv2.putText(
            img, str(j % 10), (x, 155), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (20, 20, 20), 3
        )
    return img


def _faixa_braco(semente: int = 0) -> np.ndarray:
    """Madeira com veio, trastes e brilho: o braço do violão engana o detector.

    Textura de verdade, com alta frequência preservada: o veio da madeira é o que
    derruba a uniformidade (medido no quadro real: 0,842 contra 0,888 do painel).
    """
    rng = np.random.default_rng(semente)
    base = rng.integers(70, 200, (300, 1200), dtype=np.uint8)
    veio = cv2.GaussianBlur(base, (0, 0), 1.0)
    madeira = cv2.cvtColor(veio, cv2.COLOR_GRAY2BGR)
    gradiente = np.linspace(-45, 45, 1200)[None, :, None]
    madeira = np.clip(madeira.astype(np.int16) + gradiente, 0, 255)
    img = madeira.astype(np.uint8)
    for i in range(6):
        y = 60 + i * 30
        cv2.line(img, (20, y), (1180, y), (60, 60, 60), 2)
    for x in range(60, 1180, 120):  # trastes
        cv2.line(img, (x, 0), (x + 40, 299), (40, 40, 40), 3)
    return img


def test_uniformidade_separa_painel_de_braco() -> None:
    """O fundo do painel é muito mais liso que a madeira do braço."""
    assert uniformidade(_faixa_tablatura()) > uniformidade(_faixa_braco()) + 0.15


def test_painel_ganha_do_braco_na_escolha() -> None:
    """Com o painel em `meio` e o braço em `base`, a escolha tem de ser `meio`."""
    quadro = np.zeros((1080, 1200, 3), np.uint8)
    quadro[300:600] = _faixa_tablatura()  # meio
    quadro[620:920] = _faixa_braco()  # base
    achados = candidatos(quadro)
    nomes = {c.nome for c in achados}
    assert "meio" in nomes, f"o painel não foi nem candidato: {nomes}"
    escolhido = escolher(quadro)
    assert escolhido is not None
    # a TAB sintética ocupa y 300-600 e o braço y 620-920: as 6 cordas escolhidas têm de
    # estar na TAB. (O teste antigo conferia só o NOME "meio", que a faixa fixa recebe mesmo
    # quando as 6 linhas dela caem no braço; o portão das cordas contínuas troca essa
    # faixa pela TAB de verdade, que sai com o nome `y<topo>`.)
    ys = [escolhido.y0 + y for y in escolhido.grade.linhas_y]
    assert min(ys) >= 300 and max(ys) <= 600, f"cordas em {ys} ({escolhido.nome})"


def test_quadro_vazio_nao_tem_painel() -> None:
    """Sem 6 linhas não há painel: o inventário não pode inventar um."""
    assert escolher(np.full((1080, 1200, 3), 250, np.uint8)) is None


def test_espacamento_irregular_reprova_o_painel() -> None:
    """5 linhas de partitura + 1 de tablatura não é pauta de cordas.

    Medido no `sky guitar` (`(henze) nocturno`, t=228 s): `[138, 154, 170, 185, 202, 342]`,
    lacunas 16, 16, 15, 17, **140**. O detector aceitava por causa do fallback "picos mais
    fortes" do `achar_cordas` — e 61 % do lido virou bolinha de nota.
    """
    assert espacamento_regular([138, 154, 170, 185, 202, 342]) is False
    assert espacamento_regular([8, 38, 67, 97, 127, 156]) is True  # passo ~30 regular
    assert espacamento_regular([10, 22, 34, 46, 58]) is True
    assert espacamento_regular([10]) is False


def test_papel_branco_separa_tablatura_do_braco() -> None:
    """A TAB sobre papel tem muito branco; a madeira do braço quase nenhum (C1, rodada 0007)."""
    assert papel_branco(_faixa_tablatura()) > papel_branco(_faixa_braco()) + 0.5


def test_cinco_linhas_fortes_mais_uma_fraca_e_pauta() -> None:
    """Pauta: 5 linhas cheias e 1 linha fraca (viga/haste) no mesmo espaçamento.

    Medido nos iwaki VN18, VN20 e FP38 (rodada 0007): a 6ª linha tem força ~0,38 e as
    outras ~0,86. Essa faixa não é tablatura, mesmo com espaçamento regular.
    """
    img = np.full((200, 1200, 3), 245, np.uint8)
    for i in range(5):
        y = 40 + i * 14
        cv2.line(img, (20, y), (1180, y), (30, 30, 30), 2)
    cv2.line(img, (400, 26), (520, 26), (30, 30, 30), 1)  # linha fraca, acima
    linhas = [26, 40, 54, 68, 82, 96]
    assert espacamento_regular(linhas)
    assert e_pauta(img, linhas) is True


def test_seis_linhas_fortes_nao_sao_pauta() -> None:
    """A TAB de 6 cordas cheias não é recusada pelo critério da pauta."""
    img = np.full((200, 1200, 3), 245, np.uint8)
    linhas = [30 + i * 20 for i in range(6)]
    for y in linhas:
        cv2.line(img, (20, y), (1180, y), (30, 30, 30), 2)
    assert e_pauta(img, linhas) is False


def test_mesmas_linhas_tolera_so_desvio_pequeno() -> None:
    """Refinar só estreita em x: as cordas em y têm de ser as mesmas."""
    assert mesmas_linhas(
        [945, 966, 988, 1009, 1030, 1051], [946, 966, 988, 1010, 1030, 1051]
    )
    assert not mesmas_linhas(
        [945, 966, 988, 1009, 1030, 1051], [767, 781, 796, 810, 824, 838]
    )
    assert not mesmas_linhas([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5])


def _quadro_com_pauta_e_tab(
    pauta: list[int], tab: list[int], largura: int = 300, altura: int = 400
) -> np.ndarray:
    """Quadro branco com linhas pretas horizontais: pauta em cima, TAB embaixo."""
    quadro = np.full((altura, largura, 3), 235, dtype=np.uint8)
    for y in pauta + tab:
        cv2.line(quadro, (20, y), (largura - 20, y), (30, 30, 30), 2)
    return quadro


def test_aparar_pauta_corta_a_caixa_para_so_a_tab() -> None:
    quadro = _quadro_com_pauta_e_tab(
        pauta=[60, 76, 92, 108, 124], tab=[180, 205, 230, 255, 280, 305]
    )
    rect = (0, 30, 300, 340)
    assert aparar_pauta(quadro, rect) == (0, 155, 300, 330)


def test_aparar_pauta_sem_pauta_em_cima_nao_mexe_na_caixa() -> None:
    quadro = _quadro_com_pauta_e_tab(pauta=[], tab=[180, 205, 230, 255, 280, 305])
    rect = (0, 150, 300, 340)
    assert aparar_pauta(quadro, rect) == rect


def test_aparar_pauta_so_pauta_nao_vira_tab() -> None:
    quadro = _quadro_com_pauta_e_tab(pauta=[60, 76, 92, 108, 124], tab=[])
    rect = (0, 30, 300, 200)
    assert aparar_pauta(quadro, rect) == rect
