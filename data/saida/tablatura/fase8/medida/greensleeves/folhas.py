"""Folhas dos dois piores erros de tempo: quadro no instante do ouro.

Vermelho: x da coluna acesa segundo o ouro (coluna_x_quadro).
Verde: centro de cada token previsto (notas e não-notas) da tela, com a casa lida.
"""

import json
import sys

sys.path.insert(0, "/app")

from PIL import Image, ImageDraw  # noqa: E402

from tab import leitor  # noqa: E402
from tab.conferir import _fonte, _quadro_rgb  # noqa: E402

VIDEO = "/acervo/pablo romé/greensleeves 💚 guía de estudio 👌 partitura + tab + pdf.mp4"
OURO = "/app/data/gold/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf.json"
PRED = "/app/data/saida/fase8/medida/greensleeves/run1.json"
SAIDA = "/app/data/saida/fase8/medida/greensleeves"
LARG = 1500

ouro = json.load(open(OURO, encoding="utf-8"))
pred = json.load(open(PRED, encoding="utf-8"))
telas_pred = {t["id"]: t for t in pred["telas"]}

ALVOS = [62.0, 126.0]
f_txt = _fonte(24)
f_peq = _fonte(18)
blocos = []
for t_alvo in ALVOS:
    inst = next(i for i in ouro["instantes"] if float(i["t"]) == t_alvo)
    tid = inst["tela"]
    x_ouro = inst["coluna_x_quadro"]
    tela = telas_pred[tid]
    x0, y0, x1, y1 = tela["painel"]
    passo = tela["passo"]
    toks = [n for n in pred["notas"] + pred["nao_notas"] if n["tela"] == tid]

    quadro = _quadro_rgb(leitor.quadro_em(VIDEO, max(0.0, t_alvo - 0.02)))
    y0m, y1m = max(0, y0 - 6), min(quadro.height, y1 + 6)
    recorte = quadro.crop((x0, y0m, x1, y1m))
    esc = LARG / recorte.width
    recorte = recorte.resize((LARG, round(recorte.height * esc)), Image.LANCZOS)
    d = ImageDraw.Draw(recorte)
    H = recorte.height
    # x do ouro: linha vermelha
    xo = (x_ouro - x0) * esc
    d.line([(xo, 0), (xo, H)], fill=(230, 0, 0), width=3)
    # centros dos tokens previstos: tick verde com a casa lida
    for n in toks:
        xc = (n["x_centro_quadro"] - x0) * esc
        d.line([(xc, H - 14), (xc, H)], fill=(0, 160, 60), width=3)
        if n.get("t_ini") is not None:
            pass
        casa = n.get("casa", n.get("casa_recuperada"))
        d.text((xc - 6, H - 40), f"{n['corda']}:{casa}", font=f_peq, fill=(0, 120, 40))

    cab = (
        f"t={t_alvo} s, tela {tid}, passo {passo} px | vermelho = x do ouro {x_ouro} | "
        f"verde = centros previstos (corda:casa)"
    )
    # colunas do ouro nesta tela, com a nota mais perto do x do ouro
    gold_tela = ouro["telas"][tid - 1]["notas"]
    mais_perto = sorted(gold_tela, key=lambda n: abs(n.get("x_centro_quadro", n.get("x_quadro")) - x_ouro))[:4]
    rod = "tab do ouro mais perto do x vermelho: " + ", ".join(
        f"c{n['corda']}={n['casa']}@{round(n.get('x_centro_quadro', n.get('x_quadro')),1)}" for n in mais_perto
    )
    bl = Image.new("RGB", (LARG, H + 100), (255, 255, 255))
    db = ImageDraw.Draw(bl)
    db.text((0, 4), cab, font=f_peq, fill=(0, 0, 0))
    bl.paste(recorte, (0, 36))
    db.text((0, H + 44), rod, font=f_peq, fill=(20, 60, 140))
    blocos.append(bl)

altura = sum(b.height for b in blocos) + 30 * (len(blocos) + 1)
folha = Image.new("RGB", (LARG + 40, altura), (255, 255, 255))
y = 20
for b in blocos:
    folha.paste(b, (20, y))
    y += b.height + 20
folha.save(f"{SAIDA}/folha_piores_tempo.png")
print("ok", f"{SAIDA}/folha_piores_tempo.png", folha.size)
