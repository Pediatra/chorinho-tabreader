"""Regerar o conjunto de símbolos numa JANELA nova (o conserto da captura).

Motivo: o detector recortava o símbolo em 2,4 x 1,6 passos — menos de duas cordas — e o dono viu o
símbolo cortado. Crescer a janela **não é parâmetro**: medido, crescer sem retreinar é neutro-para-pior
(0,197/0,216 -> 0,193/0,210), porque o modelo foi **treinado** na janela pequena. O conserto exige as
três coisas juntas: janela nova **+** retreinar **+** rótulo na janela nova.

Este módulo faz a parte que não depende do dono: relê `data/gold/simbolos_marcados.json` (que guarda
`x`, `y`, `frac`, `passo` de cada marca) e regera **positivos e negativos** na janela pedida, num
diretório novo — **sem tocar no gabarito original**.

Duas armadilhas estão tratadas de propósito, porque já custaram rodada:

1. **O espaço de coordenada dos negativos.** `cx`, `cy` não dizem se são do quadro ou da ROI; foi esse
   erro que fez a LOCA cair de 0,89–0,91 para 0,74–0,79 quando os negativos foram recortados do lugar
   errado. Aqui o espaço é **medido** antes (`--conferir-espaco`), comparando a tinta nos dois recortes.
2. **O `frac` de cada imagem.** Só os positivos guardam `frac`; os negativos herdam por imagem — e
   imagem sem `frac` conhecido é pulada em vez de adivinhada.

Uso:

    python -m tab.regerar_janela --jx 1.5 --jy 1.25 --saida data/gold/simbolos_marcados_j25
"""

import argparse
import glob
import json
import os
import sys

import cv2

from .caminhos import ARTEFATOS
from .inventario import ler_quadro
from .painel import escolher

GOLD = ARTEFATOS.parent / "data" / "gold" / "simbolos_marcados.json"


def _painel(canal: str, frac: float, cache: dict):
    """Devolve ``(quadro, painel)`` para (canal, frac), com cache — evita reabrir vídeo por recorte."""
    chave = (canal, round(float(frac), 3))
    if chave in cache:
        return cache[chave]
    par = (None, None)
    for video in sorted(glob.glob(f"/acervo/{canal}/*.mp4")):
        quadro, _ = ler_quadro(video, frac)
        if quadro is not None:
            painel = escolher(quadro)
            if painel is not None:
                par = (quadro, painel)
                break
    cache[chave] = par
    return par


def conferir_espaco(dados: dict, cache: dict, amostras: int = 40) -> str:
    """Mede se `cx, cy` dos negativos estão em coordenada da ROI ou do quadro.

    Args:
        dados: gabarito lido.
        cache: cache de painéis.
        amostras: quantos negativos medir.

    Returns:
        ``"ROI"`` ou ``"QUADRO"``, pelo lado que tiver mais tinta nos recortes.
    """
    roi = quadro = 0
    for caso in dados["negativos"][:amostras]:
        bruto, painel = _painel(caso["canal"], 0.5, cache)
        if bruto is None or painel is None or not (14 <= painel.grade.passo <= 45):
            continue
        passo = painel.grade.passo
        hx, hy = int(0.5 * passo), int(0.4 * passo)
        cinza_roi = painel.roi if painel.roi.ndim == 2 else cv2.cvtColor(painel.roi, cv2.COLOR_BGR2GRAY)
        cinza_quadro = bruto if bruto.ndim == 2 else cv2.cvtColor(bruto, cv2.COLOR_BGR2GRAY)
        for nome, base in (("ROI", cinza_roi), ("QUADRO", cinza_quadro)):
            y, x = int(caso["cy"]), int(caso["cx"])
            if not (0 <= y < base.shape[0] and 0 <= x < base.shape[1]):
                continue
            rec = base[max(0, y - hy):y + hy, max(0, x - hx):x + hx]
            if rec.size and (rec < (rec.mean() - 0.5 * rec.std())).mean() > 0.05:
                if nome == "ROI":
                    roi += 1
                else:
                    quadro += 1
    print(f"  tinta: na ROI {roi} | no quadro {quadro}")
    return "ROI" if roi >= quadro else "QUADRO"


