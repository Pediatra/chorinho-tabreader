"""Arco de ligadura não é algarismo: vai para símbolo cru, e o algarismo normal continua nota.

Medido no ouro v2 (sky guitar): 17 arcos de ligadura eram lidos como algarismo (`2`, `5`, `7`)
e viravam notas inventadas. Os arcos têm altura de 0,23 a 0,37 passo; os algarismos certos têm
0,64 ou mais. A regra é a altura, e o token baixo sai do caminho de algarismo (classe `simbolo`).

Os testes usam um classificador falso que lê TODO recorte como `7` (sem pesos, sem GPU): assim o
que decide a saída é só a geometria do token.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tab.tablatura.leitura import reconhecer
from tab.tablatura.leitura.reconhecer import (
    ALGARISMOS,
    ALTURA_MINIMA_ALGARISMO,
    _baixo_para_algarismo,
    reconhecer_linha,
)
from tab.tablatura.treino.sintetico import FONTES

#: Classes do classificador (dígitos, e as classes de técnica que o modelo conhece).
ROTULOS = [str(n) for n in range(10)] + ["10", "12", "harmonico", "tecnica"]
PASSO = 20


class _Tk:
    """Token mínimo: só a geometria que `_baixo_para_algarismo` lê."""

    def __init__(self, y0: int, y1: int) -> None:
        self.y0 = y0
        self.y1 = y1


def _linha(arco: bool, digito: str = "7") -> np.ndarray:
    """Linha de tablatura: 6 cordas, um algarismo na corda 2 e (opcional) um arco entre 1 e 2."""
    larg, alt = 500, int(PASSO * 7.6)
    img = Image.new("RGB", (larg, alt), (255, 255, 255))
    d = ImageDraw.Draw(img)
    ys = [int(PASSO * 0.8) + i * PASSO for i in range(6)]
    for y in ys:
        d.line([(30, y), (larg - 30, y)], fill=(60, 60, 60), width=2)
    fonte = ImageFont.truetype(FONTES[0], int(PASSO * 1.2))
    x = 150
    bb = d.textbbox((0, 0), digito, font=fonte)
    w = bb[2] - bb[0]
    d.text(
        (int(x - w / 2), int(ys[1] - (bb[3] + bb[1]) / 2)),
        digito,
        font=fonte,
        fill=(0, 0, 0),
    )
    if arco:
        # arco de ligadura: meia elipse de 0,8 passo de largura e 0,4 de altura, acima da corda 2
        cx = 320
        d.arc(
            [cx - 8, ys[1] - 0.9 * PASSO, cx + 8, ys[1] - 0.1 * PASSO],
            start=180,
            end=360,
            fill=(0, 0, 0),
            width=2,
        )
    return np.array(img)[:, :, ::-1].copy()


def _todos_viram_sete(monkeypatch) -> None:
    """Troca o classificador por um que lê todo recorte como `7` com confiança 0,9."""

    def _probs(recortes, modelo, dev):
        linha = np.zeros(len(ROTULOS))
        linha[ROTULOS.index("7")] = 0.9
        linha[ROTULOS.index("tecnica")] = 0.1
        return np.tile(linha, (len(recortes), 1))

    monkeypatch.setattr(reconhecer, "_probs", _probs)


def test_altura_separa_arco_de_algarismo() -> None:
    """Token de 0,37 passo é baixo (arco); token de 0,88 passo é algarismo."""
    assert _baixo_para_algarismo(_Tk(0, round(0.37 * PASSO)), PASSO)
    assert not _baixo_para_algarismo(_Tk(0, round(0.88 * PASSO)), PASSO)
    assert 0.37 < ALTURA_MINIMA_ALGARISMO < 0.64


def test_arco_desenhado_sobre_as_cordas_vira_simbolo_e_nao_nota(monkeypatch) -> None:
    """Sem algarismo: o arco lido como `7` não aparece como casa; vira símbolo cru."""
    _todos_viram_sete(monkeypatch)
    r = reconhecer_linha(_linha(arco=True, digito="7"), None, ROTULOS, "cpu")
    casas = [n for n in r["notas"] if n["casa"] in ALGARISMOS]
    simbolos = [n for n in r["notas"] if n["casa"] == "simbolo"]
    assert len(simbolos) == 1, "o arco tem de ficar como símbolo, não sumir"
    assert simbolos[0]["corda"] == 1
    # o `7` da corda 2 continua a ser a única nota de casa
    assert [n["casa"] for n in casas] == ["7"]
    assert casas[0]["corda"] == 2


def test_algarismo_normal_continua_nota(monkeypatch) -> None:
    """Sem arco: o `7` da corda 2 é nota, e nada é tirado dele pela regra de altura."""
    _todos_viram_sete(monkeypatch)
    r = reconhecer_linha(_linha(arco=False, digito="7"), None, ROTULOS, "cpu")
    casas = [n for n in r["notas"] if n["casa"] in ALGARISMOS]
    assert [n["casa"] for n in casas] == ["7"]
    assert casas[0]["corda"] == 2
    assert not [n for n in r["notas"] if n["casa"] == "simbolo"]


def test_discriminador_nao_devolve_arco_a_algarismo(monkeypatch) -> None:
    """Mesmo um discriminador que diz `é algarismo` com 1,0 não transforma o arco em nota."""
    _todos_viram_sete(monkeypatch)

    def _disc_sim(recortes):
        return np.ones(len(recortes))

    r = reconhecer_linha(
        _linha(arco=True, digito="7"),
        None,
        ROTULOS,
        "cpu",
        discriminador=_disc_sim,
    )
    casas_nao_simbolo = [
        n for n in r["notas"] if n["casa"] in ALGARISMOS and n["corda"] == 1
    ]
    assert casas_nao_simbolo == []


def test_nota_de_arco_guarda_a_classe_lida(monkeypatch) -> None:
    """O símbolo guarda o que o classificador leu (`top3`), para o mapa por canal ver o arco."""
    _todos_viram_sete(monkeypatch)
    r = reconhecer_linha(_linha(arco=True, digito="7"), None, ROTULOS, "cpu")
    simbolo = next(n for n in r["notas"] if n["casa"] == "simbolo")
    assert "simbolo_cru" in simbolo or "simbolo_recusado" in simbolo
    registro = simbolo.get("simbolo_cru") or simbolo.get("simbolo_recusado")
    assert registro["top3"][0][0] == "7"
