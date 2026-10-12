"""Regras de combinação das mãos (Wholebody + MediaPipe), com dados sintéticos."""

from __future__ import annotations

from tab.maos_combinar import afirmacoes, combinar


def _pontos_xy(caixa: list[float]) -> list[list[float]]:
    """21 pontos entre os cantos da caixa; a caixa dos pontos é a própria caixa.

    Args:
        caixa: ``[x0, y0, x1, y1]``.

    Returns:
        Pontos ``[x, y]``.
    """
    x0, y0, x1, y1 = caixa
    return [[x0 + (x1 - x0) * k / 20, y0 + (y1 - y0) * k / 20] for k in range(21)]


def _mao_wb(caixa: list[float], media: float) -> dict:
    """Mão do Wholebody com os 21 scores iguais a ``media``.

    Args:
        caixa: caixa da mão.
        media: média (e valor de cada score).

    Returns:
        Mão no formato de ``tab.maos_detector`` (``caixa``, ``media``, ``pts``).
    """
    return {
        "caixa": caixa,
        "media": media,
        "pts": [[x, y, media] for x, y in _pontos_xy(caixa)],
    }


def _pessoa(
    esq: tuple[list[float], float] | None, dir_: tuple[list[float], float] | None
) -> dict:
    """Pessoa do Wholebody com a mão esquerda e a direita, cada uma (caixa, média).

    Args:
        esq: ``(caixa, media)`` da mão esquerda da pessoa.
        dir_: ``(caixa, media)`` da mão direita da pessoa.

    Returns:
        Pessoa com ``caixa`` e as duas mãos (uma mão ausente vira média zero).
    """
    sem_mao = [0.0, 0.0, 1.0, 1.0]
    e = esq or (sem_mao, 0.0)
    d = dir_ or (sem_mao, 0.0)
    return {
        "caixa": [0, 0, 400, 800],
        "esquerda": _mao_wb(e[0], e[1]),
        "direita": _mao_wb(d[0], d[1]),
    }


def _mp(
    caixa: list[float], lado: str, na_tab: bool = False, score: float = 0.9
) -> dict:
    """Mão do MediaPipe no formato do censo.

    Args:
        caixa: caixa da mão.
        lado: ``L`` ou ``R``.
        na_tab: se a mão está dentro do painel da tablatura.
        score: score de detecção do MediaPipe.

    Returns:
        Mão com ``lado``, ``score``, ``caixa``, ``pts`` ``[x, y]`` e ``na_tab``.
    """
    return {
        "lado": lado,
        "score": score,
        "caixa": caixa,
        "pts": _pontos_xy(caixa),
        "na_tab": na_tab,
    }


ESQ_PERTO = [100.0, 300.0, 160.0, 380.0]
DIR_LONGE = [250.0, 300.0, 310.0, 380.0]
LONGE = [500.0, 500.0, 560.0, 580.0]


def test_wholebody_abaixo_do_limiar_nao_entra() -> None:
    """Média 0,39 não entra; média exatamente no limiar também não (comparação estrita)."""
    maos = combinar([_pessoa((ESQ_PERTO, 0.39), (DIR_LONGE, 0.9))], [])
    assert [m["lado"] for m in maos] == ["direita"]

    maos = combinar([_pessoa((ESQ_PERTO, 0.4), None)], [])
    assert maos == []


def test_wholebody_acima_do_limiar_entra_com_lado_do_corpo() -> None:
    """Mão acima do limiar entra com o lado da chave do corpo e origem wholebody."""
    maos = combinar([_pessoa((ESQ_PERTO, 0.8), (DIR_LONGE, 0.6))], [])
    assert [(m["lado"], m["origem"]) for m in maos] == [
        ("esquerda", "wholebody"),
        ("direita", "wholebody"),
    ]
    esq = maos[0]
    assert esq["media"] == 0.8
    assert esq["caixa"] == ESQ_PERTO
    assert len(esq["pts"]) == 21
    assert esq["pts"][0] == [ESQ_PERTO[0], ESQ_PERTO[1]]
    assert esq["scores"] == [0.8] * 21


