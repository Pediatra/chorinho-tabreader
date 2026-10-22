"""Avaliação do alinhador contra a régua provisória do A1 (trilha A2).

A régua (``data/saida/audio/a1/atraso_mvp.json``) é o ataque achado COM ajuda do marcador,
conferido por escuta do dono. Ela serve só para avaliar: nunca entra no alinhador.

Para cada coluna da régua presente na saída, compara ``t_audio`` com ``t_som`` do fluxo e das
alturas (passada 2). Todo número sai com denominador ("X de Y colunas da régua"). Colunas da
saída sem par na régua são contadas à parte, porque não têm verdade aqui.

Uso::

    python -m tab.audio_alinhar_avaliar --alinhado SAIDA.json \\
        --regua data/saida/audio/a1/atraso_mvp.json [--saida RESUMO.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

#: Limiares de acerto, em segundos.
LIMITE_50_S = 0.050
LIMITE_100_S = 0.100
LIMITE_FALSO_S = 0.200

#: Limiares de confiança da curva confiança x acerto.
LIMIARES_CONFIANCA = (0.0, 0.2, 0.4, 0.6, 0.8)


def ler_regua(caminho: str) -> tuple[dict, dict]:
    """Lê a régua do A1 e devolve os ataques de fluxo e de alturas (passada 2).

    Eventos de passagem com uma coluna só são ignorados (ver ``avaliar``). Chaves
    duplicadas (mesma tela, exibição e coluna) também são contadas.

    Args:
        caminho: JSON do ``tab.audio_atraso``.

    Returns:
        ``(regua, info)``: ``regua`` mapeia ``(tela, exibicao, coluna)`` a
        ``{"fluxo": t|None, "alturas": t|None}``; ``info`` traz contagens de eventos lidos,
        ignorados e chaves duplicadas.
    """
    with open(caminho, encoding="utf-8") as f:
        bruto = json.load(f)
    eventos = bruto["eventos"]
    colunas_por_passagem: Counter = Counter(
        (e["tela"], e["exibicao"], e["passagem"]) for e in eventos
    )
    regua: dict[tuple[int, int, int], dict] = {}
    ignorados = 0
    duplicadas = 0
    for e in eventos:
        if colunas_por_passagem[(e["tela"], e["exibicao"], e["passagem"])] == 1:
            ignorados += 1
            continue
        chave = (int(e["tela"]), int(e["exibicao"]), int(e["coluna"]))
        if chave in regua:
            duplicadas += 1
        passada = e["passada2"]
        regua[chave] = {
            "fluxo": passada["fluxo"]["t_som"],
            "alturas": passada["alturas"]["t_som"],
        }
    info = {
        "eventos_lidos": len(eventos),
        "eventos_ignorados_passagem_de_1_coluna": ignorados,
        "chaves_duplicadas": duplicadas,
    }
    return regua, info


def _proporcao(x: int, y: int) -> str:
    """Texto ``x de y (p %)``, com denominador sempre visível.

    Args:
        x: numerador.
        y: denominador.

    Returns:
        ``"x de y (p %)"``, com ``p`` a 1 casa decimal (``"0 de 0"`` se y for zero).
    """
    if y == 0:
        return "0 de 0"
    return f"{x} de {y} ({100.0 * x / y:.1f} %)"


def _pior_categoria(motivo: str | None) -> str:
    """Categoria da recusa, sem os números: ``"exibicao_recusada: cos 0.3"`` vira o prefixo.

    Args:
        motivo: texto da recusa, ou ``None``.

    Returns:
        Categoria (``"afirmada"`` se ``motivo`` for ``None``).
    """
    if motivo is None:
        return "afirmada"
    return motivo.split(":")[0].strip()


def avaliar(alinhado: dict, regua: dict, info_regua: dict) -> dict:
    """Compara a saída do alinhador com a régua e monta totais, tabelas e curva.

    Args:
        alinhado: JSON de saída de ``tab.audio_alinhar``.
        regua: mapa de ``ler_regua``.
        info_regua: contagens de ``ler_regua``.

    Returns:
        Dicionário com ``regua`` (contagens), ``totais``, ``por_exibicao``, ``recusas``,
        ``curva`` e ``sem_par``.
    """
    saida = {(c["tela"], c["exibicao"], c["coluna"]): c for c in alinhado["colunas"]}
    chaves_regua_sem_saida = [k for k in regua if k not in saida]
    com_referencia = [
        k
        for k in regua
        if k in saida
        and (regua[k]["fluxo"] is not None or regua[k]["alturas"] is not None)
    ]
    sem_referencia = [k for k in regua if k in saida and k not in com_referencia]
    sem_par = [k for k in saida if k not in regua]

    linhas = []
    for k in sorted(com_referencia):
        reg = regua[k]
        c = saida[k]
        t = c["t_audio"]
        refs = [r for r in (reg["fluxo"], reg["alturas"]) if r is not None]
        afirmada = t is not None
        d_fluxo = (
            abs(t - reg["fluxo"]) if afirmada and reg["fluxo"] is not None else None
        )
        d_min = min((abs(t - r) for r in refs), default=None) if afirmada else None
        linhas.append(
            {
                "chave": k,
                "afirmada": afirmada,
                "confianca": c["confianca"],
                "categoria": _pior_categoria(c["motivo"]),
                "ok50": d_fluxo is not None and d_fluxo <= LIMITE_50_S,
                "ok100": d_fluxo is not None and d_fluxo <= LIMITE_100_S,
                "ok50_qualquer": d_min is not None and d_min <= LIMITE_50_S,
                "falso": d_min is not None and d_min > LIMITE_FALSO_S,
            }
        )

    y = len(linhas)
    afirmadas = [ln for ln in linhas if ln["afirmada"]]
    totais = {
        "Y_colunas_regua_com_saida": y,
        "afirmadas": len(afirmadas),
        "recusadas": y - len(afirmadas),
        "ok50_fluxo": sum(ln["ok50"] for ln in linhas),
        "ok100_fluxo": sum(ln["ok100"] for ln in linhas),
        "ok50_fluxo_ou_alturas": sum(ln["ok50_qualquer"] for ln in linhas),
        "falsos_mais_de_200ms": sum(ln["falso"] for ln in linhas),
        "sem_referencia_na_regua": len(sem_referencia),
    }
    recusas = Counter(ln["categoria"] for ln in linhas if not ln["afirmada"])

    info_ex = {(e["tela"], e["exibicao"]): e for e in alinhado.get("exibicoes", [])}
    sem_par_afirmada_ex: Counter = Counter(
        (k[0], k[1]) for k in sem_par if saida[k]["t_audio"] is not None
    )
    por_exibicao = []
    for tela, exib in sorted({(ln["chave"][0], ln["chave"][1]) for ln in linhas}):
        sub = [ln for ln in linhas if ln["chave"][:2] == (tela, exib)]
        cols_regua = [k[2] for k in regua if k[:2] == (tela, exib)]
        trecho_ex = info_ex.get((tela, exib), {}).get("trecho_colunas")
        por_exibicao.append(
            {
                "tela": tela,
                "exibicao": exib,
                "trecho_alinhador": trecho_ex,
                "trecho_regua": (
                    [min(cols_regua), max(cols_regua)] if cols_regua else None
                ),
                "afirmadas_sem_par": sem_par_afirmada_ex.get((tela, exib), 0),
                "Y": len(sub),
                "afirmadas": sum(ln["afirmada"] for ln in sub),
                "ok50_fluxo": sum(ln["ok50"] for ln in sub),
                "ok100_fluxo": sum(ln["ok100"] for ln in sub),
                "ok50_fluxo_ou_alturas": sum(ln["ok50_qualquer"] for ln in sub),
                "falsos": sum(ln["falso"] for ln in sub),
                "recusadas": sum(not ln["afirmada"] for ln in sub),
            }
        )

    curva = []
    for limiar in LIMIARES_CONFIANCA:
        sel = [
            ln
            for ln in afirmadas
            if ln["confianca"] is not None and ln["confianca"] >= limiar
        ]
        curva.append(
            {
                "confianca_minima": limiar,
                "afirmadas": len(sel),
                "ok100_fluxo": sum(ln["ok100"] for ln in sel),
                "falsos": sum(ln["falso"] for ln in sel),
            }
        )

    afirmadas_sem_par = sum(1 for k in sem_par if saida[k]["t_audio"] is not None)
    return {
        "regua": {
            **info_regua,
            "Y_definicao": "colunas da régua presentes na saída com pelo menos uma referência",
            "regua_sem_saida": len(chaves_regua_sem_saida),
        },
        "totais": totais,
        "por_exibicao": por_exibicao,
        "recusas": dict(sorted(recusas.items())),
        "curva": curva,
        "sem_par": {
            "colunas_da_saida_sem_par_na_regua": len(sem_par),
            "afirmadas_sem_par": afirmadas_sem_par,
        },
    }


def _imprimir(res: dict) -> None:
    """Imprime totais, tabela por exibição e curva, com denominadores.

    Args:
        res: saída de ``avaliar``.
    """
    t = res["totais"]
    y = t["Y_colunas_regua_com_saida"]
    print(f"Y (colunas da régua com saída e referência): {y}")
    print(f"afirmadas: {_proporcao(t['afirmadas'], y)}")
    print(f"<= 50 ms do fluxo:            {_proporcao(t['ok50_fluxo'], y)}")
    print(f"<= 100 ms do fluxo:           {_proporcao(t['ok100_fluxo'], y)}")
    print(f"<= 50 ms do fluxo OU alturas: {_proporcao(t['ok50_fluxo_ou_alturas'], y)}")
    print(f"falsos (> 200 ms dos dois):   {_proporcao(t['falsos_mais_de_200ms'], y)}")
    print(f"recusadas: {_proporcao(t['recusadas'], y)} | motivos: {res['recusas']}")
    sp = res["sem_par"]
    print(
        f"colunas da saída sem par na régua: {sp['colunas_da_saida_sem_par_na_regua']}"
        f" | afirmadas entre elas: {sp['afirmadas_sem_par']} (sem verdade aqui)"
    )
    print(
        "por exibição (tela, exibição: Y | afirm | <=50 | <=100 | <=50 F/A | falsos | rec"
        " | afirm sem par | trecho alinhador | trecho régua):"
    )
    for ln in res["por_exibicao"]:
        print(
            f"  t{ln['tela']:>2} e{ln['exibicao']}: {ln['Y']:>2} | {ln['afirmadas']:>2}"
            f" | {ln['ok50_fluxo']:>2} | {ln['ok100_fluxo']:>2}"
            f" | {ln['ok50_fluxo_ou_alturas']:>2} | {ln['falsos']:>2}"
            f" | {ln['recusadas']:>2} | {ln['afirmadas_sem_par']:>2}"
            f" | {ln['trecho_alinhador']} | {ln['trecho_regua']}"
        )
    print("curva confiança x acerto (afirmadas com confiança >= limiar):")
    for ln in res["curva"]:
        print(
            f"  >= {ln['confianca_minima']:.1f}: afirmadas {ln['afirmadas']}"
            f" | <= 100 ms {ln['ok100_fluxo']} | falsas {ln['falsos']}"
        )


def main() -> int:
    """Ponto de entrada da CLI: avalia uma saída do alinhador contra a régua.

    Returns:
        Código de saída (0 se deu certo).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--alinhado", required=True, help="saída do alinhador")
    parser.add_argument("--regua", required=True, help="régua do A1 (atraso_mvp.json)")
    parser.add_argument("--saida", help="grava o resumo neste JSON")
    args = parser.parse_args()

    with open(args.alinhado, encoding="utf-8") as f:
        alinhado = json.load(f)
    regua, info = ler_regua(args.regua)
    res = avaliar(alinhado, regua, info)
    res["metodo"] = alinhado["metodo"]
    print(f"metodo: {alinhado['metodo']} | régua: {info}")
    _imprimir(res)
    if args.saida:
        os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
        texto = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True)
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
        print(f"gravado: {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
