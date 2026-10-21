"""Candidatas a quadros extras do gabarito do braço (validação da frente B3)."""

import json

import cv2
import numpy as np

from tab.caminhos import MAOS_M8, acervo
from tab.maos_corda_sem_direita import quadro_bgr
from tab.maos_padroes_preparar import VIDEOS

NOMES = ["retrato", "noturno", "lacrimosa", "glimpse"]
ALVOS = {
    "retrato": [255.0, 655.0],
    "noturno": [400.0, 600.0],
    "lacrimosa": [190.0, 440.0],
    "glimpse": [270.0, 650.0],
}


def main() -> None:
    """Extrai 3 candidatas por alvo e monta a folha."""
    saida = MAOS_M8 / "quadros_extra"
    miniaturas = []
    lista = []
    for nome, entrada in zip(NOMES, VIDEOS, strict=True):
        cam = json.loads((MAOS_M8 / f"camera_{nome}.json").read_text())
        tempos = sorted(float(t) for t in cam)
        for alvo in ALVOS[nome]:
            for desvio in (-8.0, 0.0, 8.0):
                t = min(tempos, key=lambda x: abs(x - (alvo + desvio)))
                q = quadro_bgr(acervo() / entrada["arquivo"], t)
                s, dx, dy = cam[f"{t:.3f}"]
                mini = cv2.resize(q, (640, 360))
                rotulo = f"{nome} t={t:.3f} s={s:.2f} dy={dy:.0f}"
                cv2.putText(mini, rotulo, (8, 24), 0, 0.7, (0, 0, 255), 2)
                miniaturas.append(mini)
                lista.append({"nome": nome, "arquivo": entrada["arquivo"], "t": t})
    linhas = [np.hstack(miniaturas[i : i + 3]) for i in range(0, len(miniaturas), 3)]
    pares = [np.vstack(linhas[i : i + 4]) for i in range(0, len(linhas), 4)]
    for k, folha in enumerate(pares):
        cv2.imwrite(str(saida / f"candidatas_{k}.jpg"), folha)
    (saida / "candidatas.json").write_text(json.dumps(lista, indent=1))


if __name__ == "__main__":
    main()