def main() -> int:
    """Regera positivos e negativos na janela pedida e escreve o conjunto novo."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--jx", type=float, default=1.5)
    ap.add_argument("--jy", type=float, default=1.25)
    ap.add_argument("--saida", default=str(GOLD.parent / "simbolos_marcados_j25"))
    args = ap.parse_args()

    dados = json.loads(GOLD.read_text(encoding="utf-8"))
    cache: dict = {}
    espaco = conferir_espaco(dados, cache)
    print(f"espaço dos negativos (medido): {espaco}")
    if espaco != "ROI":
        print("espaço inesperado — abortando em vez de recortar do lugar errado", file=sys.stderr)
        return 2

    frac_por_imagem: dict[str, float] = {}
    for caso in dados["positivos"]:
        frac_por_imagem.setdefault(caso["imagem"], caso["frac"])

    os.makedirs(f"{args.saida}/positivos", exist_ok=True)
    os.makedirs(f"{args.saida}/negativos", exist_ok=True)

    novos_pos, novos_neg = [], []
    for i, caso in enumerate(dados["positivos"]):
        quadro, painel = _painel(caso["canal"], caso["frac"], cache)
        passo = float(caso.get("passo") or 0)
        if quadro is None or painel is None or not (14 <= passo <= 45):
            continue
        cinza = quadro if quadro.ndim == 2 else cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
        hx, hy = int(args.jx * passo), int(args.jy * passo)
        x, y = int(caso["x"]), int(caso["y"])
        rec = cinza[max(0, y - hy):y + hy, max(0, x - hx):x + hx]
        if rec.shape[0] < 14 or rec.shape[1] < 14:
            continue
        nome = f"p{i:04d}.png"
        cv2.imwrite(f"{args.saida}/positivos/{nome}", rec)
        novos_pos.append({**caso, "arquivo": nome})

    for i, caso in enumerate(dados["negativos"]):
        _bruto, painel = _painel(caso["canal"], frac_por_imagem.get(caso["imagem"], 0.5), cache)
        if painel is None or not (14 <= painel.grade.passo <= 45):
            continue
        passo = painel.grade.passo
        cinza = painel.roi if painel.roi.ndim == 2 else cv2.cvtColor(painel.roi, cv2.COLOR_BGR2GRAY)
        hx, hy = int(args.jx * passo), int(args.jy * passo)
        # DOIS FORMATOS de negativo, os dois em coordenada da ROI: os de token usam `cx, cy` e os de
        # janela vazia usam `x, y` (com `vazio: true`). Sem tratar os dois, o módulo quebra no meio.
        if "cx" in caso:
            x, y = int(caso["cx"]), int(caso["cy"])
        elif "x" in caso:
            x, y = int(caso["x"]), int(caso["y"])
        else:
            continue
        rec = cinza[max(0, y - hy):y + hy, max(0, x - hx):x + hx]
        if rec.shape[0] < 14 or rec.shape[1] < 14:
            continue
        nome = f"n{i:04d}.png"
        cv2.imwrite(f"{args.saida}/negativos/{nome}", rec)
        novos_neg.append({**caso, "arquivo": nome})

    (ARTEFATOS.parent / args.saida / "simbolos_marcados.json").write_text(
        json.dumps(
            {
                "origem": dados.get("origem"),
                "regra_do_dono": dados.get("regra_do_dono"),
                "janela": [args.jx, args.jy],
                "positivos": novos_pos,
                "negativos": novos_neg,
                "espaco_dos_negativos": f"{espaco} (conferido por medicao)",
                "nota": "regerado de x,y,frac,passo do original; o gabarito original NAO foi tocado",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"POSITIVOS {len(novos_pos)} | NEGATIVOS {len(novos_neg)} | janela {args.jx}x{args.jy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
