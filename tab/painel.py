"""Onde está o painel de tablatura no quadro — uma implementação só.

Havia **três** cópias desta escolha (`inventario.analisar_quadro`,
`transcrever.achar_painel`, `varredura.medir_quadro`) e as três erravam igual: ordenavam
por `(glifos_centrados, n_glifos)`.

Medido nesta noite num quadro real do `sky guitar` (t=88 s), com as caixas desenhadas no
quadro para conferir:

- a tablatura de verdade está na faixa `meio`: 6 linhas, passo 29,6, 36 glifos,
  uniformidade de fundo **0,888**;
- a faixa `base` é o **braço do violão** mais o corpo e a mão: 6 "linhas" (as cordas),
  39 "glifos" (trastes e cruzamentos), 34 "centrados" — e **ganhava** no critério antigo
  por ter mais glifos centrados. Uniformidade **0,842**.

O portão que separa os dois é a **uniformidade do fundo**, que já tinha sido medida nas
rodadas 42–45 e nunca havia entrado no código. Aqui ela entra como **primeiro critério**,
sem limiar fixo: entre candidatos com 6 linhas e glifos, ganha o de fundo mais liso.

Uso:
    from .painel import escolher
    c = escolher(frame)
    if c is not None:
        ...  # c.roi, c.grade, c.uniformidade, c.score
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .tabseg import Grade, segmentar

#: Faixas verticais onde o painel costuma estar (a posição varia por vídeo).
FAIXAS: list[tuple[str, int, int]] = [
    ("topo", 0, 400),
    ("meio", 300, 750),
    ("base", 620, 1080),
]

#: Mínimo de glifos para uma faixa ser considerada painel (evita região vazia).
MIN_GLIFOS = 5


@dataclass
class Candidato:
    """Uma faixa candidata a painel, com o que foi medido nela."""

    nome: str
    y0: int
    y1: int
    roi: np.ndarray
    grade: Grade
    uniformidade: float
    score: tuple[float, int]

    @property
    def passo(self) -> float:
        """Passo entre cordas, em px."""
        return float(self.grade.passo)


def uniformidade(roi: np.ndarray, k: int = 15, tol: int = 12) -> float:
    """Fração de pixels perto da mediana local — o fundo é liso?

    Papel e painel de cor sólida deixam a maior parte dos pixels perto da mediana
    local; madeira, sombra e brilho do braço não deixam.

    Args:
        roi: recorte (BGR ou cinza).
        k: tamanho do kernel da mediana (ímpar).
        tol: tolerância em níveis de cinza.

    Returns:
        Fração entre 0 e 1; quanto maior, mais liso o fundo.
    """
    cinza = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    if cinza.size == 0:
        return 0.0
    mediana = cv2.medianBlur(cinza, k)
    diferenca = np.abs(cinza.astype(np.int16) - mediana.astype(np.int16))
    return float((diferenca <= tol).mean())


def candidatos(frame: np.ndarray, min_glifos: int = MIN_GLIFOS) -> list[Candidato]:
    """Todas as faixas com 6 cordas, medida a uniformidade do fundo de cada uma.

    Args:
        frame: quadro inteiro.
        min_glifos: mínimo de glifos para aceitar a faixa.

    Returns:
        Lista de candidatos, sem ordenar.
    """
    achados: list[Candidato] = []
    for nome, y0, y1 in FAIXAS:
        y1 = min(y1, frame.shape[0])
        if y1 - y0 < 60:
            continue
        roi = frame[y0:y1, :]
        try:
            g = segmentar(roi)
        except Exception:  # nunca derrubar a varredura por uma faixa ruim
            continue
        if len(g.linhas_y) != 6 or len(g.glifos) < min_glifos:
            continue
        u = uniformidade(roi)
        achados.append(
            Candidato(
                nome=nome,
                y0=y0,
                y1=y1,
                roi=roi,
                grade=g,
                uniformidade=u,
                score=(round(u, 3), g.glifos_centrados),
            )
        )
    return achados


def melhor(achados: list[Candidato]) -> Candidato | None:
    """O melhor candidato da lista (uniformidade primeiro, centrados depois).

    Args:
        achados: candidatos já medidos.

    Returns:
        O melhor, ou None se a lista estiver vazia.
    """
    return max(achados, key=lambda c: c.score) if achados else None


def criar(
    nome: str, y0: int, y1: int, roi: np.ndarray, grade: Grade
) -> Candidato | None:
    """Monta um candidato a partir de uma grade JÁ segmentada.

    Existe para quem precisa medir as faixas de qualquer jeito (a varredura mede
    picos e cursor em todas) e não quer pagar `segmentar` duas vezes.

    Args:
        nome: nome da faixa.
        y0: topo da faixa no quadro.
        y1: base da faixa no quadro.
        roi: recorte da faixa.
        grade: resultado de ``segmentar(roi)``.

    Returns:
        O candidato, ou None se a faixa não tem 6 cordas nem glifos suficientes.
    """
    if len(grade.linhas_y) != 6 or len(grade.glifos) < MIN_GLIFOS:
        return None
    u = uniformidade(roi)
    return Candidato(
        nome=nome,
        y0=y0,
        y1=y1,
        roi=roi,
        grade=grade,
        uniformidade=u,
        score=(round(u, 3), grade.glifos_centrados),
    )


def escolher(frame: np.ndarray, min_glifos: int = MIN_GLIFOS) -> Candidato | None:
    """Escolhe a faixa que é painel de tablatura (ou None se não houver).

    O critério é a uniformidade do fundo primeiro e os glifos centrados depois —
    invertido em relação ao critério antigo, que preferia o braço do violão.

    Args:
        frame: quadro inteiro.
        min_glifos: mínimo de glifos para aceitar a faixa.

    Returns:
        O melhor candidato, ou None.
    """
    achados = candidatos(frame, min_glifos)
    return melhor(achados)
