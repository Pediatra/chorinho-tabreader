"""Compara, por instante, a regra antiga (mais próxima) e a nova (última passada)."""

import json
from pathlib import Path

from tab.avaliar_video import (
    _x_ouro,
    avaliar,
    casar_sem_instante,
    casar_telas,
    classificar_instante,
    coluna_atual,
    coluna_que_chega,
    coluna_do_ouro,
    ler_predicao,
    ocorrencias,
    tela_em_t,
)

FPS = 59.940060
ouro = json.loads(Path("data/gold/ouro_video/south_american_music_easy_guitar_tutorial_with_sheet_and_tab.json").read_text())
pred = ler_predicao(json.loads(Path("data/saida/fase8/medida/south_american_v2/run1.json").read_text()))
ids = [int(t["id"]) for t in ouro["telas"]]
mapa = casar_telas(ids, ouro["instantes"], pred.telas)
mapa, _ = casar_sem_instante(ouro["telas"], mapa, pred.telas)
ocorr = {t.id: ocorrencias(t) for t in pred.telas}
xs = {int(t["id"]): [_x_ouro(n) for n in t["notas"]] for t in ouro["telas"]}


def antiga(clique, xs_o, passo):
    if not xs_o or passo <= 0:
        return clique
    perto = min(xs_o, key=lambda x: abs(x - clique))
    return perto if abs(perto - clique) <= passo else clique


for ins in ouro["instantes"]:
    t = float(ins["t"])
    tela = tela_em_t(t, ins.get("tela"), mapa, pred.telas)
    if tela is None or ins.get("coluna_x_quadro") is None:
        continue
    atual = coluna_atual(t, tela, ocorr[tela.id])
    chega = coluna_que_chega(t, tela, ocorr[tela.id], FPS)
    c = float(ins["coluna_x_quadro"])
    xo = xs[int(ins["tela"])]
    a, n = antiga(c, xo, tela.passo), coluna_do_ouro(c, xo, tela.passo)
    ca = classificar_instante(t, a, atual, tela.passo, chega)
    cn = classificar_instante(t, n, atual, tela.passo, chega)
    if ca != cn:
        print(f"t={t} clique={c} passo={tela.passo:.1f} antiga={a} ({ca}) nova={n} ({cn}) "
              f"prevista={atual.x if atual else None} chega={chega.x if chega else None}")
