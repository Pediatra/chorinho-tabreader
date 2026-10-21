"""Variante de teste: linha fina (escura em y, clara em y±3) para a razão da 6ª linha.

Mede, para cada pauta das páginas do piloto e da validação, a razão abaixo/acima com a
regra de ``_forca_de_linha`` (a usada em ``e_tablatura``) e com a regra fina, para
comparar. Não altera ``tab/``; é só diagnóstico.

    python data/saida/partitura/diag/variante_fina.py
"""

import json

import numpy as np

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_recortes import CRISTA_DELTA_EXT, FonteQuadro, _cinza, processar_quadro
from tab.partitura_video import MARGEM_ENTRELINHAS, TOLERANCIA_SEXTA_LINHA, _forca_de_linha
from tab.video import _slug

DIAG = RAIZ / "data" / "saida" / "partitura" / "diag"
SEM_PRODUTO = RAIZ / "data" / "saida" / "partitura" / "sem_produto"


def _forca_fina(cinza: np.ndarray, y: float, e: float, x0: int, x1: int) -> float:
    """Como ``_forca_de_linha``, mas a coluna só conta se a linha é fina.

    Args:
        cinza: quadro em tons de cinza.
        y: linha candidata.
        e: entrelinha.
        x0: início horizontal.
        x1: fim horizontal (exclusivo).

    Returns:
        Fração de colunas com linha fina.
    """
    altura = cinza.shape[0]
    yc = round(y)
    meia = round(e / 2)
    if x1 <= x0 or yc - 3 < 0 or yc + 3 >= altura:
        return 0.0
    ya = min(max(yc - meia, 0), altura - 1)
    yb = min(max(yc + meia, 0), altura - 1)
    ref = (cinza[ya, x0:x1].astype(np.int32) + cinza[yb, x0:x1].astype(np.int32)) / 2
    centro = cinza[yc, x0:x1].astype(np.int32)
    acima = cinza[yc - 3, x0:x1].astype(np.int32)
    abaixo = cinza[yc + 3, x0:x1].astype(np.int32)
    presente = (centro <= ref - CRISTA_DELTA_EXT) & (acima >= ref - 10) & (abaixo >= ref - 10)
    return float(np.count_nonzero(presente)) / (x1 - x0)


def _razoes(cinza, ys, e, x0, x1, forca):
    """Razões abaixo e acima com a função de força dada.

    Args:
        cinza: quadro em tons de cinza.
        ys: as 5 linhas.
        e: entrelinha.
        x0: início horizontal.
        x1: fim horizontal.
        forca: função ``(cinza, y, e, x0, x1) -> float``.

    Returns:
        ``(abaixo, acima)``.
    """
    med = float(np.median([forca(cinza, y, e, x0, x1) for y in ys]))

    def r(c):
        f = max(forca(cinza, c + d, e, x0, x1) for d in range(-TOLERANCIA_SEXTA_LINHA, TOLERANCIA_SEXTA_LINHA + 1))
        return f / med if med > 0 else 0.0

    return r(ys[4] + e), r(ys[0] - e)


def main() -> None:
    """Imprime as razões das duas regras para as pautas de validação e do piloto."""
    grupos = []
    for linha in (DIAG / "validacao_videos.txt").read_text(encoding="utf-8").splitlines():
        stem, video = linha.split("\t")
        grupos.append((f"VAL {stem[:12]}", video, DIAG / "paginar_validacao" / stem / "recortes"))
    for video in (DIAG / "piloto_videos.txt").read_text(encoding="utf-8").splitlines():
        pasta = SEM_PRODUTO / _slug(video) / "recortes"
        if (pasta / "indice.json").exists():
            grupos.append((f"PIL {_slug(video)[:12]}", video, pasta))
    for rotulo, video, pasta in grupos:
        paginas = {}
        for e in json.loads((pasta / "indice.json").read_text(encoding="utf-8")):
            paginas.setdefault(e["pagina"], e["t"])
        caminho = str(acervo() / video)
        canal = video.split("/")[0]
        for numero, t in sorted(paginas.items()):
            quadro = quadro_em(caminho, t)
            if quadro is None:
                continue
            fonte = FonteQuadro(origem="video", canal=canal, video=video, t=t)
            entradas, _, _ = processar_quadro(
                fonte, quadro, "video", primeiro_numero=1,
                margem_cima=MARGEM_ENTRELINHAS, margem_baixo=MARGEM_ENTRELINHAS,
            )
            cinza = _cinza(quadro)
            for k, en in enumerate([x for x in entradas if not x["sem_pauta"]]):
                x0, x1 = en["caixa_recorte"][0], en["caixa_recorte"][2]
                a1 = _razoes(cinza, en["ys"], en["entrelinha"], x0, x1, _forca_de_linha_wrap)
                a2 = _razoes(cinza, en["ys"], en["entrelinha"], x0, x1, _forca_fina)
                print(
                    f"{rotulo} P{numero:02d} pauta {k} y0={en['ys'][0]} e={en['entrelinha']}"
                    f" atual abaixo={a1[0]:.3f} acima={a1[1]:.3f}"
                    f" fina abaixo={a2[0]:.3f} acima={a2[1]:.3f}"
                )


def _forca_de_linha_wrap(cinza, y, e, x0, x1):
    """Adaptador para ``_forca_de_linha`` com a mesma assinatura de ``_forca_fina``."""
    return _forca_de_linha(cinza, y, e, x0, x1)


if __name__ == "__main__":
    main()
