"""A escolha do painel: fundo liso ganha do braço do violão.

Medido num quadro real do `sky guitar` (t=88 s): a tablatura de verdade está na faixa
`meio` (uniformidade 0,888) e a faixa `base` é o braço mais a mão (0,842) — e o critério
antigo, que ordenava por glifos centrados, escolhia o braço.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.painel import candidatos, escolher, espacamento_regular, uniformidade


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
    assert escolhido.nome == "meio", f"escolheu {escolhido.nome}"


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
