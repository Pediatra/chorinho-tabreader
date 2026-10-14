"""Testes do detector de tablatura: sem GPU e sem acervo.

Cobrem a normalização do sistema (altura 160, cordas nas linhas esperadas), os alvos
(pico 1 no centro de cada nota), o formato da saída do modelo, a decodificação com
um modelo oráculo (que devolve os próprios alvos), e o determinismo da amostra de
treino.
"""

from __future__ import annotations

import random

import numpy as np
import pytest
import torch
from torch import nn

from tab.detector_tab import (
    ALTURA_NORM,
    DESLOC,
    FONTES_TREINO,
    PASSO_NORM,
    ROTULO_IDX,
    STRIDE,
    TECNICA_IDX,
    DetectorTab,
    _amostra_treino,
    _parser,
    alvos_do_sistema,
    detectar,
    normalizar_sistema,
    x_para_original,
)
from tab.sintetico_sistema import gerar_sistema


@pytest.fixture(scope="module")
def sistema() -> tuple[np.ndarray, dict]:
    """Um sistema gerado, com semente fixa."""
    return gerar_sistema(random.Random(3), FONTES_TREINO)


class _Oraculo(nn.Module):
    """Modelo que devolve, como logits, os próprios alvos de um sistema."""

    def __init__(self, alvos: dict[str, np.ndarray]) -> None:
        """Guarda os alvos de um sistema.

        Args:
            alvos: saída de `alvos_do_sistema`.
        """
        super().__init__()
        self.centro = torch.from_numpy(alvos["centro"])[None]
        self.classe = torch.from_numpy(alvos["classe"])[None]
        self.tecnica = torch.from_numpy(alvos["tecnica"])[None]

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Devolve logits que decodificam exatamente os alvos.

        Args:
            x: entrada (ignorada).

        Returns:
            Dict no formato de `DetectorTab.forward`.
        """
        del x
        centro = torch.where(self.centro > 0.5, 10.0, -10.0)
        classe = torch.full((*self.classe.shape, 26), -10.0)
        valido = self.classe >= 0
        idx = self.classe.clamp(min=0)[..., None]
        classe.scatter_(-1, idx, 10.0)
        classe = torch.where(valido[..., None], classe, torch.zeros_like(classe))
        tecnica = self.tecnica * 20.0 - 10.0
        return {"centro": centro, "classe": classe, "tecnica": tecnica}


def test_normalizar_altura_160_e_cordas_nas_linhas_esperadas(
    sistema: tuple[np.ndarray, dict],
) -> None:
    """O sistema normalizado tem 160 px e cada corda cai na linha 16*(2,5+k)."""
    img, info = sistema
    arr, escala, y_topo = normalizar_sistema(img, info["linhas_y"], info["passo"])
    assert arr.shape[0] == ALTURA_NORM == 160
    assert arr.shape[1] % STRIDE == 0
    assert escala == pytest.approx(PASSO_NORM / info["passo"])
    prof = 1.0 - arr.mean(axis=1)
    for k in range(6):
        esperado = (2.5 + k) * PASSO_NORM
        # Ponto de y normalizado calculado pela origem da imagem deve coincidir.
        assert (info["linhas_y"][k] - y_topo) * escala == pytest.approx(
            esperado, abs=2.0 * escala
        )
        vizinhanca = prof[round(esperado) - 2 : round(esperado) + 3]
        assert vizinhanca.max() > np.median(prof) + 0.05, k


def test_x_para_original_inverte_a_escala(sistema: tuple[np.ndarray, dict]) -> None:
    """Um x original vai para normalizado e volta com a mesma escala."""
    img, info = sistema
    _, escala, _ = normalizar_sistema(img, info["linhas_y"], info["passo"])
    x = float(info["notas"][0]["x"])
    assert x_para_original(x * escala, escala) == pytest.approx(x)


def test_alvos_tem_pico_1_no_centro_de_cada_nota(
    sistema: tuple[np.ndarray, dict],
) -> None:
    """Cada nota deixa um pico exato de 1 na sua corda, no bin do centro."""
    img, info = sistema
    arr, escala, _ = normalizar_sistema(img, info["linhas_y"], info["passo"])
    alvos = alvos_do_sistema(info["notas"], escala, arr.shape[1])
    comp = arr.shape[1] // STRIDE
    assert alvos["centro"].shape == (6, comp)
    assert alvos["classe"].shape == (6, comp)
    assert alvos["tecnica"].shape == (6, comp, 10)
    for nota in info["notas"]:
        k = nota["corda"] - 1
        u = (nota["x"] * escala - DESLOC) / STRIDE
        pico = int(np.clip(round(u), 0, comp - 1))
        assert alvos["centro"][k, pico] == pytest.approx(1.0)
        assert alvos["classe"][k, pico] == ROTULO_IDX[nota["rotulo"]]
        if nota["tecnica"] is not None:
            assert alvos["tecnica"][k, pico, TECNICA_IDX[nota["tecnica"]]] == 1.0


def test_modelo_forward_formas_e_parametros() -> None:
    """Forward num lote pequeno devolve as formas certas e o modelo tem o porte previsto."""
    modelo = DetectorTab()
    n = sum(p.numel() for p in modelo.parameters())
    assert 300_000 <= n <= 1_500_000
    modelo.eval()
    with torch.no_grad():
        saida = modelo(torch.zeros(2, 1, 160, 128))
    assert saida["centro"].shape == (2, 6, 32)
    assert saida["classe"].shape == (2, 6, 32, 26)
    assert saida["tecnica"].shape == (2, 6, 32, 10)


def test_modelo_rejeita_largura_nao_multipla_de_4() -> None:
    """Largura fora do múltiplo de 4 é recusada com erro claro."""
    modelo = DetectorTab()
    with pytest.raises(ValueError, match="múltiplo de 4"):
        modelo(torch.zeros(1, 1, 160, 130))


def test_detectar_com_oraculo_recupera_todas_as_notas(
    sistema: tuple[np.ndarray, dict],
) -> None:
    """Com alvos perfeitos, `detectar` recupera cada nota com x a 0,5 passo e rótulo certo."""
    img, info = sistema
    arr, escala, _ = normalizar_sistema(img, info["linhas_y"], info["passo"])
    oraculo = _Oraculo(alvos_do_sistema(info["notas"], escala, arr.shape[1]))
    preds = detectar(oraculo, img, info["linhas_y"], info["passo"])
    tol = 0.5 * info["passo"]
    for nota in info["notas"]:
        candidatas = [
            p
            for p in preds
            if p["corda"] == nota["corda"] and abs(p["x"] - nota["x"]) <= tol
        ]
        assert candidatas, nota
        assert any(p["rotulo"] == nota["rotulo"] for p in candidatas), nota
    assert len(preds) == len(info["notas"])


def test_cli_treinar_aceita_pasta_de_saida(tmp_path) -> None:
    """`treinar --saida` leva a pasta de saída até a função de treino."""
    args = _parser().parse_args(
        ["treinar", "--semente", "1", "--saida", str(tmp_path / "v2")]
    )
    assert args.saida == tmp_path / "v2"
    assert args.semente == 1
    padrao = _parser().parse_args(["treinar", "--semente", "1"])
    assert padrao.saida is None


def test_gerar_alvos_e_deterministico() -> None:
    """A mesma semente de dados dá exatamente a mesma amostra de treino."""
    a = _amostra_treino(12345)
    b = _amostra_treino(12345)
    for parte_a, parte_b in zip(a, b, strict=True):
        assert np.array_equal(parte_a, parte_b)
    assert a[0].shape == (160, 512)
    assert a[1].shape == (6, 128)
