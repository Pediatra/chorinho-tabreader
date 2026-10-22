"""Trilha das mãos: combina o Wholebody e o MediaPipe numa lista de mãos por quadro.

Regras puras, sem rtmlib, sem mediapipe e sem cv2: o detector (``tab.maos_detector``)
entrega as pessoas achadas pelo Wholebody e as mãos do MediaPipe, e este módulo decide
o que conta como mão achada. Separado do detector para que estas regras tenham teste no
gate.

Ordem das regras (``combinar``):

1. mão do Wholebody com média dos 21 scores acima de ``LIMIAR_WB``, com o lado do corpo;
2. complemento: mão do MediaPipe fora da tablatura e longe de todas as mãos aceitas;
3. as mãos do complemento se fundem entre si.

Medido e REPROVADO (2026-10-12): uma regra de honestidade que fundia esquerda e direita
da mesma pessoa em uma mão ``incerto`` foi testada nos 90 quadros de validação. A regra
não ganhou nenhum quadro (C04 e N09 trocaram a mão direita falsa por perder também a
esquerda verdadeira, que virou ``incerto``) e perdeu 2 (C08, N25: duas mãos reais,
próximas): 84/90 contra 86/90. A sobreposição das caixas não separa os casos (erros com
sobreposição de 0,96 a 1,00; acertos perdidos de 0,90 a 1,00), e a regra não tocou o C17
(sobreposição 0,28). Ficou fora. Não
foi ajustada nos mesmos 90 quadros. O valor ``incerto`` continua previsto no formato e em
``afirmacoes``, para uma regra futura; nenhuma regra atual o produz.
"""

from __future__ import annotations

from tab.maos.tabela import fundir_maos, sobreposicao

#: Mão do Wholebody existe quando a média dos 21 scores passa disto (comparação
#: estrita). ESCOLHIDO NOS MESMOS 90 quadros da validação (``validacao.py``): 0,4 deu
#: 84/90 e 0,5 deu 81/90. Logo, o 86/90 da combinação NÃO é número fora do ajuste.
LIMIAR_WB = 0.4

#: Mão do MediaPipe entra no complemento quando a sobreposição com TODA mão aceita do
#: Wholebody é menor que isto. Valor definido pelo coordenador; não reajustado nesta
#: tarefa.
SOBREPOSICAO_COMPLEMENTO = 0.3

#: Lado do rótulo do MediaPipe para o lado usado aqui.
LADO_MEDIAPIPE = {"L": "esquerda", "R": "direita"}


def _mao_do_wholebody(mao: dict, lado: str) -> dict:
    """Converte uma mão do Wholebody para o formato devolvido por ``combinar``.

    Args:
        mao: mão da pessoa, com ``caixa``, ``media`` e ``pts`` no formato ``[x, y, score]``.
        lado: ``esquerda``, ``direita`` ou ``incerto``.

    Returns:
        Mão com ``origem = "wholebody"``, ``pts`` como ``[x, y]`` e ``scores`` separados.
    """
    return {
        "lado": lado,
        "origem": "wholebody",
        "caixa": list(mao["caixa"]),
        "pts": [[x, y] for x, y, _ in mao["pts"]],
        "scores": [s for _, _, s in mao["pts"]],
        "media": mao["media"],
    }


def _mao_do_mediapipe(mao: dict) -> dict:
    """Converte uma mão do MediaPipe para o formato devolvido por ``combinar``.

    Args:
        mao: mão do censo, com ``lado`` (``L`` ou ``R``), ``caixa`` e ``pts`` ``[x, y]``.

    Returns:
        Mão com ``origem = "mediapipe"`` e ``scores``/``media`` iguais a None (o MediaPipe
        não dá score por ponto no censo).
    """
    return {
        "lado": LADO_MEDIAPIPE[mao["lado"]],
        "origem": "mediapipe",
        "caixa": list(mao["caixa"]),
        "pts": [list(p) for p in mao["pts"]],
        "scores": None,
        "media": None,
    }


def _maos_da_pessoa(pessoa: dict) -> list[dict]:
    """Mãos aceitas de uma pessoa do Wholebody, cada uma com o lado do corpo.

    Args:
        pessoa: ``caixa`` da pessoa e, para ``esquerda`` e ``direita``, uma mão com
            ``caixa``, ``media`` e ``pts`` (``[x, y, score]``).

    Returns:
        Zero, uma ou duas mãos; cada mão com média acima de ``LIMIAR_WB``.
    """
    return [
        _mao_do_wholebody(pessoa[lado], lado)
        for lado in ("esquerda", "direita")
        if pessoa[lado]["media"] > LIMIAR_WB
    ]


def combinar(pessoas_wb: list[dict], maos_mp: list[dict]) -> list[dict]:
    """Mãos de um quadro, pelas regras do módulo.

    Args:
        pessoas_wb: pessoas do Wholebody (``caixa``, ``esquerda`` e ``direita``, cada uma
            com ``caixa``, ``media`` e ``pts`` ``[x, y, score]``).
        maos_mp: mãos do MediaPipe (``lado`` ``L``/``R``, ``caixa``, ``score``,
            ``pts`` ``[x, y]`` e ``na_tab``).

    Returns:
        Uma entrada por mão, com ``lado`` (``esquerda``, ``direita`` ou ``incerto``),
        ``origem``, ``caixa``, ``pts``, ``scores`` (ou None), ``media`` (ou None).
    """
    aceitas: list[dict] = []
    for pessoa in pessoas_wb:
        aceitas += _maos_da_pessoa(pessoa)

    complemento = [
        m
        for m in maos_mp
        if not m["na_tab"]
        and all(
            sobreposicao(m["caixa"], a["caixa"]) < SOBREPOSICAO_COMPLEMENTO
            for a in aceitas
        )
    ]
    aceitas += [_mao_do_mediapipe(m) for m in fundir_maos(complemento)]
    return aceitas


def afirmacoes(maos: list[dict]) -> dict:
    """O que o quadro afirma: há mão esquerda, direita ou de lado incerto.

    Args:
        maos: saída de ``combinar``.

    Returns:
        ``{"esquerda": bool, "direita": bool, "incerto": bool}``.
    """
    lados = {m["lado"] for m in maos}
    return {
        "esquerda": "esquerda" in lados,
        "direita": "direita" in lados,
        "incerto": "incerto" in lados,
    }
