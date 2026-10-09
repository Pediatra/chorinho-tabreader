"""Monta amostras para GABARITO VERIFICADO a partir do acervo real.

Para cada (vídeo, instante): extrai o quadro, acha a grade da tablatura, recorta a
região da TAB ampliada (para leitura humana) e grava a segmentação automática
(corda, x, caixa de cada glifo). O rótulo (a casa) é preenchido à mão depois.

Uso:
    python -m tab.ouro --saida data/saida/ouro --n 6
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random

import cv2
import numpy as np

from .caminhos import SAIDA, acervo
from .inventario import ler_quadro
from .painel import escolher

RAIZ = acervo()


def melhor_faixa(frame: np.ndarray):
    """Painel de tablatura do quadro — a MESMA escolha do pipeline (`tab.painel`).

    Aqui havia uma cópia do critério antigo (glifos centrados), que num quadro real do
    `sky guitar` escolhia o **braço do violão** em vez da tablatura. Montagem de gabarito
    feita na faixa errada é gabarito errado — e o gabarito é a verdade do projeto.

    Args:
        frame: quadro inteiro.

    Returns:
        O candidato escolhido (`.nome`, `.roi`, `.grade`) ou None.
    """
    return escolher(frame)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=RAIZ)
    ap.add_argument("--saida", default=str(SAIDA / "ouro"))
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--por-canal", type=int, default=1)
    ap.add_argument("--canais", nargs="*", default=None)
    # Vários instantes: medido no `sky guitar`, a tablatura aparece da metade para o
    # fim, então procurar em 0,5/0,7/0,85 custa pouco e evita montagem sem tablatura.
    ap.add_argument("--instantes", nargs="+", type=float, default=[0.5, 0.7, 0.85])
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    os.makedirs(args.saida, exist_ok=True)
    rng = random.Random(args.seed)

    canais = [
        d
        for d in sorted(glob.glob(os.path.join(args.raiz, "*")))
        if os.path.isdir(d) and os.path.basename(d) != "derived"
    ]
    if args.canais:
        canais = [d for d in canais if os.path.basename(d) in args.canais]
    feitos = 0
    indice = []
    for canal in canais:
        if feitos >= args.n:
            break
        vids = sorted(glob.glob(os.path.join(canal, "**", "*.mp4"), recursive=True))
        if not vids:
            continue
        sucessos_canal = 0
        for v in rng.sample(vids, min(len(vids), 12)):
            if feitos >= args.n or sucessos_canal >= args.por_canal:
                break
            m, frac_usada, via = None, None, None
            for frac in args.instantes:
                quadro, via_lido = ler_quadro(v, frac)
                if quadro is None:
                    continue
                candidato = melhor_faixa(quadro)
                if candidato is None:
                    continue
                chave = (round(candidato.uniformidade, 3), len(candidato.grade.glifos))
                if m is None or chave > (
                    round(m.uniformidade, 3),
                    len(m.grade.glifos),
                ):
                    m, frac_usada, via = candidato, frac, via_lido
            if m is None:
                continue
            faixa, roi, g = m.nome, m.roi, m.grade
            nome = f"{feitos:02d}_{os.path.basename(canal)[:14].strip()}"
            pasta = os.path.join(args.saida, nome)
            os.makedirs(pasta, exist_ok=True)
            # recorte da TAB, 2x, para leitura humana
            l0 = max(0, g.linhas_y[0] - int(1.2 * g.passo))
            l1 = min(roi.shape[0], g.linhas_y[-1] + int(1.2 * g.passo))
            crop = roi[l0:l1, :]
            crop2 = cv2.resize(
                crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
            )
            cv2.imwrite(os.path.join(pasta, "crop2x.png"), crop2)
            glifos = []
            for gl in g.glifos:
                glifos.append(
                    {
                        "corda": int(gl.corda),
                        "x0": int(gl.x0),
                        "x1": int(gl.x1),
                        "y0": int(gl.y0 - l0),
                        "y1": int(gl.y1 - l0),
                        "coluna": int(gl.coluna),
                        "casa": None,
                    }
                )
            auto = {
                "video": os.path.relpath(v, args.raiz),
                "instante_frac": frac_usada,
                "via": via,
                "faixa": faixa,
                "y0_roi": l0,
                "passo": round(g.passo, 2),
                "linhas_y": g.linhas_y,
                "glifos": glifos,
            }
            with open(os.path.join(pasta, "auto.json"), "w") as fh:
                json.dump(auto, fh, ensure_ascii=False, indent=1)
            indice.append(
                {
                    "amostra": nome,
                    "video": auto["video"],
                    "faixa": faixa,
                    "passo": auto["passo"],
                    "n_glifos": len(glifos),
                }
            )
            print(
                f"{nome}: {auto['video'][:56]} | faixa={faixa} passo={auto['passo']} "
                f"glifos={len(glifos)}",
                flush=True,
            )
            feitos += 1
            sucessos_canal += 1
    with open(os.path.join(args.saida, "indice.json"), "w") as fh:
        json.dump(indice, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
