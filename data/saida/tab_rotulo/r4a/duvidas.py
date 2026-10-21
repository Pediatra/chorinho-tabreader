"""Recortes largos das notas em dúvida (rodada 0203), com a nota circulada."""

import json

import cv2

from tab import ataque_r4 as A
from tab import caminhos, leitor, painel

r2 = caminhos.TAB_ROTULO / "r2"
SAIDA = caminhos.TAB_ROTULO / "r4a" / "duvidas"
CASOS = [
    ("1_parenteses", "t82", 36, ["t36-n29", "t36-n37"]),
    ("2_cifra_club", "t82", 2, ["t2-n1", "t2-n4"]),
    ("3_from_this_place_t1", "pat_metheny", 1, ["t1-n63"]),
    ("3_from_this_place_t4", "pat_metheny", 4, ["t4-n70"]),
    ("3_from_this_place_t5", "pat_metheny", 5, ["t5-n3"]),
]
ferr = caminhos.SAIDA / "t82" / "ferramenta"
indice = {int(r["id"]): r for r in json.loads((ferr / "indice.json").read_text())}
slug = "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover"
ftp = json.loads((r2 / "conferir" / f"{slug}.json").read_text())
qftp = {int(t["id"]): float(t["quadro_ref_s"]) for t in ftp["telas"]}
for nome, fonte, tela, chaves in CASOS:
    if fonte == "t82":
        video, t = caminhos.acervo() / indice[tela]["video"], float(indice[tela]["t"])
        gab = A.gabarito_por_tela(r2 / "conferir_novos" / "ataque_t82.json")[tela]
    else:
        video, t = caminhos.acervo() / ftp["video"], qftp[tela]
        gab = A.gabarito_por_tela(r2 / "conferir" / "ataque_pat_metheny.json")[tela]
    quadro = leitor.quadro_em(str(video), t)
    c = painel.escolher_ou_mascara(quadro)
    img = quadro.copy()
    y0, y1 = int(c.grade.linhas_y[0]), int(c.grade.linhas_y[-1])
    oy = int(getattr(c, "y0", 0))
    xs = []
    for n in gab:
        if n["nota"] in chaves:
            x = int(n["x_centro_quadro"])
            y = oy + int(c.grade.linhas_y[n["corda"] - 1])
            cv2.circle(img, (x, y), int(0.75 * c.passo), (0, 0, 255), 2)
            xs.append(x)
    p = c.passo
    a = max(0, int(min(xs) - 12 * p))
    b = min(img.shape[1], int(max(xs) + 12 * p))
    top = max(0, oy + y0 - int(3 * p))
    bot = min(img.shape[0], oy + y1 + int(3 * p))
    sub = img[top:bot, a:b]
    sub = cv2.resize(sub, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(SAIDA / f"{nome}.png"), sub)
    print(nome, sub.shape, [(n["nota"], n["casa"], n["corda"]) for n in gab if n["nota"] in chaves])
