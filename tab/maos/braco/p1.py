"""Rodada 1028, P1: medida da previsão de trastes em perspectiva (``r``).

Nos quadros de m26 e m27 com nut e com os trastes 5 e 12 numerados pelo dono, a previsão
é feita a partir dessas duas âncoras e comparada com os outros trastes marcados. O erro
é medido em casas: a posição marcada pelo dono é levada à curva prevista (interpolação
na tabela de posições) e a diferença de número é o erro.

A regra atual (``prever_trastes``, com o nut fixando b) e uma referência linear (c = 0,
mesma âncora de nut) são medidas lado a lado.

CLI: ``python -m tab.maos_braco_p1 medir``. Grava ``data/saida/maos/m21/p1_r.json``.
"""

from __future__ import annotations

import itertools
import sys

import numpy as np

from tab.comum.caminhos import (
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    MAOS_M21,
    MAOS_M26,
    MAOS_M27,
)
from tab.maos.braco.detector import _gravar_json, _ler_json
from tab.maos.braco.gabarito import numerar_trastes
from tab.maos.braco.regra import N_MAXIMO, eixo_do_braco, prever_trastes, s_do_traste

#: Âncoras do teste do pré-registro.
ANCORAS = (5, 12)
#: Mínimo de trastes numerados no quadro.
MINIMO_TRASTES = 4
#: Limites do pré-registro (casas).
LIMITE_MEDIANA = 0.15
LIMITE_P90 = 0.30
ARQUIVO_P1 = MAOS_M21 / "p1_r.json"


def _projetar(pontos: list[list[float]] | None, origem, u) -> list[float]:
    """Posição ao longo do eixo de cada ponto (``t``).

    Args:
        pontos: pontos ``[x, y]``.
        origem: origem do eixo.
        u: vetor unitário do eixo.

    Returns:
        Lista de ``t`` na mesma ordem.
    """
    return [float(np.dot(np.asarray(p, dtype=float) - origem, u)) for p in pontos]


def _erros_casas(
    t_tabela: dict[int, float], t_marcados: dict[int, float]
) -> tuple[list[float], int]:
    """Erro em casas de cada traste marcado contra a curva prevista.

    Args:
        t_tabela: ``{numero: t}`` da curva prevista (inclui 0 para o nut).
        t_marcados: ``{numero: t}`` dos trastes marcados pelo dono, exceto as âncoras.

    Returns:
        ``(erros, fora)``: erros absolutos em casas e quantos caíram fora da curva.
    """
    numeros = sorted(t_tabela)
    t_vals = [t_tabela[n] for n in numeros]
    if any(x >= y for x, y in itertools.pairwise(t_vals)):
        return [], len(t_marcados)
    erros: list[float] = []
    fora = 0
    for n, t in t_marcados.items():
        if not (t_vals[0] <= t <= t_vals[-1]):
            fora += 1
            continue
        n_hat = float(np.interp(t, t_vals, numeros))
        erros.append(abs(n_hat - n))
    return erros, fora


def _resumo(erros: list[float]) -> dict:
    """Mediana e p90 dos erros, com a contagem.

    Args:
        erros: erros em casas.

    Returns:
        Dicionário com ``n``, ``mediana`` e ``p90`` (None sem erros).
    """
    if not erros:
        return {"n": 0, "mediana": None, "p90": None}
    return {
        "n": len(erros),
        "mediana": round(float(np.median(erros)), 4),
        "p90": round(float(np.percentile(erros, 90)), 4),
    }


