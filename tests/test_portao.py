"""O portão de tablatura: forma da entrada, duas classes e dois logits.

Testes sem acervo e sem GPU — o gate padrão (`make test`) não monta o HD. O que se
trava aqui é o que quebrou nas rodadas anteriores: entrada com forma fixa, o positivo
sintético NASCENDO no conjunto (a classe que não nascia custou três retreinos) e o
gabarito rotulado à mão preservado no formato combinado.
"""

from __future__ import annotations

import json

import cv2
import numpy as np
import pytest
import torch

import tab.portao as portao
from tab.portao import (
    ALTURA,
    CASOS_PORTAO,
    GOLD_PORTAO,
    LARGURA,
    ROTULOS,
    PortaoCNN,
    montar_dataset,
    montar_folha,
    montar_treino,
    pesos_de_classe,
    preparar,
)

#: Chaves de um caso do gabarito — o formato que `acrescentar_casos` tem de manter.
CHAVES_CASO = (
    "arquivo",
    "canal",
    "video",
    "instante_frac",
    "faixa",
    "uniformidade",
    "passo",
    "glifos",
    "rotulo",
)


def test_preparar_devolve_forma_esperada() -> None:
    """`preparar` devolve (1, ALTURA, LARGURA) em float 0..1, de BGR e de cinza."""
    bgr = np.full((300, 800, 3), 128, np.uint8)
    cinza = np.full((300, 800), 200, np.uint8)
    for entrada in (bgr, cinza):
        saida = preparar(entrada)
        assert saida.shape == (1, ALTURA, LARGURA)
        assert saida.dtype == np.float32
        assert float(saida.min()) >= 0.0
        assert float(saida.max()) <= 1.0


def test_dataset_sintetico_tem_as_duas_classes() -> None:
    """O gerador entrega positivo E negativo; meio conjunto é tablatura."""
    X, y = montar_dataset(4, seed=0)
    assert X.shape == (8, 1, ALTURA, LARGURA)
    assert set(np.unique(y).tolist()) == {0, 1}
    assert int(y.sum()) == 4


def test_rede_devolve_dois_logits() -> None:
    """A saída é logit por classe — nada de uma dimensão só."""
    modelo = PortaoCNN()
    saida = modelo(torch.zeros(2, 1, ALTURA, LARGURA))
    assert saida.shape == (2, 2)


def test_pesos_de_classe_igualam_a_contribuicao() -> None:
    """Com peso de classe, 9 negativos e 3 positivos pesam o mesmo na perda."""
    y = np.array([0] * 9 + [1] * 3)
    pesos = pesos_de_classe(y)
    assert np.isclose(pesos[0] * 9, pesos[1] * 3)
    assert pesos.min() > 0.0


def test_montar_treino_junta_real_e_sintetico() -> None:
    """Sem recorte real, o treino cai no sintético e continua balanceado."""
    X, y, pesos = montar_treino([], n_sint=3, seed=0)
    assert X.shape == (6, 1, ALTURA, LARGURA)
    assert int(y.sum()) == 3
    assert pesos.shape == (2,)


def test_montar_folha_grava_png_com_o_indice(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A folha de leitura sai no disco — é o artefato que o dono audita."""
    monkeypatch.setattr(portao, "CASOS_PORTAO", tmp_path)
    casos: list[dict] = []
    for i in range(3):
        nome = f"{i:03d}_p.png"
        img = np.full((200, 600, 3), 40 * i, np.uint8)
        cv2.imwrite(str(tmp_path / nome), img)
        casos.append({"arquivo": nome, "canal": "c", "rotulo": None})
    destino = tmp_path / "folha.png"
    montar_folha(casos, [0, 1, 2], str(destino), cols=2, celula=(200, 120))
    lida = cv2.imread(str(destino))
    assert lida is not None
    assert lida.shape[0] == 240
    assert lida.shape[1] == 400


def test_gold_do_portao_mantem_formato_e_rotulos() -> None:
    """Todo caso tem as mesmas chaves, rótulo válido e PNG próprio no disco."""
    gold = json.loads(GOLD_PORTAO.read_text(encoding="utf-8"))
    assert set(gold.keys()) == {"como_foi_rotulado", "folhas", "casos"}
    assert gold["casos"], "o gabarito do portão não pode ficar vazio"
    for caso in gold["casos"]:
        assert tuple(caso.keys()) == CHAVES_CASO
        assert caso["rotulo"] in ROTULOS
        assert (CASOS_PORTAO / str(caso["arquivo"])).exists()