def test_esquerda_e_direita_com_caixas_quase_iguais_continuam_duas() -> None:
    """Mesma pessoa, esquerda e direita com caixas quase iguais: DUAS mãos, cada uma com
    o seu lado. A regra de honestidade foi reprovada (ver a docstring do módulo), então
    nada funde as duas em uma mão incerta.
    """
    quase_igual = [100.0, 300.0, 160.0, 380.0]
    pessoa = _pessoa((ESQ_PERTO, 0.9), (quase_igual, 0.6))
    maos = combinar([pessoa], [])
    assert sorted((m["lado"], m["media"]) for m in maos) == [
        ("direita", 0.6),
        ("esquerda", 0.9),
    ]
    assert afirmacoes(maos) == {"esquerda": True, "direita": True, "incerto": False}


def test_maos_separadas_continuam_duas() -> None:
    """Esquerda e direita longe uma da outra são duas mãos, sem regra de honestidade."""
    maos = combinar([_pessoa((ESQ_PERTO, 0.9), (DIR_LONGE, 0.9))], [])
    assert sorted(m["lado"] for m in maos) == ["direita", "esquerda"]
    assert afirmacoes(maos) == {"esquerda": True, "direita": True, "incerto": False}


def test_mediapipe_sobre_wholebody_nao_entra() -> None:
    """Mão do MediaPipe em cima de uma mão aceita do Wholebody não entra."""
    maos = combinar(
        [_pessoa((ESQ_PERTO, 0.9), None)],
        [_mp(ESQ_PERTO, "L")],
    )
    assert [m["origem"] for m in maos] == ["wholebody"]


def test_mediapipe_longe_entra_com_origem_e_lado_do_rotulo() -> None:
    """Mão do MediaPipe longe das aceitas entra com origem mediapipe e lado do rótulo."""
    maos = combinar(
        [_pessoa((ESQ_PERTO, 0.9), None)],
        [_mp(LONGE, "R")],
    )
    assert [(m["lado"], m["origem"]) for m in maos] == [
        ("esquerda", "wholebody"),
        ("direita", "mediapipe"),
    ]
    complemento = maos[1]
    assert complemento["scores"] is None
    assert complemento["media"] is None
    assert complemento["caixa"] == LONGE


def test_mediapipe_sobre_mao_do_wholebody_com_caixa_quase_igual_nao_entra() -> None:
    """Com as duas mãos do Wholebody aceitas, o complemento que cai sobre uma delas não
    entra, mesmo que a outra tenha caixa quase igual.
    """
    quase_igual = [100.0, 300.0, 160.0, 380.0]
    maos = combinar(
        [_pessoa((ESQ_PERTO, 0.9), (quase_igual, 0.6))],
        [_mp(ESQ_PERTO, "L")],
    )
    assert sorted(m["origem"] for m in maos) == ["wholebody", "wholebody"]


def test_mediapipe_na_tab_nao_entra() -> None:
    """Mão desenhada dentro da tablatura nunca entra, mesmo longe das demais."""
    maos = combinar([], [_mp(LONGE, "L", na_tab=True)])
    assert maos == []


def test_mediapipe_duplicadas_entre_si_viram_uma() -> None:
    """Duas mãos do MediaPipe da mesma caixa se fundem; fica a de maior score."""
    maos = combinar(
        [],
        [_mp(LONGE, "R", score=0.6), _mp(LONGE, "R", score=0.95)],
    )
    assert len(maos) == 1
    assert maos[0]["lado"] == "direita"
    assert maos[0]["origem"] == "mediapipe"


def test_afirmacoes_sem_mao_e_com_mediapipe() -> None:
    """Quadro sem nenhuma mão afirma nada; mão só do MediaPipe afirma o seu lado."""
    assert afirmacoes([]) == {"esquerda": False, "direita": False, "incerto": False}
    maos = combinar([], [_mp(LONGE, "L")])
    assert afirmacoes(maos) == {"esquerda": True, "direita": False, "incerto": False}
