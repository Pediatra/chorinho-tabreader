"""Razões da 6ª linha (tablatura) de todas as pautas das páginas do piloto e da validação.

Para cada página (``indice.json`` de ``paginar``), relê o quadro no instante ``t`` e roda
``processar_quadro`` com as mesmas margens de ``paginar``, de modo que vê todas as pautas
achadas, inclusive as que ``paginar`` descartou como tablatura. Para cada pauta, grava a
razão abaixo e acima (``razoes_de_tablatura``), a mediana das 5 linhas e a decisão de
``e_tablatura``.

A saída vai para a tela; o arquivo ``diag/razoes_tab.txt`` é esse texto, uma linha por
pauta, com um resumo no fim (distribuição da maior razão das descartadas e das mantidas,
separadas, para a validação e para o piloto).

    python data/saida/partitura/diag/razoes_tab.py > data/saida/partitura/diag/razoes_tab.txt
"""

import json
from pathlib import Path

import numpy as np

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_recortes import FonteQuadro, _cinza, processar_quadro
from tab.partitura_video import (
    MARGEM_ENTRELINHAS,
    e_tablatura,
    razoes_de_tablatura,
)
from tab.video import _slug

DIAG = RAIZ / "data" / "saida" / "partitura" / "diag"
SEM_PRODUTO = RAIZ / "data" / "saida" / "partitura" / "sem_produto"
PAGINAS_VALIDACAO = DIAG / "paginar_validacao"


def _paginas(pasta: Path) -> dict[int, tuple[float, list[dict]]]:
    """Páginas de um índice de ``paginar``: ``{pagina: (t, exibicoes)}``.

    Args:
        pasta: pasta ``recortes/`` com ``indice.json``.

    Returns:
        Um item por página, com o instante e as exibições.
    """
    indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
    paginas: dict[int, tuple[float, list[dict]]] = {}
    for entrada in indice:
        paginas.setdefault(entrada["pagina"], (entrada["t"], entrada["exibicoes"]))
    return paginas


def _linhas_de_um_video(rotulo: str, video: str, pasta: Path) -> list[tuple[bool, float, float, float]]:
    """Imprime e devolve as razões de todas as pautas de um vídeo.

    Args:
        rotulo: nome curto do vídeo para a saída.
        video: caminho do vídeo, relativo ao acervo.
        pasta: pasta ``recortes/`` de ``paginar`` do vídeo.

    Returns:
        ``(descartada, razao_maior, razao_abaixo, razao_acima)`` de cada pauta.
    """
    registros: list[tuple[bool, float, float, float]] = []
    caminho = str(acervo() / video)
    canal = Path(video).parts[0]
    for numero, (t, _) in sorted(_paginas(pasta).items()):
        quadro = quadro_em(caminho, t)
        if quadro is None:
            print(f"{rotulo} P{numero:02d} t={t:.2f}: sem quadro")
            continue
        fonte = FonteQuadro(origem="video", canal=canal, video=video, t=t)
        entradas, _, _ = processar_quadro(
            fonte,
            quadro,
            "video",
            primeiro_numero=1,
            margem_cima=MARGEM_ENTRELINHAS,
            margem_baixo=MARGEM_ENTRELINHAS,
        )
        cinza = _cinza(quadro)
        for k, entrada in enumerate([e for e in entradas if not e["sem_pauta"]]):
            x0, x1 = entrada["caixa_recorte"][0], entrada["caixa_recorte"][2]
            abaixo, acima, mediana = razoes_de_tablatura(
                cinza, entrada["ys"], entrada["entrelinha"], x0, x1
            )
            descartada = e_tablatura(
                cinza, entrada["ys"], entrada["entrelinha"], x0, x1
            )
            registros.append((descartada, abaixo, acima, mediana))
            print(
                f"{rotulo} P{numero:02d} pauta {k} t={t:.2f}"
                f" y0={entrada['ys'][0]} e={entrada['entrelinha']}"
                f" abaixo={abaixo:.3f} acima={acima:.3f} mediana={mediana:.3f}"
                f" {'TAB (descartada)' if descartada else 'mantida'}"
            )
    return registros


def _resumo(titulo: str, registros: list[tuple[bool, float, float, float]]) -> None:
    """Imprime a distribuição da maior razão das pautas descartadas e das mantidas.

    Args:
        titulo: rótulo do grupo.
        registros: ``(descartada, abaixo, acima, mediana)`` de cada pauta.
    """
    for descartada, rotulo in ((True, "descartadas"), (False, "mantidas")):
        maiores = [max(a, b) for d, a, b, _ in registros if d is descartada]
        if not maiores:
            print(f"{titulo} {rotulo}: 0")
            continue
        q = np.quantile(maiores, [0, 0.5, 1])
        print(
            f"{titulo} {rotulo}: {len(maiores)} pautas, maior razao min {q[0]:.3f},"
            f" mediana {q[1]:.3f}, max {q[2]:.3f}"
        )


def main() -> None:
    """Grava ``razoes_tab.txt`` com a validação (produtos) e o piloto."""
    validacao = (DIAG / "validacao_videos.txt").read_text(encoding="utf-8").splitlines()
    piloto = (DIAG / "piloto_videos.txt").read_text(encoding="utf-8").splitlines()
    registros_val: list[tuple[bool, float, float, float]] = []
    registros_pil: list[tuple[bool, float, float, float]] = []
    for linha in validacao:
        stem, video = linha.split("\t")
        registros_val += _linhas_de_um_video(
            f"VAL {stem[:14]}", video, PAGINAS_VALIDACAO / stem / "recortes"
        )
    for video in piloto:
        pasta = SEM_PRODUTO / _slug(video) / "recortes"
        if not (pasta / "indice.json").exists():
            continue
        registros_pil += _linhas_de_um_video(f"PIL {_slug(video)[:14]}", video, pasta)
    _resumo("VALIDACAO", registros_val)
    _resumo("PILOTO", registros_pil)


if __name__ == "__main__":
    main()
