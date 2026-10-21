"""Folha de quadros candidatos (M11): 10 instantes por vídeo, entre 8 % e 92 % da duração.

Lê os vídeos escolhidos do índice M3B, pega 10 quadros igualmente espaçados em cada
um e monta uma folha JPEG (uma linha por vídeo) para o revisor escolher os quadros
que o dono vai rotular. Também grava o JSON com a lista de quadros.
"""

import json
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import SAIDA, acervo
from tab.leitor import info
from tab.maos_corda_sem_direita import quadro_bgr

PASTA = SAIDA / "maos" / "m11" / "quadros_tempo"
INDICE = SAIDA / "maos" / "m3b" / "indice.json"
VIDEOS = ("q01", "q03", "q04", "q05", "q06", "q08", "q13")
N_QUADROS = 10
FRAC_INI = 0.08
FRAC_FIM = 0.92
LARGURA, ALTURA = 384, 216


def instantes(duracao: float) -> list[float]:
    """Instantes igualmente espaçados entre 8 % e 92 % da duração.

    Args:
        duracao: duração do vídeo em segundos.

    Returns:
        Lista de ``N_QUADROS`` instantes em segundos, arredondados a 3 casas.
    """
    passo = (FRAC_FIM - FRAC_INI) / (N_QUADROS - 1)
    return [round(duracao * (FRAC_INI + k * passo), 3) for k in range(N_QUADROS)]


def ler_arquivos() -> dict[str, str]:
    """Mapa id -> caminho relativo ao acervo, lido do índice M3B.

    Returns:
        Dicionário com os 7 ids escolhidos apontando para o campo ``arquivo``.
    """
    dados = json.loads(INDICE.read_text())
    mapa = {q["id"]: q["arquivo"] for q in dados["quadros"]}
    return {i: mapa[i] for i in VIDEOS}


def main() -> None:
    """Gera a folha JPEG e o JSON com os quadros candidatos."""
    PASTA.mkdir(parents=True, exist_ok=True)
    arquivos = ler_arquivos()
    lista = []
    linhas = []
    for vid, arquivo in arquivos.items():
        caminho = acervo() / arquivo
        duracao = float(info(str(caminho))["duracao_s"])
        print(f"{vid} duracao={duracao:.3f}s", flush=True)
        minis = []
        for j, t in enumerate(instantes(duracao)):
            try:
                q = quadro_bgr(caminho, t)
                mini = cv2.resize(q, (LARGURA, ALTURA))
            except Exception as erro:  # noqa: BLE001 - registra e segue para os outros
                print(f"ERRO {vid} #{j} t={t:.3f}: {erro!r}", flush=True)
                mini = np.zeros((ALTURA, LARGURA, 3), dtype=np.uint8)
            cv2.putText(
                mini, f"{vid} #{j} t={t:.3f}", (6, 22), 0, 0.5, (0, 0, 255), 2
            )
            minis.append(mini)
            lista.append(
                {"id": vid, "j": j, "arquivo": arquivo, "t": t, "duracao": duracao}
            )
        linhas.append(np.hstack(minis))
    cv2.imwrite(str(PASTA / "candidatas.jpg"), np.vstack(linhas))
    (PASTA / "candidatas.json").write_text(
        json.dumps(lista, indent=1, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
