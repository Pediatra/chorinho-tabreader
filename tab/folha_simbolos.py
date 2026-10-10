"""Folha de contato dos SÍMBOLOS INTEIROS que o dono marcou — exibição, não detecção.

Por que existe: o dono viu o símbolo **cortado** na auditoria, e ele estava certo — a janela que o modelo
julga tem 2,4 x 1,6 passos (menos de duas cordas), e era ELA que a página mostrava. Medido depois: mostrar
uma janela maior **não muda a detecção** (78 acertos nos dois lados), mas **mostra o símbolo inteiro**.

Este módulo é só o lado da exibição: recorta cada marca do dono numa janela GENEROSA (4,0 x 3,2 passos,
para caber arco, chave e o que cruza cordas) e monta folhas de 24 recortes — pequenas o bastante para
serem lidas de uma vez. **Não toca no pipeline.**

Uso:

    python -m tab.folha_simbolos --saida data/saida/folha_inteira --jx 2.0 --jy 1.6
"""

import argparse
import glob
import json
import os
import pathlib
import sys

import cv2
import numpy as np

from .inventario import ler_quadro
from .painel import escolher
from .pipeline import roi_das_cordas


def main() -> int:
    """Recorta cada marca do dono numa janela generosa e escreve folhas de 24 recortes."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--marca", default="data/gold/marcas_simbolos_6.json")
    ap.add_argument("--indice", default="data/saida/coleta_marcar/indice.json")
    ap.add_argument("--saida", default="data/saida/folha_inteira")
    ap.add_argument("--jx", type=float, default=2.0)
    ap.add_argument("--jy", type=float, default=1.6)
    ap.add_argument("--altura", type=int, default=96)
    args = ap.parse_args()

    os.makedirs(args.saida, exist_ok=True)
    indice = {
        r["arq"]: r
        for r in json.loads(pathlib.Path(args.indice).read_text(encoding="utf-8"))
    }
    marcas: dict[str, list[dict]] = {}
    for marca in json.loads(pathlib.Path(args.marca).read_text(encoding="utf-8"))[
        "marcas"
    ]:
        marcas.setdefault(marca["imagem"], []).append(marca)

    celulas = []
    for imagem, ms in sorted(marcas.items()):
        reg = indice.get(imagem)
        if reg is None:
            continue
        base = os.path.basename(str(reg["video"]))
        videos = [
            v
            for v in glob.glob(f"/acervo/{reg['canal']}/*.mp4")
            if os.path.basename(v).startswith(base[:24])
        ]
        if not videos:
            continue
        quadro, _ = ler_quadro(videos[0], reg["frac"])
        cand = escolher(quadro)
        if cand is None or not (14 <= cand.grade.passo <= 45):
            continue
        passo = cand.grade.passo
        y0, _y1 = roi_das_cordas(cand)
        cinza = quadro if quadro.ndim == 2 else cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
        for k, marca in enumerate(ms):
            # A MARCA ESTA EM COORDENADA DA FAIXA (y ~ 0..190), NAO DO QUADRO. Recortar no y cru foi o
            # erro que encheu a primeira folha de braço de violão — o mesmo erro de espaço que já me
            # custou uma rodada inteira. Aqui: y_quadro = y_faixa + y0 (o topo da faixa no quadro).
            x, y = int(marca["x"]), int(marca["y"]) + y0
            hx, hy = int(args.jx * passo), int(args.jy * passo)
            rec = cinza[max(0, y - hy) : y + hy, max(0, x - hx) : x + hx]
            if rec.shape[0] < 16 or rec.shape[1] < 16:
                continue
            nome = f"{imagem.split('_')[0]}_{k:03d}.png"
            cv2.imwrite(f"{args.saida}/{nome}", rec)
            escala = args.altura / rec.shape[0]
            im = cv2.resize(rec, (max(24, int(rec.shape[1] * escala)), args.altura))
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
            et = np.full((16, im.shape[1], 3), 255, np.uint8)
            cv2.putText(
                et,
                nome[:-4],
                (2, 12),
                cv2.FONT_HERSHEY_PLAIN,
                0.9,
                (0, 0, 200),
                1,
            )
            celulas.append(np.vstack([et, im]))

    total = 0
    for s in range(0, len(celulas), 24):
        grupo = celulas[s : s + 24]
        linhas = []
        for i in range(0, len(grupo), 6):
            linha = grupo[i : i + 6]
            largura = max(c.shape[1] for c in linha)
            linha = [
                cv2.copyMakeBorder(
                    c,
                    0,
                    6,
                    0,
                    largura - c.shape[1],
                    cv2.BORDER_CONSTANT,
                    value=(255, 255, 255),
                )
                for c in linha
            ]
            linhas.append(np.hstack(linha))
        largura = max(linha.shape[1] for linha in linhas)
        linhas = [
            cv2.copyMakeBorder(
                ln,
                0,
                6,
                0,
                largura - ln.shape[1],
                cv2.BORDER_CONSTANT,
                value=(180, 180, 180),
            )
            for ln in linhas
        ]
        cv2.imwrite(f"{args.saida}/folha_{s // 24}.png", np.vstack(linhas))
        total += 1
    print(
        f"recortes: {len(celulas)} | folhas: {total} | janela {args.jx}x{args.jy} passos | saida {args.saida}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
