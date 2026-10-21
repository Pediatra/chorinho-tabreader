"""A1 da partitura: imagem limpa antes do Audiveris (rodada 3110).

Variantes de limpeza do recorte de sem produto, medidas pelo Audiveris x2_margem:

- ``b``: o maior dos 3 canais de cada pixel (cinza pelo máximo de R, G e B);
- ``c``: pixels com saturação > 0,20 e brilho > 0,40 (HSV) viram branco (cursor de
  reprodução, faixa amarela);
- ``d``: moldura branca de 50 px no recorte, antes de o Audiveris ampliar 2×.

O conjunto "com faixa" é o do ``medir.py``: fração de pixels amarelos > 0,05 na entrada
ampliada da condição ``x2_margem`` do piloto. Hoje são 36 recortes; 24 leem.

Só lê o que está gravado e grava as imagens e as execuções na pasta da frente A.
Não lê vídeo.

Uso (dentro do container, na raiz do projeto)::

    python -m tab.partitura_imagem --variante b
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from .caminhos import PART_FRENTE_A, PARTITURA_SEM_PRODUTO
from .partitura_omr import rodar_um

PASTA_SP = PARTITURA_SEM_PRODUTO
LIMIAR_FAIXA = 0.05
SATURACAO_MINIMA = 0.20
BRILHO_MINIMO = 0.40
MOLDURA_PX = 50
VARIANTES = ("b", "c", "d")


def _com_faixa(entrada: Path) -> bool:
    """Diz se a entrada ampliada tem cursor amarelo acima do limiar (regra do ``medir.py``).

    Args:
        entrada: ``entrada.png`` da condição ``x2_margem`` do recorte.

    Returns:
        True se a fração de pixels amarelos passa de ``LIMIAR_FAIXA``.
    """
    img = cv2.imread(str(entrada))
    if img is None:
        return False
    b, g, r = [c.astype(int) for c in cv2.split(img)]
    amarelo = ((r - b) > 40) & ((g - b) > 40)
    return float(amarelo.mean()) > LIMIAR_FAIXA


def conjunto_com_faixa() -> list[dict]:
    """Os recortes "com faixa" do piloto sem produto, com o PNG 1× de origem.

    Returns:
        Lista de ``{"slug", "id", "origem", "ok_base"}``, na ordem do piloto. ``ok_base`` é o
        resultado do ``x2_margem`` sem limpeza, vindo do ``execucao.json``.
    """
    itens = []
    for pasta in sorted(PASTA_SP.iterdir()):
        execucao = pasta / "omr" / "audiveris" / "x2_margem" / "execucao.json"
        if not execucao.exists():
            continue
        for registro in json.loads(execucao.read_text(encoding="utf-8")):
            rid = registro["id"]
            entrada = pasta / "omr" / "audiveris" / "x2_margem" / rid / "entrada.png"
            if not entrada.exists() or not _com_faixa(entrada):
                continue
            origem = pasta / "recortes" / f"{rid}.png"
            itens.append(
                {
                    "slug": pasta.name,
                    "id": rid,
                    "origem": str(origem),
                    "ok_base": bool(registro["ok"]),
                }
            )
    return itens


def limpar(imagem: np.ndarray, variante: str) -> np.ndarray:
    """Aplica a variante ao recorte 1× (sem ampliar; o Audiveris amplia depois).

    Args:
        imagem: recorte BGR, como lido pelo OpenCV.
        variante: ``b``, ``c`` ou ``d``.

    Returns:
        Imagem BGR com a limpeza aplicada.

    Raises:
        ValueError: se a variante não existe.
    """
    if variante == "b":
        maximo = imagem.max(axis=2)
        return cv2.cvtColor(maximo, cv2.COLOR_GRAY2BGR)
    if variante == "c":
        hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)
        faixa = (hsv[..., 1] / 255.0 > SATURACAO_MINIMA) & (
            hsv[..., 2] / 255.0 > BRILHO_MINIMO
        )
        saida = imagem.copy()
        saida[faixa] = 255
        return saida
    if variante == "d":
        return cv2.copyMakeBorder(
            imagem,
            MOLDURA_PX,
            MOLDURA_PX,
            MOLDURA_PX,
            MOLDURA_PX,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255),
        )
    raise ValueError(f"variante desconhecida: {variante}")


def rodar(variante: str) -> dict:
    """Roda uma variante nos 36 recortes com faixa e devolve o resumo.

    Args:
        variante: ``b``, ``c`` ou ``d``.

    Returns:
        Documento com ``variante``, ``total``, ``ok`` (quantos leem), ``ok_base`` (quantos
        liam sem limpeza) e ``registros`` (um por recorte).
    """
    pasta_base = PART_FRENTE_A / "variantes" / variante
    limpos = PART_FRENTE_A / "variantes" / variante / "png"
    limpos.mkdir(parents=True, exist_ok=True)
    registros = []
    for item in conjunto_com_faixa():
        img = cv2.imread(item["origem"])
        if img is None:
            registros.append({**item, "ok": False, "motivo": "recorte ilegível"})
            continue
        destino = limpos / f"{item['slug'][:30]}__{item['id']}.png"
        cv2.imwrite(str(destino), limpar(img, variante))
        execucao = rodar_um(
            "audiveris",
            "x2_margem",
            {"id": f"{item['slug'][:30]}__{item['id']}"},
            pasta_base=pasta_base,
            origem=destino,
        )
        registros.append(
            {
                **item,
                "ok": bool(execucao["ok"]),
                "motivo": execucao.get("motivo"),
                "segundos": execucao.get("segundos"),
            }
        )
    return {
        "variante": variante,
        "total": len(registros),
        "ok": sum(1 for r in registros if r["ok"]),
        "ok_base": sum(1 for r in registros if r["ok_base"]),
        "registros": registros,
    }


def main(argv: list[str] | None = None) -> int:
    """Roda uma variante e grava o resumo na pasta da frente A.

    Args:
        argv: ``--variante {b,c,d}``.

    Returns:
        Zero em caso de sucesso.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variante", choices=VARIANTES, required=True)
    args = parser.parse_args(argv)
    documento = rodar(args.variante)
    saida = PART_FRENTE_A / "variantes" / args.variante / "resumo.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"variante {args.variante}: {documento['ok']}/{documento['total']} leem"
        f" (sem limpeza: {documento['ok_base']}/{documento['total']})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
