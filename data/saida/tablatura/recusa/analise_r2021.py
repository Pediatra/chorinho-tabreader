"""Limiares e combinações de sinais que separam painéis errados dos certos (r2021).

Lê ``sinais_r2021.json`` (gerado por ``sinais_r2021.py``) e, para cada sinal, acha o
melhor limiar único (``<=`` ou ``>=``) que pega mais telas erradas recusando no máximo
``CERTAS_MAX`` certas. Depois testa a regra OU de dois sinais (todas as duplas), com o
mesmo teto de certas recusadas, e lista as 5 melhores duplas. Por fim imprime as
erradas que nenhuma dessas regras pega.

Uso:
    python data/saida/tablatura/recusa/analise_r2021.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
SAIDA = RAIZ / "data/saida/tablatura/recusa"
SINAIS_JSON = SAIDA / "sinais_r2021.json"

#: Teto de certas recusadas (2 % de 582).
CERTAS_MAX = 11

#: Sinais testados (campos de ``sinais_r2021.json``; booleanos viram 0/1).
SINAIS = [
    "cordas_continuas",
    "deriva_px",
    "deriva_passos",
    "cordas_convergem",
    "forca_min",
    "forca_media",
    "forca_desvio",
    "espacamento_regular",
    "notas_por_largura",
    "e_tablatura",
    "saturacao_media",
    "cinza_desvio",
    "fracao_borda",
    "papel_branco",
    "uniformidade",
    "passo",
    "n_notas",
    "conf_media",
    "e_pauta",
    "largura",
    "altura",
    "x0",
    "y0",
]

#: Campos que mostramos para as erradas que escapam.
MOSTRAR = [
    "forca_min",
    "deriva_passos",
    "cordas_continuas",
    "cordas_convergem",
    "notas_por_largura",
    "saturacao_media",
    "fracao_borda",
    "uniformidade",
]

Regra = tuple[str, str, float]


def _vetor(linhas: list[dict[str, Any]], campo: str) -> np.ndarray:
    """Valores de um sinal por linha; None e booleanos viram NaN ou 0/1.

    Args:
        linhas: linhas de ``sinais_r2021.json``.
        campo: nome do sinal.

    Returns:
        Vetor float, com NaN onde o valor é None.
    """
    valores = []
    for linha in linhas:
        v = linha.get(campo)
        valores.append(np.nan if v is None else float(v))
    return np.array(valores, dtype=np.float64)


def _colunas(vals: np.ndarray) -> tuple[list[tuple[str, float]], np.ndarray]:
    """Todas as regras de um sinal (``<=`` e ``>=`` em cada valor observado).

    Args:
        vals: valores do sinal por tela (NaN = sem medida, nunca dispara).

    Returns:
        A lista ``(operador, limiar)`` de cada coluna, e a matriz de disparos
        (telas x regras) em booleano.
    """
    observados = np.unique(vals[~np.isnan(vals)])
    cols: list[tuple[str, float]] = []
    for t in observados:
        cols.append(("<=", float(t)))
        cols.append((">=", float(t)))
    flags = np.zeros((len(vals), len(cols)), dtype=bool)
    for j, (op, t) in enumerate(cols):
        flags[:, j] = vals <= t if op == "<=" else vals >= t
    return cols, flags


def _melhor_unico(pegas: np.ndarray, recusas: np.ndarray) -> int | None:
    """Índice da regra que pega mais erradas, dentro do teto de certas recusadas.

    Args:
        pegas: erradas pegas por regra.
        recusas: certas recusadas por regra.

    Returns:
        O índice da melhor regra válida (desempate: menos certas recusadas),
        ou None se nenhuma pega alguma errada dentro do teto.
    """
    validas = np.flatnonzero((recusas <= CERTAS_MAX) & (pegas > 0))
    if validas.size == 0:
        return None
    ordem = np.lexsort((recusas[validas], -pegas[validas]))
    return int(validas[ordem[0]])


def main() -> None:
    """Imprime os limiares únicos, as 5 melhores duplas e as erradas que escapam."""
    linhas = json.loads(SINAIS_JSON.read_text(encoding="utf-8"))
    err = np.array([bool(r["errada"]) for r in linhas])
    cert = ~err
    print(f"telas: {len(linhas)}  erradas: {err.sum()}  certas: {cert.sum()}")
    print(f"teto de certas recusadas: {CERTAS_MAX}\n")

    # 1. limiar único por sinal
    colunas: dict[str, tuple[list[tuple[str, float]], np.ndarray]] = {}
    melhores_unicos: list[tuple[int, int, str, Regra]] = []
    print("LIMIAR UNICO por sinal (melhor dentro do teto)")
    print(
        f"{'sinal':22}{'regra':>22}{'pegas/20':>10}{'certas/582':>12}{'sem medida':>12}"
    )
    for campo in SINAIS:
        vals = _vetor(linhas, campo)
        cols, flags = _colunas(vals)
        colunas[campo] = (cols, flags)
        pegas = flags[err].sum(axis=0)
        recusas = flags[cert].sum(axis=0)
        melhor = _melhor_unico(pegas, recusas)
        sem = int(np.isnan(vals).sum())
        if melhor is None:
            print(f"{campo:22}{'(nenhuma)':>22}{'0':>10}{'-':>12}{sem:>12}")
            continue
        op, t = cols[melhor]
        regra_txt = f"{op} {t:.4g}"
        print(
            f"{campo:22}{regra_txt:>22}{int(pegas[melhor]):>10}"
            f"{int(recusas[melhor]):>12}{sem:>12}"
        )
        melhores_unicos.append(
            (int(pegas[melhor]), -int(recusas[melhor]), campo, (campo, op, t))
        )

    # 2. duplas OU, cada sinal com a sua regra (todas as combinações de regras)
    print("\nDUPLAS OU (cada uma com limiar; teto de certas recusadas no total)")
    resultados: list[tuple[int, int, Regra, Regra]] = []
    for i, a in enumerate(SINAIS):
        cols_a, fa = colunas[a]
        ea = fa[err].astype(np.float32)
        ca = fa[cert].astype(np.float32)
        sa_e = ea.sum(axis=0)
        sa_c = ca.sum(axis=0)
        for b in SINAIS[i + 1 :]:
            cols_b, fb = colunas[b]
            eb = fb[err].astype(np.float32)
            cb = fb[cert].astype(np.float32)
            pe = sa_e[:, None] + eb.sum(axis=0)[None, :] - ea.T @ eb
            rc = sa_c[:, None] + cb.sum(axis=0)[None, :] - ca.T @ cb
            score = pe * 1000.0 - rc
            score = np.where((rc <= CERTAS_MAX) & (pe > 0), score, -1e12)
            ia, ib = np.unravel_index(int(np.argmax(score)), score.shape)
            if score[ia, ib] < -1e11:
                continue
            oa, ta = cols_a[ia]
            ob, tb = cols_b[ib]
            resultados.append(
                (
                    int(pe[ia, ib]),
                    int(rc[ia, ib]),
                    (a, oa, ta),
                    (b, ob, tb),
                )
            )
    resultados.sort(key=lambda r: (-r[0], r[1]))
    print(f"duplas com alguma regra valida: {len(resultados)}")
    top = resultados[:5]
    for pe, rc, ra, rb in top:
        print(
            f"  pegas {pe:2d}/20  certas recusadas {rc:2d}/582  "
            f"{ra[0]} {ra[1]} {ra[2]:.4g}  OU  {rb[0]} {rb[1]} {rb[2]:.4g}"
        )

    # 3. erradas que escapam da melhor regra única e das 5 melhores duplas
    regras_boas: list[Regra] = []
    if melhores_unicos:
        melhores_unicos.sort(key=lambda r: (-r[0], -r[1]))
        regras_boas.append(melhores_unicos[0][3])
    print("\nERRADAS QUE ESCAPAM (nem o melhor limiar unico nem as 5 duplas pegam)")
    pegou = np.zeros(len(linhas), dtype=bool)
    for regra in regras_boas:
        pegou |= _disparo(linhas, colunas, regra)
    for _pe, _rc, ra, rb in top:
        pegou |= _disparo(linhas, colunas, ra) | _disparo(linhas, colunas, rb)
    escapes = [r for r, p, e in zip(linhas, pegou, err, strict=True) if e and not p]
    print(f"  escapam: {len(escapes)} de {int(err.sum())}")
    for r in escapes:
        sinais = " ".join(f"{c}={_fmt(r.get(c))}" for c in MOSTRAR)
        print(f"  k={r['k']} tela={r['tela']} erro={r.get('erro')} {sinais}")

    print("\nCERTAS RECUSADAS pela melhor dupla")
    if top:
        ra, rb = top[0][2], top[0][3]
        marcadas = _disparo(linhas, colunas, ra) | _disparo(linhas, colunas, rb)
        recusadas = [
            r for r, m, c in zip(linhas, marcadas, cert, strict=True) if m and c
        ]
        print(
            f"  {len(recusadas)} certas: "
            + ", ".join(f"k={r['k']} tela={r['tela']}" for r in recusadas)
        )


def _disparo(
    linhas: list[dict[str, Any]],
    colunas: dict[str, tuple[list[tuple[str, float]], np.ndarray]],
    regra: Regra,
) -> np.ndarray:
    """Quais telas disparam a regra (um sinal, com operador e limiar).

    Args:
        linhas: linhas de ``sinais_r2021.json``.
        colunas: regras de cada sinal, já calculadas.
        regra: ``(sinal, operador, limiar)``.

    Returns:
        Máscara booleana, uma posição por tela.
    """
    campo, op, t = regra
    cols, flags = colunas[campo]
    j = cols.index((op, t))
    return flags[:, j].copy()


def _fmt(v: Any) -> str:
    """Formata um valor de sinal para a linha de escape.

    Args:
        v: valor (número, bool ou None).

    Returns:
        Texto curto.
    """
    if v is None:
        return "None"
    if isinstance(v, bool):
        return str(v)
    return f"{float(v):.3g}"


if __name__ == "__main__":
    main()
