"""Varre TINTA_V_MAX na assinatura e confere as páginas contra o produto.

Para cada vídeo de ``validacao_videos.txt`` (com produto), amostra o quadro a QPS_PAGINAS
uma vez, calcula a assinatura para cada valor de ``TINTA_V_MAX`` pedido e agrupa em
páginas. Imprime, por valor, quantas páginas saem, quantas telas do produto caem numa
página (pelo instante do meio da primeira exibição, como ``conferir_paginas``) e quais
páginas não cobrem tela nenhuma.

    python data/saida/partitura/diag/sweep_tinta.py 110:0.25 140:0.25 110:0.5

Cada argumento é ``V:FRACAO`` (``TINTA_V_MAX`` e ``FRACAO_TINTA``).
"""

import json
import sys
from pathlib import Path

from tab import partitura_video as pv
from tab.caminhos import RAIZ, acervo
from tab.leitor import info, quadros
from tab.partitura_pauta import achar_pautas

DIAG = RAIZ / "data" / "saida" / "partitura" / "diag"
PRODUTOS = RAIZ / "data" / "saida" / "fase8" / "rede"


def _meio_das_telas(stem: str) -> list[tuple[int, float]]:
    """Instante do meio da primeira exibição válida de cada tela do produto.

    Args:
        stem: nome do produto (sem extensão).

    Returns:
        ``(numero_da_tela, meio)`` para cada tela com exibição válida.
    """
    produto = json.loads((PRODUTOS / f"{stem}.json").read_text(encoding="utf-8"))
    saida = []
    for tela in produto["telas"]:
        exibicao = pv.instante_da_tela(tela)
        if exibicao is not None:
            saida.append((int(tela["id"]), exibicao))
    return saida


def main(valores: list[tuple[int, float]]) -> None:
    """Roda a varredura para cada vídeo e cada par ``(TINTA_V_MAX, FRACAO_TINTA)``.

    Args:
        valores: pares ``(TINTA_V_MAX, FRACAO_TINTA)`` a testar.
    """
    lista = (DIAG / "validacao_videos.txt").read_text(encoding="utf-8").splitlines()
    for linha in lista:
        stem, arquivo = linha.split("\t")
        caminho = str(acervo() / arquivo)
        duracao = float(info(caminho)["duracao_s"])
        amostras = {v: [] for v in valores}
        for t, quadro in quadros(caminho, 0.0, duracao, pv.QPS_PAGINAS):
            pautas = achar_pautas(quadro)
            for v, f in valores:
                pv.TINTA_V_MAX = v
                pv.FRACAO_TINTA = f
                amostras[(v, f)].append((t, pv.assinatura(quadro, pautas)))
        pv.TINTA_V_MAX = 110
        pv.FRACAO_TINTA = 0.25
        telas = _meio_das_telas(stem)
        print(f"== {stem}: telas {len(telas)}")
        for v, f in valores:
            paginas = pv.agrupar_paginas(amostras[(v, f)])
            sem_tela = [
                numero
                for numero, pagina in enumerate(paginas, start=1)
                if not any(
                    e["t0"] <= meio <= e["t1"]
                    for _, meio in telas
                    for e in pagina["exibicoes"]
                )
            ]
            cobertas = sum(
                1
                for _, meio in telas
                if any(
                    e["t0"] <= meio <= e["t1"]
                    for pagina in paginas
                    for e in pagina["exibicoes"]
                )
            )
            print(
                f"  V<{v} F>={f}: paginas {len(paginas)}, telas cobertas {cobertas}/{len(telas)},"
                f" paginas sem tela {sem_tela}"
            )


if __name__ == "__main__":
    main([(int(a.split(":")[0]), float(a.split(":")[1])) for a in sys.argv[1:]])
