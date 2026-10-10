"""Mede a DISTRIBUIÇÃO DE FORMAS do marcador no acervo — antes de escrever qualquer associação.

Por que existe: o `sky guitar` ("retrato brasileiro") tem marcador que **pula em patamares**; o código de
tempo mede **velocidade**, que é um *proxy* do estilo "deslizamento" (do `iwaki/henze`), e por isso devolve
`veredito: lento` e **zero tempos**. O dono levantou a objeção que decide o desenho: fixar "ler patamares"
seria a **segunda** regra fixa, e o acervo tem 17 canais e 3.908 vídeos — "e os próximos?".

A formulação que não depende de estilo: **o marcador é um ESTADO** — em cada quadro existe uma nota atual,
e o onset dela é o primeiro quadro em que ela passa a ser a atual. Isso cobre varredura, patamares, quebra
de linha, destaque de dígito e ausência **com a mesma regra**.

Antes de implementar, este módulo MEDE quais formas existem — porque a forma da série decide **como** o
estado é construído (se houver destaque de dígito em muitos vídeos, o estado **não é** uma posição x).

Uso:

    python -m tab.formas_do_marcador --por-canal 1 --passo 30 --json data/saida/formas_marcador.json
"""

import argparse
import glob
import json
import os
import pathlib
import sys
from collections import Counter

from .cursor import rastrear
from .inventario import ler_quadro
from .painel import escolher
from .pipeline import roi_das_cordas


def classificar(resumo: dict) -> str:
    """Classifica a forma do marcador pela série de um vídeo.

    Args:
        resumo: ``resumo`` devolvido por :func:`tab.cursor.rastrear`.

    Returns:
        Uma de ``ausente``, ``pisca``, ``varre``, ``salta``, ``indefinida``.
    """
    cobertura = float(resumo.get("cobertura") or 0.0)
    if cobertura == 0.0:
        return "ausente"
    saltos = int(resumo.get("n_saltos") or 0)
    distintas = int(resumo.get("posicoes_x_distintas") or 0)
    intervalo = resumo.get("intervalo_mediano_entre_saltos_s")
    # PISCANTE: aparece e some, e o x quase não muda de lugar (poucas posições distintas).
    if cobertura < 0.5 and distintas <= 3:
        return "pisca"
    # PATAMARES: muitos saltos discretos, com posições distintas e intervalo regular.
    if saltos >= 20 and distintas >= 10 and intervalo is not None:
        return "salta"
    # VARREDURA: o x percorre o quadro com poucos saltos discretos.
    if distintas >= 5 and saltos < 20:
        return "varre"
    return "indefinida"


def main() -> int:
    """Varre uma amostra do acervo e classifica a forma do marcador por vídeo."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default="/acervo")
    ap.add_argument("--por-canal", type=int, default=1)
    ap.add_argument("--passo", type=int, default=30)
    ap.add_argument("--json")
    args = ap.parse_args()

    canais = sorted(
        d for d in os.listdir(args.raiz) if os.path.isdir(os.path.join(args.raiz, d))
    )
    linhas = []
    for canal in canais:
        videos = sorted(glob.glob(os.path.join(args.raiz, canal, "*.mp4")))[
            : args.por_canal
        ]
        for video in videos:
            try:
                quadro, _ = ler_quadro(video, 0.5)
                if quadro is None:
                    linhas.append(
                        {
                            "canal": canal,
                            "video": os.path.basename(video),
                            "forma": "quadro ilegivel",
                        }
                    )
                    continue
                cand = escolher(quadro)
                if cand is None:
                    linhas.append(
                        {
                            "canal": canal,
                            "video": os.path.basename(video),
                            "forma": "sem painel",
                        }
                    )
                    continue
                y0, y1 = roi_das_cordas(cand)
                r = rastrear(video, (y0, y1), passo=args.passo)
                resumo = r.get("resumo") or {}
                forma = classificar(resumo)
                linhas.append(
                    {
                        "canal": canal,
                        "video": os.path.basename(video),
                        "forma": forma,
                        "cobertura": round(float(resumo.get("cobertura") or 0.0), 3),
                        "saltos": resumo.get("n_saltos"),
                        "distintas": resumo.get("posicoes_x_distintas"),
                        "salto_px": resumo.get("salto_mediano_px"),
                        "intervalo_s": resumo.get("intervalo_mediano_entre_saltos_s"),
                        "matiz": resumo.get("matiz_mediana"),
                    }
                )
            except Exception as erro:
                linhas.append(
                    {
                        "canal": canal,
                        "video": os.path.basename(video),
                        "forma": f"erro: {type(erro).__name__}",
                    }
                )
            print(
                f"{canal[:16]:<16} {os.path.basename(video)[:34]:<34} {linhas[-1]['forma']}",
                flush=True,
            )
    contagem = Counter(x["forma"] for x in linhas)
    print("\nDISTRIBUIÇÃO DE FORMAS:", dict(contagem))
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(
                {"linhas": linhas, "distribuicao": dict(contagem)},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
