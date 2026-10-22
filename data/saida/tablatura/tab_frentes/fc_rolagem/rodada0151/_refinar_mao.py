"""Referência à mão (rodada 0151): x sub-pixel da barra escolhida pelo número impresso.

Lê ESCOLHAS (JSON, uma lista por janela de saltos.json). Para cada salto escolhido, pega o
quadro de antes e o de depois do salto (mesma grade do módulo), e mede o centro de massa
da escuridão numa janela de +-4 px em volta do x escolhido, nas linhas da pauta. O peso é
255 - cinza (pixels mascarados pesam zero). Não usa a regra de 60 % das colunas.

Uso: python _refinar_mao.py ESCOLHAS.json SAIDA.json
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from tab import leitor
from tab import rolagem_saltos as rs

MEIA = 4


def centroide(bgr: np.ndarray, x: int) -> float | None:
    """Centro de massa da escuridão em volta de ``x``, nas linhas da pauta."""
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mask = rs.mascara(bgr)
    linhas = np.flatnonzero((cinza < rs.ESCURO).mean(axis=1) >= rs.FRACAO_PAUTA)
    r0, r1 = linhas[0], linhas[-1] + 1
    sub = cinza[r0:r1, x - MEIA : x + MEIA + 1].astype(np.float32)
    msk = mask[r0:r1, x - MEIA : x + MEIA + 1]
    peso = np.where(msk, 0.0, np.clip(255.0 - sub, 0.0, None)).mean(axis=0)
    if peso.sum() <= 0:
        return None
    xs = np.arange(x - MEIA, x + MEIA + 1, dtype=np.float32)
    return float((xs * peso).sum() / peso.sum())


def main() -> int:
    """Refina as escolhas e grava a tabela com erros contra os caminhos a e b."""
    escolhas = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    saida = Path(sys.argv[2])
    linhas = []
    for janela in escolhas:
        rel = json.loads(Path(janela["saltos_json"]).read_text(encoding="utf-8"))
        quadros = list(
            leitor.quadros(
                rel["video"],
                rel["t0"],
                rel["t0"] + rel["dur"],
                rel["qps"],
                recorte_y=tuple(rel["recorte"]),
            )
        )
        tempos = np.array([t for t, _ in quadros])
        for e in janela["escolhas"]:
            s = rel["saltos"][e["salto"]]
            ia = int(np.argmin(np.abs(tempos - s["t_antes"])))
            ib = int(np.argmin(np.abs(tempos - s["t_depois"])))
            xa = centroide(quadros[ia][1], e["x_antes"])
            xb = centroide(quadros[ib][1], e["x_depois"])
            mao = None if xa is None or xb is None else xb - xa
            linhas.append(
                {
                    "janela": f"t0={rel['t0']}",
                    "salto": e["salto"],
                    "t_antes": s["t_antes"],
                    "t_depois": s["t_depois"],
                    "compasso": e["numero"],
                    "x_antes_det": e["x_antes"],
                    "x_depois_det": e["x_depois"],
                    "x_antes_sub": xa,
                    "x_depois_sub": xb,
                    "dx_mao": mao,
                    "dx_a": s["dx_total"],
                    "dx_b": s["dx_b_total"],
                    "erro_a": None if mao is None else abs(s["dx_total"] - mao),
                    "erro_b": None
                    if (mao is None or s["dx_b_total"] is None)
                    else abs(s["dx_b_total"] - mao),
                }
            )
            print(
                f"{s['t_antes']:8.2f} comp {e['numero']:>3}  mao={mao}  "
                f"a={s['dx_total']:9.2f}  b={s['dx_b_total']}"
            )
    saida.write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
