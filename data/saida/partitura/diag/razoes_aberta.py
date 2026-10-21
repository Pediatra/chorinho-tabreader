"""Protótipo: 6ª linha medida só com traço horizontal longo (abertura de L entrelinhas)."""

import cv2
import numpy as np

from tab.caminhos import acervo
from tab.leitor import quadro_em
from tab.partitura_recortes import FonteQuadro, _cinza, _tinta_escura, processar_quadro
from tab.partitura_video import MARGEM_ENTRELINHAS
from tab.video import _slug

import razoes_tab as R  # noqa: E402

COMPRIMENTOS = (6, 10, 15)


def cobertura(aberta, y, x0, x1):
    yc = round(y)
    faixa = aberta[max(yc - 2, 0): yc + 3, x0:x1]
    return float(faixa.any(axis=0).mean()) if faixa.size else 0.0


def razoes(quadro, ys, e, x0, x1):
    v = cv2.cvtColor(quadro, cv2.COLOR_BGR2HSV)[:, :, 2]
    lado = 2 * round(e) + 1
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (lado, lado))
    op = cv2.MORPH_BLACKHAT if _tinta_escura(_cinza(quadro)) else cv2.MORPH_TOPHAT
    tinta = (cv2.morphologyEx(v, op, k) > 60).astype(np.uint8)
    saida = []
    for L in COMPRIMENTOS:
        h = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, round(L * e)), 1))
        aberta = cv2.morphologyEx(tinta, cv2.MORPH_OPEN, h) > 0
        med = float(np.median([cobertura(aberta, y, x0, x1) for y in ys]))
        ab = max(cobertura(aberta, ys[4] + e + d, x0, x1) for d in range(-2, 3))
        ac = max(cobertura(aberta, ys[0] - e + d, x0, x1) for d in range(-2, 3))
        saida.append((L, ab / med if med else 0, ac / med if med else 0, med))
    return saida


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
        for k, en in enumerate([x for x in ents if not x["sem_pauta"]]):
            x0, x1 = en["caixa_recorte"][0], en["caixa_recorte"][2]
            txt = " ".join(f"L{L}:ab={a:.2f},ac={b:.2f},m={m:.2f}" for L, a, b, m in razoes(q, en["ys"], en["entrelinha"], x0, x1))
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
