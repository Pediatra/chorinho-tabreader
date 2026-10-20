"""Rótulo de ataque por nota, com a faixa "não sei" (rodada 0205).

A partir das probabilidades das técnicas que o detector dá a cada nota
(``detector_tab.detectar(..., com_escores=True)``):

- "sim" se todas as técnicas sem ataque estão abaixo de ``LIMIAR_SIM``;
- "nao" se alguma passa de ``LIMIAR_NAO``;
- "nao_sei" no meio;
- slide sem nota de origem na mesma corda até ``ORIGEM_SLIDE_MAX`` passos à esquerda é
  slide de entrada: "sim" (regra do dono, rodada 0203).

Os limiares foram escolhidos nos ouros para os pesos ``_atqg`` e, de novo, para os ``_atqt``
(``DETECTOR_CALIBRADO``, rodada 0207), com o mesmo resultado. Não valem para outros pesos.
"""

from collections.abc import Sequence

from tab import caminhos
from tab.ataque_r4 import ORIGEM_SLIDE_MAX, TECNICAS_SUPERVISIONADAS
from tab.detector_tab import TECNICAS_MODELO

#: Pesos em que os limiares foram escolhidos (rodadas 0205 e 0207, dobra 0, semente 1).
DETECTOR_CALIBRADO = caminhos.ARTEFATOS / "detector_tab_final_atqt_s1" / "modelo.pt"

#: Acima disto, a técnica tira o ataque: "nao" (rodada 0203).
LIMIAR_NAO = 0.15

#: Abaixo disto em todas as técnicas sem ataque, a nota é "sim" (rodada 0205).
LIMIAR_SIM = 0.02

#: Técnica do modelo -> ``ataque_motivo`` do esquema, quando a nota é "nao".
MOTIVO_DA_TECNICA = {
    "h": "h",
    "p": "p",
    "/": "slide_ligado",
    "\\": "slide_ligado",
    "lig": "prolongamento",
    "orn": "mordente",
    "enfeite": "mordente",
}

_SLIDES = {"/", "\\"}


def _acima(nota: dict, limiar: float) -> dict[str, float]:
    """As técnicas sem ataque da nota com probabilidade acima do limiar.

    Args:
        nota: com ``tecnica_p`` na ordem de ``TECNICAS_MODELO``.
        limiar: limiar de probabilidade.

    Returns:
        Técnica -> probabilidade.
    """
    p = dict(zip(TECNICAS_MODELO, nota["tecnica_p"], strict=True))
    return {t: p[t] for t in TECNICAS_SUPERVISIONADAS if p[t] > limiar}


def _tem_origem(notas: Sequence[dict], j: int, passo: float) -> bool:
    """Se há nota na mesma corda até ``ORIGEM_SLIDE_MAX`` passos à esquerda da nota j.

    Args:
        notas: notas da tela, com ``corda`` e ``x_centro_quadro``.
        j: índice da nota.
        passo: passo da tela, em px.

    Returns:
        ``True`` se há nota de origem para o slide.
    """
    n = notas[j]
    return any(
        q["corda"] == n["corda"]
        and 0 < n["x_centro_quadro"] - q["x_centro_quadro"] <= ORIGEM_SLIDE_MAX * passo
        for q in notas
    )


def rotular(notas: Sequence[dict], passo: float) -> list[tuple[str, str]]:
    """``(ataque, ataque_motivo)`` de cada nota de uma tela.

    Args:
        notas: notas da tela, com ``corda``, ``x_centro_quadro`` e ``tecnica_p``.
        passo: passo da tela, em px.

    Returns:
        Um par por nota, na mesma ordem. Os motivos são os de ``tab.esquema``.
    """
    saida = []
    for j, n in enumerate(notas):
        fracas = _acima(n, LIMIAR_SIM)
        if not fracas:
            saida.append(("sim", "normal"))
            continue
        entrada = not _tem_origem(notas, j, passo)
        if set(fracas) <= _SLIDES and entrada:
            saida.append(("sim", "slide_entrada"))
            continue
        fortes = _acima(n, LIMIAR_NAO)
        if fortes and not (set(fortes) <= _SLIDES and entrada):
            melhor = max(fortes, key=fortes.__getitem__)
            saida.append(("nao", MOTIVO_DA_TECNICA[melhor]))
        else:
            saida.append(("nao_sei", "tinta_sem_explicacao"))
    return saida
