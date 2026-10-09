"""Símbolo NÃO se descarta: o que não é algarismo tem de sobreviver à leitura.

Direção definida pelo dono do projeto: o extrator lia o número e jogava fora o
símbolo em volta — um `7` com barra de slide virava `{"casa": "7"}` e o slide
desaparecia. Agora o token guarda as caixas dos componentes, grava o recorte cru em
PNG (deduplicado por hash) e tenta recuperar a casa de dentro do símbolo.

Estes testes usam um modelo de mentira: o que se afere aqui é o **encanamento**, não a
acurácia (essa é medida por `tab.avaliar`, no gabarito real).
"""

from __future__ import annotations

import random

import torch

from tab.reconhecer import reconhecer_linha
from tab.sintetico import gerar_linha

ROTULOS = [str(n) for n in range(25)] + ["harmonico", "tecnica", "junk"]


class ModeloFixo(torch.nn.Module):
    """Modelo de mentira: devolve sempre a mesma classe, com confiança alta."""

    def __init__(self, n_classes: int, indice: int) -> None:
        super().__init__()
        self.n_classes = n_classes
        self.indice = indice

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Logits fixos (a classe escolhida ganha de lavada)."""
        logits = torch.full((x.shape[0], self.n_classes), -10.0)
        logits[:, self.indice] = 10.0
        return logits


def _linha_sintetica(seed: int = 4):
    return gerar_linha(random.Random(seed))[0]


def test_simbolo_e_gravado_e_registrado(tmp_path) -> None:
    """Token não numérico sai com recorte cru em PNG e assinatura de forma."""
    modelo = ModeloFixo(len(ROTULOS), ROTULOS.index("tecnica"))
    r = reconhecer_linha(
        _linha_sintetica(),
        modelo,
        ROTULOS,
        "cpu",
        dir_simbolos=str(tmp_path),
        prefixo="canal_x",
    )
    com_simbolo = [n for n in r["notas"] if "simbolo_cru" in n]
    assert com_simbolo, "nenhum símbolo registrado: o teste não exercitou o caminho"

    simbolo = com_simbolo[0]["simbolo_cru"]
    for campo in ("partes", "larguras_passo", "componentes", "classe", "top3"):
        assert campo in simbolo, campo
    assert simbolo["larguras_passo"], "sem largura dos componentes não há assinatura"
    assert simbolo["png"], "o recorte cru não foi gravado"
    assert (tmp_path / "canal_x" / f"{simbolo['hash']}.png").exists()


def test_algarismo_simples_nao_vira_simbolo(tmp_path) -> None:
    """Dígito de um componente só não polui o acervo de símbolos."""
    modelo = ModeloFixo(len(ROTULOS), ROTULOS.index("7"))
    r = reconhecer_linha(
        _linha_sintetica(), modelo, ROTULOS, "cpu", dir_simbolos=str(tmp_path)
    )
    simples = [n for n in r["notas"] if n["casa"] == "7" and "simbolo_cru" not in n]
    assert simples, "todo token foi tratado como símbolo; a regra está larga demais"


def test_toda_nota_leva_confianca(tmp_path) -> None:
    """A confiança por nota foi pedida pelo dono do projeto e vale para toda nota."""
    modelo = ModeloFixo(len(ROTULOS), ROTULOS.index("3"))
    r = reconhecer_linha(_linha_sintetica(), modelo, ROTULOS, "cpu")
    assert r["notas"]
    for nota in r["notas"]:
        assert 0.0 <= nota["confianca"] <= 1.0
        assert nota["corda"] >= 1
