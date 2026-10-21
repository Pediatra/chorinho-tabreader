"""Protótipo: 6ª linha contada só em colunas onde o traço escuro é fino (não viga)."""

import cv2
import numpy as np

from tab.caminhos import acervo
from tab.leitor import quadro_em
from tab.partitura_recortes import FonteQuadro, _cinza, _tinta_escura, processar_quadro
from tab.partitura_video import MARGEM_ENTRELINHAS
from tab.video import _slug

import razoes_tab as R  # noqa: E402

FRACOES = (0.25, 0.35)


def mascara(quadro, e):
    v = cv2.cvtColor(quadro, cv2.COLOR_BGR2HSV)[:, :, 2]
    lado = 2 * round(e) + 1
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (lado, lado))
    op = cv2.MORPH_BLACKHAT if _tinta_escura(_cinza(quadro)) else cv2.MORPH_TOPHAT
    return cv2.morphologyEx(v, op, k) > 40


def fina(m, y, x0, x1, teto):
    """Fração de colunas com traço escuro em y±2 cuja corrida vertical tem altura <= teto."""
    yc = round(y)
    n = 0
    for x in range(x0, x1):
        col = m[:, x]
        achou = False
        for yy in range(max(yc - 2, 0), min(yc + 3, m.shape[0])):
            if col[yy]:
                a = yy
                while a > 0 and col[a - 1]:
                    a -= 1
                b = yy
                while b < m.shape[0] - 1 and col[b + 1]:
                    b += 1
                if b - a + 1 <= teto:
                    achou = True
                    break
        n += achou
    return n / max(1, x1 - x0)


def razoes(quadro, ys, e, x0, x1):
    m = mascara(quadro, e)
    out = []
    for f in FRACOES:
        teto = max(3, round(f * e))
        med = float(np.median([fina(m, y, x0, x1, teto) for y in ys]))
        ab = max(fina(m, ys[4] + e + d, x0, x1, teto) for d in (-2, 0, 2))
        ac = max(fina(m, ys[0] - e + d, x0, x1, teto) for d in (-2, 0, 2))
        out.append((f, ab / med if med else 0, ac / med if med else 0, med))
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
        for k, en in enumerate([x for x in ents if not x["sem_pauta"]]):
            x0, x1 = en["caixa_recorte"][0], en["caixa_recorte"][2]
            txt = " ".join(f"F{f}:ab={a:.2f},ac={b:.2f},m={m:.2f}" for f, a, b, m in razoes(q, en["ys"], en["entrelinha"], x0, x1))
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
