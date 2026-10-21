"""Protótipo: 6ª linha pela cobertura nos trechos da largura (2º pior de N trechos)."""

import numpy as np

from tab.caminhos import acervo
from tab.leitor import quadro_em
from tab.partitura_recortes import FonteQuadro, _cinza, processar_quadro
from tab.partitura_video import MARGEM_ENTRELINHAS, TOLERANCIA_SEXTA_LINHA, _forca_de_linha
from tab.video import _slug

import razoes_tab as R  # noqa: E402

NS = (6, 10)


def por_trechos(cinza, y, e, x0, x1, n):
    bordas = np.linspace(x0, x1, n + 1).round().astype(int)
    return sorted(_forca_de_linha(cinza, y, e, a, b) for a, b in zip(bordas[:-1], bordas[1:]))


def razoes(cinza, ys, e, x0, x1):
    out = []
    for n in NS:
        ref = float(np.median([por_trechos(cinza, y, e, x0, x1, n)[1] for y in ys]))
        def lado(c):
            return max(por_trechos(cinza, c + d, e, x0, x1, n)[1]
                       for d in range(-TOLERANCIA_SEXTA_LINHA, TOLERANCIA_SEXTA_LINHA + 1))
        ab, ac = lado(ys[4] + e), lado(ys[0] - e)
        out.append((n, ab / ref if ref else 0, ac / ref if ref else 0, ref))
    return out


def video(rotulo, vid, pasta):
    caminho = str(acervo() / vid)
    canal = vid.split("/")[0]
    for numero, (t, _) in sorted(R._paginas(pasta).items()):
        q = quadro_em(caminho, t)
        if q is None:
            continue
        fonte = FonteQuadro(origem="video", canal=canal, video=vid, t=t)
        ents, _, _ = processar_quadro(fonte, q, "video", primeiro_numero=1,
                                      margem_cima=MARGEM_ENTRELINHAS, margem_baixo=MARGEM_ENTRELINHAS)
        cinza = _cinza(q)
        for k, en in enumerate([x for x in ents if not x["sem_pauta"]]):
            x0, x1 = en["caixa_recorte"][0], en["caixa_recorte"][2]
            txt = " ".join(f"N{n}:ab={a:.2f},ac={b:.2f},m={m:.2f}" for n, a, b, m in razoes(cinza, en["ys"], en["entrelinha"], x0, x1))
            print(f"{rotulo} P{numero:02d} pauta {k} y0={en['ys'][0]:.0f} e={en['entrelinha']} {txt}", flush=True)


def main():
    for linha in (R.DIAG / "validacao_videos.txt").read_text().splitlines():
        stem, vid = linha.split("\t")
        video(f"VAL {stem[:14]}", vid, R.PAGINAS_VALIDACAO / stem / "recortes")
    for vid in (R.DIAG / "piloto_videos.txt").read_text().splitlines():
        pasta = R.SEM_PRODUTO / _slug(vid) / "recortes"
        if (pasta / "indice.json").exists():
            video(f"PIL {_slug(vid)[:14]}", vid, pasta)


if __name__ == "__main__":
    main()
