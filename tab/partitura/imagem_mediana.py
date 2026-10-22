"""A1a da partitura: mediana de quadros no tempo, e a combinação d+b (rodada 3110).

- ``a``: mediana, pixel a pixel, de N = 15 quadros espaçados em [t0, t1] da primeira exibição
  do recorte, recortados na mesma caixa (``caixa_recorte`` do ``indice.json``). O cursor de
  reprodução se move, e a mediana tira ele do fundo.
- ``db``: combinação prevista no briefing, se a A1a não recuperar nada: maior dos 3 canais
  (variante b), depois moldura branca de 50 px (variante d).

Quadros só por ``tab.leitor.quadro_em`` (ffmpeg em software; 44 % do acervo é AV1). Um vídeo
por vez. A leitura é feita pelo Audiveris ``x2_margem``, como nas outras variantes.

Este módulo só roda depois que o paginar da D1 terminar, porque ambos leem o HD externo.

Uso (dentro do container, na raiz do projeto)::

    python -m tab.partitura_imagem_mediana --variante a
    python -m tab.partitura_imagem_mediana --variante db
"""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np

from tab.comum.caminhos import PART_FRENTE_A, acervo
from tab.comum.leitor import quadro_em
from tab.partitura.imagem import PASTA_SP, conjunto_com_faixa, limpar
from tab.partitura.omr import rodar_um

N_QUADROS = 15
VARIANTES = ("a", "db")


def _indice_do_slug(slug: str) -> dict[str, dict]:
    """Entradas do ``recortes/indice.json`` de um vídeo do piloto, pelo id.

    Args:
        slug: nome da pasta do vídeo em ``PASTA_SP``.

    Returns:
        Mapa id -> entrada do índice.
    """
    indice = json.loads(
        (PASTA_SP / slug / "recortes" / "indice.json").read_text(encoding="utf-8")
    )
    return {e["id"]: e for e in indice}


def mediana_do_recorte(
    video: str, caixa: list[int], t0: float, t1: float
) -> np.ndarray:
    """Mediana pixel a pixel de N quadros espaçados em [t0, t1], na caixa do recorte.

    Args:
        video: ``canal/arquivo`` do vídeo, no acervo.
        caixa: ``[x0, y0, x1, y1]`` do recorte no quadro do vídeo.
        t0: início da exibição, em segundos.
        t1: fim da exibição, em segundos.

    Returns:
        Imagem BGR com a mediana.

    Raises:
        ValueError: se não sair nenhum quadro.
    """
    x0, y0, x1, y1 = caixa
    caminho = str(acervo() / video)
    recortes = []
    for k in range(N_QUADROS):
        t = t0 + (t1 - t0) * (k + 0.5) / N_QUADROS
        quadro = quadro_em(caminho, t)
        if quadro is None:
            continue
        recortes.append(quadro[y0:y1, x0:x1])
    if not recortes:
        raise ValueError(f"nenhum quadro em {video} [{t0}, {t1}]")
    pilha = np.stack(recortes).astype(np.uint8)
    return np.median(pilha, axis=0).astype(np.uint8)


def rodar(variante: str) -> dict:
    """Roda a A1a (ou d+b) nos 36 recortes com faixa e devolve o resumo.

    Args:
        variante: ``a`` (mediana no tempo) ou ``db`` (maior dos canais, depois moldura;
            recorte 1×, sem mediana).

    Returns:
        Documento com ``variante``, ``total``, ``ok``, ``ok_base`` e ``registros``.
    """
    pasta_base = PART_FRENTE_A / "variantes" / variante
    png_dir = pasta_base / "png"
    png_dir.mkdir(parents=True, exist_ok=True)
    registros = []
    indices: dict[str, dict[str, dict]] = {}
    for item in conjunto_com_faixa():
        slug = item["slug"]
        indices.setdefault(slug, _indice_do_slug(slug))
        entrada = indices[slug][item["id"]]
        nome = f"{slug[:30]}__{item['id']}"
        destino = png_dir / f"{nome}.png"
        try:
            if variante == "a":
                exib = entrada["exibicoes"][0]
                mediana = mediana_do_recorte(
                    entrada["video"], entrada["caixa_recorte"], exib["t0"], exib["t1"]
                )
                cv2.imwrite(str(destino), mediana)
            else:
                origem = cv2.imread(item["origem"])
                cv2.imwrite(str(destino), limpar(limpar(origem, "b"), "d"))
        except ValueError as falha:
            registros.append({**item, "ok": False, "motivo": str(falha)})
            continue
        execucao = rodar_um(
            "audiveris",
            "x2_margem",
            {"id": nome},
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
    """Roda a variante e grava o resumo na pasta da frente A.

    Args:
        argv: ``--variante {a,db}``.

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
