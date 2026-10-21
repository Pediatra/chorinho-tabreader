"""Diagnóstico: polaridade da tinta por quadro (mediana do quadro inteiro e da região).

Para cada amostra do vídeo, imprime a mediana do cinza no quadro inteiro e na região das
pautas, a polaridade que ``_tinta_escura`` dá em cada caso e o número de pautas. Serve
para ver se a polaridade vira de um quadro para o outro.

    python data/saida/partitura/diag/diag_polaridade.py --busca blackbird --t1 60
"""

import argparse

import numpy as np

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadros
from tab.partitura_pauta import achar_pautas
from tab.partitura_recortes import _cinza, _tinta_escura


DIAG = RAIZ / "data" / "saida" / "partitura" / "diag"


def main() -> None:
    """Imprime uma linha por amostra do intervalo pedido."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--busca", required=True, help="trecho do nome na piloto_videos.txt")
    parser.add_argument("--t0", type=float, default=0.0)
    parser.add_argument("--t1", type=float, required=True)
    args = parser.parse_args()
    lista = (DIAG / "piloto_videos.txt").read_text(encoding="utf-8").splitlines()
    video = next(linha for linha in lista if args.busca.lower() in linha.lower())
    caminho = str(acervo() / video)
    for t, quadro in quadros(caminho, args.t0, args.t1, 1.0):
        cinza = _cinza(quadro)
        pautas = achar_pautas(quadro)
        if pautas:
            primeira = min(pautas, key=lambda p: p.ys[0])
            ultima = max(pautas, key=lambda p: p.ys[4])
            e = primeira.entrelinha
            y0 = max(0, int(primeira.ys[0] - 4 * e))
            y1 = min(cinza.shape[0], int(ultima.ys[4] + 4 * e) + 1)
            regiao = cinza[y0:y1]
        else:
            regiao = cinza
        print(
            f"t={t:6.1f} mediana_quadro {float(np.median(cinza)):6.1f}"
            f" escura_quadro {_tinta_escura(cinza)!s:5}"
            f" mediana_regiao {float(np.median(regiao)):6.1f}"
            f" escura_regiao {_tinta_escura(regiao)!s:5} pautas {len(pautas)}"
        )


if __name__ == "__main__":
    main()
