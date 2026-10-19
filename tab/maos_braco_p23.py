"""Rodada 1028, P2 + P3: medida nas rodadas 1026 e 1027 com os pesos atuais.

Quatro configurações por rodada, medidas contra o gabarito final do dono (a mesma medida
do ``medir`` do ciclo): antes (``previsto.json`` já gravado), P3 sobre o antes, P2
(recalculado com ``um_braco``, na GPU) e P2 + P3. O P3 só sinaliza (sinal S4).

CLI: ``python -m tab.maos_braco_p23 medir``. Grava ``data/saida/maos/m21/p23_ciclos.json``.
"""

from __future__ import annotations

import sys

from .caminhos import MAOS_M21
from .maos_braco_ciclo import (
    ARQUIVO_PREVISTO,
    ESTAGIO1,
    ESTAGIO2,
    FORMATO_GABARITO,
    RODADAS,
    _ler_json,
    aplicar_consenso,
    medir_quadros,
    previsto_do_resultado,
)
from .maos_braco_detector import (
    PASSOS,
    _carregar_pesos,
    _gravar_json,
    _imagem,
    _trava_gpu,
)
from .maos_braco_localizador import _carregar_localizador, cadeia, sinalizado

ARQUIVO_P23 = MAOS_M21 / "p23_ciclos.json"
#: Critério do pré-registro (P2 + P3, 1027): falsos que passam ≤ 1 de 64.
LIMITE_FALSOS_1027 = 1


def recalcular_p2(numero: str, indice: dict, ordem: list[str]) -> dict:
    """Previsão do P2: a cadeia com o estágio 1 de um braço só (GPU).

    Args:
        numero: rodada (chave de ``RODADAS``).
        indice: ``indice.json`` da rodada.
        ordem: ordem dos ids (a mesma do ``previsto.json``).

    Returns:
        Previsão no formato de ``previsto.json``.
    """
    rodada = RODADAS[numero]
    pasta = rodada.pasta
    por_id = {item["id"]: item for item in indice["quadros"]}
    previstos: dict[str, dict] = {}
    with _trava_gpu():
        loc = _carregar_localizador(ESTAGIO1)
        dois, _ = _carregar_pesos(ESTAGIO2, PASSOS)
        for id_q in ordem:
            item = por_id[id_q]
            imagem = _imagem(pasta / item["png"])
            resultado = cadeia(loc, dois, imagem, id_q, conjunta=True, um_braco=True)
            previstos[id_q] = previsto_do_resultado(
                item, resultado, sinalizado(resultado)
            )
    return {
        "formato": FORMATO_GABARITO,
        "semente": indice["semente"],
        "pesos": {
            "estagio1": ESTAGIO1,
            "estagio2": ESTAGIO2,
            "conjunta": True,
            "um_braco": True,
        },
        "ordem": list(ordem),
        "quadros": previstos,
    }


def _resumo(medida: dict) -> dict:
    """Totais da medida que o pré-registro usa.

    Args:
        medida: saída de ``medir_quadros``.

    Returns:
        Certos entregues, falsos que passam, sinalizados e medidos.
    """
    t = medida["totais"]
    return {
        "medidos": t["medidos"],
        "certos_entregues": t["entregue_certo"],
        "falsos_passam": t["falsos_passam_n"],
        "sinalizados": t["sinalizados"],
        "por_classe": t["por_classe"],
    }


def medir(numeros: tuple[str, ...] = ("1026", "1027")) -> int:
    """Mede as quatro configurações nas rodadas e grava o json.

    Args:
        numeros: rodadas a medir.

    Returns:
        0 ao terminar.
    """
    saida: dict = {"rodada": 1028, "parte": "P2+P3", "rodadas": {}}
    for numero in numeros:
        rodada = RODADAS[numero]
        antes = _ler_json(rodada.pasta / ARQUIVO_PREVISTO)
        gabarito = _ler_json(rodada.gabarito)
        indice = _ler_json(rodada.pasta / "indice.json")
        dimensoes = {q["id"]: (q["largura"], q["altura"]) for q in indice["quadros"]}
        p2 = recalcular_p2(numero, indice, antes["ordem"])
        p3 = aplicar_consenso(antes, dimensoes)
        p23 = aplicar_consenso(p2, dimensoes)
        configs = {
            "antes": antes,
            "P3": p3,
            "P2": p2,
            "P2+P3": p23,
        }
        resultado = {}
        for nome, doc in configs.items():
            medida = medir_quadros(doc, gabarito, rodada.proxima)
            resultado[nome] = _resumo(medida)
            resultado[nome]["S4_sinalizados"] = sum(
                1
                for id_q in doc["ordem"]
                if doc["quadros"][id_q].get("S4", {}).get("S4")
            )
        saida["rodadas"][numero] = resultado
        print(f"{numero}: {resultado}", file=sys.stderr)
    _gravar_json(ARQUIVO_P23, saida)
    return 0


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    return medir()


if __name__ == "__main__":
    sys.exit(main())
