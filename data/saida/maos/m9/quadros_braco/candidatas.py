"""Candidatas a quadro do gabarito do braço nos vídeos da confirmação (M9)."""

import json
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import SAIDA, acervo
from tab.maos_corda_sem_direita import quadro_bgr

PASTA = SAIDA / "maos" / "m9" / "quadros_braco"
PRODUTOS = {f"sky_{i}": SAIDA / "maos" / "m3d" / f"sky_{i}.json" for i in (1, 2, 3, 5, 6)}


def main() -> None:
    """6 candidatas por vídeo, em instantes de notas presas espalhados no tempo."""
    lista = []
    linhas = []
    for nome, caminho in PRODUTOS.items():
        prod = json.loads(Path(caminho).read_text())
        arquivo = prod["video"]["arquivo"]
        tempos = sorted(
            {round(n["t_ini"], 3) for n in prod["notas"]
             if n.get("t_ini") is not None and str(n.get("casa")) not in ("0", "None")}
        )
        escolhidos = [tempos[int(k * (len(tempos) - 1) / 5)] for k in range(6)]
        minis = []
        for j, t in enumerate(escolhidos):
            q = quadro_bgr(acervo() / arquivo, t)
            mini = cv2.resize(q, (480, 270))
            cv2.putText(mini, f"{nome} #{j} t={t:.3f}", (6, 22), 0, 0.6, (0, 0, 255), 2)
            minis.append(mini)
            lista.append({"nome": nome, "j": j, "arquivo": arquivo, "t": t})
        linhas.append(np.hstack(minis))
    cv2.imwrite(str(PASTA / "candidatas.jpg"), np.vstack(linhas))
    (PASTA / "candidatas.json").write_text(json.dumps(lista, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
