"""Calibração do braço pela música num vídeo fora do MVP, medida contra o dono.

Lê o produto (notas com ``t_ini``) e as pontas dos dedos em cada instante
(``tab.maos_pontas_notas``), calibra a homografia pela música (consenso sobre 3
conjuntos de sementes), mede a estabilidade entre os conjuntos e compara com o gabarito
do dono num quadro do braço (``data/gold/maos/braco.json``). Grava ``medicao.json`` e
``conferencia.png`` (grade prevista em vermelho, pontos do dono em verde) na pasta de
saída.

Uso::

    python -m tab.maos_braco_fora --produto PRODUTO.json --pontas PONTAS.json \\
        --quadro q16
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, MAOS_M3
from .maos_avaliar_dedos import carregar_json
from .maos_calibrar_por_notas import (
    avaliar,
    diferenca_entre_h,
    mapa_de_maos,
    montar_conjunto,
)
from .maos_medicoes_braco import (
    CONJUNTOS_DE_SEMENTES,
    desenhar_conferencia,
    gabarito_dono,
    medir_contra_dono,
)
from .maos_refinar_braco import consenso

#: Índice dos quadros do gabarito do braço (tempo e png de cada quadro).
INDICE_QUADROS = MAOS_M3.parent / "m3b" / "indice.json"

#: Pares de conjuntos comparados na estabilidade (0-1, 0-2, 1-2).
PARES = ((0, 1), (0, 2), (1, 2))


def estabilidade(Hs: list[np.ndarray]) -> dict[str, Any]:
    """Diferença, em px sobre a grade, entre as homografias de cada par de conjuntos.

    Args:
        Hs: uma homografia por conjunto de sementes (na ordem dos conjuntos).

    Returns:
        ``entre_conjuntos`` (uma entrada por par, com ``par``, ``mediana_px`` e
        ``maximo_px``) e ``resumo`` (média e amplitude, entre os pares, da mediana e do
        máximo).
    """
    entre = [{"par": f"{a}-{b}", **diferenca_entre_h(Hs[a], Hs[b])} for a, b in PARES]
    medianas = [p["mediana_px"] for p in entre]
    maximos = [p["maximo_px"] for p in entre]
    resumo = {
        "mediana_px_media": round(float(np.mean(medianas)), 3),
        "mediana_px_amplitude": round(float(np.ptp(medianas)), 3),
        "maximo_px_media": round(float(np.mean(maximos)), 3),
        "maximo_px_amplitude": round(float(np.ptp(maximos)), 3),
    }
    return {"entre_conjuntos": entre, "resumo": resumo}


def achar_quadro(indice: dict[str, Any], quadro: str) -> dict[str, Any]:
    """Entrada do índice de quadros com o id dado.

    Args:
        indice: conteúdo de ``data/saida/maos/m3b/indice.json``.
        quadro: id do quadro (``q16``...).

    Returns:
        A entrada, com ``t`` (instante) e ``png`` (caminho relativo à pasta m3b).

    Raises:
        ValueError: se o id não está no índice.
    """
    for entrada in indice["quadros"]:
        if entrada["id"] == quadro:
            return entrada
    raise ValueError(f"quadro {quadro} não está no índice dos quadros")


def contar_notas(
    produto: list[dict[str, Any]], pontas: list[dict[str, Any]]
) -> dict[str, int]:
    """Quantas notas pisadas e instantes, e quantos instantes têm mão esquerda.

    Args:
        produto: lista ``notas`` do produto.
        pontas: lista ``instantes`` do JSON de pontas.

    Returns:
        ``notas_pisadas`` (casa > 0 com ``t_ini``), ``instantes_pisados`` (distintos),
        ``instantes_com_mao_esquerda`` (dos instantes de pontas com nota pisada) e
        ``instantes_pontas``.
    """
    pisadas = [n for n in produto if n.get("t_ini") is not None and n["casa"] > 0]
    instantes = {round(float(n["t_ini"]), 3) for n in pisadas}
    com_mao = {
        round(float(r["t_ini"]), 3)
        for r in pontas
        if any(m["lado"] == "esquerda" for m in r["maos"])
    }
    return {
        "notas_pisadas": len(pisadas),
        "instantes_pisados": len(instantes),
        "instantes_com_mao_esquerda": len(instantes & com_mao),
        "instantes_pontas": len(pontas),
    }


def _jsonavel(valor: Any) -> Any:
    """Converte escalares e arrays do numpy para tipos do JSON.

    Args:
        valor: objeto não serializável de outra forma.

    Returns:
        Lista ou escalar nativo do Python.
    """
    if hasattr(valor, "tolist"):
        return valor.tolist()
    return str(valor)


def main() -> None:
    """Calibra pela música, mede contra o gabarito do dono e grava a conferência."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--produto", type=Path, required=True)
    parser.add_argument("--pontas", type=Path, required=True)
    parser.add_argument("--quadro", required=True, help="id no braco.json (ex.: q16)")
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="pasta de saída (padrão: data/saida/maos/m3d/<quadro>)",
    )
    parser.add_argument(
        "--recuo",
        type=float,
        default=0.0,
        help="recuo da ponta sobre o DIP, fração do dedo (0 = ponta pura)",
    )
    args = parser.parse_args()
    saida = args.saida or MAOS_M3.parent / "m3d" / args.quadro

    produto = carregar_json(args.produto)["notas"]
    pontas = carregar_json(args.pontas)["instantes"]
    contagem = contar_notas(produto, pontas)
    print(f"contagem: {contagem}", flush=True)
    conj = montar_conjunto(produto, mapa_de_maos(pontas), recuo=args.recuo)
    print(
        f"notas descartadas (casa fora do braço): {conj.descartadas_casa}", flush=True
    )

    consensos = []
    for k, sementes in enumerate(CONJUNTOS_DE_SEMENTES):
        cons = consenso(conj, sementes)
        consensos.append(cons)
        inliers = [c.get("inliers", "invalida") for c in cons["candidatos"]]
        print(
            f"conjunto {k}: escolhida {cons['semente']}, inliers {inliers}, "
            f"sementes invalidas {cons['invalidas']}",
            flush=True,
        )
    H = consensos[0]["H"]
    estab = estabilidade([c["H"] for c in consensos])
    print(f"estabilidade: {estab['resumo']}", flush=True)

    dono = gabarito_dono(GABARITO_BRACO, args.quadro)
    medida = medir_contra_dono(H, dono)
    entrada = achar_quadro(carregar_json(INDICE_QUADROS), args.quadro)
    quadro_png = cv2.imread(str(INDICE_QUADROS.parent / entrada["png"]))
    if quadro_png is None:
        raise SystemExit(f"sem o png do quadro {args.quadro}: {entrada['png']}")
    conferencia = desenhar_conferencia(quadro_png, H, dono)

    saida.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(saida / "conferencia.png"), conferencia)
    resultado = {
        "quadro": args.quadro,
        "recuo": args.recuo,
        "t_quadro": entrada["t"],
        "produto": str(args.produto),
        "pontas": str(args.pontas),
        "contagem": contagem,
        "descartadas_casa": conj.descartadas_casa,
        "inliers_do_conjunto_0": int(avaliar(H, conj)["n"]),
        "notas_com_pontas": len(conj.indices),
        "consenso": [
            {
                "conjunto": k,
                "escolhida": c["semente"],
                "sementes_invalidas": c["invalidas"],
                "candidatos": [
                    {kk: vv for kk, vv in cand.items() if kk != "H"}
                    for cand in c["candidatos"]
                ],
            }
            for k, c in enumerate(consensos)
        ],
        "estabilidade": estab,
        "H": H.tolist(),
        "contra_dono": medida,
        "conferencia_png": str(saida / "conferencia.png"),
    }
    (saida / "medicao.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=_jsonavel),
        encoding="utf-8",
    )

    trastes = medida["trastes"]
    print(
        f"contra o dono ({len(dono['trastes'])} trastes marcados):\n"
        f"  corda1 {medida['cordas']['corda1']['px_media']} px "
        f"(fracao {medida['cordas']['corda1']['fracao_span_16_media']})\n"
        f"  corda6 {medida['cordas']['corda6']['px_media']} px "
        f"(fracao {medida['cordas']['corda6']['fracao_span_16_media']})\n"
        f"  nut {medida['nut']['px']} px (fracao casa1 "
        f"{medida['nut']['fracao_casa1']})\n"
        f"  trastes dentro de 1/4 de casa: {trastes['n_com_traste_previsto']}/"
        f"{trastes['n_total']}, fracao mediana {trastes['fracao_mediana_dos_casados']}"
    )
    print(f"gravado: {saida / 'medicao.json'} e {saida / 'conferencia.png'}")


if __name__ == "__main__":
    main()
