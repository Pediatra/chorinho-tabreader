"""Mão esquerda como âncora do braço (M3b, ideia do dono, rodada 1006).

Passo 1 (este módulo, com GPU): roda o ``DetectorMaos`` do M1 nos 20 quadros do gabarito
e grava os pontos das mãos em ``data/saida/maos/m3b/detector2/maos.json``. Depois disso,
todo o resto roda sobre esse JSON, sem GPU.

Uso (dentro do container, com GPU)::

    python -m tab.maos_ancora extrair
"""

from __future__ import annotations

import argparse
import json
import sys

import cv2

from .caminhos import MAOS_M3B
from .maos_detector import DetectorMaos

PASTA_QUADROS = MAOS_M3B / "quadros"
PASTA_DETECTOR2 = MAOS_M3B / "detector2"
ARQUIVO_MAOS = PASTA_DETECTOR2 / "maos.json"
INDICE = MAOS_M3B / "indice.json"


def _pontos_da_mao(pts: list[list[float]]) -> list[list[float]]:
    """Os pontos de uma mão como ``[x, y, score]``; score ``None`` se não houver.

    Args:
        pts: pontos ``[x, y, score]`` (Wholebody) ou ``[x, y]`` (saída de combinar).

    Returns:
        Lista de ``[x, y, score]`` com a mesma ordem.
    """
    saida = []
    for p in pts:
        score = float(p[2]) if len(p) > 2 else None
        saida.append([float(p[0]), float(p[1]), score])
    return saida


def _registro_do_quadro(id_quadro: str, saida: dict, forma: tuple[int, int]) -> dict:
    """Registro JSON de um quadro: pontos das mãos com o lado do corpo.

    Args:
        id_quadro: id do quadro (``q01``...).
        saida: saída de ``DetectorMaos.detectar``.
        forma: ``(altura, largura)`` do quadro em px.

    Returns:
        Dicionário com ``id``, ``forma``, ``maos`` (lado, caixa, média dos scores e os 21
        pontos) e ``pessoas`` (uma entrada por pessoa do Wholebody, com as duas mãos).
    """
    maos = []
    for mao in saida["maos"]:
        maos.append(
            {
                "lado": mao.get("lado"),
                "origem": mao.get("origem"),
                "caixa": mao.get("caixa"),
                "media": mao.get("media"),
                "pts": _pontos_da_mao(mao["pts"]) if "pts" in mao else None,
            }
        )
    pessoas = []
    for pessoa in saida["pessoas_wb"]:
        pessoas.append(
            {
                "caixa": pessoa["caixa"],
                "esquerda": _pontos_da_mao(pessoa["esquerda"]["pts"]),
                "direita": _pontos_da_mao(pessoa["direita"]["pts"]),
            }
        )
    return {
        "id": id_quadro,
        "forma": [int(forma[0]), int(forma[1])],
        "maos": maos,
        "pessoas": pessoas,
    }


def extrair(ids: list[str] | None = None) -> list[dict]:
    """Roda o detector de mãos (GPU) nos quadros pedidos e devolve os registros.

    Args:
        ids: ids dos quadros (``q01``...). ``None`` = todos os 20 do índice.

    Returns:
        Um registro por quadro, na ordem do índice.

    Raises:
        SystemExit: se algum quadro pedido não estiver no índice.
    """
    indice = json.loads(INDICE.read_text(encoding="utf-8"))["quadros"]
    if ids is not None:
        pedidos = set(ids)
        indice = [q for q in indice if q["id"] in pedidos]
        if len(indice) != len(pedidos):
            raise SystemExit("quadro pedido fora do índice do m3b")

    det = DetectorMaos("cuda")
    registros = []
    for item in indice:
        bgr = cv2.imread(str(PASTA_QUADROS / f"{item['id']}.png"))
        if bgr is None:
            raise SystemExit(f"quadro ilegível: {item['id']}")
        saida = det.detectar(bgr, None)
        registros.append(_registro_do_quadro(item["id"], saida, bgr.shape[:2]))
        print(
            f"{item['id']}: {len(saida['maos'])} mão(s), "
            f"{len(saida['pessoas_wb'])} pessoa(s)"
        )
    return registros


def main() -> int:
    """CLI do passo de âncora: ``extrair`` grava ``maos.json`` (precisa de GPU).

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    sub.add_parser("extrair", help="roda o detector de mãos e grava maos.json")
    args = ap.parse_args()
    if args.comando == "extrair":
        registros = extrair()
        PASTA_DETECTOR2.mkdir(parents=True, exist_ok=True)
        ARQUIVO_MAOS.write_text(
            json.dumps({"formato": 1, "quadros": registros}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"gravado: {ARQUIVO_MAOS} ({len(registros)} quadros)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