def medir_quadro(registro: dict, dimensoes: tuple[int, int]) -> dict | None:
    """Erros de um quadro: regra atual e referência linear, a partir de 5 e 12.

    Args:
        registro: quadro do gabarito do dono (com nut e trastes).
        dimensoes: ``(largura, altura)`` do quadro.

    Returns:
        Erros em casas dos dois métodos, ou None se o quadro não serve ao teste.
    """
    if not isinstance(registro.get("nut"), list):
        return None
    numerados = [
        item for item in numerar_trastes(registro) if item["numero"] is not None
    ]
    if len(numerados) < MINIMO_TRASTES:
        return None
    por_numero = {item["numero"]: item["ponto"] for item in numerados}
    if not all(n in por_numero for n in ANCORAS):
        return None
    ancoras = {n: por_numero[n] for n in ANCORAS}
    corda1, corda6 = registro["corda1"], registro["corda6"]
    nut = registro["nut"]
    origem, u = eixo_do_braco(corda1, corda6)
    media = np.mean([np.asarray(p, dtype=float) for p in ancoras.values()], axis=0)
    if float(np.dot(media - np.asarray(nut, dtype=float), u)) < 0.0:
        u = -u
    t_nut = _projetar([nut], origem, u)[0]
    t_marcados = {
        n: _projetar([p], origem, u)[0]
        for n, p in por_numero.items()
        if n not in ANCORAS
    }
    # Regra atual: pontos previstos, projetados no mesmo eixo.
    previsao = prever_trastes(nut, corda1, corda6, ancoras, dimensoes, N_MAXIMO)
    tabela_atual = {0: t_nut}
    for n, ponto in previsao.items():
        tabela_atual[n] = _projetar([ponto], origem, u)[0]
    # Referência linear: t = t_nut + a * s, com a pelas duas âncoras.
    s_a = [s_do_traste(n) for n in ANCORAS]
    t_a = [_projetar([ancoras[n]], origem, u)[0] for n in ANCORAS]
    a = float(np.mean([(t - t_nut) / s for t, s in zip(t_a, s_a, strict=True)]))
    tabela_linear = {n: t_nut + a * s_do_traste(n) for n in range(0, N_MAXIMO + 1)}
    erros_atual, fora_atual = _erros_casas(tabela_atual, t_marcados)
    erros_linear, fora_linear = _erros_casas(tabela_linear, t_marcados)
    return {
        "atual": erros_atual,
        "atual_fora": fora_atual,
        "linear": erros_linear,
        "linear_fora": fora_linear,
    }


def medir() -> int:
    """Roda o teste do P1 nas fontes m26 e m27 e grava o json.

    Returns:
        0 ao terminar.
    """
    dados = {"atual": [], "linear": []}
    quadros = []
    fora = {"atual": 0, "linear": 0}
    fontes = (
        ("M26", GABARITO_BRACO_M26, MAOS_M26),
        ("M27", GABARITO_BRACO_M27, MAOS_M27),
    )
    for origem, gabarito, pasta in fontes:
        indice = {q["id"]: q for q in _ler_json(pasta / "indice.json")["quadros"]}
        for id_quadro, registro in _ler_json(gabarito)["quadros"].items():
            if registro.get("braco") != "sim":
                continue
            quadro = indice[id_quadro]
            dimensoes = (quadro["largura"], quadro["altura"])
            resultado = medir_quadro(registro, dimensoes)
            if resultado is None:
                continue
            quadros.append(f"{origem}-{id_quadro}")
            dados["atual"] += resultado["atual"]
            dados["linear"] += resultado["linear"]
            fora["atual"] += resultado["atual_fora"]
            fora["linear"] += resultado["linear_fora"]
    resumo = {
        "regra_atual": _resumo(dados["atual"]),
        "referencia_linear": _resumo(dados["linear"]),
    }
    passa = (
        resumo["regra_atual"]["mediana"] is not None
        and resumo["regra_atual"]["mediana"] <= LIMITE_MEDIANA
        and resumo["regra_atual"]["p90"] <= LIMITE_P90
    )
    saida = {
        "rodada": 1028,
        "parte": "P1",
        "ancoras": list(ANCORAS),
        "quadros": quadros,
        "quadros_usados": len(quadros),
        "fora_da_curva": fora,
        "limites": {"mediana": LIMITE_MEDIANA, "p90": LIMITE_P90},
        "resumo": resumo,
        "passa_regra_atual": passa,
        "comando": "python -m tab.maos_braco_p1 medir",
    }
    _gravar_json(ARQUIVO_P1, saida)
    print(f"P1: {len(quadros)} quadros; {resumo}; passa={passa}", file=sys.stderr)
    return 0


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    return medir()


if __name__ == "__main__":
    sys.exit(main())
