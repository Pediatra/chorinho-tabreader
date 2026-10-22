"""Braço do violão x TAB escura: a deriva das cordas separa os dois.

A TAB tem cordas horizontais; o braço, vista de lado, tem cordas que convergem. O gate
`_cordas_convergem` (usado em `escolher_ou_mascara`) tem de dizer "braço" só para a
segunda.
"""

from __future__ import annotations

import cv2
import numpy as np

from tab.tablatura.leitura import painel as P
from tab.tablatura.leitura.tabseg import Grade

PASSO = 40
CORDAS = [60 + PASSO * i for i in range(6)]


def _quadro(inclinacao: float) -> np.ndarray:
    """Faixa escura com 6 cordas claras; ``inclinacao`` é o desvio em y entre as bordas.

    Args:
        inclinacao: quanto cada corda sobe (negativo) ou desce (positivo) em toda a largura.

    Returns:
        Imagem BGR de 260 x 900.
    """
    img = np.full((260, 900, 3), 30, np.uint8)
    for y in CORDAS:
        cv2.line(img, (0, y), (899, round(y + inclinacao)), (200, 200, 200), 2)
    return img


def _candidato(img: np.ndarray, y0: int = 0) -> P.Candidato:
    """Candidato mínimo com as cordas do teste sobre o recorte inteiro.

    Args:
        img: quadro de teste.
        y0: onde o recorte começa no quadro.

    Returns:
        Candidato com ``roi`` = quadro e grade de 6 cordas.
    """
    grade = Grade(
        altura=img.shape[0],
        largura=img.shape[1],
        linhas_y=list(CORDAS),
        passo=float(PASSO),
    )
    return P.Candidato(
        nome="teste",
        y0=y0,
        y1=y0 + img.shape[0],
        roi=img,
        grade=grade,
        uniformidade=1.0,
        score=(1.0, 0),
    )


def test_cordas_horizontais_nao_sao_braco() -> None:
    """Cordas paralelas (TAB) não passam do limite de convergência."""
    assert not P._cordas_convergem(_candidato(_quadro(0)))


def test_cordas_convergentes_sao_braco() -> None:
    """Cordas que sobem 0,5 passo entre as bordas (braço) passam do limite."""
    assert P._cordas_convergem(_candidato(_quadro(-0.5 * PASSO)))


def test_braco_reto_perde_para_a_tab_escura_em_outra_faixa(monkeypatch) -> None:
    """Rodada 0213: o braço que não converge perde para a TAB escura mais embaixo."""
    braco = _candidato(_quadro(0), y0=0)
    tab_escura = _candidato(_quadro(0), y0=600)
    monkeypatch.setattr(P, "escolher", lambda frame: braco)
    monkeypatch.setattr(
        P, "candidatos_escuros_estreitos", lambda f: [(1.0, tab_escura)]
    )
    monkeypatch.setattr(P, "refinar", lambda c: c)
    monkeypatch.setattr(P, "e_tablatura", lambda c: True)
    assert P.escolher_ou_mascara(np.zeros((1080, 900, 3), np.uint8)) is tab_escura


def test_tab_escura_na_mesma_faixa_nao_troca_o_escolhido(monkeypatch) -> None:
    """Se a TAB escura é a mesma faixa do escolhido, o escolhido fica (os que já acertam)."""
    escolhido = _candidato(_quadro(0), y0=600)
    mesma = _candidato(_quadro(0), y0=610)
    monkeypatch.setattr(P, "escolher", lambda frame: escolhido)
    monkeypatch.setattr(P, "candidatos_escuros_estreitos", lambda f: [(1.0, mesma)])
    monkeypatch.setattr(P, "refinar", lambda c: c)
    monkeypatch.setattr(P, "e_tablatura", lambda c: True)
    assert P.escolher_ou_mascara(np.zeros((1080, 900, 3), np.uint8)) is escolhido


def test_sem_tab_escura_o_escolhido_fica(monkeypatch) -> None:
    """Sem TAB escura no quadro, nada muda."""
    escolhido = _candidato(_quadro(0), y0=0)
    monkeypatch.setattr(P, "escolher", lambda frame: escolhido)
    monkeypatch.setattr(P, "candidatos_escuros_estreitos", lambda f: [])
    assert P.escolher_ou_mascara(np.zeros((1080, 900, 3), np.uint8)) is escolhido
